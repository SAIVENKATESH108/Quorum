import logging
import uuid
import os

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.dependencies import get_user_report
from src.db.models import Report
from src.db.session import get_db
from src.schemas.reports import (
    ReportDetailResponse,
    ReportSectionResponse,
    SourceResponse,
)
from src.services.pdf_generator import (
    build_quorum_system_documentation_pdf,
    compile_research_report_to_pdf,
)

logger = logging.getLogger("quorum.api.reports")

router = APIRouter(prefix="/api/reports", tags=["Reports"])


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
        # Check if pre-compiled in public or docs
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

        # Otherwise build in memory
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


@router.get(
    "/{report_id}/pdf",
    summary="Download publication-grade research paper PDF for a report",
)
async def get_report_pdf(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Compiles report sections, citations, and verified DOI metadata into a
    pixel-perfect, publication-grade ReportLab PDF.
    """
    stmt = (
        select(Report)
        .options(
            selectinload(Report.project),
            selectinload(Report.sections),
            selectinload(Report.sources),
        )
        .where(Report.id == report_id)
    )
    result = await db.execute(stmt)
    report = result.scalars().first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    try:
        source_type = getattr(report, "source_type", "academic") or "academic"
        source_ref = getattr(report, "source_ref", None)

        pdf_bytes = compile_research_report_to_pdf(
            report_title=report.query,
            sections=report.sections,
            sources=report.sources,
            lead_author="Quorum Autonomous Multi-Agent Swarm",
            source_type=source_type,
            source_ref=source_ref,
        )

        safe_slug = "".join(c if c.isalnum() else "_" for c in report.query[:30]).strip("_")
        filename = f"quorum_research_{safe_slug}_{str(report.id)[:8]}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        logger.error(f"Failed to generate report PDF for {report_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compile report PDF: {str(exc)}",
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

