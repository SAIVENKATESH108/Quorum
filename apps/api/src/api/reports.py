import logging
import uuid
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, Security, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.dependencies import get_user_report
from src.core.security import (
    get_current_user,
    get_current_user_from_token,
    require_non_guest_write_access,
    security_bearer,
)
from src.db.models import Project, Report, ReportStatus, User, UserRole
from src.db.session import get_db
from src.schemas.reports import (
    ReportDetailResponse,
    ReportSectionResponse,
    ReportSummaryResponse,
    SourceResponse,
)
from src.services.pdf_generator import (
    build_quorum_system_documentation_pdf,
    compile_research_report_to_pdf,
)

logger = logging.getLogger("quorum.api.reports")

router = APIRouter(prefix="/api/reports", tags=["Reports"])

# ── Status group mapping ──────────────────────────────────────────────────────
# "in_progress" is a UI-friendly group covering actively running pipeline states.
# "running" is NOT a persisted ReportStatus value and is never used here.
_STATUS_GROUP_MAP = {
    "pending": [ReportStatus.PENDING],
    "planning": [ReportStatus.PLANNING],
    "in_progress": [ReportStatus.RESEARCHING, ReportStatus.FACT_CHECKING, ReportStatus.WRITING],
    "complete": [ReportStatus.COMPLETE],
    "needs_review": [ReportStatus.NEEDS_REVIEW],
    "failed": [ReportStatus.FAILED],
}


class ReportListResponse(BaseModel):
    """Paginated report list envelope."""
    items: List[ReportSummaryResponse]
    total: int
    """Total visible reports matching the current filter (scoped to caller's authorized scope)."""
    limit: int
    offset: int
    has_more: bool


class ReportCountsResponse(BaseModel):
    """Per-status-group report counts scoped to the current caller's visible scope."""
    all: int
    pending: int
    planning: int
    in_progress: int
    """researching + fact_checking + writing"""
    complete: int
    needs_review: int
    failed: int


class ProviderStatusItem(BaseModel):
    status: str
    observed_at: Optional[str] = None


class ProvidersStatusResponse(BaseModel):
    cloud: ProviderStatusItem
    local: ProviderStatusItem
    neural_pulse: ProviderStatusItem


def _apply_visibility(stmt, current_user: User):
    """Apply owner/guest/admin report visibility filter to a select statement."""
    if current_user.role == UserRole.GUEST.value:
        return stmt.where(Report.is_guest_demo.is_(True), Project.is_guest_demo.is_(True))
    if current_user.role == UserRole.ADMIN.value:
        return stmt
    return stmt.where(Project.user_id == current_user.id)


def _apply_status_filter(stmt, status_param: Optional[str]):
    """
    Apply server-side status filter. 'in_progress' maps to researching/fact_checking/writing.
    Returns the statement unchanged for 'all' or None.
    """
    if not status_param or status_param == "all":
        return stmt
    statuses = _STATUS_GROUP_MAP.get(status_param)
    if statuses is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status filter '{status_param}'. Valid values: "
                   f"all, {', '.join(_STATUS_GROUP_MAP.keys())}",
        )
    return stmt.where(Report.status.in_(statuses))


@router.get(
    "/system/documentation-pdf",
    summary="Download Quorum System Documentation & Engineering Specification PDF",
)
async def get_system_documentation_pdf() -> Response:
    """
    Returns the official, publication-grade 9-page Quorum System Documentation PDF
    with double borders, two-pass NumberedCanvas page numbering, architecture specifications,
    and REST/PostgreSQL reference tables.
    """
    try:
        possible_paths = [
            os.path.join(os.getcwd(), "docs", "Quorum_System_Documentation.pdf"),
            os.path.join(os.getcwd(), "..", "web", "public", "Quorum_System_Documentation.pdf"),
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "docs", "Quorum_System_Documentation.pdf"),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    pdf_bytes = f.read()
                return Response(
                    content=pdf_bytes,
                    media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="Quorum_System_Documentation.pdf"'},
                )

        pdf_bytes = build_quorum_system_documentation_pdf()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="Quorum_System_Documentation.pdf"'},
        )
    except Exception as exc:
        logger.error(f"Failed to generate system documentation PDF: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate documentation PDF: {str(exc)}",
        )


@router.get(
    "/counts",
    response_model=ReportCountsResponse,
    summary="Per-status-group report counts scoped to the current caller's visible scope",
)
async def get_report_counts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportCountsResponse:
    """
    Returns report counts for every status group visible to the caller.
    Uses identical visibility rules as GET /api/reports.
    Guest callers see only curated demo report counts.
    """
    base = select(Report.status, func.count(Report.id).label("cnt")).join(
        Project, Report.project_id == Project.id
    )
    base = _apply_visibility(base, current_user)
    base = base.group_by(Report.status)

    result = await db.execute(base)
    raw: dict[str, int] = {}
    for row in result.all():
        raw[row.status] = row.cnt

    in_progress = sum(
        raw.get(s.value, 0)
        for s in [ReportStatus.RESEARCHING, ReportStatus.FACT_CHECKING, ReportStatus.WRITING]
    )
    total_all = sum(raw.values())

    return ReportCountsResponse(
        all=total_all,
        pending=raw.get(ReportStatus.PENDING.value, 0),
        planning=raw.get(ReportStatus.PLANNING.value, 0),
        in_progress=in_progress,
        complete=raw.get(ReportStatus.COMPLETE.value, 0),
        needs_review=raw.get(ReportStatus.NEEDS_REVIEW.value, 0),
        failed=raw.get(ReportStatus.FAILED.value, 0),
    )


@router.get(
    "/providers/status",
    response_model=ProvidersStatusResponse,
    summary="Get sanitized AI provider availability statuses",
)
async def get_providers_status(
    current_user: User = Depends(require_non_guest_write_access),
) -> ProvidersStatusResponse:
    """
    Return provider availability statuses without making external outbound requests.
    Option C:
    - Anonymous: 401
    - Guest Judge: 403 (Guest Judge cannot create reports)
    - Owner/Member: returns safe status summary.
    Never exposes API keys, Authorization headers, plan names, quota limits/usage,
    trace IDs, raw provider errors, or endpoint URLs.
    """
    from src.agents.providers import get_provider_observation
    from src.core.config import settings

    np_key = (getattr(settings, "NEURAL_PULSE_API_KEY", None) or "").strip()
    if not np_key:
        np_status = "not_configured"
        np_observed_at = None
    else:
        observation = get_provider_observation("NeuralPulse")
        if observation:
            np_status = observation.get("status", "unknown")
            np_observed_at = observation.get("observed_at")
        else:
            np_status = "unknown"
            np_observed_at = None

    return ProvidersStatusResponse(
        cloud=ProviderStatusItem(status="available"),
        local=ProviderStatusItem(status="available"),
        neural_pulse=ProviderStatusItem(status=np_status, observed_at=np_observed_at),
    )


@router.get(
    "",
    response_model=ReportListResponse,
    summary="Paginated list of reports within the current user's visible scope",
)
async def list_reports(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportListResponse:
    """
    Workspace-wide paginated report index backing the /reports dashboard page.

    - Admin: all reports.
    - Guest: only curated demo reports (is_guest_demo=true, parent project is_guest_demo=true).
    - Member: only reports from projects owned by the caller.

    Ordering: created_at DESC, id DESC (deterministic; Report has no updated_at field).
    Status filter: server-side, applied before pagination and total count.
    """
    # ── Base query with visibility ────────────────────────────────────────────
    base = select(Report).join(Project, Report.project_id == Project.id)
    base = _apply_visibility(base, current_user)
    base = _apply_status_filter(base, status_filter)

    # ── Count total matching visible records (same visibility + status filter) ──
    count_base = select(func.count(Report.id)).join(Project, Report.project_id == Project.id)
    count_base = _apply_visibility(count_base, current_user)
    count_base = _apply_status_filter(count_base, status_filter)
    total_res = await db.execute(count_base)
    total = total_res.scalar() or 0

    # ── Fetch page ────────────────────────────────────────────────────────────
    page_stmt = (
        base
        .order_by(Report.created_at.desc(), Report.id.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(page_stmt)
    items = [ReportSummaryResponse.model_validate(r) for r in result.scalars().all()]

    return ReportListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.get(
    "/{report_id}",
    response_model=ReportDetailResponse,
    summary="Get full report details",
)
async def get_report_detail(
    report: Report = Depends(get_user_report),
) -> ReportDetailResponse:
    """
    Retrieve full report detail including status, sections ordered by order_index,
    and cited sources. Reusable ownership check ensures cross-user safety.
    """
    sorted_sections = sorted(report.sections, key=lambda s: s.order_index)

    return ReportDetailResponse(
        id=report.id,
        project_id=report.project_id,
        status=report.status,
        query=report.query,
        is_guest_demo=report.is_guest_demo,
        created_at=report.created_at,
        completed_at=report.completed_at,
        sections=[ReportSectionResponse.model_validate(s) for s in sorted_sections],
        sources=[SourceResponse.model_validate(src) for src in report.sources],
    )


@router.get(
    "/{report_id}/pdf",
    summary="Download publication-grade research paper PDF for a report",
)
async def get_report_pdf(
    report: Report = Depends(get_user_report),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Compiles report sections, citations, and verified DOI metadata into a
    pixel-perfect, publication-grade ReportLab PDF.
    Enforces tenant and demo hierarchy visibility via get_user_report dependency.
    """
    sections = list(report.sections) if report.sections else []
    sources = list(report.sources) if report.sources else []

    if not sections and not sources:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report has no synthesized content yet",
        )

    try:
        source_type = getattr(report, "source_type", "academic") or "academic"
        source_ref = getattr(report, "source_ref", None)

        pdf_bytes = compile_research_report_to_pdf(
            report_title=report.query,
            sections=sections,
            sources=sources,
            lead_author="Quorum Autonomous Multi-Agent Swarm",
            source_type=source_type,
            source_ref=source_ref,
        )

        safe_slug = "".join(c if c.isalnum() else "_" for c in report.query[:35]).strip("_")
        filename = f"quorum_research_{safe_slug}_{str(report.id)[:8]}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        logger.error(f"Failed to generate report PDF for {report.id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compile report PDF: {str(exc)}",
        )


@router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel or delete a report",
    dependencies=[Depends(require_non_guest_write_access)],
)
async def delete_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete or cancel a report belonging to the authenticated user."""
    stmt = (
        select(Report)
        .options(selectinload(Report.project))
        .where(Report.id == report_id)
    )
    result = await db.execute(stmt)
    report = result.scalars().first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    if current_user.role != "admin" and (not report.project or report.project.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not own this report",
        )

    await db.delete(report)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
