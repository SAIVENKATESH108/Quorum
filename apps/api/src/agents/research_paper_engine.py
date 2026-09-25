"""
Quorum Research Studio — 7-Stage Evidence-First Research Paper Pipeline.

Design principles:
- The LLM is a planner, extractor, synthesiser, and editor — NOT the source of truth.
- The source registry and Claim-Evidence Matrix ARE the source of truth.
- Every claim must map to a persisted evidence block before it is written.
- No stage marks itself complete until its work is durably persisted.
- Failures are explainable (failed_stage + error_message recorded).
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.providers import AIProvider, get_default_provider
from src.agents.research_providers import (
    DEFAULT_PROVIDERS,
    SourceCandidate,
)
from src.db.models import (
    ClaimEvidenceMapping,
    ResearchEvidence,
    ResearchJobStatus,
    ResearchPaperJob,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PII / Secret Scrubber
# ---------------------------------------------------------------------------

# Patterns that strongly indicate sensitive content.
# This list assists — it cannot guarantee detection of all sensitive information.
_SCRUB_PATTERNS = [
    (re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b"), "email_address"),
    (re.compile(r"\b(?:https?://[^\s]+@[^\s]+)\b"), "url_with_credentials"),
    (re.compile(r"(?i)\b(?:password|passwd|secret|token|api[_\-]?key|bearer|access[_\-]?key|private[_\-]?key)\s*[:=]\s*\S+"), "credential"),
    (re.compile(r"(?i)\b(?:sk-[a-zA-Z0-9]{20,}|evo_live_[a-zA-Z0-9]+|ghp_[a-zA-Z0-9]+|npm_[a-zA-Z0-9]+)\b"), "api_key"),
    (re.compile(r"\b(?:postgresql|mysql|mongodb|redis)://[^\s]+\b"), "database_connection_string"),
    (re.compile(r"(?i)\b(?:\d{4}[-\s]?){4}\b"), "potential_card_number"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "ssn_pattern"),
    (re.compile(r"(?i)\blocalhost\b|\b127\.0\.0\.1\b|\b10\.\d+\.\d+\.\d+\b|\b192\.168\.\d+\.\d+\b"), "private_network_address"),
    (re.compile(r"(?i)\b[a-z0-9\-]+\.internal\b|\b[a-z0-9\-]+\.corp\b|\b[a-z0-9\-]+\.local\b"), "internal_hostname"),
]


def scrub_text(text: str) -> Dict[str, Any]:
    """
    Scan text for likely sensitive patterns.

    Returns:
        {
            "findings": [ { "type": str, "excerpt": str (redacted), "start": int, "end": int } ],
            "sanitized": str  — original text with matched ranges replaced by [REDACTED:type]
            "warning": str    — always shown to user
        }

    NOTE: Automated scrubbing assists review but CANNOT guarantee detection of
    all sensitive information. The user must review and confirm before transmitting.
    """
    findings = []
    sanitized = text

    for pattern, label in _SCRUB_PATTERNS:
        for m in pattern.finditer(text):
            findings.append({
                "type": label,
                "excerpt": m.group()[:50] + ("..." if len(m.group()) > 50 else ""),
                "start": m.start(),
                "end": m.end(),
            })

    # Replace from end to start to preserve offsets
    sorted_findings = sorted(findings, key=lambda f: f["start"], reverse=True)
    for f in sorted_findings:
        sanitized = sanitized[: f["start"]] + f"[REDACTED:{f['type']}]" + sanitized[f["end"]:]

    return {
        "findings": findings,
        "sanitized": sanitized,
        "warning": (
            "Automated scrubbing assists review but cannot guarantee detection of all "
            "sensitive information. Review the sanitized content carefully before confirming."
        ),
        "finding_count": len(findings),
    }


# ---------------------------------------------------------------------------
# Research Plan Generator (Stage A)
# ---------------------------------------------------------------------------

async def stage_a_generate_plan(
    job: ResearchPaperJob,
    provider: AIProvider,
) -> Dict[str, Any]:
    """
    Convert the sanitized research question into a bounded research plan.
    Generates sub-questions and retrieval queries.
    Plan is persisted before any external retrieval occurs.
    """
    max_queries_by_depth = {"quick": 3, "standard": 5, "thorough": 8}
    max_q = max_queries_by_depth.get(job.depth, 5)

    system = (
        "You are a rigorous research librarian constructing a scoped, evidence-first "
        "research plan. Output ONLY valid JSON. Do not invent facts. "
        "Your plan defines the search space; actual evidence will be retrieved by external providers."
    )

    prompt = (
        f"Research question: \"{job.sanitized_question or job.research_question}\"\n"
        f"Paper type: {job.paper_type}\n"
        f"Depth: {job.depth}\n"
        f"Keywords: {', '.join(job.domain_keywords or [])}\n"
        f"Date range: {job.date_from or 'any'} to {job.date_to or 'present'}\n"
        f"Preferred source types: {', '.join(job.preferred_source_types or ['peer-reviewed', 'preprint'])}\n\n"
        f"Generate a JSON research plan with:\n"
        f"- 'sub_questions': list of {min(max_q, 4)} focused sub-questions (strings)\n"
        f"- 'search_queries': list of up to {max_q} targeted search queries for academic databases (strings)\n"
        f"- 'scope_note': one sentence describing the evidence boundary\n"
        f"- 'excluded_topics': list of out-of-scope topics\n"
        f"Rules: Do not include invented claims. Do not predict findings. Queries are neutral."
    )

    raw = await provider.complete(prompt, system=system)
    plan = _parse_json_safe(raw, default={
        "sub_questions": [job.sanitized_question or job.research_question],
        "search_queries": [job.sanitized_question or job.research_question],
        "scope_note": f"Evidence-bounded review of: {job.research_question}",
        "excluded_topics": [],
    })
    return plan


# ---------------------------------------------------------------------------
# Source Retrieval (Stage B)
# ---------------------------------------------------------------------------

async def stage_b_retrieve_sources(
    job: ResearchPaperJob,
    research_plan: Dict[str, Any],
    db: AsyncSession,
    on_progress: Optional[Callable[[str], Any]] = None,
) -> tuple[List[SourceCandidate], Dict[str, Any]]:
    """
    Execute search queries across available providers.
    Persists raw provider result counts. Does not invent sources.
    Returns (all_candidates, provider_summary).
    """
    queries = research_plan.get("search_queries", [job.research_question])[:8]
    depth_limits = {"quick": 3, "standard": 5, "thorough": 8}
    per_query_limit = depth_limits.get(job.depth, 5)

    all_candidates: List[SourceCandidate] = []
    providers_attempted = []
    providers_succeeded = []
    providers_failed: Dict[str, str] = {}
    executed_queries = []

    excluded_domains = set(d.lower() for d in (job.excluded_domains or []))
    date_from = job.date_from

    for provider in DEFAULT_PROVIDERS:
        providers_attempted.append(provider.provider_name)
        provider_ok = await provider.health_check()
        if not provider_ok:
            providers_failed[provider.provider_name] = "Health check failed — provider not reachable"
            logger.warning(f"[ResearchStudio] {provider.provider_name} health check failed; skipping")
            continue

        try:
            results_for_provider: List[SourceCandidate] = []
            for query in queries:
                if on_progress:
                    await on_progress(f"Querying {provider.provider_name}: {query[:60]}…")
                result = await provider.search(
                    query,
                    max_results=per_query_limit,
                    date_from=date_from,
                )
                executed_queries.append({
                    "provider": provider.provider_name,
                    "query": query,
                    "success": result.success,
                    "results_returned": len(result.candidates),
                    "executed_at": result.retrieved_at,
                })
                if result.success:
                    results_for_provider.extend(result.candidates)
                else:
                    logger.warning(f"[ResearchStudio] {provider.provider_name} query failed: {result.error}")

            if results_for_provider:
                providers_succeeded.append(provider.provider_name)
                all_candidates.extend(results_for_provider)

        except Exception as exc:
            providers_failed[provider.provider_name] = str(exc)
            logger.error(f"[ResearchStudio] Provider {provider.provider_name} raised: {exc}", exc_info=True)

    provider_summary = {
        "providers_attempted": providers_attempted,
        "providers_succeeded": providers_succeeded,
        "providers_failed": providers_failed,
        "executed_queries": executed_queries,
        "total_raw_candidates": len(all_candidates),
    }
    return all_candidates, provider_summary


# ---------------------------------------------------------------------------
# Source Verification & Deduplication (Stage C)
# ---------------------------------------------------------------------------

def stage_c_verify_and_deduplicate(
    candidates: List[SourceCandidate],
    excluded_domains: List[str],
) -> tuple[List[SourceCandidate], List[SourceCandidate]]:
    """
    Verify URL syntax, deduplicate by canonical identifier (DOI > arXiv ID > URL),
    and exclude candidates from excluded domains.

    Returns (accepted, excluded).
    Does NOT manufacture DOIs or fabricate metadata.
    """
    seen_identifiers: set[str] = set()
    seen_urls: set[str] = set()
    accepted: List[SourceCandidate] = []
    excluded: List[SourceCandidate] = []
    excluded_lower = [d.lower() for d in excluded_domains]

    for candidate in candidates:
        # Validate URL syntax
        url = candidate.canonical_url
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            candidate.exclusion_reason = "Invalid or non-HTTP URL"
            candidate.is_excluded = True
            excluded.append(candidate)
            continue

        # Excluded domain check
        url_lower = url.lower()
        domain_blocked = any(excl in url_lower for excl in excluded_lower)
        if domain_blocked:
            candidate.exclusion_reason = "Domain excluded by user preference"
            candidate.is_excluded = True
            excluded.append(candidate)
            continue

        # Deduplication key: prefer stable identifier over URL
        dedup_key = candidate.identifier or url
        if dedup_key in seen_identifiers:
            candidate.exclusion_reason = "Duplicate of previously accepted source"
            candidate.is_excluded = True
            excluded.append(candidate)
            continue
        if url in seen_urls:
            candidate.exclusion_reason = "Duplicate URL"
            candidate.is_excluded = True
            excluded.append(candidate)
            continue

        seen_identifiers.add(dedup_key)
        seen_urls.add(url)
        accepted.append(candidate)

    return accepted, excluded


# ---------------------------------------------------------------------------
# Evidence Extraction (Stage D)
# ---------------------------------------------------------------------------

async def stage_d_extract_evidence(
    job: ResearchPaperJob,
    accepted: List[SourceCandidate],
    db: AsyncSession,
) -> List[ResearchEvidence]:
    """
    Convert accepted SourceCandidates into persisted ResearchEvidence rows.
    Evidence blocks contain only what was actually retrieved from the provider —
    no LLM-generated abstracts or invented excerpts.
    """
    evidence_rows: List[ResearchEvidence] = []
    sub_questions = (job.research_plan or {}).get("sub_questions", [job.research_question])

    for candidate in accepted:
        # Topic tag assignment: match provider/source class to sub-questions
        topic_tags = _assign_topic_tags(candidate, sub_questions)

        row = ResearchEvidence(
            job_id=job.id,
            provider=candidate.provider,
            source_identifier=candidate.identifier,
            canonical_url=candidate.canonical_url,
            title=candidate.title,
            authors=candidate.authors or [],
            publisher=candidate.publisher,
            publication_date=candidate.publication_date,
            source_class=candidate.source_class,
            access_level=candidate.access_level,
            retrieved_excerpt=candidate.abstract,  # Only use actual retrieved abstract — never invented text
            topic_tags=topic_tags,
            inclusion_reason=candidate.inclusion_reason,
            is_excluded=False,
            retrieval_timestamp=datetime.fromisoformat(candidate.retrieval_timestamp)
            if candidate.retrieval_timestamp
            else datetime.now(timezone.utc),
        )
        db.add(row)
        evidence_rows.append(row)

    await db.flush()  # Assign IDs without committing yet
    return evidence_rows


def _assign_topic_tags(candidate: SourceCandidate, sub_questions: List[str]) -> List[str]:
    """Simple keyword-overlap tag assignment — no LLM, no inference."""
    tags: List[str] = [candidate.source_class]
    title_lower = candidate.title.lower()
    for idx, sq in enumerate(sub_questions[:6]):
        words = [w.lower() for w in sq.split() if len(w) > 4]
        if any(w in title_lower for w in words):
            tags.append(f"sub_q_{idx + 1}")
    return tags


# ---------------------------------------------------------------------------
# Claim-Evidence Matrix Construction + Paper Synthesis (Stages E + F)
# ---------------------------------------------------------------------------

async def stage_ef_synthesize_with_matrix(
    job: ResearchPaperJob,
    evidence_rows: List[ResearchEvidence],
    db: AsyncSession,
    provider: AIProvider,
    on_progress: Optional[Callable[[str], Any]] = None,
) -> tuple[str, List[ClaimEvidenceMapping]]:
    """
    Stage E: Build Claim-Evidence Matrix.
    Stage F: Synthesise paper using ONLY the evidence blocks + matrix.

    The LLM receives the complete evidence registry and is forbidden from
    inventing sources, DOIs, authors, or results not present in evidence.
    """
    if not evidence_rows:
        raise ValueError(
            "Cannot synthesise paper — no evidence blocks available. "
            "All source providers returned no usable results."
        )

    # Build concise evidence registry for the prompt
    ev_lines: List[str] = []
    for idx, ev in enumerate(evidence_rows, 1):
        authors_str = "; ".join(ev.authors or [])[:100] if ev.authors else "Unknown"
        ev_lines.append(
            f"[{idx}] {ev.title}\n"
            f"    Authors: {authors_str}\n"
            f"    Source: {ev.publisher or ev.provider} ({ev.source_class})\n"
            f"    Date: {ev.publication_date or 'unknown'}\n"
            f"    Identifier: {ev.source_identifier or 'N/A'}\n"
            f"    URL: {ev.canonical_url}\n"
            f"    Access level: {ev.access_level}\n"
            f"    Excerpt: {(ev.retrieved_excerpt or '')[:400] or '[abstract unavailable — metadata only]'}\n"
        )

    evidence_registry = "\n".join(ev_lines)
    plan = job.research_plan or {}
    sub_questions_text = "\n".join(f"  {i+1}. {sq}" for i, sq in enumerate(plan.get("sub_questions", [job.research_question])))

    system = (
        "You are a rigorous academic writer who writes ONLY from supplied evidence. "
        "STRICT RULES:\n"
        "1. Write only claims supported by the supplied evidence blocks.\n"
        "2. Cite sources using their exact reference number [N] from the evidence registry.\n"
        "3. Do NOT invent sources, authors, dates, DOIs, titles, datasets, experiments, "
        "results, or URLs not in the evidence registry.\n"
        "4. When evidence conflicts, describe the disagreement and cite both sides.\n"
        "5. When evidence is insufficient, write: 'Evidence is insufficient to determine "
        "this from the retrieved sources.'\n"
        "6. Do NOT claim global novelty, patentability, originality, or publication acceptance.\n"
        "7. Distinguish evidence from interpretation. Use hedged language for interpretations.\n"
        "8. Label every figure or table with its provenance.\n"
        "9. Output the complete paper as structured Markdown.\n"
        "10. After the paper, output a JSON block tagged <CLAIM_MATRIX> containing a JSON "
        "array of objects with keys: claim_id, claim_text, claim_type, evidence_numbers "
        "(list of [N] integers), citation_strength "
        "(directly_supported|partially_supported|contextual_only|unsupported), "
        "requires_review (bool). Close with </CLAIM_MATRIX>."
    )

    prompt = (
        f"Research question: \"{job.sanitized_question or job.research_question}\"\n"
        f"Paper type: {job.paper_type}\n"
        f"Citation format: {job.citation_format}\n"
        f"Authors (leave blank if not provided by user): {', '.join(job.authors or [])}\n\n"
        f"Sub-questions to address:\n{sub_questions_text}\n\n"
        f"EVIDENCE REGISTRY ({len(evidence_rows)} sources):\n"
        f"{'='*60}\n{evidence_registry}\n{'='*60}\n\n"
        f"Write an {job.paper_type.replace('_', ' ')} paper addressing the sub-questions "
        f"using ONLY the evidence above. Include: Abstract, Keywords, Introduction, "
        f"Related Work, Methodology, Findings (cite evidence inline as [N]), "
        f"Discussion, Limitations, Ethics Considerations, Conclusion, References. "
        f"For system papers distinguish: verified facts / external findings / proposed design / assumptions. "
        f"Then output the Claim-Evidence Matrix JSON block as described."
    )

    if on_progress:
        await on_progress(f"LLM synthesis in progress ({len(evidence_rows)} evidence blocks)…")

    raw_paper = await provider.complete(prompt, system=system)

    # Split paper content from claim matrix JSON
    paper_content, claim_matrix_raw = _extract_claim_matrix(raw_paper)

    # Parse claim matrix and create DB rows
    claim_rows: List[ClaimEvidenceMapping] = []
    ev_by_index = {idx: ev for idx, ev in enumerate(evidence_rows, 1)}

    for item in (claim_matrix_raw or []):
        claim_id = str(item.get("claim_id", f"C{len(claim_rows)+1:03d}"))
        claim_text = str(item.get("claim_text", ""))[:2000]
        if not claim_text:
            continue
        ev_nums = item.get("evidence_numbers") or []
        strength = item.get("citation_strength", "unsupported")
        requires_review = bool(item.get("requires_review", strength == "unsupported"))

        # Link to first matching evidence block
        first_ev_id = None
        if ev_nums:
            first_idx = ev_nums[0] if isinstance(ev_nums[0], int) else None
            if first_idx and first_idx in ev_by_index:
                first_ev_id = ev_by_index[first_idx].id

        row = ClaimEvidenceMapping(
            job_id=job.id,
            evidence_id=first_ev_id,
            claim_id=claim_id,
            claim_text=claim_text,
            claim_type=str(item.get("claim_type", "descriptive")),
            citation_strength=strength,
            requires_review=requires_review,
        )
        db.add(row)
        claim_rows.append(row)

    await db.flush()
    return paper_content, claim_rows


# ---------------------------------------------------------------------------
# Citation Validation (Stage G)
# ---------------------------------------------------------------------------

def stage_g_validate_citations(
    paper_content: str,
    evidence_rows: List[ResearchEvidence],
    claim_rows: List[ClaimEvidenceMapping],
) -> Dict[str, Any]:
    """
    Deterministic validation of citations before marking artifact as ready.
    Returns a detailed validation report — never silently strips citations.
    """
    n_sources = len(evidence_rows)
    valid_citation_numbers = set(range(1, n_sources + 1))

    # Find all inline [N] citations in paper
    inline_citations = re.findall(r"\[(\d+)\]", paper_content)
    inline_numbers = [int(n) for n in inline_citations]

    orphaned = [n for n in inline_numbers if n not in valid_citation_numbers]
    valid_inline = [n for n in inline_numbers if n in valid_citation_numbers]

    # Unsupported claims
    unsupported_claims = [
        {"claim_id": c.claim_id, "claim_text": c.claim_text[:150]}
        for c in claim_rows
        if c.citation_strength == "unsupported"
    ]
    flagged_claims = [
        {"claim_id": c.claim_id, "reason": "requires_review"}
        for c in claim_rows
        if c.requires_review
    ]

    # Access level summary
    access_summary: Dict[str, int] = {}
    for ev in evidence_rows:
        access_summary[ev.access_level] = access_summary.get(ev.access_level, 0) + 1

    total_claims = len(claim_rows)
    supported_claims = sum(
        1 for c in claim_rows
        if c.citation_strength in ("directly_supported", "partially_supported")
    )
    coverage_pct = round((supported_claims / total_claims * 100) if total_claims else 0.0, 1)

    passed = (
        len(orphaned) == 0
        and coverage_pct >= 50.0
        and len(unsupported_claims) == 0
    )

    return {
        "passed": passed,
        "inline_citations_found": len(set(valid_inline)),
        "orphaned_citations": orphaned,
        "sources_cited": len(set(valid_inline)),
        "sources_available": n_sources,
        "total_claims": total_claims,
        "supported_claims": supported_claims,
        "unsupported_claims": unsupported_claims,
        "flagged_claims": flagged_claims,
        "evidence_coverage_pct": coverage_pct,
        "access_level_summary": access_summary,
        "validation_notes": (
            [] if passed else [
                *(
                    [f"Orphaned citations detected: {orphaned}. These reference numbers exceed the evidence registry."]
                    if orphaned else []
                ),
                *(
                    [f"Evidence coverage is {coverage_pct}% — below the 50% threshold."]
                    if coverage_pct < 50.0 else []
                ),
                *(
                    [f"{len(unsupported_claims)} unsupported claims present."]
                    if unsupported_claims else []
                ),
            ]
        ),
    }


# ---------------------------------------------------------------------------
# Full Pipeline Orchestrator
# ---------------------------------------------------------------------------

class ResearchPaperEngine:
    """
    Orchestrates the 7-stage evidence-first research paper pipeline.
    Each stage updates the job status in the DB before proceeding.
    On failure, records the failed stage and error before raising.
    """

    def __init__(self, db_session: AsyncSession, provider: Optional[AIProvider] = None):
        self.db = db_session
        self.provider = provider or get_default_provider("cloud")

    async def _set_status(
        self,
        job: ResearchPaperJob,
        status: ResearchJobStatus,
        **extra: Any,
    ) -> None:
        job.status = status
        for key, val in extra.items():
            setattr(job, key, val)
        await self.db.flush()
        logger.info(f"[ResearchEngine] Job {job.id}: → {status.value}")

    async def run(
        self,
        job: ResearchPaperJob,
        on_progress: Optional[Callable[[str], Any]] = None,
    ) -> ResearchPaperJob:
        """Execute all stages. Returns the updated job on completion or failure."""

        async def progress(msg: str) -> None:
            logger.info(f"[ResearchEngine] {msg}")
            if on_progress:
                try:
                    await on_progress(msg)
                except Exception:
                    pass

        try:
            # ── Stage A: Research Plan ─────────────────────────────────────
            await self._set_status(job, ResearchJobStatus.PLANNING)
            await progress("Stage A: Generating research plan…")
            plan = await stage_a_generate_plan(job, self.provider)
            job.research_plan = plan
            await self.db.flush()

            # ── Stage B: Source Retrieval ──────────────────────────────────
            await self._set_status(job, ResearchJobStatus.RETRIEVING_SOURCES)
            await progress("Stage B: Retrieving sources from academic providers…")
            candidates, prov_summary = await stage_b_retrieve_sources(
                job, plan, self.db, on_progress=progress
            )
            job.providers_attempted = prov_summary["providers_attempted"]
            job.providers_succeeded = prov_summary["providers_succeeded"]
            job.providers_failed = prov_summary["providers_failed"]
            job.executed_queries = prov_summary["executed_queries"]
            await self.db.flush()

            # ── Stage C: Verification & Deduplication ─────────────────────
            await self._set_status(job, ResearchJobStatus.VERIFYING_SOURCES)
            await progress(f"Stage C: Verifying {len(candidates)} candidates…")
            accepted, exc_list = stage_c_verify_and_deduplicate(
                candidates, job.excluded_domains or []
            )
            job.sources_retrieved = len(accepted)
            job.sources_excluded = len(exc_list)
            await self.db.flush()

            if not accepted:
                await self._set_status(
                    job,
                    ResearchJobStatus.FAILED,
                    error_message=(
                        "All retrieved source candidates were excluded after verification. "
                        "Try broader search terms, different source types, or a wider date range."
                    ),
                    failed_stage="verifying_sources",
                )
                await self.db.commit()
                return job

            # ── Stage D: Evidence Extraction ───────────────────────────────
            await self._set_status(job, ResearchJobStatus.EXTRACTING_EVIDENCE)
            await progress(f"Stage D: Extracting evidence blocks from {len(accepted)} sources…")
            evidence_rows = await stage_d_extract_evidence(job, accepted, self.db)

            # ── Stages E + F: Claim Matrix + Synthesis ─────────────────────
            await self._set_status(job, ResearchJobStatus.SYNTHESIZING)
            await progress("Stage E+F: Building Claim-Evidence Matrix and synthesising paper…")
            paper_content, claim_rows = await stage_ef_synthesize_with_matrix(
                job, evidence_rows, self.db, self.provider, on_progress=progress
            )
            job.paper_content = paper_content
            await self.db.flush()

            # ── Stage G: Citation Validation ───────────────────────────────
            await self._set_status(job, ResearchJobStatus.CITATION_VALIDATION)
            await progress("Stage G: Validating citations and grounding…")
            val_result = stage_g_validate_citations(paper_content, evidence_rows, claim_rows)
            job.citation_validation_result = val_result
            job.evidence_coverage_pct = val_result["evidence_coverage_pct"]
            job.citation_validity_count = val_result["inline_citations_found"]
            job.citation_total_count = val_result["sources_available"]
            job.flagged_claims_count = len(val_result["flagged_claims"])

            # Update claim rows with validation results
            for cr in claim_rows:
                cr.validation_passed = val_result["passed"]
                if cr.citation_strength == "unsupported":
                    cr.validation_note = "Unsupported claim — requires human review before approval"

            await self.db.flush()

            if not val_result["passed"] and val_result["orphaned_citations"]:
                # Fail with clear explanation — do not silently strip citations
                await self._set_status(
                    job,
                    ResearchJobStatus.NEEDS_REVIEW,
                    error_message=(
                        f"Citation validation failed: {'; '.join(val_result['validation_notes'])}. "
                        "Human review required before approval."
                    ),
                )
            else:
                # Advance to artifact generation
                await self._set_status(job, ResearchJobStatus.GENERATING_ARTIFACTS)
                await progress("Stage G: Generating IEEE draft PDF artifact…")
                try:
                    from src.services.pdf_generator import compile_ieee_research_paper_to_pdf

                    pdf_path = compile_ieee_research_paper_to_pdf(
                        job_id=str(job.id),
                        paper_title=job.paper_title or job.research_question,
                        paper_content=paper_content,
                        authors=job.authors or [],
                        paper_type=job.paper_type,
                        evidence_rows=evidence_rows,
                        claim_rows=claim_rows,
                        executed_queries=job.executed_queries or [],
                    )
                    job.artifact_pdf_path = pdf_path
                    await self.db.flush()
                    await progress(f"PDF generated successfully: {pdf_path}")
                except Exception as pdf_err:
                    logger.error(f"[ResearchEngine] Failed to generate PDF: {pdf_err}", exc_info=True)

                await self._set_status(job, ResearchJobStatus.NEEDS_REVIEW)
                await progress("Pipeline complete. Awaiting human review.")

            await self.db.commit()
            return job

        except Exception as exc:
            logger.error(f"[ResearchEngine] Job {job.id} failed: {exc}", exc_info=True)
            try:
                current_stage = job.status.value if job.status else "unknown"
                job.status = ResearchJobStatus.FAILED
                job.error_message = str(exc)[:2000]
                job.failed_stage = current_stage
                await self.db.commit()
            except Exception as commit_exc:
                logger.error(f"[ResearchEngine] Failed to commit failure state: {commit_exc}")
            return job


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json_safe(text: str, default: Any = None) -> Any:
    """Extract and parse JSON from raw LLM output, tolerating markdown fences."""
    try:
        clean = text.strip()
        if "```json" in clean:
            clean = clean.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in clean:
            clean = clean.split("```", 1)[1].split("```", 1)[0]
        return json.loads(clean.strip())
    except Exception:
        return default


def _extract_claim_matrix(raw_paper: str) -> tuple[str, Optional[List[Dict[str, Any]]]]:
    """
    Split the LLM output into (paper_content, claim_matrix).
    The model is instructed to wrap the matrix in <CLAIM_MATRIX>...</CLAIM_MATRIX>.
    """
    if "<CLAIM_MATRIX>" in raw_paper and "</CLAIM_MATRIX>" in raw_paper:
        parts = raw_paper.split("<CLAIM_MATRIX>", 1)
        paper_content = parts[0].strip()
        matrix_raw = parts[1].split("</CLAIM_MATRIX>", 1)[0].strip()
        matrix = _parse_json_safe(matrix_raw, default=[])
        if isinstance(matrix, list):
            return paper_content, matrix
    return raw_paper.strip(), None
