import logging
import uuid
from typing import Dict, List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import get_current_user_from_token, security_bearer
from src.db.models import AgentRun, AgentTask, Project, Report, ReportSource, Source, User, UserRole
from src.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sources", tags=["Sources"])


class SourceItem(BaseModel):
    id: str
    url: str
    title: str
    domain: str
    category: str
    report_id: Optional[str] = None
    report_title: Optional[str] = None
    linked_report_count: int = 1
    """COUNT(DISTINCT report_sources.report_id) for this source, scoped to visible reports."""
    occurrence_count: int = 1
    """Number of report-source reference rows for this source URL across visible reports."""
    verified: bool = True
    confidence: float = 0.95


class SourceStats(BaseModel):
    total: int
    """COUNT(DISTINCT sources.id) for visible authorized sources."""
    academic_domain_count: int
    """Subset of visible sources whose URL domain matches known academic publisher patterns."""
    academic_domain_classification: str = "heuristic_url_domain"
    note: str = (
        "Academic-domain classification is inferred from source URL domains "
        "(arxiv.org, doi.org, ieee.org, nature.com, etc.) and is not a verified "
        "peer-review classification."
    )
    filtered_by_category: Optional[str] = None
    """Present when stats are scoped to a specific category filter."""


def _categorize_domain(domain: str) -> str:
    """
    Heuristic URL-domain classification.
    Returns one of: 'academic' | 'technical' | 'financial' | 'general'.
    This is NOT a peer-review classification.
    """
    d = domain.lower()
    if any(k in d for k in ["arxiv", "nature", "ieee", "science", "doi.org", "acm.org", "biorxiv"]):
        return "academic"
    if any(k in d for k in ["github", "gitlab", "huggingface", "docs.", "dev."]):
        return "technical"
    if any(k in d for k in ["sec.gov", "bloomberg", "reuters", "wsj", "ft.com", "federalreserve"]):
        return "financial"
    return "general"


async def _resolve_current_user(
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials],
    db: AsyncSession,
) -> Optional[User]:
    """Resolve caller identity from Bearer token or session cookie. Raises 401 on invalid token."""
    token = auth.credentials if auth else None
    if not token and hasattr(request, "cookies"):
        token = request.cookies.get("quorum_session")
    if not token:
        return None
    user = await get_current_user_from_token(token, db=db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def _build_visible_report_uuids(
    current_user: Optional[User],
    db: AsyncSession,
) -> List[uuid.UUID]:
    """
    Return UUIDs of reports visible to the caller, respecting owner/guest/admin policy.
    Returns an empty list when there are no visible reports.
    """
    stmt = (
        select(Report.id)
        .join(Project, Report.project_id == Project.id)
    )
    if current_user is None or current_user.role == UserRole.GUEST.value:
        stmt = stmt.where(Report.is_guest_demo.is_(True), Project.is_guest_demo.is_(True))
    elif current_user.role == UserRole.ADMIN.value:
        pass  # admin sees all
    else:
        stmt = stmt.where(Project.user_id == current_user.id)

    res = await db.execute(stmt)
    return [row[0] for row in res.all()]


async def _build_visible_sources(
    current_user: User,
    category: Optional[str],
    db: AsyncSession,
) -> List[SourceItem]:
    """
    Retrieve unique visible sources aggregated from research reports.
    Both GET /api/sources and GET /api/sources/stats share this exact definition.
    """
    report_uuids = await _build_visible_report_uuids(current_user, db)
    if not report_uuids:
        return []

    # ── 1. Compute linked_report_count per Source.id via SQL aggregation ─────
    #   COUNT(DISTINCT report_sources.report_id) scoped to visible reports.
    linked_count_stmt = (
        select(
            ReportSource.source_id,
            func.count(ReportSource.report_id.distinct()).label("linked_count"),
        )
        .where(ReportSource.report_id.in_(report_uuids))
        .group_by(ReportSource.source_id)
    )
    linked_res = await db.execute(linked_count_stmt)
    linked_count_by_source_id: Dict[uuid.UUID, int] = {
        row.source_id: row.linked_count for row in linked_res.all()
    }

    # ── 2. Fetch source rows joined to one representative report ──────────────
    source_stmt = (
        select(Source, ReportSource.report_id, Report.query)
        .join(ReportSource, ReportSource.source_id == Source.id)
        .join(Report, ReportSource.report_id == Report.id)
        .where(ReportSource.report_id.in_(report_uuids))
        .order_by(Source.created_at.desc())
    )
    src_res = await db.execute(source_stmt)

    # sources_map deduplicates by URL; occurrence_count tracks raw join row count
    sources_map: Dict[str, SourceItem] = {}

    for s, rep_id, rep_query in src_res.all():
        url = s.url.strip()
        parsed = urlparse(url)
        domain = parsed.netloc or "web"
        cat = _categorize_domain(domain if domain != "web" else url)

        # Apply category filter — same heuristic as stats endpoint
        if category and category != "all" and cat != category:
            continue

        rep_id_str = str(rep_id)
        rep_title = rep_query[:100] if rep_query else None
        lrc = linked_count_by_source_id.get(s.id, 1)

        if url in sources_map:
            sources_map[url].occurrence_count += 1
            # Keep the first representative report; update linked count to max
            sources_map[url].linked_report_count = max(sources_map[url].linked_report_count, lrc)
        else:
            sources_map[url] = SourceItem(
                id=str(s.id),
                url=url,
                title=s.title or url,
                domain=domain,
                category=cat,
                report_id=rep_id_str,
                report_title=rep_title,
                linked_report_count=lrc,
                occurrence_count=1,
                verified=True,
                confidence=0.96,
            )

    # ── 3. Augment with agent-task claim evidence (unstructured findings) ─────
    task_stmt = (
        select(AgentTask.result, AgentRun.report_id)
        .join(AgentRun, AgentTask.agent_run_id == AgentRun.id)
        .where(
            AgentRun.report_id.in_(report_uuids),
            AgentTask.result.isnot(None),
        )
    )
    task_res = await db.execute(task_stmt)
    for result_json, rep_id in task_res.all():
        if not isinstance(result_json, dict):
            continue
        rep_id_str = str(rep_id)

        # Update verification status for already-known sources from evaluations
        for ev in result_json.get("evaluations", []):
            if isinstance(ev, dict) and ev.get("source_url"):
                ev_url = ev["source_url"].strip()
                if ev_url in sources_map:
                    sources_map[ev_url].verified = (ev.get("status") == "verified")
                    sources_map[ev_url].confidence = float(ev.get("confidence", 0.95))
    return list(sources_map.values())


@router.get(
    "/stats",
    response_model=SourceStats,
    summary="Backend-authoritative source statistics for the current caller's visible scope",
)
async def get_source_stats(
    request: Request,
    category: Optional[str] = None,
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> SourceStats:
    """
    Returns aggregate source statistics scoped to the same visibility rules as GET /api/sources.

    - total: COUNT(DISTINCT visible sources) identical to GET /api/sources item count
    - academic_domain_count: subset classified as 'academic' by URL-domain heuristic
    - Category filter scopes both total and academic_domain_count to that category.
    """
    current_user = await _resolve_current_user(request, auth, db)
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access source statistics",
            headers={"WWW-Authenticate": "Bearer"},
        )
    sources = await _build_visible_sources(current_user, category, db)
    total = len(sources)
    academic_count = sum(1 for s in sources if s.category == "academic")

    return SourceStats(
        total=total,
        academic_domain_count=academic_count,
        filtered_by_category=category if (category and category != "all") else None,
    )


@router.get(
    "",
    response_model=List[SourceItem],
    summary="List all harvested research sources visible to the current caller",
)
async def list_sources(
    request: Request,
    category: Optional[str] = None,
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> List[SourceItem]:
    """
    Retrieve unique visible sources aggregated from research reports.

    - Authenticated callers (owner/member) see sources from their own projects' reports.
    - Guest evaluators see only sources from explicitly curated demo reports.
    - Unauthenticated callers receive 401.
    - occurrence_count: number of report-source reference rows for this URL across visible reports.
    - linked_report_count: COUNT(DISTINCT report_id) for this source across visible reports.
    """
    current_user = await _resolve_current_user(request, auth, db)
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access source library",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await _build_visible_sources(current_user, category, db)
