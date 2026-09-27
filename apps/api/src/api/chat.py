import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_user_report
from src.core.security import get_current_user_from_token, security_bearer
from src.db.models import Project, Report, User, UserRole
from src.db.session import get_db
from src.services.rag.chat_engine import (
    ABSTENTION_TEXT,
    SwarmChatEngine,
    SwarmChatResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["Report Chat"])


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class CitationRef(BaseModel):
    index: int
    title: str
    url: str
    access_level: Optional[str] = None
    score: Optional[float] = None


class ChatMessageResponse(BaseModel):
    reply: str
    citations: List[CitationRef] = []
    abstained: bool = False
    retrieved_count: int = 0
    diagnostics: Optional[Dict[str, Any]] = None


# Global singleton instance of SwarmChatEngine
_chat_engine = SwarmChatEngine()


@router.post(
    "/{report_id}/chat",
    response_model=ChatMessageResponse,
    summary="Chat with report findings (Ask the Swarm)",
)
async def chat_with_report(
    report_id: uuid.UUID,
    payload: ChatMessageRequest,
    request: Request,
    report: Report = Depends(get_user_report),
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> ChatMessageResponse:
    """
    Evidence-grounded conversational research assistant answering queries strictly grounded
    in the synthesized sections and verified sources of the specified report.
    Supports authenticated users and guest read-only access for published reports
    while strictly enforcing database-level project/report boundary in vector retrieval.
    Excludes private code and local-folder chunks for guest evaluators at SQL level.
    """
    token = auth.credentials if auth else None
    if not token and hasattr(request, "cookies"):
        token = request.cookies.get("quorum_session")

    current_user: Optional[User] = None
    if token:
        current_user = await get_current_user_from_token(token, db=db)

    is_guest = current_user is None or current_user.role == UserRole.GUEST.value
    access_level = "public" if is_guest else None

    # 2. Execute grounded RAG chat turn with SQL-level exclusion for guests
    try:
        result: SwarmChatResult = await _chat_engine.chat(
            session=db,
            project_id=report.project_id,
            report_id=report.id,
            user_query=payload.message,
            access_level=access_level,
            exclude_code_and_local=is_guest,
            top_k=5,
            min_similarity=0.30,
        )
        await db.commit()
    except Exception as exc:
        logger.error(f"[SwarmChat] RAG execution error: {exc}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve evidence or generate response.",
        )

    citations_list = [
        CitationRef(
            index=c.index,
            title=c.title,
            url=c.url,
            access_level=c.access_level,
            score=c.score,
        )
        for c in result.citations
    ]

    return ChatMessageResponse(
        reply=result.reply,
        citations=citations_list,
        abstained=result.abstained,
        retrieved_count=result.retrieved_count,
        diagnostics=result.diagnostics,
    )
