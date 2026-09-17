import pytest
from unittest.mock import MagicMock
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


@pytest.mark.asyncio
async def test_multiple_distinct_report_pdfs():
    """Verify downloading PDFs for two distinct report IDs produces distinct, report-specific PDFs."""
    import uuid
    from httpx import AsyncClient, ASGITransport
    from src.main import app

    report_id_1 = uuid.UUID("59d45060-3a06-46bd-8491-1dd4269e5d55")
    report_id_2 = uuid.UUID("2b267e3c-71f7-413a-ae3f-eff7aeb0e743")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Download Report 1 PDF
        res1 = await client.get(f"/api/reports/{report_id_1}/pdf")
        assert res1.status_code == 200
        assert res1.headers["content-type"] == "application/pdf"
        assert res1.content.startswith(b"%PDF-")
        cd1 = res1.headers.get("content-disposition", "")
        assert "Quorum_System_Documentation.pdf" not in cd1
        assert str(report_id_1)[:8] in cd1

        # Download Report 2 PDF
        res2 = await client.get(f"/api/reports/{report_id_2}/pdf")
        assert res2.status_code == 200
        assert res2.headers["content-type"] == "application/pdf"
        assert res2.content.startswith(b"%PDF-")
        cd2 = res2.headers.get("content-disposition", "")
        assert "Quorum_System_Documentation.pdf" not in cd2
        assert str(report_id_2)[:8] in cd2

        # Verify the two generated PDFs are distinct and non-empty
        assert res1.content != res2.content
        assert len(res1.content) > 1000
        assert len(res2.content) > 1000
