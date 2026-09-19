import asyncio
import logging
import uuid
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_user_project
from src.core.events import format_report_channel, publish_event
from src.core.rate_limiter import check_report_creation_rate_limit
from src.core.security import get_current_user
from src.db.models import Project, Report, ReportStatus, User
from src.db.session import async_session_maker, get_db
from src.schemas.projects import ProjectCreate, ProjectResponse, ProjectUpdate
from src.schemas.reports import (
    ReportCreate,
    ReportCreateResponse,
    ReportSummaryResponse,
)

logger = logging.getLogger("quorum.api.projects")

router = APIRouter(prefix="/api/projects", tags=["Projects"])


async def _run_report_pipeline_background(report_id: uuid.UUID, query: str) -> None:
    """Background task executing the report generation pipeline via OrchestrationEngine."""
    try:
        from src.agents.engine import OrchestrationEngine, StatusPublisher

        publisher = StatusPublisher()

        # Forward engine events directly into Redis pub/sub for real-time WebSocket subscribers
        async def forward_to_redis(event):
            try:
                channel = format_report_channel(event.report_id)
                await publish_event(
                    channel,
                    {
                        "type": "report_status",
                        "data": event.to_dict(),
                        "timestamp": event.timestamp,
                    },
                )
            except Exception as e:
                logger.warning(f"[PIPELINE] Could not publish event to Redis: {e}")

        publisher.subscribe(forward_to_redis)
        engine = OrchestrationEngine(publisher=publisher, session_factory=async_session_maker)
        await engine.run_report(report_id=report_id)
    except Exception as exc:
        logger.exception(f"[PIPELINE] Background report DAG execution error for {report_id}: {exc}")


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
)
async def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Create a new project owned by the authenticated user."""
    project = Project(
        id=uuid.uuid4(),
        user_id=current_user.id,
        title=payload.title,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.get(
    "",
    response_model=List[ProjectResponse],
    summary="List current user's projects",
)
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ProjectResponse]:
    """Retrieve all projects belonging to the authenticated user."""
    stmt = (
        select(Project)
        .where(Project.user_id == current_user.id)
        .order_by(Project.created_at.desc())
    )
    result = await db.execute(stmt)
    projects = result.scalars().all()
    return [ProjectResponse.model_validate(p) for p in projects]


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get single project detail",
)
async def get_project_detail(
    project: Project = Depends(get_user_project),
) -> ProjectResponse:
    """Retrieve detail of a project owned by the authenticated user."""
    return ProjectResponse.model_validate(project)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project title",
)
async def update_project(
    payload: ProjectUpdate,
    project: Project = Depends(get_user_project),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Update title of a project owned by the authenticated user."""
    project.title = payload.title
    await db.commit()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project",
)
async def delete_project(
    project: Project = Depends(get_user_project),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a project and cascade delete all associated reports."""
    await db.delete(project)
    await db.commit()


@router.post(
    "/{project_id}/reports",
    response_model=ReportCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new report in project",
    dependencies=[Depends(check_report_creation_rate_limit)],
)
async def create_report(
    payload: ReportCreate,
    project: Project = Depends(get_user_project),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportCreateResponse:
    """
    Create a new report in pending status, schedule background DAG execution,
    and return report_id immediately (<500ms).
    """
    report = Report(
        id=uuid.uuid4(),
        project_id=project.id,
        query=payload.query,
        status=ReportStatus.PENDING,
        provider_mode=payload.provider_mode or "cloud",
        source_type=payload.source_type or "query",
        source_ref=payload.source_ref,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Trigger Orchestration DAG in background without blocking response (<500ms)
    asyncio.create_task(_run_report_pipeline_background(report.id, payload.query))


    return ReportCreateResponse(
        id=report.id,
        report_id=report.id,
        status=report.status,
        query=report.query,
        created_at=report.created_at,
    )


@router.get(
    "/{project_id}/reports",
    response_model=List[ReportSummaryResponse],
    summary="List reports in project",
)
async def list_project_reports(
    project: Project = Depends(get_user_project),
    db: AsyncSession = Depends(get_db),
) -> List[ReportSummaryResponse]:
    """List all reports belonging to a specified project."""
    stmt = (
        select(Report)
        .where(Report.project_id == project.id)
        .order_by(Report.created_at.desc())
    )
    result = await db.execute(stmt)
    reports = result.scalars().all()
    return [ReportSummaryResponse.model_validate(r) for r in reports]
