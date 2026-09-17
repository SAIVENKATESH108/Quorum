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
