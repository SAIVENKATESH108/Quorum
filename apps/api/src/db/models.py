import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RESEARCHING = "researching"
    FACT_CHECKING = "fact_checking"
    WRITING = "writing"
    COMPLETE = "complete"
    FAILED = "failed"


class AgentRole(str, enum.Enum):
    ORCHESTRATOR = "orchestrator"
    RESEARCHER = "researcher"
    FACT_CHECKER = "fact_checker"
    WRITER = "writer"
    DOCUMENT_ANALYZER = "document_analyzer"


class AgentRunStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AgentTaskStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="projects")
    reports: Mapped[List["Report"]] = relationship(
        "Report",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[ReportStatus] = mapped_column(
        SQLEnum(
            ReportStatus,
            name="reportstatus",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=ReportStatus.PENDING,
        nullable=False,
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="query", nullable=True)
    source_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="reports")
    agent_runs: Mapped[List["AgentRun"]] = relationship(
        "AgentRun",
        back_populates="report",
        cascade="all, delete-orphan",
    )
    sections: Mapped[List["ReportSection"]] = relationship(
        "ReportSection",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="ReportSection.order_index",
    )
    report_sources: Mapped[List["ReportSource"]] = relationship(
        "ReportSource",
        back_populates="report",
        cascade="all, delete-orphan",
    )
    sources: Mapped[List["Source"]] = relationship(
        "Source",
        secondary="report_sources",
        viewonly=True,
    )


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_role: Mapped[AgentRole] = mapped_column(
        SQLEnum(
            AgentRole,
            name="agentrole",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    status: Mapped[AgentRunStatus] = mapped_column(
        SQLEnum(
            AgentRunStatus,
            name="agentrunstatus",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=AgentRunStatus.QUEUED,
        nullable=False,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    report: Mapped["Report"] = relationship("Report", back_populates="agent_runs")
    tasks: Mapped[List["AgentTask"]] = relationship(
        "AgentTask",
        back_populates="agent_run",
        cascade="all, delete-orphan",
    )


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[AgentTaskStatus] = mapped_column(
        SQLEnum(
            AgentTaskStatus,
            name="agenttaskstatus",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=AgentTaskStatus.QUEUED,
        nullable=False,
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    agent_run: Mapped["AgentRun"] = relationship("AgentRun", back_populates="tasks")


class ReportSection(Base):
    __tablename__ = "report_sections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    heading: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    report: Mapped["Report"] = relationship("Report", back_populates="sections")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    source_reports: Mapped[List["ReportSource"]] = relationship(
        "ReportSource",
        back_populates="source",
        cascade="all, delete-orphan",
    )
    reports: Mapped[List["Report"]] = relationship(
        "Report",
        secondary="report_sources",
        viewonly=True,
    )


class ReportSource(Base):
    __tablename__ = "report_sources"

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        primary_key=True,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        primary_key=True,
    )
    cited_in_section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_sections.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    report: Mapped["Report"] = relationship("Report", back_populates="report_sources")
    source: Mapped["Source"] = relationship("Source", back_populates="source_reports")
    cited_in_section: Mapped[Optional["ReportSection"]] = relationship("ReportSection")
