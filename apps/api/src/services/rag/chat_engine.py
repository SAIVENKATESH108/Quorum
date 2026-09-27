"""
Swarm Chat Engine — Evidence-Bound Retrieval QA with Deterministic Citation Validation.

Guarantees:
- Answers strictly bounded by retrieved, authorized chunks.
- Deterministic citation verification: every citation must map to an actual retrieved chunk.
- No silent citation deletion: invalid citations trigger corrective regeneration or safe abstention.
- Strict abstention when evidence is absent or insufficient.
- Preserves project, report, and codebase authorization boundaries.
- Distinguishes GitHub repository citations (pinned SHA blob links) from Local-Folder citations (pure text references, never fake links).
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.providers import AIProvider, GeminiProvider, get_default_provider
from src.services.rag.embeddings import EmbeddingProvider, get_default_embedding_provider
from src.services.rag.indexer import ReportIndexer
from src.services.rag.vector_store import (
    PgVectorStoreProvider,
    RetrievedChunk,
    VectorStoreProvider,
)

logger = logging.getLogger(__name__)

ABSTENTION_REPORT = (
    "I could not determine this from the indexed report, files, and verified sources available to this chat."
)
ABSTENTION_CODEBASE = (
    "I could not determine this from the indexed repository or local-folder files available to this chat."
)
ABSTENTION_TEXT = ABSTENTION_REPORT


@dataclass
class ChatCitation:
    index: int
    title: str
    url: str
    chunk_id: str
    access_level: str
    score: float
    source_type: str = "report"
    is_ast: bool = False
    is_heuristic: bool = False
    line_range: Optional[str] = None


@dataclass
class SwarmChatResult:
    reply: str
    citations: List[ChatCitation]
    retrieved_count: int
    validation_passed: bool
    abstained: bool
    diagnostics: Dict[str, Any]


class SwarmChatEngine:
    """Orchestrates grounded retrieval QA with deterministic citation validation."""

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        vector_store: Optional[VectorStoreProvider] = None,
        llm_provider: Optional[AIProvider] = None,
    ):
        self.embedding_provider = embedding_provider or get_default_embedding_provider()
        self.vector_store = vector_store or PgVectorStoreProvider()
        self.llm_provider = llm_provider or GeminiProvider(model="gemini-3.1-flash-lite")
        self.indexer = ReportIndexer(embedding_provider=self.embedding_provider)

    @staticmethod
    def classify_question(query: str) -> str:
        q_lower = query.lower()
        if any(k in q_lower for k in ("migration", "schema", "table", "alembic", "sql", "ddl")):
            return "migration_schema"
        if any(k in q_lower for k in ("config", "yaml", "json", "settings", "env")):
            return "configuration"
        if any(k in q_lower for k in ("function", "class", "method", "file", "symbol", "code", "implementation", "endpoint", "line")):
            return "codebase"
        return "general"

    async def chat(
        self,
        session: AsyncSession,
        project_id: uuid.UUID,
        user_query: str,
        report_id: Optional[uuid.UUID] = None,
        source_type: Optional[str] = None,
        repo_identifier: Optional[str] = None,
        commit_sha: Optional[str] = None,
        access_level: Optional[str] = None,
        exclude_code_and_local: bool = False,
        top_k: int = 5,
        min_similarity: float = 0.35,
    ) -> SwarmChatResult:
        """
        Execute grounded chat turn across report chunks or repository/local-folder chunks.
        Strictly enforces database-level authorization via SQL query.
        """
        # 1. If report_id provided and source_type is report, ensure report index exists
        if report_id is not None and (source_type is None or source_type == "report"):
            await self.indexer.index_report(report_id, session, reindex=False)

        # 2. Classify question
        question_category = self.classify_question(user_query)
        is_code_query = question_category in ("codebase", "migration_schema", "configuration") or (
            source_type in ("github_repo", "local_folder")
        )
        abstention_msg = ABSTENTION_CODEBASE if is_code_query else ABSTENTION_REPORT

        # 3. Embed user query with verified 1536-dim provider
        query_vector = await self.embedding_provider.embed_query(user_query)

        # 4. Retrieve chunks with database-enforced isolation
        retrieved_chunks = await self.vector_store.similarity_search(
            session=session,
            query_vector=query_vector,
            project_id=project_id,
            report_id=report_id,
            source_type=source_type,
            repo_identifier=repo_identifier,
            commit_sha=commit_sha,
            access_level=access_level,
            exclude_code_and_local=exclude_code_and_local,
            top_k=top_k,
            min_similarity=min_similarity,
        )

        diagnostics = {
            "query": user_query,
            "question_category": question_category,
            "source_type": source_type,
            "repo_identifier": repo_identifier,
            "retrieved_chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "title": c.source_title,
                    "relative_path": c.relative_path,
                    "symbol_name": c.symbol_name,
                    "is_ast": c.is_ast,
                    "heuristic_label": "heuristic code block" if (is_code_query and not c.is_ast) else "ast symbol",
                    "score": round(c.score, 4),
                    "access_level": c.access_level,
                    "redacted": c.redaction_applied,
                }
                for c in retrieved_chunks
            ],
            "top_similarity": round(retrieved_chunks[0].score, 4) if retrieved_chunks else 0.0,
        }

        # 5. Evidence sufficiency check
        if not retrieved_chunks:
            logger.info(f"[SwarmChatEngine] No chunks met similarity threshold ({min_similarity}). Abstaining.")
            return SwarmChatResult(
                reply=abstention_msg,
                citations=[],
                retrieved_count=0,
                validation_passed=True,
                abstained=True,
                diagnostics=diagnostics,
            )

        # 6. Assemble grounded prompt
        valid_chunk_map: Dict[str, RetrievedChunk] = {c.chunk_id: c for c in retrieved_chunks}
        prompt, system_prompt = self._build_grounded_prompt(user_query, retrieved_chunks, is_code_query, abstention_msg)

        # 7. Generate answer
        raw_reply = await self.llm_provider.complete(prompt, system=system_prompt)

        # If LLM itself stated it could not determine, preserve abstention
        if abstention_msg.lower() in raw_reply.lower() or "could not determine" in raw_reply.lower():
            return SwarmChatResult(
                reply=abstention_msg,
                citations=[],
                retrieved_count=len(retrieved_chunks),
                validation_passed=True,
                abstained=True,
                diagnostics=diagnostics,
            )

        # 8. Deterministic Citation Validation
        cited_ids = self._extract_cited_chunk_ids(raw_reply)
        invalid_ids = [cid for cid in cited_ids if cid not in valid_chunk_map]

        if invalid_ids:
            logger.warning(
                f"[SwarmChatEngine] LLM cited invalid/unretrieved chunk IDs: {invalid_ids}. "
                f"Attempting single corrective regeneration."
            )
            corrective_prompt = (
                f"{prompt}\n\n"
                f"CORRECTION REQUIRED:\n"
                f"Your previous draft cited invalid chunk IDs that were NOT in the provided excerpts: {invalid_ids}.\n"
                f"You must cite ONLY the provided chunk IDs ({list(valid_chunk_map.keys())}).\n"
                f"If the provided context does not support the answer, reply exactly:\n"
                f"\"{abstention_msg}\""
            )
            raw_reply = await self.llm_provider.complete(corrective_prompt, system=system_prompt)
            cited_ids = self._extract_cited_chunk_ids(raw_reply)
            invalid_ids = [cid for cid in cited_ids if cid not in valid_chunk_map]

            if invalid_ids:
                logger.error(
                    f"[SwarmChatEngine] Corrective regeneration failed; still cited invalid IDs: {invalid_ids}. "
                    f"Withholding answer and safely abstaining."
                )
                return SwarmChatResult(
                    reply=abstention_msg,
                    citations=[],
                    retrieved_count=len(retrieved_chunks),
                    validation_passed=False,
                    abstained=True,
                    diagnostics={**diagnostics, "validation_error": f"Invalid citations: {invalid_ids}"},
                )

        # 9. Transform valid chunk citations to display citations
        final_reply, citations = self._format_display_citations(raw_reply, cited_ids, valid_chunk_map)

        return SwarmChatResult(
            reply=final_reply,
            citations=citations,
            retrieved_count=len(retrieved_chunks),
            validation_passed=True,
            abstained=False,
            diagnostics=diagnostics,
        )

    def _build_grounded_prompt(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        is_code_query: bool,
        abstention_msg: str,
    ) -> tuple[str, str]:
        if is_code_query:
            system_prompt = (
                "You are Quorum Swarm, a code-grounded engineering assistant.\n"
                "You must answer questions strictly and solely from the provided codebase excerpts below.\n"
                "CODEBASE CITATION RULES:\n"
                "- Every factual statement about code, functions, classes, tables, or files must cite its supporting excerpt [chk_...].\n"
                "- You may ONLY cite chunk IDs explicitly present in CONTEXT EXCERPTS.\n"
                "- Never invent file names, function names, classes, methods, endpoints, migrations, or line ranges.\n"
                "- Do not infer a function's implementation from its name.\n"
                "- Distinguish direct code evidence from interpretation.\n"
                "- If the excerpts do not contain sufficient evidence to answer the question, you MUST answer exactly:\n"
                f'"{abstention_msg}"'
            )
        else:
            system_prompt = (
                "You are Quorum Swarm, an evidence-grounded research assistant.\n"
                "You must answer questions strictly and solely from the provided context excerpts below.\n"
                "CITATION RULES:\n"
                "- Every factual statement must cite its supporting excerpt using the exact bracketed chunk ID [chk_...].\n"
                "- You may ONLY cite chunk IDs explicitly present in CONTEXT EXCERPTS.\n"
                "- Never invent chunk IDs, filenames, URLs, DOIs, authors, or statistics.\n"
                "- If the excerpts do not contain sufficient evidence, answer exactly:\n"
                f'"{abstention_msg}"'
            )

        context_lines = []
        for c in chunks:
            redacted_tag = " (sanitized)" if c.redaction_applied else ""
            ast_tag = " [AST verified]" if c.is_ast else " [Heuristic block]"
            path_info = f"File: {c.relative_path or c.source_title}\n" if c.relative_path else f"Source: {c.source_title or 'Document'}\n"
            symbol_info = f"Symbol: {c.symbol_name} ({c.symbol_type}){ast_tag}\n" if c.symbol_name else ""
            line_info = f"Lines: {c.page_or_line_range}\n" if c.page_or_line_range else ""

            context_lines.append(
                f"[{c.chunk_id}]\n"
                f"{path_info}"
                f"{symbol_info}"
                f"{line_info}"
                f"Source Type: {c.source_type}{redacted_tag}\n"
                f"Content:\n{c.content}\n"
            )

        context_str = "\n---\n".join(context_lines)

        user_prompt = (
            f"CONTEXT EXCERPTS:\n{context_str}\n\n"
            f"USER QUESTION: {query}\n\n"
            f"Provide a direct, factual answer citing chunk IDs [chk_...] for every material claim. "
            f"If the context does not answer the question, state that evidence is insufficient."
        )

        return user_prompt, system_prompt

    def _extract_cited_chunk_ids(self, text: str) -> List[str]:
        """Extracts unique cited chunk IDs in appearance order."""
        matches = re.findall(r"\[(chk_[a-zA-Z0-9_]+)\]", text)
        seen = set()
        ordered = []
        for m in matches:
            if m not in seen:
                seen.add(m)
                ordered.append(m)
        return ordered

    def _format_display_citations(
        self,
        raw_text: str,
        cited_ids: List[str],
        valid_chunk_map: Dict[str, RetrievedChunk],
    ) -> tuple[str, List[ChatCitation]]:
        citations: List[ChatCitation] = []
        formatted_text = raw_text

        for idx, cid in enumerate(cited_ids, start=1):
            chunk = valid_chunk_map[cid]

            # Construct safe title and url
            if chunk.source_type == "github_repo":
                # Pinned commit SHA blob URL
                display_url = chunk.source_url or ""
                title = f"{chunk.relative_path}:{chunk.page_or_line_range}" if chunk.relative_path else (chunk.source_title or "Repository File")
            elif chunk.source_type == "local_folder":
                # Local folder: pure text reference, NO hyperlink
                display_url = ""
                title = f"{chunk.relative_path}:{chunk.page_or_line_range}" if chunk.relative_path else (chunk.source_title or "Local File")
            else:
                display_url = chunk.source_url or (
                    f"#section-{chunk.report_section_id}" if chunk.report_section_id else "#"
                )
                title = chunk.source_title or (
                    chunk.heading_hierarchy.replace("Report > ", "")
                    if chunk.heading_hierarchy
                    else "Report Finding"
                )

            citations.append(
                ChatCitation(
                    index=idx,
                    title=title,
                    url=display_url,
                    chunk_id=cid,
                    access_level=chunk.access_level,
                    score=round(chunk.score, 4),
                    source_type=chunk.source_type,
                    is_ast=chunk.is_ast,
                    is_heuristic=not chunk.is_ast if chunk.source_type in ("github_repo", "local_folder") else False,
                    line_range=chunk.page_or_line_range,
                )
            )

            # Replace [chk_...] with [idx]
            formatted_text = formatted_text.replace(f"[{cid}]", f"[{idx}]")

        return formatted_text, citations
