"""
Research Studio — FastAPI router for research paper job lifecycle.

Endpoints:
  POST   /api/research-jobs              — Create job (Step 1: define paper)
  GET    /api/research-jobs?report_id=X  — List jobs for a report
  GET    /api/research-jobs/{job_id}     — Get full job detail
  POST   /api/research-jobs/{job_id}/confirm-consent   — Step 2: PII consent
  PUT    /api/research-jobs/{job_id}/plan              — Step 3: edit research plan
  POST   /api/research-jobs/{job_id}/run              — Start pipeline execution
  POST   /api/research-jobs/{job_id}/approve-or-reject — Step 5: human review gate
  GET    /api/research-jobs/{job_id}/pdf               — Download persisted PDF
  GET    /api/research-jobs/providers/health           — Provider availability status
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.agents.research_paper_engine import (
    ResearchPaperEngine,
    scrub_text,
)
from src.agents.research_providers import check_all_providers
from src.api.dependencies import get_user_report
from src.db.models import (
    Report,
    ResearchJobStatus,
    ResearchPaperJob,
)
from src.db.session import get_db
from src.schemas.research_jobs import (
    ApprovalRequest,
    ConsentConfirmRequest,
    PlanEditRequest,
    ProviderHealthResponse,
    ResearchJobCreateRequest,
    ResearchJobDetail,
    ResearchJobSummary,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/research-jobs", tags=["Research Studio"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_job_or_404(job_id: uuid.UUID, db: AsyncSession) -> ResearchPaperJob:
    stmt = (
        select(ResearchPaperJob)
        .options(
            selectinload(ResearchPaperJob.evidence_blocks),
            selectinload(ResearchPaperJob.claim_mappings),
        )
        .where(ResearchPaperJob.id == job_id)
    )
    result = await db.execute(stmt)
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")
    return job


def _job_to_detail(job: ResearchPaperJob) -> ResearchJobDetail:
    return ResearchJobDetail.model_validate(job)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/providers/health", response_model=ProviderHealthResponse)
async def get_provider_health() -> ProviderHealthResponse:
    """Check which research source providers are currently reachable."""
    statuses = await check_all_providers()
    return ProviderHealthResponse(
        providers=statuses,
        available_count=sum(1 for v in statuses.values() if v),
        total_count=len(statuses),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ResearchJobDetail)
async def create_research_job(
    body: ResearchJobCreateRequest,
    report: Report = Depends(get_user_report),
    db: AsyncSession = Depends(get_db),
) -> ResearchJobDetail:
    """
    Step 1: Define the research paper and run PII scrubbing.
    Returns the job in SCRUB_REQUIRED status with scrub findings populated.
    Does NOT start retrieval — consent is required next.
    """
    scrub = scrub_text(body.research_question)

    job = ResearchPaperJob(
        report_id=report.id,
        status=ResearchJobStatus.SCRUB_REQUIRED,
        paper_title=body.paper_title,
        authors=body.authors or [],
        research_question=body.research_question,
        domain_keywords=body.domain_keywords or [],
        paper_type=body.paper_type,
        depth=body.depth,
        citation_format=body.citation_format,
        date_from=body.date_from,
        date_to=body.date_to,
        preferred_source_types=body.preferred_source_types or ["peer_reviewed", "preprint"],
        excluded_domains=body.excluded_domains or [],
        scrub_findings=scrub,
        sanitized_question=scrub["sanitized"],
        consent_confirmed=False,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return _job_to_detail(job)


@router.get("", response_model=List[ResearchJobSummary])
async def list_research_jobs(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> List[ResearchJobSummary]:
    """List all research paper jobs for a given report."""
    stmt = (
        select(ResearchPaperJob)
        .where(ResearchPaperJob.report_id == report_id)
        .order_by(ResearchPaperJob.created_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [ResearchJobSummary.model_validate(r) for r in rows]


@router.get("/{job_id}", response_model=ResearchJobDetail)
async def get_research_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ResearchJobDetail:
    """Get full job detail including evidence blocks and claim matrix."""
    job = await _get_job_or_404(job_id, db)
    return _job_to_detail(job)


@router.post("/{job_id}/confirm-consent", response_model=ResearchJobDetail)
async def confirm_consent(
    job_id: uuid.UUID,
    body: ConsentConfirmRequest,
    db: AsyncSession = Depends(get_db),
) -> ResearchJobDetail:
    """
    Step 2: User confirms the sanitized content may be transmitted externally.
    Advances job to AWAITING_CONSENT → PLANNING ready-state.
    Will not proceed unless confirmed=True.
    """
    job = await _get_job_or_404(job_id, db)

    if job.status not in (ResearchJobStatus.SCRUB_REQUIRED, ResearchJobStatus.AWAITING_CONSENT):
        raise HTTPException(
            status_code=409,
            detail=f"Job is in status '{job.status.value}' — consent step already passed or not applicable.",
        )

    if not body.confirmed:
        raise HTTPException(
            status_code=400,
            detail="Consent must be explicitly confirmed (confirmed=true) before external search begins.",
        )

    job.consent_confirmed = True
    job.consent_timestamp = datetime.now(timezone.utc)
    if body.sanitized_question_override:
        job.sanitized_question = body.sanitized_question_override.strip()
    job.status = ResearchJobStatus.AWAITING_CONSENT  # Ready for plan review next

    await db.commit()
    await db.refresh(job)
    return _job_to_detail(job)


@router.put("/{job_id}/plan", response_model=ResearchJobDetail)
async def update_research_plan(
    job_id: uuid.UUID,
    body: PlanEditRequest,
    db: AsyncSession = Depends(get_db),
) -> ResearchJobDetail:
    """
    Step 3: User reviews and optionally edits the research plan before execution.
    Plan is persisted before retrieval begins.
    """
    job = await _get_job_or_404(job_id, db)

    if not job.consent_confirmed:
        raise HTTPException(
            status_code=409,
            detail="Consent must be confirmed before editing the research plan.",
        )

    existing_plan = job.research_plan or {}
    if body.sub_questions is not None:
        existing_plan["sub_questions"] = body.sub_questions
    if body.search_queries is not None:
        existing_plan["search_queries"] = body.search_queries
    if body.excluded_topics is not None:
        existing_plan["excluded_topics"] = body.excluded_topics

    job.research_plan = existing_plan
    await db.commit()
    await db.refresh(job)
    return _job_to_detail(job)


@router.post("/{job_id}/run", status_code=status.HTTP_202_ACCEPTED, response_model=ResearchJobDetail)
async def run_research_job(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ResearchJobDetail:
    """
    Start the 7-stage research pipeline execution as a background task.
    Requires consent to have been confirmed.
    """
    job = await _get_job_or_404(job_id, db)

    if not job.consent_confirmed:
        raise HTTPException(
            status_code=409,
            detail="Explicit consent must be confirmed before the pipeline can run.",
        )

    runnable_statuses = {
        ResearchJobStatus.AWAITING_CONSENT,
        ResearchJobStatus.DRAFT,
        ResearchJobStatus.FAILED,  # Allow retry on failed jobs
    }
    if job.status not in runnable_statuses:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Job is in status '{job.status.value}'. "
                "Only jobs in awaiting_consent, draft, or failed may be run."
            ),
        )

    # Mark as planning immediately so subsequent polls show progress
    job.status = ResearchJobStatus.PLANNING
    await db.commit()

    # Run pipeline asynchronously
    background_tasks.add_task(_run_pipeline_background, job_id)

    await db.refresh(job)
    return _job_to_detail(job)


async def _run_pipeline_background(job_id: uuid.UUID) -> None:
    """Background task: obtain a fresh DB session and execute the pipeline."""
    from src.db.session import async_session_maker

    async with async_session_maker() as db:
        try:
            stmt = (
                select(ResearchPaperJob)
                .options(
                    selectinload(ResearchPaperJob.evidence_blocks),
                    selectinload(ResearchPaperJob.claim_mappings),
                )
                .where(ResearchPaperJob.id == job_id)
            )
            result = await db.execute(stmt)
            job = result.scalars().first()
            if not job:
                logger.error(f"[ResearchBG] Job {job_id} not found in background task")
                return

            engine = ResearchPaperEngine(db_session=db)
            await engine.run(job)
        except Exception as exc:
            logger.error(f"[ResearchBG] Unhandled error for job {job_id}: {exc}", exc_info=True)


@router.post("/{job_id}/approve-or-reject", response_model=ResearchJobDetail)
async def approve_or_reject_job(
    job_id: uuid.UUID,
    body: ApprovalRequest,
    db: AsyncSession = Depends(get_db),
) -> ResearchJobDetail:
    """
    Step 5: Human review gate. Requires all 5 checklist items.
    approval is never automatic — this endpoint must be called explicitly.
    """
    job = await _get_job_or_404(job_id, db)

    if job.status not in (ResearchJobStatus.NEEDS_REVIEW, ResearchJobStatus.APPROVED, ResearchJobStatus.REJECTED):
        raise HTTPException(
            status_code=409,
            detail=f"Job status is '{job.status.value}' — approval is only available for jobs in needs_review.",
        )

    if body.action == "approve":
        required_checks = ["reviewed_sources", "verified_facts", "understood_disclaimers",
                           "reviewed_sensitive_content", "approve_for_use"]
        not_checked = [k for k in required_checks if not body.checklist.get(k)]
        if not_checked:
            raise HTTPException(
                status_code=400,
                detail=f"The following checklist items must be checked before approval: {not_checked}",
            )
        job.status = ResearchJobStatus.APPROVED
        job.approved_at = datetime.now(timezone.utc)
    else:
        job.status = ResearchJobStatus.REJECTED

    job.review_checklist = body.checklist
    job.reviewer_notes = body.reviewer_notes
    await db.commit()
    await db.refresh(job)
    return _job_to_detail(job)


@router.get("/{job_id}/pdf")
async def download_research_pdf(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Download the persisted research paper PDF.
    Returns 404 if PDF has not been generated yet.
    Returns 202 if the job is still in progress.
    """
    job = await _get_job_or_404(job_id, db)

    if job.status in (ResearchJobStatus.DRAFT, ResearchJobStatus.SCRUB_REQUIRED,
                      ResearchJobStatus.AWAITING_CONSENT, ResearchJobStatus.PLANNING,
                      ResearchJobStatus.RETRIEVING_SOURCES, ResearchJobStatus.EXTRACTING_EVIDENCE,
                      ResearchJobStatus.VERIFYING_SOURCES, ResearchJobStatus.SYNTHESIZING,
                      ResearchJobStatus.CITATION_VALIDATION, ResearchJobStatus.GENERATING_ARTIFACTS):
        raise HTTPException(
            status_code=202,
            detail=f"PDF is not ready yet. Current status: {job.status.value}",
        )

    if not job.artifact_pdf_path:
        raise HTTPException(
            status_code=404,
            detail="PDF artifact has not been generated for this job. Generate the artifact first.",
        )

    import os
    if not os.path.isfile(job.artifact_pdf_path):
        raise HTTPException(
            status_code=404,
            detail="PDF file was not found on disk. It may have been moved or deleted.",
        )

    return FileResponse(
        path=job.artifact_pdf_path,
        media_type="application/pdf",
        filename=f"research-paper-{job_id}.pdf",
    )
