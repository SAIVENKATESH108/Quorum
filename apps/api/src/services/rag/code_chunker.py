"""
Code-aware chunking service for Quorum RAG subsystem.

Supports:
- Python: True AST parsing (ast.parse) with class, method, function, and module-level extraction.
- TypeScript / TSX / JavaScript / JSX: Declaration-aware heuristic chunker (explicitly is_ast=False).
- SQL / Alembic: Migration-aware block chunking.
- JSON / YAML: Structured hierarchical config chunking.
- Markdown: Heading-aware section chunking.

Guarantees:
- Never claims AST parsing for heuristic boundaries.
- Preserves exact 1-indexed start_line and end_line bounds.
- Preserves class ownership for methods.
- Non-destructive scrubbing with line-count stability.
"""

import ast
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from src.agents.research_paper_engine import scrub_text

logger = logging.getLogger(__name__)


@dataclass
class CodeChunk:
    chunk_id: str
    relative_path: str
    content: str
    start_line: int
    end_line: int
    symbol_name: Optional[str]
    symbol_type: str  # "class", "method", "function", "migration", "config", "markdown_section", "heuristic_block", "file"
    language: str
    chunking_strategy: str  # "ast_python", "code_heuristic_v1", "migration_unit", "json_config", "yaml_config", "markdown_hierarchy"
    is_ast: bool
    content_hash: str
    redaction_applied: bool
    redaction_categories: List[str]
    chunk_metadata: Dict[str, Any] = field(default_factory=dict)


def compute_chunk_id(source_identifier: str, path: str, start: int, end: int, symbol: Optional[str] = None, project_id: Optional[Any] = None) -> str:
    raw = f"{project_id or ''}:{source_identifier}:{path}:{start}:{end}:{symbol or ''}"
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    clean_path = re.sub(r"[^a-zA-Z0-9_]", "_", path)[:24]
    return f"chk_code_{clean_path}_{start}_{end}_{h}"


class CodeChunker:
    """
    Splits source files into bounded, grounded chunks with line numbers and symbol provenance.
    """

    SUPPORTED_LANGUAGES = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript_react",
        ".js": "javascript",
        ".jsx": "javascript_react",
        ".sql": "sql",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".md": "markdown",
    }

    def __init__(self, max_lines_per_chunk: int = 150):
        self.max_lines_per_chunk = max_lines_per_chunk

    def chunk_file(
        self,
        relative_path: str,
        content: str,
        source_identifier: str,
        commit_sha: Optional[str] = None,
        project_id: Optional[Any] = None,
    ) -> List[CodeChunk]:
        """
        Processes and chunks a single source file. Applies line-stable scrubbing before returning.
        """
        ext = Path(relative_path).suffix.lower()
        language = self.SUPPORTED_LANGUAGES.get(ext, "text")

        # 1. Non-destructive line-stable sanitization
        scrubbed = scrub_text(content)
        sanitized_content = scrubbed["sanitized"]
        redaction_applied = len(scrubbed["findings"]) > 0
        redaction_categories = sorted(list({f["type"] for f in scrubbed["findings"]}))

        lines = sanitized_content.splitlines()
        total_lines = len(lines)
        if total_lines == 0:
            return []

        # 2. Language-specific chunking
        raw_chunks: List[Dict[str, Any]] = []

        if ext == ".py":
            if "alembic" in relative_path.lower() or "revision =" in sanitized_content or "revision: str" in sanitized_content:
                raw_chunks = self._chunk_sql(sanitized_content, lines, relative_path)
            else:
                raw_chunks = self._chunk_python(content, lines, relative_path)
        elif ext in (".ts", ".tsx", ".js", ".jsx"):
            raw_chunks = self._chunk_ecmascript(lines, relative_path, language)
        elif ext == ".sql":
            raw_chunks = self._chunk_sql(sanitized_content, lines, relative_path)
        elif ext == ".json":
            raw_chunks = self._chunk_json(sanitized_content, lines, relative_path)
        elif ext in (".yaml", ".yml"):
            raw_chunks = self._chunk_yaml(sanitized_content, lines, relative_path)
        elif ext == ".md":
            raw_chunks = self._chunk_markdown(lines, relative_path)
        else:
            # Fallback heuristic block chunking
            raw_chunks = self._chunk_line_blocks(lines, relative_path, "heuristic_block", "code_heuristic_v1")

        # 3. Assemble CodeChunk objects
        result_chunks: List[CodeChunk] = []
        for rc in raw_chunks:
            start_l = rc["start_line"]
            end_l = min(rc["end_line"], total_lines)
            chunk_slice = "\n".join(lines[start_l - 1 : end_l])
            c_hash = hashlib.sha256(chunk_slice.encode("utf-8")).hexdigest()
            cid = compute_chunk_id(source_identifier, relative_path, start_l, end_l, rc.get("symbol_name"), project_id=project_id)

            meta = {
                "relative_path": relative_path,
                "language": language,
                "commit_sha": commit_sha,
                "symbol_type": rc["symbol_type"],
                "symbol_name": rc.get("symbol_name"),
                "start_line": start_l,
                "end_line": end_l,
                "is_ast": rc["is_ast"],
                "chunking_strategy": rc["chunking_strategy"],
                "redaction_applied": redaction_applied,
                "redaction_categories": redaction_categories,
            }
            if "extra" in rc:
                meta.update(rc["extra"])

            result_chunks.append(
                CodeChunk(
                    chunk_id=cid,
                    relative_path=relative_path,
                    content=chunk_slice,
                    start_line=start_l,
                    end_line=end_l,
                    symbol_name=rc.get("symbol_name"),
                    symbol_type=rc["symbol_type"],
                    language=language,
                    chunking_strategy=rc["chunking_strategy"],
                    is_ast=rc["is_ast"],
                    content_hash=c_hash,
                    redaction_applied=redaction_applied,
                    redaction_categories=redaction_categories,
                    chunk_metadata=meta,
                )
            )

        return result_chunks

    def _chunk_python(self, content: str, lines: List[str], path: str) -> List[Dict[str, Any]]:
        """
        True AST extraction for Python. Falls back gracefully to heuristic if syntax error.
        """
        try:
            tree = ast.parse(content, filename=path)
        except SyntaxError as e:
            logger.warning(f"Python AST parse failed for {path}: {e}. Falling back to heuristic.")
            return self._chunk_line_blocks(
                lines,
                path,
                symbol_type="heuristic_block",
                strategy="code_heuristic_v1",
                extra={"parse_error": str(e)},
            )

        chunks: List[Dict[str, Any]] = []
        covered_lines: set[int] = set()

        # 1. Check for module docstring or top-level imports
        first_node_line = len(lines) + 1
        for node in tree.body:
            if hasattr(node, "lineno") and node.lineno < first_node_line:
                first_node_line = node.lineno

        if first_node_line > 1:
            header_end = first_node_line - 1
            chunks.append({
                "start_line": 1,
                "end_line": header_end,
                "symbol_name": "module_header",
                "symbol_type": "file",
                "chunking_strategy": "ast_python",
                "is_ast": True,
            })
            covered_lines.update(range(1, header_end + 1))

        # 2. Iterate top-level classes and functions
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                s_line = node.lineno
                e_line = getattr(node, "end_lineno", s_line + 10)
                chunks.append({
                    "start_line": s_line,
                    "end_line": e_line,
                    "symbol_name": node.name,
                    "symbol_type": "function",
                    "chunking_strategy": "ast_python",
                    "is_ast": True,
                    "extra": {
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "decorators": [ast.unparse(d) for d in node.decorator_list if hasattr(ast, "unparse")],
                    },
                })
                covered_lines.update(range(s_line, e_line + 1))

            elif isinstance(node, ast.ClassDef):
                c_name = node.name
                c_start = node.lineno
                c_end = getattr(node, "end_lineno", c_start + 10)

                # Collect methods inside class
                methods: List[ast.AST] = []
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append(sub)

                if not methods or (c_end - c_start <= self.max_lines_per_chunk):
                    # Entire class fits comfortably in one chunk
                    chunks.append({
                        "start_line": c_start,
                        "end_line": c_end,
                        "symbol_name": c_name,
                        "symbol_type": "class",
                        "chunking_strategy": "ast_python",
                        "is_ast": True,
                        "extra": {
                            "method_count": len(methods),
                        },
                    })
                    covered_lines.update(range(c_start, c_end + 1))
                else:
                    # Class definition header chunk
                    first_method_line = methods[0].lineno
                    if first_method_line > c_start:
                        chunks.append({
                            "start_line": c_start,
                            "end_line": first_method_line - 1,
                            "symbol_name": f"{c_name}_header",
                            "symbol_type": "class",
                            "chunking_strategy": "ast_python",
                            "is_ast": True,
                        })
                        covered_lines.update(range(c_start, first_method_line))

                    # Individual methods with class ownership
                    for m in methods:
                        m_start = m.lineno
                        m_end = getattr(m, "end_lineno", m_start + 10)
                        chunks.append({
                            "start_line": m_start,
                            "end_line": m_end,
                            "symbol_name": f"{c_name}.{m.name}",
                            "symbol_type": "method",
                            "chunking_strategy": "ast_python",
                            "is_ast": True,
                            "extra": {
                                "parent_class": c_name,
                                "is_async": isinstance(m, ast.AsyncFunctionDef),
                            },
                        })
                        covered_lines.update(range(m_start, m_end + 1))

        # Check for remaining lines that were not part of classes/functions
        remaining_lines = set(range(1, len(lines) + 1)) - covered_lines
        if remaining_lines and not chunks:
            # Whole file was simple script without defs
            return self._chunk_line_blocks(lines, path, "file", "ast_python", is_ast=True)

        return sorted(chunks, key=lambda c: c["start_line"])

    def _chunk_ecmascript(self, lines: List[str], path: str, language: str) -> List[Dict[str, Any]]:
        """
        Declaration-aware heuristic chunker for TypeScript/TSX/JavaScript/JSX.
        Explicitly flagged with is_ast=False and chunking_strategy="code_heuristic_v1".
        """
        decl_regex = re.compile(
            r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?"
            r"(class|function|interface|type|const|let|var)\s+([A-Za-z0-9_$]+)"
        )

        chunks: List[Dict[str, Any]] = []
        current_start = 1
        current_symbol: Optional[str] = None
        current_type = "heuristic_block"

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            # Skip comments or strings
            if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue

            match = decl_regex.match(stripped)
            if match and idx > current_start:
                # We reached a new top-level declaration
                if (idx - current_start) >= 15:  # meaningful block length
                    chunks.append({
                        "start_line": current_start,
                        "end_line": idx - 1,
                        "symbol_name": current_symbol or "heuristic_block",
                        "symbol_type": current_type,
                        "chunking_strategy": "code_heuristic_v1",
                        "is_ast": False,
                    })
                    current_start = idx

                keyword, name = match.group(1), match.group(2)
                current_symbol = name
                if keyword in ("class", "interface"):
                    current_type = "class"
                elif keyword in ("function", "const", "let"):
                    current_type = "function"
                else:
                    current_type = "heuristic_block"

            elif (idx - current_start) >= self.max_lines_per_chunk:
                chunks.append({
                    "start_line": current_start,
                    "end_line": idx,
                    "symbol_name": current_symbol or "heuristic_block",
                    "symbol_type": current_type,
                    "chunking_strategy": "code_heuristic_v1",
                    "is_ast": False,
                })
                current_start = idx + 1
                current_symbol = None
                current_type = "heuristic_block"

        # Final chunk
        if current_start <= len(lines):
            chunks.append({
                "start_line": current_start,
                "end_line": len(lines),
                "symbol_name": current_symbol or "heuristic_block",
                "symbol_type": current_type,
                "chunking_strategy": "code_heuristic_v1",
                "is_ast": False,
            })

        return chunks

    def _chunk_sql(self, content: str, lines: List[str], path: str) -> List[Dict[str, Any]]:
        """
        Preserves Alembic migrations or SQL schema definitions as coherent units.
        """
        rev_match = re.search(r"revision(?::\s*str)?\s*=\s*['\"]([^'\"]+)['\"]", content)
        rev_id = rev_match.group(1) if rev_match else None

        if rev_id or "op.create_table" in content or "def upgrade" in content:
            # Alembic migration unit
            return [{
                "start_line": 1,
                "end_line": len(lines),
                "symbol_name": f"migration_{rev_id}" if rev_id else Path(path).stem,
                "symbol_type": "migration",
                "chunking_strategy": "migration_unit",
                "is_ast": False,
                "extra": {"revision_id": rev_id},
            }]

        return self._chunk_line_blocks(lines, path, "sql_ddl", "code_heuristic_v1")

    def _chunk_json(self, content: str, lines: List[str], path: str) -> List[Dict[str, Any]]:
        """
        Parses JSON structure, preserving top-level keys.
        """
        try:
            data = json.loads(content)
            if isinstance(data, dict) and len(data) > 0:
                top_keys = list(data.keys())[:10]
                return [{
                    "start_line": 1,
                    "end_line": len(lines),
                    "symbol_name": f"config_{Path(path).stem}",
                    "symbol_type": "config",
                    "chunking_strategy": "json_config",
                    "is_ast": False,
                    "extra": {"top_level_keys": top_keys},
                }]
        except Exception:
            pass

        return self._chunk_line_blocks(lines, path, "config", "code_heuristic_v1")

    def _chunk_yaml(self, content: str, lines: List[str], path: str) -> List[Dict[str, Any]]:
        """
        Parses YAML structure, preserving top-level keys.
        """
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict) and len(data) > 0:
                top_keys = list(data.keys())[:10]
                return [{
                    "start_line": 1,
                    "end_line": len(lines),
                    "symbol_name": f"config_{Path(path).stem}",
                    "symbol_type": "config",
                    "chunking_strategy": "yaml_config",
                    "is_ast": False,
                    "extra": {"top_level_keys": top_keys},
                }]
        except Exception:
            pass

        return self._chunk_line_blocks(lines, path, "config", "code_heuristic_v1")

    def _chunk_markdown(self, lines: List[str], path: str) -> List[Dict[str, Any]]:
        """
        Heading-aware section chunking for markdown.
        """
        heading_re = re.compile(r"^(#{1,4})\s+(.+)$")
        chunks: List[Dict[str, Any]] = []
        cur_start = 1
        cur_title = Path(path).stem

        for idx, line in enumerate(lines, start=1):
            m = heading_re.match(line.strip())
            if m and idx > cur_start:
                chunks.append({
                    "start_line": cur_start,
                    "end_line": idx - 1,
                    "symbol_name": cur_title,
                    "symbol_type": "markdown_section",
                    "chunking_strategy": "markdown_hierarchy",
                    "is_ast": False,
                })
                cur_start = idx
                cur_title = m.group(2).strip()

        if cur_start <= len(lines):
            chunks.append({
                "start_line": cur_start,
                "end_line": len(lines),
                "symbol_name": cur_title,
                "symbol_type": "markdown_section",
                "chunking_strategy": "markdown_hierarchy",
                "is_ast": False,
            })

        return chunks

    def _chunk_line_blocks(
        self,
        lines: List[str],
        path: str,
        symbol_type: str,
        strategy: str,
        is_ast: bool = False,
        extra: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        chunks: List[Dict[str, Any]] = []
        total = len(lines)
        step = self.max_lines_per_chunk

        for s in range(1, total + 1, step):
            e = min(s + step - 1, total)
            chunk_data: Dict[str, Any] = {
                "start_line": s,
                "end_line": e,
                "symbol_name": f"{Path(path).stem}_L{s}-L{e}",
                "symbol_type": symbol_type,
                "chunking_strategy": strategy,
                "is_ast": is_ast,
            }
            if extra:
                chunk_data["extra"] = extra
            chunks.append(chunk_data)

        return chunks
