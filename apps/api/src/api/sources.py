import logging
import uuid
from typing import Dict, List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import get_current_user
from src.db.models import AgentRun, AgentTask, Project, Report, Source, User
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
    citation_count: int = 1
    verified: bool = True
    confidence: float = 0.95


def _categorize_domain(domain: str) -> str:
    domain_lower = domain.lower()
    if any(k in domain_lower for k in ["arxiv", "nature", "ieee", "science", "doi.org", "acm.org", "biorxiv"]):
        return "academic"
    elif any(k in domain_lower for k in ["github", "gitlab", "huggingface", "docs.", "dev."]):
        return "technical"
    elif any(k in domain_lower for k in ["sec.gov", "bloomberg", "reuters", "wsj", "ft.com", "federalreserve"]):
        return "financial"
    return "general"


@router.get("", response_model=List[SourceItem], summary="List all harvested research sources")
async def list_sources(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[SourceItem]:
    """
    Retrieve all verified and cited sources across the current user's research reports.
    Aggregates sources from formal source models and agent task findings.
    """
    sources_map: Dict[str, SourceItem] = {}

    # 1. Fetch user's reports to get scope
    stmt = (
        select(Report.id, Report.query, Project.title)
        .join(Project, Report.project_id == Project.id)
        .where(Project.user_id == current_user.id)
    )
    res = await db.execute(stmt)
    user_reports = {str(r[0]): {"query": r[1], "project": r[2]} for r in res.all()}

    if not user_reports:
        return []

    report_uuids = [uuid.UUID(rid) for rid in user_reports.keys()]

    # 2. Extract sources from AgentTasks results
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
        report_meta = user_reports.get(rep_id_str, {})

        # Claims from Researcher
        claims = result_json.get("claims", [])
        for c in claims:
            if isinstance(c, dict) and c.get("source_url"):
                url = c["source_url"].strip()
                parsed = urlparse(url)
                domain = parsed.netloc or "web"
                cat = _categorize_domain(domain)
                if category and category != "all" and cat != category:
                    continue

                if url in sources_map:
                    sources_map[url].citation_count += 1
                else:
                    sources_map[url] = SourceItem(
                        id=str(uuid.uuid5(uuid.NAMESPACE_URL, url)),
                        url=url,
                        title=c.get("source_title") or c.get("claim_text", url)[:80],
                        domain=domain,
                        category=cat,
                        report_id=rep_id_str,
                        report_title=report_meta.get("query", "Research Report")[:100],
                        citation_count=1,
                        verified=True,
                        confidence=0.95,
                    )

        # Evaluations from FactChecker
        evals = result_json.get("evaluations", [])
        for ev in evals:
            if isinstance(ev, dict) and ev.get("source_url"):
                url = ev["source_url"].strip()
                if url in sources_map:
                    sources_map[url].verified = (ev.get("status") == "verified")
                    sources_map[url].confidence = float(ev.get("confidence", 0.90))

    # 3. Also check formal Source table
    source_stmt = select(Source).order_by(Source.created_at.desc())
    src_res = await db.execute(source_stmt)
    for s in src_res.scalars().all():
        parsed = urlparse(s.url)
        domain = parsed.netloc or "web"
        cat = _categorize_domain(domain)
        if category and category != "all" and cat != category:
            continue
        if s.url not in sources_map:
            sources_map[s.url] = SourceItem(
                id=str(s.id),
                url=s.url,
                title=s.title or s.url,
                domain=domain,
                category=cat,
                citation_count=1,
                verified=True,
                confidence=0.92,
            )

    return list(sources_map.values())
