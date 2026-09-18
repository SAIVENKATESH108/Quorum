import asyncio
import logging
from typing import Optional

import redis.asyncio as aioredis
from redis.asyncio import Redis

from src.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[Redis] = None
_fake_server = None
_redis_lock = asyncio.Lock()
_use_fallback = False


async def get_redis_client() -> Redis:
    """
    Get or create an async Redis client using REDIS_URL from settings.
    Gracefully falls back to FakeRedis with shared server if no Redis server is reachable.
    """
    global _redis_client, _fake_server, _use_fallback
    if _redis_client is not None:
        return _redis_client

    async with _redis_lock:
        if _redis_client is not None:
            return _redis_client

        redis_url = settings.REDIS_URL or "redis://127.0.0.1:6379/0"
        if "localhost" in redis_url:
            redis_url = redis_url.replace("localhost", "127.0.0.1")

        if not _use_fallback:
            try:
                # Create client and test connection with a short timeout
                client = aioredis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=0.1,
                    socket_timeout=None,
                )
                await asyncio.wait_for(client.ping(), timeout=0.1)
                logger.info(f"[REDIS] Connected to Redis at {redis_url}")
                _redis_client = client
                return _redis_client
            except Exception as exc:
                logger.warning(
                    f"[REDIS] Could not connect to Redis at {redis_url} ({exc}). Using in-memory FakeRedis fallback."
                )
                _use_fallback = True


        # Fallback to shared FakeServer
        try:
            import fakeredis
            import fakeredis.aioredis
            if _fake_server is None:
                _fake_server = fakeredis.FakeServer()
            _redis_client = fakeredis.aioredis.FakeRedis(server=_fake_server, decode_responses=True)
            return _redis_client
        except ImportError:
            raise RuntimeError(f"Failed to connect to Redis at {redis_url} and fakeredis is not installed.")


async def close_redis_client() -> None:
    """Close active Redis connections."""
    global _redis_client
    if _redis_client is not None:
        try:
            if hasattr(_redis_client, "aclose"):
                await _redis_client.aclose()
            else:
                await _redis_client.close()
        except Exception as exc:
            logger.warning(f"[REDIS] Error closing Redis client: {exc}")
        _redis_client = None
