import uuid
from typing import Optional
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.security import get_current_user, get_current_user_from_token, security_bearer
from src.db.models import Project, Report, ReportStatus, User
from src.db.session import get_db


async def get_user_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """
    Reusable dependency verifying that a project exists and belongs to the authenticated user.
    - 404 Not Found if project does not exist.
    - 403 Forbidden if project is private and caller is not owner or admin.
    """
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalars().first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if current_user.role == "admin":
        pass
    elif current_user.role == "guest":
        if not project.is_guest_demo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: private project",
            )
    elif project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not own this project",
        )

    return project


async def get_user_report(
    report_id: uuid.UUID,
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> Report:
    """
    Reusable dependency verifying that a report exists and enforces tenant isolation.
    - 404 Not Found if report does not exist.
    - 403 Forbidden if report is private and caller is not owner or admin.
    - Curated demo access requires both report.is_guest_demo AND parent project.is_guest_demo.
    - Anonymous access permitted ONLY for curated demo reports. Private reports require auth.
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

    token = auth.credentials if auth else None
    if not token and hasattr(request, "cookies"):
        token = request.cookies.get("quorum_session")

    # If authenticated, enforce role and tenant isolation
    if token:
        current_user = await get_current_user_from_token(token, db=db)
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if current_user.role == "admin":
            return report

        if current_user.role == "guest":
            parent_is_demo = report.project and report.project.is_guest_demo
            if not (report.is_guest_demo and parent_is_demo):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: private report",
                )
            return report

        # Normal user
        if report.project and report.project.user_id and report.project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: you do not own this report",
            )
        return report

    # Unauthenticated / anonymous callers:
    parent_is_demo = report.project and report.project.is_guest_demo
    if not (report.is_guest_demo and parent_is_demo and report.status == ReportStatus.COMPLETE):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return report

