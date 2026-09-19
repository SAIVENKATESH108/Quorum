import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from src.db.models import ReportStatus


class ReportCreate(BaseModel):
    """Schema for submitting a research query or codebase/paper generation request."""
    query: str = Field(..., min_length=3, description="The research query, repo URL, or project name")
    source_type: Optional[str] = Field("query", description="'query', 'github_repo', or 'local_folder'")
    source_ref: Optional[str] = Field(None, description="GitHub repository URL or local folder path")
    provider_mode: Optional[str] = Field(
        "cloud",
        description="'cloud', 'local' (Ollama offline), or 'neural_pulse' (Evorozen Neural Pulse)",
    )
    file_tree: Optional[dict] = Field(None, description="Optional client-read local directory tree and files")


class ReportSectionResponse(BaseModel):
    """Schema for a report section."""
    id: uuid.UUID
    heading: str
    content: str
    order_index: int

    model_config = ConfigDict(from_attributes=True)


class SourceResponse(BaseModel):
    """Schema for a cited source."""
    id: uuid.UUID
    url: str
    title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReportSummaryResponse(BaseModel):
    """Schema for report listing summary."""
    id: uuid.UUID
    project_id: uuid.UUID
    status: ReportStatus
    query: str
    provider_mode: Optional[str] = "cloud"
    error_message: Optional[str] = None
    source_type: Optional[str] = "query"
    source_ref: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ReportDetailResponse(ReportSummaryResponse):
    """Full report detail schema including ordered sections and sources."""
    sections: List[ReportSectionResponse] = []
    sources: List[SourceResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ReportCreateResponse(BaseModel):
    """Immediate response on report creation (<500ms)."""
    id: uuid.UUID
    report_id: uuid.UUID
    status: ReportStatus
    query: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
