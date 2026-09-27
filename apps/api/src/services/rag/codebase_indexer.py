"""
Codebase and Repository Indexer for Quorum RAG Subsystem.

Enforces:
1. GitHub commit pinning BEFORE file fetching (resolved_commit_sha).
2. Honest handling of tree truncation (truncated=True).
3. Structured skip reasons across all filtered files.
4. Mandatory external embedding consent for local folders and private repositories.
5. Exact 1536-dim vector embeddings via GeminiEmbeddingProvider.
6. SQL-level isolation and transactional upsert.
"""

import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote
import uuid

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import RAGChunk
from src.services.github_connector import GitHubConnector
from src.services.rag.code_chunker import CodeChunk, CodeChunker
from src.services.rag.code_policy import IndexingPolicy, IngestionDiagnostics, SkipReason
from src.services.rag.embeddings import EmbeddingProvider, get_default_embedding_provider

logger = logging.getLogger(__name__)


class ConsentRequiredError(Exception):
    """Raised when user consent is missing for external embedding transmission."""
    pass


class CodebaseIndexer:
    """
    Indexes GitHub repositories and local folders into rag_chunks.
    """

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        policy: Optional[IndexingPolicy] = None,
    ):
        self.embedding_provider = embedding_provider or get_default_embedding_provider()
        self.policy = policy or IndexingPolicy()
        self.chunker = CodeChunker()

    async def index_github_repo(
        self,
        project_id: uuid.UUID,
        repo_url: str,
        session: AsyncSession,
        ref: Optional[str] = None,
        github_token: Optional[str] = None,
        user_consent: bool = False,
        is_private: bool = False,
        reindex: bool = False,
    ) -> IngestionDiagnostics:
        """
        Ingests a GitHub repository into rag_chunks.
        Resolves commit SHA FIRST before any file fetching occurs.
        """
        owner, repo = GitHubConnector.parse_repo_url(repo_url)
        repo_identifier = f"{owner}/{repo}"

        diagnostics = IngestionDiagnostics(policy_name=self.policy.policy_name)
        diagnostics.requested_ref = ref or "HEAD"

        # Privacy check for private repositories
        if is_private and not user_consent:
            raise ConsentRequiredError(
                f"External embedding consent is required before indexing private repository '{repo_identifier}'."
            )

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Quorum-Code-RAG/1.0",
        }
        if github_token:
            headers["Authorization"] = f"token {github_token}"

        async with httpx.AsyncClient(headers=headers, timeout=25.0) as client:
            # 1. Fetch metadata
            meta_res = await client.get(f"https://api.github.com/repos/{owner}/{repo}")
            if meta_res.status_code == 404:
                raise ValueError(f"GitHub repository '{owner}/{repo}' not found.")
            meta_res.raise_for_status()
            meta = meta_res.json()
            default_branch = meta.get("default_branch", "main")
            target_ref = ref or default_branch
            diagnostics.requested_ref = target_ref

            # 2. RESOLVE COMMIT SHA FIRST (Immutable revision pinning)
            commit_res = await client.get(f"https://api.github.com/repos/{owner}/{repo}/commits/{target_ref}")
            commit_res.raise_for_status()
            commit_data = commit_res.json()
            resolved_commit_sha = commit_data.get("sha")
            if not resolved_commit_sha:
                raise RuntimeError(f"Could not resolve commit SHA for '{repo_identifier}@{target_ref}'.")
            diagnostics.resolved_commit_sha = resolved_commit_sha

            # 3. Fetch Tree recursively using the resolved commit
            tree_res = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/git/trees/{resolved_commit_sha}?recursive=1"
            )
            tree_res.raise_for_status()
            tree_data = tree_res.json()
            diagnostics.tree_sha = tree_data.get("sha")

            if tree_data.get("truncated", False):
                diagnostics.is_partial = True
                diagnostics.warning = (
                    "GitHub repository tree was truncated by the API. Partial repository coverage only."
                )
                diagnostics.record_skip(SkipReason.TREE_TRUNCATED_OR_NOT_ENUMERATED)

            raw_tree = tree_data.get("tree", [])
            diagnostics.total_discovered_files = len([item for item in raw_tree if item.get("type") == "blob"])

            # 4. Filter files with structured skip reasons
            eligible_files: List[Dict[str, Any]] = []

            for item in raw_tree:
                if item.get("type") != "blob":
                    continue
                path = item.get("path", "")
                size = item.get("size", 0)
                ext = Path(path).suffix.lower()

                # Denied directories (vendor / dependency)
                parts = Path(path).parts
                if any(denied in parts for denied in self.policy.denied_directories):
                    diagnostics.record_skip(SkipReason.DEPENDENCY_OR_VENDOR_DIRECTORY)
                    continue

                # Denied filenames
                if Path(path).name.lower() in self.policy.denied_filenames:
                    diagnostics.record_skip(SkipReason.GENERATED_OR_MINIFIED_FILE)
                    continue

                # Minified files
                if path.endswith(".min.js") or path.endswith(".min.css") or path.endswith(".map"):
                    diagnostics.record_skip(SkipReason.GENERATED_OR_MINIFIED_FILE)
                    continue

                # Binary extensions
                if ext in self.policy.binary_extensions:
                    diagnostics.record_skip(SkipReason.BINARY_OR_NON_TEXT)
                    continue

                # Unsupported extensions
                if ext not in self.policy.allowed_extensions:
                    diagnostics.record_skip(SkipReason.UNSUPPORTED_EXTENSION)
                    continue

                # File size limit
                if size > self.policy.max_file_bytes:
                    diagnostics.record_skip(SkipReason.FILE_TOO_LARGE)
                    continue

                eligible_files.append({"path": path, "size": size, "sha": item.get("sha")})

            # Deterministic sorting (alphabetical)
            eligible_files.sort(key=lambda x: x["path"])

            # 5. Fetch file content using the SAME verified commit SHA
            selected_files: List[Dict[str, Any]] = []
            total_bytes = 0

            for f in eligible_files:
                if len(selected_files) >= self.policy.max_files_count:
                    diagnostics.record_skip(SkipReason.TOTAL_CONTEXT_BUDGET_EXCEEDED)
                    continue
                if (total_bytes + f["size"]) > self.policy.max_total_bytes:
                    diagnostics.record_skip(SkipReason.TOTAL_CONTEXT_BUDGET_EXCEEDED)
                    continue

                try:
                    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{resolved_commit_sha}/{f['path']}"
                    file_res = await client.get(raw_url)
                    if file_res.status_code == 200:
                        content = file_res.text
                        selected_files.append({
                            "path": f["path"],
                            "content": content,
                            "size": len(content),
                        })
                        total_bytes += len(content)
                    else:
                        diagnostics.record_skip(SkipReason.INACCESSIBLE_OR_FETCH_FAILED)
                except Exception as e:
                    logger.warning(f"Failed to fetch {f['path']} at commit {resolved_commit_sha}: {e}")
                    diagnostics.record_skip(SkipReason.INACCESSIBLE_OR_FETCH_FAILED)

            diagnostics.total_indexed_bytes = total_bytes

            # 6. Chunk each file
            all_chunks: List[CodeChunk] = []
            for sf in selected_files:
                f_chunks = self.chunker.chunk_file(
                    relative_path=sf["path"],
                    content=sf["content"],
                    source_identifier=repo_identifier,
                    commit_sha=resolved_commit_sha,
                    project_id=project_id,
                )
                all_chunks.extend(f_chunks)
                diagnostics.indexed_files += 1
                if any(c.redaction_applied for c in f_chunks):
                    diagnostics.total_sanitized_files += 1

            if not all_chunks:
                logger.info(f"No code chunks generated for {repo_identifier}@{resolved_commit_sha}.")
                return diagnostics

            # 7. Embed chunks (Exact 1536-dim assert)
            chunk_texts = [f"Code file: {c.relative_path}\nSymbol: {c.symbol_name or 'block'}\n{c.content}" for c in all_chunks]
            embeddings = await self.embedding_provider.embed_documents(chunk_texts)

            # 8. Transactional persistence
            # Clear existing chunks for same revision if reindex is requested
            if reindex:
                await session.execute(
                    delete(RAGChunk).where(
                        RAGChunk.project_id == project_id,
                        RAGChunk.repo_identifier == repo_identifier,
                        RAGChunk.commit_sha == resolved_commit_sha,
                    )
                )

            for c, emb in zip(all_chunks, embeddings):
                encoded_path = quote(c.relative_path, safe="/")
                # Immutable GitHub blob URL pinned to verified commit SHA
                blob_url = f"https://github.com/{owner}/{repo}/blob/{resolved_commit_sha}/{encoded_path}#L{c.start_line}-L{c.end_line}"
                
                db_chunk = RAGChunk(
                    chunk_id=c.chunk_id,
                    project_id=project_id,
                    report_id=None,
                    report_section_id=None,
                    source_id=None,
                    document_type="code_symbol" if c.symbol_type != "file" else "code_file",
                    source_type="github_repo",
                    access_level="private" if is_private else "public",
                    source_title=f"{c.relative_path}:{c.start_line}-{c.end_line}",
                    source_url=blob_url,
                    heading_hierarchy=c.symbol_name,
                    page_or_line_range=f"L{c.start_line}-L{c.end_line}",
                    content=c.content,
                    content_hash=c.content_hash,
                    redaction_applied=c.redaction_applied,
                    redaction_categories=c.redaction_categories,
                    repo_identifier=repo_identifier,
                    commit_sha=resolved_commit_sha,
                    relative_path=c.relative_path,
                    symbol_name=c.symbol_name,
                    symbol_type=c.symbol_type,
                    start_line=c.start_line,
                    end_line=c.end_line,
                    is_ast=c.is_ast,
                    chunk_metadata=c.chunk_metadata,
                    embedding=emb,
                    embedding_provider=self.embedding_provider.provider_name,
                    embedding_model=self.embedding_provider.model_name,
                    embedding_dimension=self.embedding_provider.expected_dimensions,
                    chunking_strategy=c.chunking_strategy,
                    chunking_version="v2_code",
                )
                session.add(db_chunk)

            await session.commit()
            return diagnostics

    async def index_local_folder(
        self,
        project_id: uuid.UUID,
        folder_name: str,
        file_tree_payload: Dict[str, Any],
        session: AsyncSession,
        user_consent: bool = False,
        reindex: bool = False,
    ) -> IngestionDiagnostics:
        """
        Ingests a client-submitted local folder payload.
        Requires explicit user consent before transmitting any content to external embeddings.
        """
        diagnostics = IngestionDiagnostics(policy_name=self.policy.policy_name)
        diagnostics.requested_ref = "local"

        if not user_consent:
            raise ConsentRequiredError(
                f"External embedding consent is mandatory before transmitting local files from '{folder_name}' to Gemini."
            )

        raw_files = file_tree_payload.get("files", [])
        diagnostics.total_discovered_files = len(raw_files)

        eligible_files: List[Dict[str, Any]] = []
        for f in raw_files:
            path = f.get("path", "")
            size = f.get("size", len(f.get("content", "")))
            ext = Path(path).suffix.lower()

            parts = Path(path).parts
            if any(denied in parts for denied in self.policy.denied_directories):
                diagnostics.record_skip(SkipReason.DEPENDENCY_OR_VENDOR_DIRECTORY)
                continue

            if Path(path).name.lower() in self.policy.denied_filenames:
                diagnostics.record_skip(SkipReason.GENERATED_OR_MINIFIED_FILE)
                continue

            if path.endswith(".min.js") or path.endswith(".min.css") or path.endswith(".map"):
                diagnostics.record_skip(SkipReason.GENERATED_OR_MINIFIED_FILE)
                continue

            if ext in self.policy.binary_extensions:
                diagnostics.record_skip(SkipReason.BINARY_OR_NON_TEXT)
                continue

            if ext not in self.policy.allowed_extensions:
                diagnostics.record_skip(SkipReason.UNSUPPORTED_EXTENSION)
                continue

            if size > self.policy.max_file_bytes:
                diagnostics.record_skip(SkipReason.FILE_TOO_LARGE)
                continue

            content = f.get("content")
            if not content:
                diagnostics.record_skip(SkipReason.INACCESSIBLE_OR_FETCH_FAILED)
                continue

            eligible_files.append({"path": path, "size": size, "content": content})

        eligible_files.sort(key=lambda x: x["path"])

        selected_files: List[Dict[str, Any]] = []
        total_bytes = 0
        for f in eligible_files:
            if len(selected_files) >= self.policy.max_files_count:
                diagnostics.record_skip(SkipReason.TOTAL_CONTEXT_BUDGET_EXCEEDED)
                continue
            if (total_bytes + f["size"]) > self.policy.max_total_bytes:
                diagnostics.record_skip(SkipReason.TOTAL_CONTEXT_BUDGET_EXCEEDED)
                continue

            selected_files.append(f)
            total_bytes += f["size"]

        diagnostics.total_indexed_bytes = total_bytes

        all_chunks: List[CodeChunk] = []
        for sf in selected_files:
            f_chunks = self.chunker.chunk_file(
                relative_path=sf["path"],
                content=sf["content"],
                source_identifier=f"local_{folder_name}",
                commit_sha=None,
                project_id=project_id,
            )
            all_chunks.extend(f_chunks)
            diagnostics.indexed_files += 1
            if any(c.redaction_applied for c in f_chunks):
                diagnostics.total_sanitized_files += 1

        if not all_chunks:
            return diagnostics

        chunk_texts = [f"Local code file: {c.relative_path}\nSymbol: {c.symbol_name or 'block'}\n{c.content}" for c in all_chunks]
        embeddings = await self.embedding_provider.embed_documents(chunk_texts)

        if reindex:
            await session.execute(
                delete(RAGChunk).where(
                    RAGChunk.project_id == project_id,
                    RAGChunk.repo_identifier == folder_name,
                    RAGChunk.source_type == "local_folder",
                )
            )

        for c, emb in zip(all_chunks, embeddings):
            # Local citations are pure virtual paths, NEVER a fake URL or Git SHA
            local_ref = f"{c.relative_path}:L{c.start_line}-L{c.end_line}"
            
            db_chunk = RAGChunk(
                chunk_id=c.chunk_id,
                project_id=project_id,
                report_id=None,
                report_section_id=None,
                source_id=None,
                document_type="code_symbol" if c.symbol_type != "file" else "code_file",
                source_type="local_folder",
                access_level="private",
                source_title=local_ref,
                source_url=None,  # Strictly None for local folders
                heading_hierarchy=c.symbol_name,
                page_or_line_range=f"L{c.start_line}-L{c.end_line}",
                content=c.content,
                content_hash=c.content_hash,
                redaction_applied=c.redaction_applied,
                redaction_categories=c.redaction_categories,
                repo_identifier=folder_name,
                commit_sha=None,
                relative_path=c.relative_path,
                symbol_name=c.symbol_name,
                symbol_type=c.symbol_type,
                start_line=c.start_line,
                end_line=c.end_line,
                is_ast=c.is_ast,
                chunk_metadata=c.chunk_metadata,
                embedding=emb,
                embedding_provider=self.embedding_provider.provider_name,
                embedding_model=self.embedding_provider.model_name,
                embedding_dimension=self.embedding_provider.expected_dimensions,
                chunking_strategy=c.chunking_strategy,
                chunking_version="v2_code",
            )
            session.add(db_chunk)

        await session.commit()
        return diagnostics
