import uuid
from typing import Any, Dict, Generic, List, Optional, Sequence, Type, TypeVar

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.base import Base
from src.db.models import (
    AgentRun,
    AgentRunStatus,
    Report,
    ReportSource,
    ReportStatus,
    Source,
)

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Generic repository implementing standard CRUD operations."""

    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model

    async def create(self, **kwargs: Any) -> T:
        """Create a new model instance."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def get_by_id(self, id: uuid.UUID) -> Optional[T]:
        """Fetch a single record by primary key."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalars().first()

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        **filters: Any,
    ) -> Sequence[T]:
        """List records with optional pagination and exact match filters."""
        stmt = select(self.model)
        for attr, value in filters.items():
            if hasattr(self.model, attr) and value is not None:
                stmt = stmt.where(getattr(self.model, attr) == value)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update(self, id: uuid.UUID, **kwargs: Any) -> Optional[T]:
        """Update fields on an existing record by id."""
        # Filter out keys not on model
        valid_updates = {k: v for k, v in kwargs.items() if hasattr(self.model, k)}
        if not valid_updates:
            return await self.get_by_id(id)

        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**valid_updates)
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalars().first()

    async def delete(self, id: uuid.UUID) -> bool:
        """Delete a record by id."""
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return (result.rowcount or 0) > 0


class ReportRepository(BaseRepository[Report]):
    """Repository for Report entities with domain-specific queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Report)

    async def get_with_sections(self, report_id: uuid.UUID) -> Optional[Report]:
        """Fetch report eager-loading its sections and associated sources."""
        stmt = (
            select(Report)
            .where(Report.id == report_id)
            .options(
                selectinload(Report.sections),
                selectinload(Report.report_sources).selectinload(ReportSource.source),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_project(
        self,
        project_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Report]:
        """List all reports belonging to a specific project."""
        stmt = (
            select(Report)
            .where(Report.project_id == project_id)
            .order_by(Report.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_status(
        self,
        report_id: uuid.UUID,
        status: ReportStatus,
    ) -> Optional[Report]:
        """Update report processing status and completion timestamp if complete."""
        values: Dict[str, Any] = {"status": status}
        if status in (ReportStatus.COMPLETE, ReportStatus.FAILED):
            values["completed_at"] = func.now()

        stmt = (
            update(Report)
            .where(Report.id == report_id)
            .values(**values)
            .returning(Report)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalars().first()


class SourceRepository(BaseRepository[Source]):
    """Repository for Source entities with vector search support."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Source)

    async def get_by_url(self, url: str) -> Optional[Source]:
        """Fetch source by unique URL."""
        stmt = select(Source).where(Source.url == url)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def find_similar(
        self,
        embedding: List[float],
        limit: int = 5,
    ) -> Sequence[Source]:
        """Retrieve sources most similar to the given vector embedding using cosine distance."""
        stmt = (
            select(Source)
            .where(Source.embedding.isnot(None))
            .order_by(Source.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class AgentRunRepository(BaseRepository[AgentRun]):
    """Repository for AgentRun entities with task relationship queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, AgentRun)

    async def get_with_tasks(self, run_id: uuid.UUID) -> Optional[AgentRun]:
        """Fetch agent run with all associated tasks eager-loaded."""
        stmt = (
            select(AgentRun)
            .where(AgentRun.id == run_id)
            .options(selectinload(AgentRun.tasks))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_report(
        self,
        report_id: uuid.UUID,
    ) -> Sequence[AgentRun]:
        """List all agent runs for a specific report."""
        stmt = (
            select(AgentRun)
            .where(AgentRun.report_id == report_id)
            .order_by(AgentRun.started_at.desc().nullslast())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_runs(self) -> Sequence[AgentRun]:
        """Fetch all runs currently queued or running."""
        stmt = (
            select(AgentRun)
            .where(AgentRun.status.in_([AgentRunStatus.QUEUED, AgentRunStatus.RUNNING]))
            .order_by(AgentRun.started_at.asc().nullsfirst())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
