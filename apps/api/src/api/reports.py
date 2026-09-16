import logging
import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_user_report
from src.db.models import Report
from src.db.session import get_db
from src.schemas.reports import (
    ReportDetailResponse,
    ReportSectionResponse,
    SourceResponse,
)

logger = logging.getLogger("quorum.api.reports")

router = APIRouter(prefix="/api/reports", tags=["Reports"])


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
    # Order sections by order_index ascending
    sorted_sections = sorted(report.sections, key=lambda s: s.order_index)

    return ReportDetailResponse(
        id=report.id,
        project_id=report.project_id,
        status=report.status,
        query=report.query,
        created_at=report.created_at,
        completed_at=report.completed_at,
        sections=[ReportSectionResponse.model_validate(s) for s in sorted_sections],
        sources=[SourceResponse.model_validate(src) for src in report.sources],
    )


@router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel or delete a report",
)
async def delete_report(
    report: Report = Depends(get_user_report),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete or cancel a report belonging to the authenticated user."""
    await db.delete(report)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
