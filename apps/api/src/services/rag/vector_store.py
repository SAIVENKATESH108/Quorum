"""
Vector Store Provider Abstraction and PgVector Implementation.

Enforces:
- Hard workspace/project/report boundary isolation in the SQL query itself.
- Strict vector dimensionality check prior to querying.
- PostgreSQL + pgvector as the production source of truth.
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import RAGChunk

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """Standardized retrieved chunk representation for RAG context and citation mapping."""
    id: uuid.UUID
    chunk_id: str
    project_id: uuid.UUID
    report_id: Optional[uuid.UUID]
    report_section_id: Optional[uuid.UUID]
    source_id: Optional[uuid.UUID]
    document_type: str
    source_type: str
    access_level: str
    source_title: Optional[str]
    source_url: Optional[str]
    heading_hierarchy: Optional[str]
    page_or_line_range: Optional[str]
    content: str
    redaction_applied: bool
    redaction_categories: Optional[List[str]]
    score: float  # Cosine similarity score (higher = closer, 0.0 to 1.0)
    distance: float  # Cosine distance (lower = closer)
    repo_identifier: Optional[str] = None
    commit_sha: Optional[str] = None
    relative_path: Optional[str] = None
    symbol_name: Optional[str] = None
    symbol_type: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    is_ast: bool = False
    chunk_metadata: Optional[Dict[str, Any]] = None


class VectorStoreProvider(ABC):
    """Abstract interface for Vector Store backends."""

    provider_name: str
    expected_dimensions: int = 1536

    @abstractmethod
    async def similarity_search(
        self,
        session: AsyncSession,
        query_vector: List[float],
        project_id: uuid.UUID,
        report_id: Optional[uuid.UUID] = None,
        source_type: Optional[str] = None,
        repo_identifier: Optional[str] = None,
        commit_sha: Optional[str] = None,
        access_level: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.0,
    ) -> List[RetrievedChunk]:
        """Perform semantic similarity search strictly filtered at the SQL query level."""
        ...

    @abstractmethod
    async def delete_chunks_by_report(
        self, session: AsyncSession, report_id: uuid.UUID
    ) -> int:
        """Delete all chunks associated with a specific report."""
        ...


class PgVectorStoreProvider(VectorStoreProvider):
    """Production VectorStoreProvider backed by PostgreSQL and pgvector."""

    provider_name = "PgVector"

    def __init__(self, expected_dimensions: int = 1536):
        self.expected_dimensions = expected_dimensions

    async def similarity_search(
        self,
        session: AsyncSession,
        query_vector: List[float],
        project_id: uuid.UUID,
        report_id: Optional[uuid.UUID] = None,
        source_type: Optional[str] = None,
        repo_identifier: Optional[str] = None,
        commit_sha: Optional[str] = None,
        access_level: Optional[str] = None,
        exclude_code_and_local: bool = False,
        top_k: int = 5,
        min_similarity: float = 0.0,
    ) -> List[RetrievedChunk]:
        """
        Execute cosine similarity search on rag_chunks table.
        Strictly enforces database-level authorization via project_id, report_id,
        and first-class repository boundaries before vector ranking.
        """
        if len(query_vector) != self.expected_dimensions:
            raise ValueError(
                f"Query vector dimensionality mismatch: expected {self.expected_dimensions}, got {len(query_vector)}"
            )

        # Build query enforcing project isolation
        distance_expr = RAGChunk.embedding.cosine_distance(query_vector)
        stmt = (
            select(RAGChunk, distance_expr.label("distance"))
            .where(RAGChunk.project_id == project_id)
        )

        if report_id is not None:
            stmt = stmt.where(RAGChunk.report_id == report_id)

        if source_type is not None:
            stmt = stmt.where(RAGChunk.source_type == source_type)

        if repo_identifier is not None:
            stmt = stmt.where(RAGChunk.repo_identifier == repo_identifier)

        if commit_sha is not None:
            stmt = stmt.where(RAGChunk.commit_sha == commit_sha)

        if access_level is not None:
            stmt = stmt.where(RAGChunk.access_level == access_level)

        if exclude_code_and_local:
            stmt = stmt.where(
                RAGChunk.repo_identifier.is_(None),
                RAGChunk.source_type != "local_folder",
                RAGChunk.source_type != "github_repo",
                RAGChunk.document_type != "local_folder",
                RAGChunk.document_type != "github_repo",
            )

        stmt = stmt.order_by("distance").limit(top_k)

        result = await session.execute(stmt)
        rows = result.all()

        retrieved: List[RetrievedChunk] = []
        for chunk, dist in rows:
            dist_val = float(dist) if dist is not None else 1.0
            sim_score = max(0.0, 1.0 - dist_val)
            if sim_score < min_similarity:
                continue

            retrieved.append(
                RetrievedChunk(
                    id=chunk.id,
                    chunk_id=chunk.chunk_id,
                    project_id=chunk.project_id,
                    report_id=chunk.report_id,
                    report_section_id=chunk.report_section_id,
                    source_id=chunk.source_id,
                    document_type=chunk.document_type,
                    source_type=chunk.source_type,
                    access_level=chunk.access_level,
                    source_title=chunk.source_title,
                    source_url=chunk.source_url,
                    heading_hierarchy=chunk.heading_hierarchy,
                    page_or_line_range=chunk.page_or_line_range,
                    content=chunk.content,
                    redaction_applied=chunk.redaction_applied,
                    redaction_categories=chunk.redaction_categories,
                    score=sim_score,
                    distance=dist_val,
                    repo_identifier=chunk.repo_identifier,
                    commit_sha=chunk.commit_sha,
                    relative_path=chunk.relative_path,
                    symbol_name=chunk.symbol_name,
                    symbol_type=chunk.symbol_type,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    is_ast=chunk.is_ast,
                    chunk_metadata=chunk.chunk_metadata,
                )
            )

        return retrieved

    async def delete_chunks_by_report(
        self, session: AsyncSession, report_id: uuid.UUID
    ) -> int:
        stmt = delete(RAGChunk).where(RAGChunk.report_id == report_id)
        res = await session.execute(stmt)
        await session.flush()
        return res.rowcount or 0
