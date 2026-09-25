"""
Unit tests for Quorum Research Studio Engine, Providers, and Validation Rules.

Verifies:
1. PII and secret detection & scrubbing (ensures zero secret leaks in external payloads).
2. Provider capability registry, normalization, DOI validation, and deduplication.
3. Citation validation rules (grounding check, orphan detection, reference list integrity).
4. IEEE-style PDF compilation via ReportLab with tables, citations, and appendix.
"""

import os
import uuid

from src.agents.research_paper_engine import (
    scrub_text,
    stage_g_validate_citations,
)
from src.agents.research_providers import (
    ArXivProvider,
    CrossRefProvider,
    OpenAlexProvider,
    SemanticScholarProvider,
    validate_doi,
)
from src.db.models import (
    ClaimEvidenceMapping,
    ResearchEvidence,
)
from src.services.pdf_generator import compile_ieee_research_paper_to_pdf


# ---------------------------------------------------------------------------
# 1. PII / Secret Scrubber Tests
# ---------------------------------------------------------------------------

def test_scrub_text_detects_credentials_and_secrets():
    """Verify scanner flags API keys, DB connection strings, and passwords without leaking values."""
    sensitive_input = (
        "Project config: DATABASE_URL=postgresql://user:secretpass123@db.internal:5432/quorum "
        "and API_KEY=sk-abcdef12345678901234567890 for auth."
    )
    result = scrub_text(sensitive_input)
    assert result["finding_count"] >= 2
    types = [f["type"] for f in result["findings"]]
    assert "database_connection_string" in types or "api_key" in types

    # Ensure sanitized text masks the secret values
    sanitized = result["sanitized"]
    assert "secretpass123" not in sanitized
    assert "sk-abcdef12345678901234567890" not in sanitized
    assert "[REDACTED:" in sanitized


def test_scrub_text_clean_content():
    """Verify scanner reports clean for standard academic and research questions."""
    clean_input = "How does Byzantine fault tolerance operate in distributed ledger protocols?"
    result = scrub_text(clean_input)
    assert result["finding_count"] == 0
    assert len(result["findings"]) == 0
    assert result["sanitized"] == clean_input


# ---------------------------------------------------------------------------
# 2. DOI Validation & Source Normalization
# ---------------------------------------------------------------------------

def test_validate_doi_standards():
    """Verify DOIs conform to standard 10.xxxx syntax and never accept invalid syntaxes."""
    assert validate_doi("10.1145/3290605.3300267") is True
    assert validate_doi("10.1038/s41586-020-2649-2") is True
    assert validate_doi("https://doi.org/10.1109/TSE.2021.3061234") is True
    assert validate_doi("invalid_doi_string") is False
    assert validate_doi("10.abc/xyz") is False
    assert validate_doi("") is False
    assert validate_doi(None) is False


def test_provider_initialization_and_metadata():
    """Verify scholarly providers initialize with appropriate classes and capabilities."""
    arxiv = ArXivProvider()
    assert arxiv.provider_name.lower() == "arxiv"
    assert "search" in arxiv.source_capabilities
    assert arxiv.default_source_class == "preprint"

    crossref = CrossRefProvider()
    assert crossref.provider_name.lower() == "crossref"
    assert crossref.default_source_class == "peer_reviewed"

    openalex = OpenAlexProvider()
    assert openalex.provider_name.lower() == "openalex"

    s2 = SemanticScholarProvider()
    assert "semantic" in s2.provider_name.lower()


# ---------------------------------------------------------------------------
# 3. Citation & Grounding Validation
# ---------------------------------------------------------------------------

def test_citation_validation_detects_hallucinated_citations():
    """Verify validator catches inline citations pointing to unregistered sources."""
    job_id = uuid.uuid4()
    ev1_id = uuid.uuid4()
    ev1 = ResearchEvidence(
        id=ev1_id,
        job_id=job_id,
        provider="arxiv",
        canonical_url="https://arxiv.org/abs/2103.00001",
        title="Consensus Benchmarks",
        source_class="preprint",
        access_level="abstract_only",
        retrieved_excerpt="Consensus achieves 4500 tps under 3-node Byzantine fault tolerance.",
    )

    evidence_rows = [ev1]
    claim_rows = [
        ClaimEvidenceMapping(
            id=uuid.uuid4(),
            job_id=job_id,
            evidence_id=ev1_id,
            claim_id="CLM-001",
            claim_text="Consensus achieves 4500 tps under 3-node fault tolerance.",
            claim_type="quantitative",
            citation_strength="directly_supported",
            requires_review=False,
            inline_citation_marker="[1]",
        )
    ]

    # Paper contains [1] (valid) and [99] (hallucinated / unregistered)
    paper_text = """
# Distributed Consensus Invariants

## Abstract
Recent benchmarks show 4500 tps [1]. An invented study claimed 100,000 tps [99].

## References
[1] Consensus Benchmarks. arXiv:2103.00001
[99] Phantom Author, Invented Journal 2024.
"""

    val_result = stage_g_validate_citations(paper_text, evidence_rows, claim_rows)
    assert val_result["passed"] is False
    assert 99 in val_result["orphaned_citations"]
    assert val_result["sources_available"] == 1


def test_citation_validation_passes_when_fully_grounded():
    """Verify validator passes when all citations map directly to persisted evidence."""
    job_id = uuid.uuid4()
    ev1_id = uuid.uuid4()
    ev1 = ResearchEvidence(
        id=ev1_id,
        job_id=job_id,
        provider="crossref",
        canonical_url="https://doi.org/10.1145/123456",
        title="Formal Verification of Multi-Agent Systems",
        source_class="peer_reviewed",
        access_level="full_text",
        retrieved_excerpt="Model checking confirms absence of livelock in finite-state agent swarms.",
    )

    evidence_rows = [ev1]
    claim_rows = [
        ClaimEvidenceMapping(
            id=uuid.uuid4(),
            job_id=job_id,
            evidence_id=ev1_id,
            claim_id="CLM-001",
            claim_text="Model checking confirms absence of livelock.",
            claim_type="descriptive",
            citation_strength="directly_supported",
            requires_review=False,
            inline_citation_marker="[1]",
        )
    ]

    paper_text = """
# Verification of Multi-Agent Systems

## Abstract
Model checking confirms absence of livelock [1].

## References
[1] Formal Verification of Multi-Agent Systems. https://doi.org/10.1145/123456
"""

    val_result = stage_g_validate_citations(paper_text, evidence_rows, claim_rows)
    assert val_result["passed"] is True
    assert len(val_result["orphaned_citations"]) == 0
    assert val_result["inline_citations_found"] == 1


# ---------------------------------------------------------------------------
# 4. ReportLab IEEE-Style PDF Compilation
# ---------------------------------------------------------------------------

def test_pdf_generation_creates_valid_file(tmp_path):
    """Verify compile_ieee_research_paper_to_pdf creates a non-empty ReportLab PDF."""
    job_id = str(uuid.uuid4())
    ev1_id = uuid.uuid4()
    ev1 = ResearchEvidence(
        id=ev1_id,
        canonical_url="https://arxiv.org/abs/2001.00001",
        title="State Machine Bounds",
        source_class="preprint",
        access_level="abstract_only",
        provider="arxiv",
        retrieved_excerpt="Replication throughput stabilizes at 12k ops/sec.",
    )

    paper_text = """
# Empirical Performance Bounds of State Machines

## Abstract
This paper analyzes throughput bounds in replicated state machines [1].

## I. Introduction
State machine replication guarantees consistency across non-faulty nodes [1].

## II. Methodology
Empirical simulation traces under Byzantine network failure regimes.

## References
[1] State Machine Bounds. arXiv:2001.00001
"""

    claim_matrix = [
        ClaimEvidenceMapping(
            id=uuid.uuid4(),
            evidence_id=ev1_id,
            claim_id="CLM-001",
            claim_text="Replication throughput stabilizes at 12k ops/sec.",
            claim_type="quantitative",
            citation_strength="directly_supported",
            requires_review=False,
            inline_citation_marker="[1]",
        )
    ]

    pdf_path = compile_ieee_research_paper_to_pdf(
        job_id=job_id,
        paper_title="Empirical Performance Bounds of State Machines",
        paper_content=paper_text,
        authors=["Alice Smith", "Bob Jones"],
        paper_type="technical_research_report",
        evidence_rows=[ev1],
        claim_rows=claim_matrix,
        executed_queries=[{"provider": "arxiv", "query": "replicated state machines", "results_count": 1, "success": True}],
        output_dir=str(tmp_path),
    )

    assert pdf_path is not None
    assert os.path.exists(pdf_path)
    file_size = os.path.getsize(pdf_path)
    assert file_size > 1000, f"Generated PDF should be non-empty (size: {file_size} bytes)"
