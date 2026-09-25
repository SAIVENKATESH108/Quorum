"""Pydantic schemas for the Research Studio API."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class ResearchJobCreateRequest(BaseModel):
    """Step 1: User submits the paper definition form."""
    research_question: str = Field(..., min_length=10, max_length=2000)
    paper_title: Optional[str] = Field(None, max_length=512)
    authors: Optional[List[str]] = Field(default=None, description="Never invent; leave empty if unknown")
    domain_keywords: Optional[List[str]] = Field(default=None, max_length=20)
    paper_type: str = Field(
        "literature_review",
        pattern="^(literature_review|technical_research_report|system_design_paper|comparative_analysis|project_capstone_paper)$",
    )
    depth: str = Field("standard", pattern="^(quick|standard|thorough)$")
    citation_format: str = Field("ieee", pattern="^(ieee|apa|mla)$")
    date_from: Optional[str] = Field(None, pattern=r"^\d{4}$")
    date_to: Optional[str] = Field(None, pattern=r"^\d{4}$")
    preferred_source_types: Optional[List[str]] = Field(default=None)
    excluded_domains: Optional[List[str]] = Field(default=None)
    output_formats: Optional[List[str]] = Field(default=None)

    @field_validator("research_question")
    @classmethod
    def no_empty_question(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("research_question must not be empty")
        return v.strip()


class ConsentConfirmRequest(BaseModel):
    """Step 2: User confirms the scrubbed content may be transmitted externally."""
    confirmed: bool = Field(..., description="Must be True to proceed")
    sanitized_question_override: Optional[str] = Field(
        None,
        description="User may supply an edited version of the sanitized question",
        max_length=2000,
    )


class PlanEditRequest(BaseModel):
    """Step 3: User may edit the research plan before retrieval begins."""
    sub_questions: Optional[List[str]] = Field(None, max_length=8)
    search_queries: Optional[List[str]] = Field(None, max_length=10)
    excluded_topics: Optional[List[str]] = Field(None)


class ApprovalRequest(BaseModel):
    """Step 5: Human review checklist + approval/rejection."""
    action: str = Field(..., pattern="^(approve|reject)$")
    reviewer_notes: Optional[str] = Field(None, max_length=5000)
    checklist: Dict[str, bool] = Field(
        ...,
        description=(
            "Must include keys: reviewed_sources, verified_facts, "
            "understood_disclaimers, reviewed_sensitive_content, approve_for_use"
        ),
    )

    @field_validator("checklist")
    @classmethod
    def require_all_checked(cls, v: Dict[str, bool]) -> Dict[str, bool]:
        required_keys = {
            "reviewed_sources",
            "verified_facts",
            "understood_disclaimers",
            "reviewed_sensitive_content",
            "approve_for_use",
        }
        missing = required_keys - v.keys()
        if missing:
            raise ValueError(f"Checklist is missing required keys: {missing}")
        return v


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------

class ScrubFinding(BaseModel):
    type: str
    excerpt: str
    start: int
    end: int


class ScrubResult(BaseModel):
    findings: List[ScrubFinding]
    sanitized: str
    warning: str
    finding_count: int


class EvidenceBlockResponse(BaseModel):
    id: uuid.UUID
    provider: str
    source_identifier: Optional[str]
    canonical_url: str
    title: str
    authors: Optional[List[str]]
    publisher: Optional[str]
    publication_date: Optional[str]
    source_class: str
    access_level: str
    retrieved_excerpt: Optional[str]
    topic_tags: Optional[List[str]]
    inclusion_reason: Optional[str]
    is_excluded: bool
    retrieval_timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class ClaimMappingResponse(BaseModel):
    id: uuid.UUID
    claim_id: str
    claim_text: str
    claim_type: str
    citation_strength: str
    requires_review: bool
    section_reference: Optional[str]
    inline_citation_marker: Optional[str]
    validation_passed: Optional[bool]
    validation_note: Optional[str]
    evidence_id: Optional[uuid.UUID]

    model_config = ConfigDict(from_attributes=True)


class ResearchJobSummary(BaseModel):
    id: uuid.UUID
    report_id: uuid.UUID
    status: str
    paper_title: Optional[str]
    research_question: str
    paper_type: str
    depth: str
    citation_format: str
    consent_confirmed: bool
    sources_retrieved: int
    sources_excluded: int
    evidence_coverage_pct: Optional[float]
    citation_validity_count: int
    citation_total_count: int
    flagged_claims_count: int
    providers_attempted: Optional[List[str]]
    providers_succeeded: Optional[List[str]]
    providers_failed: Optional[Dict[str, str]]
    error_message: Optional[str]
    failed_stage: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    approved_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ResearchJobDetail(ResearchJobSummary):
    scrub_findings: Optional[Dict[str, Any]]
    sanitized_question: Optional[str]
    research_plan: Optional[Dict[str, Any]]
    executed_queries: Optional[List[Dict[str, Any]]]
    citation_validation_result: Optional[Dict[str, Any]]
    review_checklist: Optional[Dict[str, Any]]
    reviewer_notes: Optional[str]
    paper_outline: Optional[Dict[str, Any]]
    paper_content: Optional[str]
    artifact_pdf_path: Optional[str]
    evidence_blocks: List[EvidenceBlockResponse] = []
    claim_mappings: List[ClaimMappingResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ProviderHealthResponse(BaseModel):
    providers: Dict[str, bool]
    available_count: int
    total_count: int
    timestamp: str
