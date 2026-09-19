import uuid

import pytest
from unittest.mock import MagicMock

from src.core.redis import close_redis_client
from src.db.models import (
    Project,
    Report,
    ReportSection,
    ReportSource,
    ReportStatus,
    Source,
    User,
)
from src.db.session import async_session_maker
from src.services.pdf_generator import (
    build_quorum_system_documentation_pdf,
    compile_research_report_to_pdf,
)


@pytest.mark.asyncio
async def test_build_quorum_system_documentation_pdf():
    """Verify that the 9-page system documentation PDF compiles cleanly with proper PDF header."""
    pdf_bytes = build_quorum_system_documentation_pdf()
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 20000  # Multi-page PDF
    assert pdf_bytes.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_compile_research_report_to_pdf():
    """Verify dynamic compilation of a custom research report into a publication-grade PDF."""
    sec1 = MagicMock()
    sec1.heading = "1. Introduction & Executive Overview"
    sec1.content = "Autonomous multi-agent research systems require deterministic verification."
    sec1.order_index = 0

    sec2 = MagicMock()
    sec2.heading = "2. Architectural Design & DAG Scheduling"
    sec2.content = "The topological scheduler manages asynchronous ReAct tasks across distributed workers."
    sec2.order_index = 1

    src1 = MagicMock()
    src1.title = "Formal Verification of Multi-Agent Systems"
    src1.url = "https://doi.org/10.1145/123456"
    src1.doi = "10.1145/123456"

    pdf_bytes = compile_research_report_to_pdf(
        report_title="Autonomous Verification Swarms in Distributed Systems",
        sections=[sec1, sec2],
        sources=[src1],
        lead_author="Quorum Research Swarm",
        source_type="github",
        source_ref="https://github.com/quorum/quorum",
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF-")


async def create_persisted_report(
    query: str,
    heading: str,
    content: str,
    source_title: str,
    source_url: str,
) -> Report:
    """Create a real (pipeline-shaped) report with one section and one cited source."""
    async with async_session_maker() as session:
        user = User(
            id=uuid.uuid4(),
            email=f"pdf_tester_{uuid.uuid4().hex[:8]}@quorum.ai",
            name="PDF Fixture User",
        )
        project = Project(
            id=uuid.uuid4(),
            user_id=user.id,
            title=f"PDF Fixture Project {uuid.uuid4().hex[:6]}",
        )
        report = Report(
            id=uuid.uuid4(),
            project_id=project.id,
            query=query,
            status=ReportStatus.COMPLETE,
        )
        source = Source(id=uuid.uuid4(), url=source_url, title=source_title)
        section = ReportSection(
            id=uuid.uuid4(),
            report_id=report.id,
            heading=heading,
            content=content,
            order_index=1,
        )
        link = ReportSource(
            report_id=report.id,
            source_id=source.id,
            cited_in_section_id=section.id,
        )

        session.add_all([user, project, report, source, section, link])
        await session.commit()
        return report


@pytest.mark.asyncio
async def test_multiple_distinct_report_pdfs():
    """Verify downloading PDFs for two distinct reports produces distinct, report-specific PDFs."""
    from httpx import AsyncClient, ASGITransport
    from src.main import app

    await close_redis_client()
    try:
        report_1 = await create_persisted_report(
            query="Fault-Tolerant Consensus in Asynchronous Networks",
            heading="1. Consensus Safety Under Partial Synchrony",
            content="Quorum-based replication preserves safety while tolerating f < n/3 Byzantine faults.",
            source_title="Practical Byzantine Fault Tolerance and Proactive Recovery",
            source_url="https://doi.org/10.1145/571637.571640",
        )
        report_2 = await create_persisted_report(
            query="Post-Quantum Migration Bounds for Long-Lived Archives",
            heading="1. Lattice-Based Key Encapsulation Overhead",
            content="Module-lattice KEMs trade larger ciphertexts for resistance to Shor's algorithm.",
            source_title="Module-Lattice-Based Key-Encapsulation Mechanism Standard",
            source_url="https://doi.org/10.6028/NIST.FIPS.203",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res1 = await client.get(f"/api/reports/{report_1.id}/pdf")
            assert res1.status_code == 200
            assert res1.headers["content-type"] == "application/pdf"
            assert res1.content.startswith(b"%PDF-")
            cd1 = res1.headers.get("content-disposition", "")
            assert "Quorum_System_Documentation.pdf" not in cd1
            assert str(report_1.id)[:8] in cd1

            res2 = await client.get(f"/api/reports/{report_2.id}/pdf")
            assert res2.status_code == 200
            assert res2.headers["content-type"] == "application/pdf"
            assert res2.content.startswith(b"%PDF-")
            cd2 = res2.headers.get("content-disposition", "")
            assert "Quorum_System_Documentation.pdf" not in cd2
            assert str(report_2.id)[:8] in cd2

            # Verify the two generated PDFs are distinct and non-empty
            assert res1.content != res2.content
            assert len(res1.content) > 1000
            assert len(res2.content) > 1000
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_pdf_of_unknown_report_returns_404():
    """Reports that the pipeline never produced must not be fabricated on download."""
    from httpx import AsyncClient, ASGITransport
    from src.main import app

    await close_redis_client()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get(f"/api/reports/{uuid.uuid4()}/pdf")
            assert res.status_code == 404
            assert res.json()["detail"] == "Report not found"
    finally:
        await close_redis_client()
