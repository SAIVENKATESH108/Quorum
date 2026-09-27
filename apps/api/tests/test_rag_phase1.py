"""
Phase 1 RAG Engine Test Suite.

Covers:
A. Happy-path retrieval on a real indexed report with valid citations.
B. Unanswerable questions leading to safe deterministic abstention.
C. Citation tampering detection and withholding of unsupported output.
D. Database-level authorization isolation between projects.
E. Sensitive text scrubbing before indexing (no raw secrets in storage or context).
F. Strict 1536-dimension validation on embeddings.
"""

import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.providers import AIProvider
from src.db.models import (
    Project,
    RAGChunk,
    Report,
    ReportSection,
    ReportSource,
    ReportStatus,
    Source,
    User,
)
from src.db.session import async_session_maker
from src.services.rag.chat_engine import (
    ABSTENTION_TEXT,
    SwarmChatEngine,
)
from src.services.rag.embeddings import (
    EmbeddingDimensionError,
    EmbeddingProvider,
)
from src.services.rag.indexer import ReportIndexer
from src.services.rag.vector_store import PgVectorStoreProvider


# ---------------------------------------------------------------------------
# Test Embedding Provider & Mock Helpers
# ---------------------------------------------------------------------------

class Deterministic1536EmbeddingProvider(EmbeddingProvider):
    """Deterministic embedding provider generating valid 1536-dim vectors for tests."""
    provider_name = "DeterministicTest"
    model_name = "test-1536"

    def __init__(self, expected_dimensions: int = 1536):
        super().__init__(expected_dimensions=expected_dimensions)

    def _make_vector(self, text: str) -> list[float]:
        import hashlib
        h = hashlib.sha256(text.encode("utf-8")).digest()
        vec = [float(b % 10) / 10.0 for b in h]
        full_vec = (vec * (1536 // len(vec) + 1))[:1536]
        return self._verify_vector_dimensions(full_vec)

    async def embed_query(self, text: str) -> list[float]:
        return self._make_vector(text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._make_vector(t) for t in texts]

    async def health_check(self) -> bool:
        return True


class MockLLMProvider(AIProvider):
    """Controlled mock LLM provider for deterministic test outputs."""
    name = "MockLLM"

    def __init__(self, canned_response: str | None = None, canned_responses: list[str] | None = None):
        super().__init__()
        self.canned_response = canned_response
        self.canned_responses = list(canned_responses) if canned_responses else []
        self.call_count = 0
        self.received_prompts: list[str] = []

    async def _call_api(self, prompt: str, system: str | None = None) -> str:
        self.call_count += 1
        self.received_prompts.append(prompt)
        if self.canned_responses:
            idx = min(self.call_count - 1, len(self.canned_responses) - 1)
            return self.canned_responses[idx]
        return self.canned_response or "Mock completion"


# ---------------------------------------------------------------------------
# Test Fixtures & Setup Helpers
# ---------------------------------------------------------------------------

async def create_test_project_and_report(session: AsyncSession, title: str):
    unique_id = uuid.uuid4().hex[:8]
    user = User(
        id=uuid.uuid4(),
        email=f"tester_{unique_id}@quorum.ai",
        name="Test User",
    )
    session.add(user)
    await session.flush()

    project = Project(
        id=uuid.uuid4(),
        user_id=user.id,
        title=f"Project {title} {unique_id}",
    )
    session.add(project)
    await session.flush()

    report = Report(
        id=uuid.uuid4(),
        project_id=project.id,
        query=f"Research on {title}",
        status=ReportStatus.COMPLETE,
    )
    session.add(report)
    await session.flush()

    # Section 1
    sec1 = ReportSection(
        id=uuid.uuid4(),
        report_id=report.id,
        heading="Consensus Protocol Architecture",
        content="The network implements Byzantine Fault Tolerance using quorum slices. Proof-of-Authority guarantees 2-second block finality under asynchronous network delays.",
        order_index=1,
    )
    # Section 2
    sec2 = ReportSection(
        id=uuid.uuid4(),
        report_id=report.id,
        heading="Cryptographic Security",
        content="Post-quantum lattice signatures based on ML-DSA-87 protect validator messages against Shor algorithm decryption.",
        order_index=2,
    )
    session.add_all([sec1, sec2])
    await session.flush()

    # Source
    source = Source(
        id=uuid.uuid4(),
        title="NIST FIPS 204: Module-Lattice-Based Digital Signature Standard",
        url=f"https://csrc.nist.gov/pubs/fips/204/final?v={unique_id}",
    )
    session.add(source)
    await session.flush()

    report_source = ReportSource(
        report_id=report.id,
        source_id=source.id,
        cited_in_section_id=sec2.id,
    )
    session.add(report_source)
    await session.flush()

    return user, project, report, [sec1, sec2], source


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dimension_validation():
    """Requirement 1 & 2: Vectors must be strictly verified against 1536 dimensions."""
    provider = Deterministic1536EmbeddingProvider(expected_dimensions=1536)

    # Valid 1536 vector succeeds
    vec = await provider.embed_query("test text")
    assert len(vec) == 1536

    # Incompatible length raises EmbeddingDimensionError
    with pytest.raises(EmbeddingDimensionError):
        provider._verify_vector_dimensions([0.1] * 768)

    with pytest.raises(EmbeddingDimensionError):
        provider._verify_vector_dimensions([0.1] * 384)


@pytest.mark.asyncio
async def test_sensitive_text_scrubbing_during_indexing():
    """Requirement 3 & E: Sensitive tokens (credentials/secrets) must be redacted before indexing."""
    embed_provider = Deterministic1536EmbeddingProvider()
    indexer = ReportIndexer(embedding_provider=embed_provider)

    async with async_session_maker() as session:
        user, project, report, secs, src = await create_test_project_and_report(
            session, "Secret Handling"
        )

        # Inject sensitive tokens into section 1
        secs[0].content = (
            "The cluster master connects using postgresql://mock_user:mock_scrub_pass@127.0.0.1:5432/mock_production_db "
            "with master API key sk-mock-scrub-target-0123456789 and root token bearer=jwt_secret_token_val."
        )
        await session.flush()

        # Index report
        indexed_count = await indexer.index_report(report.id, session, reindex=True)
        assert indexed_count > 0
        await session.flush()

        # Query indexed chunks
        res = await session.execute(
            select(RAGChunk).where(RAGChunk.report_id == report.id, RAGChunk.report_section_id == secs[0].id)
        )
        chunks = res.scalars().all()
        assert len(chunks) > 0

        for chk in chunks:
            # Sensitive tokens must NEVER appear in chunk content or metadata
            assert "mock_scrub_pass" not in chk.content
            assert "sk-mock-scrub-target-0123456789" not in chk.content
            assert "jwt_secret_token_val" not in chk.content
            # Redaction markers must be recorded
            assert chk.redaction_applied is True
            assert chk.redaction_categories is not None
            assert len(chk.redaction_categories) > 0
            assert "[REDACTED:" in chk.content

        # Verify original report section was NOT overwritten destructively
        res_sec = await session.execute(select(ReportSection).where(ReportSection.id == secs[0].id))
        original_sec = res_sec.scalars().first()
        assert "Sup3rS3cr3t" in original_sec.content  # Original source remains unchanged


@pytest.mark.asyncio
async def test_authorization_isolation():
    """Requirement 4 & D: Query in Project A must NEVER retrieve chunks belonging to Project B."""
    embed_provider = Deterministic1536EmbeddingProvider()
    vector_store = PgVectorStoreProvider()
    indexer = ReportIndexer(embedding_provider=embed_provider)

    async with async_session_maker() as session:
        # Create Project A
        user_a, project_a, report_a, _, _ = await create_test_project_and_report(
            session, "Alpha Architecture"
        )
        await indexer.index_report(report_a.id, session, reindex=True)

        # Create Project B with identical topic text
        user_b, project_b, report_b, _, _ = await create_test_project_and_report(
            session, "Beta Architecture"
        )
        await indexer.index_report(report_b.id, session, reindex=True)
        await session.flush()

        query_vec = await embed_provider.embed_query("Consensus Protocol Architecture")

        # Search strictly scoped to Project A
        chunks_a = await vector_store.similarity_search(
            session=session,
            query_vector=query_vec,
            project_id=project_a.id,
            report_id=report_a.id,
            top_k=10,
        )
        assert len(chunks_a) > 0
        for c in chunks_a:
            assert c.project_id == project_a.id
            assert c.project_id != project_b.id
            assert c.report_id == report_a.id

        # Search strictly scoped to Project B
        chunks_b = await vector_store.similarity_search(
            session=session,
            query_vector=query_vec,
            project_id=project_b.id,
            report_id=report_b.id,
            top_k=10,
        )
        assert len(chunks_b) > 0
        for c in chunks_b:
            assert c.project_id == project_b.id
            assert c.project_id != project_a.id
            assert c.report_id == report_b.id


@pytest.mark.asyncio
async def test_citation_tampering_and_withholding():
    """Requirement 7 & C: Non-retrieved chunk IDs must be caught and withheld or regenerated."""
    embed_provider = Deterministic1536EmbeddingProvider()
    vector_store = PgVectorStoreProvider()

    async with async_session_maker() as session:
        user, project, report, secs, src = await create_test_project_and_report(
            session, "Tampering Test"
        )

        # LLM that hallucinate a fake chunk ID on both initial call and corrective call
        mock_llm = MockLLMProvider(
            canned_responses=[
                "Network finality is achieved in 2s [chk_fake_hallucinated_id].",
                "Still citing nonexistent source [chk_fake_hallucinated_id_2].",
            ]
        )

        chat_engine = SwarmChatEngine(
            embedding_provider=embed_provider,
            vector_store=vector_store,
            llm_provider=mock_llm,
        )

        result = await chat_engine.chat(
            session=session,
            project_id=project.id,
            report_id=report.id,
            user_query="What is the finality time?",
        )

        # The engine must detect tampering, attempt corrective regeneration, and if it fails, abstain safely
        assert mock_llm.call_count == 2  # Proves corrective regeneration was attempted
        assert result.validation_passed is False
        assert result.abstained is True
        assert result.reply == ABSTENTION_TEXT
        assert result.citations == []


@pytest.mark.asyncio
async def test_unanswerable_question_abstention():
    """Requirement 6 & B: Questions outside report scope must abstain rather than hallucinate."""
    embed_provider = Deterministic1536EmbeddingProvider()
    vector_store = PgVectorStoreProvider()

    async with async_session_maker() as session:
        user, project, report, secs, src = await create_test_project_and_report(
            session, "Abstention Test"
        )

        # LLM correctly answering with standard abstention
        mock_llm = MockLLMProvider(canned_response=f"Evidence is missing. {ABSTENTION_TEXT}")

        chat_engine = SwarmChatEngine(
            embedding_provider=embed_provider,
            vector_store=vector_store,
            llm_provider=mock_llm,
        )

        # Question 1: Completely unrelated topic
        res1 = await chat_engine.chat(
            session=session,
            project_id=project.id,
            report_id=report.id,
            user_query="What is the optimal harvest temperature for organic arabica coffee beans?",
        )
        assert res1.abstained is True
        assert ABSTENTION_TEXT in res1.reply
        assert res1.citations == []

        # Question 2: Another out-of-scope question
        res2 = await chat_engine.chat(
            session=session,
            project_id=project.id,
            report_id=report.id,
            user_query="What are the FAA requirements for commercial passenger drone certification?",
        )
        assert res2.abstained is True
        assert ABSTENTION_TEXT in res2.reply
        assert res2.citations == []


@pytest.mark.asyncio
async def test_happy_path_retrieval_and_citations():
    """Requirement 8 & A: 5 answerable questions retrieve real chunks and produce valid citations."""
    embed_provider = Deterministic1536EmbeddingProvider()
    vector_store = PgVectorStoreProvider()

    async with async_session_maker() as session:
        user, project, report, secs, src = await create_test_project_and_report(
            session, "BFT and Lattice Security"
        )

        indexer = ReportIndexer(embedding_provider=embed_provider)
        await indexer.index_report(report.id, session, reindex=True)
        await session.flush()

        # Query all indexed chunk IDs for this report
        chunks_res = await session.execute(
            select(RAGChunk).where(RAGChunk.report_id == report.id)
        )
        report_chunks = chunks_res.scalars().all()
        sec1_chunk = next(c for c in report_chunks if c.report_section_id == secs[0].id)
        sec2_chunk = next(c for c in report_chunks if c.report_section_id == secs[1].id)

        # 5 distinct questions
        test_cases = [
            (
                "What consensus protocol is used?",
                f"The architecture uses Byzantine Fault Tolerance with quorum slices [{sec1_chunk.chunk_id}].",
                sec1_chunk.chunk_id,
            ),
            (
                "What is the block finality guarantee?",
                f"Proof-of-Authority guarantees 2-second block finality under delays [{sec1_chunk.chunk_id}].",
                sec1_chunk.chunk_id,
            ),
            (
                "What post-quantum signatures protect messages?",
                f"Lattice signatures based on ML-DSA-87 protect messages [{sec2_chunk.chunk_id}].",
                sec2_chunk.chunk_id,
            ),
            (
                "Which standard defines the signature scheme?",
                f"ML-DSA-87 is specified in NIST FIPS 204 [{sec2_chunk.chunk_id}].",
                sec2_chunk.chunk_id,
            ),
            (
                "How does the system defend against Shor's algorithm?",
                f"Post-quantum lattice signatures are implemented for quantum resistance [{sec2_chunk.chunk_id}].",
                sec2_chunk.chunk_id,
            ),
        ]

        for query, model_reply, expected_chunk_id in test_cases:
            mock_llm = MockLLMProvider(canned_response=model_reply)
            chat_engine = SwarmChatEngine(
                embedding_provider=embed_provider,
                vector_store=vector_store,
                llm_provider=mock_llm,
            )

            res = await chat_engine.chat(
                session=session,
                project_id=project.id,
                report_id=report.id,
                user_query=query,
                min_similarity=0.0,
            )

            assert res.validation_passed is True
            assert res.abstained is False
            assert len(res.citations) > 0
            assert res.citations[0].chunk_id == expected_chunk_id
            assert "[1]" in res.reply  # User-friendly bracket citation replaced
            assert expected_chunk_id not in res.reply  # Internal chunk ID converted to display marker


@pytest.mark.asyncio
async def test_index_lifecycle_and_cascade_deletion():
    """Requirement 5: Lifecycle re-indexing, deduplication, content updates, and cascade deletion."""
    embed_provider = Deterministic1536EmbeddingProvider()
    indexer = ReportIndexer(embedding_provider=embed_provider)

    async with async_session_maker() as session:
        user, project, report, secs, src = await create_test_project_and_report(
            session, "Lifecycle Test"
        )

        # 1. First index pass
        cnt1 = await indexer.index_report(report.id, session, reindex=False)
        assert cnt1 > 0
        await session.flush()

        # 2. Second index pass without reindex=True: must NOT duplicate chunks
        cnt2 = await indexer.index_report(report.id, session, reindex=False)
        assert cnt2 == cnt1

        res_initial = await session.execute(
            select(RAGChunk).where(RAGChunk.report_id == report.id)
        )
        assert len(res_initial.scalars().all()) == cnt1

        # 3. Update section content and reindex=True: must replace cleanly
        secs[0].content = "Updated content for consensus protocol with Raft leader election."
        await session.flush()

        cnt3 = await indexer.index_report(report.id, session, reindex=True)
        assert cnt3 > 0
        await session.flush()

        res_updated = await session.execute(
            select(RAGChunk).where(RAGChunk.report_id == report.id, RAGChunk.report_section_id == secs[0].id)
        )
        updated_chunks = res_updated.scalars().all()
        assert any("Raft leader election" in c.content for c in updated_chunks)
        assert not any("quorum slices" in c.content for c in updated_chunks)

        # 4. Cascade deletion: deleting the report must delete all its chunks
        from sqlalchemy import delete
        await session.execute(delete(Report).where(Report.id == report.id))
        await session.flush()

        res_deleted = await session.execute(
            select(RAGChunk).where(RAGChunk.report_id == report.id)
        )
        assert len(res_deleted.scalars().all()) == 0

