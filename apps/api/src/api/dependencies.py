import uuid
from typing import Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.security import get_current_user, security_bearer
from src.db.models import Project, Report, User
from src.db.session import get_db


async def get_user_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """
    Reusable dependency verifying that a project exists and belongs to the authenticated user.
    - 404 Not Found if project does not exist.
    - 403 Forbidden if project belongs to another user.
    """
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalars().first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if current_user.role != "admin" and project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not own this project",
        )

    return project


async def get_user_report(
    report_id: uuid.UUID,
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> Report:
    """
    Reusable dependency verifying that a report exists and belongs to the authenticated user.
    Loads associated sections (ordered) and sources.
    - 404 Not Found if report does not exist.
    - 403 Forbidden if report belongs to another user.
    - Supports public (unauthenticated) reads for published report pages.
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

    # If an auth header is provided, strictly enforce tenant ownership.
    if auth and auth.credentials:
        from src.core.security import get_current_user_from_token

        current_user = await get_current_user_from_token(auth.credentials, db=db)
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if (
            current_user.role != "admin"
            and report.project
            and report.project.user_id
            and report.project.user_id != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: you do not own this report",
            )

    # Unauthenticated requests remain readable (public report pages / crawlers).
    return report
