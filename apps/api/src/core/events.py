import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict

from src.core.redis import get_redis_client

logger = logging.getLogger(__name__)


def format_report_channel(report_id: Any) -> str:
    """Channel naming convention: report:{report_id}:events"""
    return f"report:{str(report_id)}:events"


async def publish_event(channel: str, event: Dict[str, Any]) -> None:
    """
    Publish an event to a Redis pub/sub channel.
    Ensures standard event shape: { type, data, timestamp }.
    """
    client = await get_redis_client()

    # Format event shape if needed
    if "type" not in event or "data" not in event:
        formatted = {
            "type": event.get("event_type", "status_update"),
            "data": event.get("metadata", event),
            "timestamp": event.get("timestamp", datetime.now(timezone.utc).isoformat()),
        }
    else:
        formatted = dict(event)
        if "timestamp" not in formatted:
            formatted["timestamp"] = datetime.now(timezone.utc).isoformat()

    payload = json.dumps(formatted)
    try:
        await client.publish(channel, payload)
        logger.debug(f"[PUB/SUB] Published to '{channel}': {payload}")
    except Exception as exc:
        logger.error(f"[PUB/SUB] Error publishing to '{channel}': {exc}")
        raise


async def subscribe_to_channel(channel: str) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Async generator subscribing to a Redis pub/sub channel.
    Yields parsed JSON event dictionaries.
    Ensures clean unsubscribe and connection cleanup when closed.
    """
    client = await get_redis_client()
    pubsub = client.pubsub()

    try:
        await pubsub.subscribe(channel)
        logger.info(f"[PUB/SUB] Subscribed to channel '{channel}'")

        async for message in pubsub.listen():
            if message and message.get("type") == "message":
                data = message.get("data")
                if isinstance(data, (bytes, bytearray)):
                    data = data.decode("utf-8")
                try:
                    event_dict = json.loads(data)
                    yield event_dict
                except Exception as exc:
                    logger.warning(f"[PUB/SUB] Failed to parse JSON message from '{channel}': {exc}")
    finally:
        try:
            await pubsub.unsubscribe(channel)
            if hasattr(pubsub, "aclose"):
                await pubsub.aclose()
            else:
                await pubsub.close()
            logger.info(f"[PUB/SUB] Unsubscribed and closed pubsub for '{channel}'")
        except Exception as exc:
            logger.warning(f"[PUB/SUB] Error during pubsub cleanup for '{channel}': {exc}")
