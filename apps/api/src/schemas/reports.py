import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from src.db.models import ReportStatus


class ReportCreate(BaseModel):
    """Schema for submitting a research query to generate a report."""
    query: str = Field(..., min_length=3, description="The research query / prompt")


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
