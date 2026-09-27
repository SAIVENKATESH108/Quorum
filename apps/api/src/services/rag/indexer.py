"""
Report and Source RAG Indexer.

Guarantees:
- Non-destructive: Original user report content and sources are NEVER overwritten or altered.
- Safe redaction: Runs scrub_text to produce a sanitized representation for indexing and retrieval.
- Exact dimensionality: Vectors verified against 1536 dimensions before persistence.
- Deterministic chunk IDs and content hashes.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.agents.research_paper_engine import scrub_text
from src.db.models import (
    RAGChunk,
    Report,
    ReportSource,
)
from src.services.rag.embeddings import EmbeddingProvider, get_default_embedding_provider

logger = logging.getLogger(__name__)


def compute_content_hash(text: str) -> str:
    """Deterministic SHA256 hash of content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ReportIndexer:
    """Extracts, sanitizes, embeds, and persists chunks for a completed report."""

    def __init__(self, embedding_provider: Optional[EmbeddingProvider] = None):
        self.embedding_provider = embedding_provider or get_default_embedding_provider()

    async def index_report(
        self,
        report_id: uuid.UUID,
        session: AsyncSession,
        reindex: bool = False,
    ) -> int:
        """
        Indexes all sections and linked sources for a given report into rag_chunks.
        Returns the total number of indexed chunks.
        """
        # 1. Check if already indexed
        if not reindex:
            existing_count_stmt = (
                select(RAGChunk.id)
                .where(RAGChunk.report_id == report_id)
                .limit(1)
            )
            existing = (await session.execute(existing_count_stmt)).scalars().first()
            if existing:
                logger.info(f"[ReportIndexer] Report {report_id} already has indexed chunks. Skipping.")
                # Count existing
                stmt = select(RAGChunk).where(RAGChunk.report_id == report_id)
                res = await session.execute(stmt)
                return len(res.scalars().all())

        # 2. Fetch report with sections and sources
        stmt = (
            select(Report)
            .where(Report.id == report_id)
            .options(
                selectinload(Report.sections),
                selectinload(Report.report_sources).selectinload(ReportSource.source),
            )
        )
        report_res = await session.execute(stmt)
        report = report_res.scalars().first()
        if not report:
            raise ValueError(f"Report {report_id} not found.")

        # If re-indexing, remove old chunks first
        if reindex:
            from sqlalchemy import delete
            await session.execute(delete(RAGChunk).where(RAGChunk.report_id == report_id))
            await session.flush()

        chunks_to_create: List[Dict[str, Any]] = []

        # 3. Chunk Report Sections
        for sec in report.sections:
            raw_content = sec.content or ""
            if not raw_content.strip():
                continue

            # Non-destructive sensitive text scan
            scrub_res = scrub_text(raw_content)
            sanitized_content = scrub_res["sanitized"]
            findings = scrub_res["findings"]
            redaction_applied = len(findings) > 0
            redaction_categories = list(set(f["type"] for f in findings)) if redaction_applied else None

            # Split large sections into paragraph-aware chunks
            paragraphs = [p.strip() for p in sanitized_content.split("\n\n") if p.strip()]
            if not paragraphs:
                paragraphs = [sanitized_content.strip()]

            current_chunk = ""
            sub_idx = 0
            for p in paragraphs:
                if len(current_chunk) + len(p) > 1200 and current_chunk:
                    chunk_text = current_chunk.strip()
                    c_hash = compute_content_hash(chunk_text)
                    chunk_id = f"chk_sec_{sec.id.hex[:10]}_{sub_idx}"
                    chunks_to_create.append({
                        "chunk_id": chunk_id,
                        "project_id": report.project_id,
                        "report_id": report.id,
                        "report_section_id": sec.id,
                        "source_id": None,
                        "document_type": "report_section",
                        "source_type": "report",
                        "access_level": "user_provided",
                        "source_title": sec.heading or "Report Section",
                        "source_url": None,
                        "heading_hierarchy": f"Report > {sec.heading}",
                        "page_or_line_range": f"Section order {sec.order_index}",
                        "content": chunk_text,
                        "content_hash": c_hash,
                        "redaction_applied": redaction_applied,
                        "redaction_categories": redaction_categories,
                    })
                    sub_idx += 1
                    current_chunk = p + "\n\n"
                else:
                    current_chunk += p + "\n\n"

            if current_chunk.strip():
                chunk_text = current_chunk.strip()
                c_hash = compute_content_hash(chunk_text)
                chunk_id = f"chk_sec_{sec.id.hex[:10]}_{sub_idx}"
                chunks_to_create.append({
                    "chunk_id": chunk_id,
                    "project_id": report.project_id,
                    "report_id": report.id,
                    "report_section_id": sec.id,
                    "source_id": None,
                    "document_type": "report_section",
                    "source_type": "report",
                    "access_level": "user_provided",
                    "source_title": sec.heading or "Report Section",
                    "source_url": None,
                    "heading_hierarchy": f"Report > {sec.heading}",
                    "page_or_line_range": f"Section order {sec.order_index}",
                    "content": chunk_text,
                    "content_hash": c_hash,
                    "redaction_applied": redaction_applied,
                    "redaction_categories": redaction_categories,
                })

        # 4. Chunk Linked Sources
        for rs in report.report_sources:
            src = rs.source
            if not src:
                continue

            src_title = src.title or src.url
            source_content = f"Source Title: {src_title}\nURL: {src.url}"
            scrub_res = scrub_text(source_content)
            sanitized_content = scrub_res["sanitized"]
            findings = scrub_res["findings"]
            redaction_applied = len(findings) > 0
            redaction_categories = list(set(f["type"] for f in findings)) if redaction_applied else None
            c_hash = compute_content_hash(sanitized_content)

            chunk_id = f"chk_src_{src.id.hex[:10]}_0"
            chunks_to_create.append({
                "chunk_id": chunk_id,
                "project_id": report.project_id,
                "report_id": report.id,
                "report_section_id": rs.cited_in_section_id,
                "source_id": src.id,
                "document_type": "source_reference",
                "source_type": "academic_or_web",
                "access_level": "metadata_only",
                "source_title": src_title,
                "source_url": src.url,
                "heading_hierarchy": f"Report Sources > {src_title}",
                "page_or_line_range": None,
                "content": sanitized_content,
                "content_hash": c_hash,
                "redaction_applied": redaction_applied,
                "redaction_categories": redaction_categories,
            })

        if not chunks_to_create:
            logger.warning(f"[ReportIndexer] No content found to index for report {report_id}.")
            return 0

        # 5. Generate verified 1536-dimensional embeddings
        texts = [c["content"] for c in chunks_to_create]
        logger.info(f"[ReportIndexer] Generating embeddings for {len(texts)} chunks via {self.embedding_provider.provider_name}...")
        embeddings = await self.embedding_provider.embed_documents(texts)

        # 6. Persist to rag_chunks
        for item, emb in zip(chunks_to_create, embeddings):
            # Verify exact length
            if len(emb) != self.embedding_provider.expected_dimensions:
                raise ValueError(
                    f"Vector length {len(emb)} != {self.embedding_provider.expected_dimensions} before persistence."
                )

            chunk_row = RAGChunk(
                chunk_id=item["chunk_id"],
                project_id=item["project_id"],
                report_id=item["report_id"],
                report_section_id=item["report_section_id"],
                source_id=item["source_id"],
                document_type=item["document_type"],
                source_type=item["source_type"],
                access_level=item["access_level"],
                source_title=item["source_title"],
                source_url=item["source_url"],
                heading_hierarchy=item["heading_hierarchy"],
                page_or_line_range=item["page_or_line_range"],
                content=item["content"],
                content_hash=item["content_hash"],
                redaction_applied=item["redaction_applied"],
                redaction_categories=item["redaction_categories"],
                embedding=emb,
                embedding_provider=self.embedding_provider.provider_name,
                embedding_model=self.embedding_provider.model_name,
                embedding_dimension=self.embedding_provider.expected_dimensions,
                chunking_strategy="paragraph_and_heading_aware",
                chunking_version="v1",
            )
            session.add(chunk_row)

        await session.flush()
        logger.info(f"[ReportIndexer] Successfully indexed {len(chunks_to_create)} chunks for report {report_id}.")
        return len(chunks_to_create)
