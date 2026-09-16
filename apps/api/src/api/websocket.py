import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from src.core.events import format_report_channel, subscribe_to_channel
from src.core.security import get_current_user_ws
from src.db.models import Project, Report, User
from src.db.session import async_session_maker

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/reports/{report_id}")
async def stream_report_status(
    websocket: WebSocket,
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user_ws),
):
    """
    WebSocket endpoint streaming real-time status events for a specific report:
    1. Verifies requesting user owns the report (via user_id foreign key on project)
    2. Subscribes to the report's Redis pub/sub channel
    3. Forwards every event formatted as JSON { type, data, timestamp }
    4. Cleanly handles disconnects and releases Redis pub/sub resources
    """
    # Verify report ownership
    async with async_session_maker() as session:
        stmt = (
            select(Report)
            .join(Project, Report.project_id == Project.id)
            .where(Report.id == report_id, Project.user_id == current_user.id)
        )
        res = await session.execute(stmt)
        report = res.scalars().first()

        if not report:
            logger.warning(
                f"[WS] User {current_user.id} unauthorized or report {report_id} not found."
            )
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Report not found or permission denied",
            )
            return

    await websocket.accept()
    logger.info(
        f"[WS] Client connected for report {report_id} (user: {current_user.email})"
    )

    channel = format_report_channel(report_id)

    try:
        # Stream events from Redis pub/sub to WebSocket
        async for event in subscribe_to_channel(channel):
            event_type = event.get("type", "report_status")
            if event_type not in ("agent_status", "task_status", "report_status"):
                # Normalize event type
                event_type = "report_status"

            payload = {
                "type": event_type,
                "data": event.get("data", {}),
                "timestamp": event.get("timestamp", datetime.now(timezone.utc).isoformat()),
            }
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        logger.info(f"[WS] Client disconnected from report {report_id}")
    except Exception as exc:
        logger.error(f"[WS] Error streaming events for report {report_id}: {exc}")
    finally:
        logger.info(f"[WS] Cleaned up WebSocket session for report {report_id}")
