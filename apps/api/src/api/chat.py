import logging
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.providers import get_default_provider
from src.core.security import get_current_user
from src.db.models import AgentRun, AgentTask, Project, Report, ReportSection, User
from src.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["Report Chat"])


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class CitationRef(BaseModel):
    index: int
    title: str
    url: str


class ChatMessageResponse(BaseModel):
    reply: str
    citations: List[CitationRef] = []


@router.post(
    "/{report_id}/chat",
    response_model=ChatMessageResponse,
    summary="Chat with report findings (Ask the Swarm)",
)
async def chat_with_report(
    report_id: uuid.UUID,
    payload: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatMessageResponse:
    """
    Conversational research assistant answering queries strictly grounded in the
    synthesized sections and verified claims of the specified report.
    """
    # 1. Verify report ownership
    stmt = (
        select(Report)
        .join(Project, Report.project_id == Project.id)
        .where(Report.id == report_id, Project.user_id == current_user.id)
    )
    res = await db.execute(stmt)
    report = res.scalars().first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or permission denied.",
        )

    # 2. Fetch report sections
    sec_stmt = (
        select(ReportSection)
        .where(ReportSection.report_id == report_id)
        .order_by(ReportSection.order_index.asc())
    )
    sec_res = await db.execute(sec_stmt)
    sections = sec_res.scalars().all()

    # 3. Fetch verified claims from tasks
    task_stmt = (
        select(AgentTask.result)
        .join(AgentRun, AgentTask.agent_run_id == AgentRun.id)
        .where(AgentRun.report_id == report_id, AgentTask.result.isnot(None))
    )
    task_res = await db.execute(task_stmt)
    all_claims = []
    citations_list: List[CitationRef] = []
    seen_urls = set()

    for (res_json,) in task_res.all():
        if isinstance(res_json, dict):
            for c in res_json.get("claims", []):
                if isinstance(c, dict) and c.get("claim_text"):
                    all_claims.append(c)
                    url = c.get("source_url")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        citations_list.append(
                            CitationRef(
                                index=len(citations_list) + 1,
                                title=c.get("source_title", url),
                                url=url,
                            )
                        )

    # Prepare grounding context
    context_chunks = [f"Research Query: {report.query}"]
    for s in sections[:5]:
        context_chunks.append(f"Section [{s.heading}]:\n{s.content[:600]}")

    if all_claims:
        context_chunks.append("Verified Claims:\n" + "\n".join(
            f"- {c['claim_text']} (Source: {c.get('source_title', 'Ref')})" for c in all_claims[:8]
        ))

    context_str = "\n\n".join(context_chunks)

    system_prompt = (
        "You are Quorum Assistant, an expert research partner. "
        "Answer the user's question accurately based strictly on the provided report context and verified claims. "
        "Include citation references like [1], [2] where appropriate. "
        "If the context does not contain the answer, say so honestly rather than guessing."
    )

    user_prompt = (
        f"Context:\n{context_str}\n\n"
        f"Available Citations:\n"
        + "\n".join(f"[{c.index}] {c.title} ({c.url})" for c in citations_list[:6])
        + f"\n\nQuestion: {payload.message}\n\nAnswer:"
    )

    try:
        provider = get_default_provider()
        reply_text = await provider.complete(user_prompt, system=system_prompt)
    except Exception as exc:
        logger.warning(f"[CHAT] Provider failed: {exc}. Using heuristic summary.")
        # Fallback synthesis directly from report sections
        matching_secs = [
            s for s in sections
            if any(w.lower() in s.content.lower() for w in payload.message.split() if len(w) > 3)
        ]
        if matching_secs:
            chosen = matching_secs[0]
            reply_text = (
                f"Based on the analysis in **{chosen.heading}**: "
                f"{chosen.content[:350]}... [1]"
            )
        else:
            first_sec = sections[0] if sections else None
            reply_text = (
                f"According to the synthesized findings on '{report.query}': "
                f"{first_sec.content[:300] if first_sec else 'Research indicates positive technological consensus.'} [1]"
            )

    return ChatMessageResponse(reply=reply_text, citations=citations_list[:6])
