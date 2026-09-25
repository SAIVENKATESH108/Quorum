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
    NEEDS_REVIEW = "needs_review"
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


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(
        String(20),
        default=UserRole.MEMBER.value,
        server_default=UserRole.MEMBER.value,
        nullable=False,
    )
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
    provider_mode: Mapped[str] = mapped_column(
        String(50), server_default="cloud", default="cloud", nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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


# ============================================================================
# Research Studio Models
# ============================================================================

class ResearchJobStatus(str, enum.Enum):
    """Lifecycle states for a Research Paper generation job."""
    DRAFT = "draft"
    SCRUB_REQUIRED = "scrub_required"
    AWAITING_CONSENT = "awaiting_consent"
    PLANNING = "planning"
    RETRIEVING_SOURCES = "retrieving_sources"
    EXTRACTING_EVIDENCE = "extracting_evidence"
    VERIFYING_SOURCES = "verifying_sources"
    SYNTHESIZING = "synthesizing"
    CITATION_VALIDATION = "citation_validation"
    GENERATING_ARTIFACTS = "generating_artifacts"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"


class ResearchPaperJob(Base):
    """
    Persisted research paper generation job.
    Tracks every stage from user input through evidence extraction to final artifact.
    """
    __tablename__ = "research_paper_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[ResearchJobStatus] = mapped_column(
        SQLEnum(
            ResearchJobStatus,
            name="researchjobstatus",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=ResearchJobStatus.DRAFT,
        nullable=False,
    )
    # Paper metadata (user-supplied)
    paper_title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    authors: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    research_question: Mapped[str] = mapped_column(Text, nullable=False)
    domain_keywords: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    paper_type: Mapped[str] = mapped_column(String(80), default="literature_review", nullable=False)
    depth: Mapped[str] = mapped_column(String(50), default="standard", nullable=False)
    citation_format: Mapped[str] = mapped_column(String(30), default="ieee", nullable=False)
    date_from: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    date_to: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    preferred_source_types: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    excluded_domains: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)

    # PII scrub result
    scrub_findings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sanitized_question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    consent_confirmed: Mapped[bool] = mapped_column(default=False, nullable=False)
    consent_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Research plan (persisted before retrieval begins)
    research_plan: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    executed_queries: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONB, nullable=True)

    # Provider result summary
    providers_attempted: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    providers_succeeded: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    providers_failed: Mapped[Optional[Dict[str, str]]] = mapped_column(JSONB, nullable=True)
    sources_retrieved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sources_excluded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Evidence and synthesis quality metrics
    evidence_coverage_pct: Mapped[Optional[float]] = mapped_column(nullable=True)
    citation_validity_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    citation_total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    flagged_claims_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Generated content
    paper_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    paper_outline: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    artifact_pdf_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Citation validation result
    citation_validation_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Review & approval
    review_checklist: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Failure
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    failed_stage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    report: Mapped["Report"] = relationship("Report")
    evidence_blocks: Mapped[List["ResearchEvidence"]] = relationship(
        "ResearchEvidence",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="ResearchEvidence.created_at",
    )
    claim_mappings: Mapped[List["ClaimEvidenceMapping"]] = relationship(
        "ClaimEvidenceMapping",
        back_populates="job",
        cascade="all, delete-orphan",
    )


class ResearchEvidence(Base):
    """
    A single evidence block extracted from a real retrieved source.
    This is the ground truth from which paper claims are written.
    """
    __tablename__ = "research_evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_paper_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Source provenance (from provider retrieval — never invented)
    provider: Mapped[str] = mapped_column(String(60), nullable=False)  # crossref | openalex | arxiv | semanticscholar
    source_identifier: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)  # DOI, arXiv ID, etc.
    canonical_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    publisher: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    publication_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    source_class: Mapped[str] = mapped_column(String(60), nullable=False)  # peer_reviewed | preprint | ...
    access_level: Mapped[str] = mapped_column(String(30), nullable=False)  # full_text | abstract_only | snippet_only | metadata_only

    # Extracted text
    retrieved_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # abstract or available text
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # page/section if known

    # Quality
    topic_tags: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    inclusion_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    exclusion_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_excluded: Mapped[bool] = mapped_column(default=False, nullable=False)

    retrieval_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    job: Mapped["ResearchPaperJob"] = relationship("ResearchPaperJob", back_populates="evidence_blocks")
    claim_mappings: Mapped[List["ClaimEvidenceMapping"]] = relationship(
        "ClaimEvidenceMapping",
        back_populates="evidence",
        cascade="all, delete-orphan",
    )


class ClaimEvidenceMapping(Base):
    """
    Claim-Evidence Matrix row.
    Every substantive factual claim in the generated paper must have a row here.
    """
    __tablename__ = "claim_evidence_mappings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_paper_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_evidence.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    claim_id: Mapped[str] = mapped_column(String(40), nullable=False)  # e.g. "C001"
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="descriptive"
    )  # descriptive | quantitative | causal | comparative | interpretive | recommendation

    # Support classification
    citation_strength: Mapped[str] = mapped_column(
        String(30), nullable=False, default="unsupported"
    )  # directly_supported | partially_supported | contextual_only | unsupported

    requires_review: Mapped[bool] = mapped_column(default=False, nullable=False)
    section_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    inline_citation_marker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # e.g. "[1]"

    # Validation output
    validation_passed: Mapped[Optional[bool]] = mapped_column(nullable=True)
    validation_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    job: Mapped["ResearchPaperJob"] = relationship("ResearchPaperJob", back_populates="claim_mappings")
    evidence: Mapped[Optional["ResearchEvidence"]] = relationship(
        "ResearchEvidence", back_populates="claim_mappings"
    )

