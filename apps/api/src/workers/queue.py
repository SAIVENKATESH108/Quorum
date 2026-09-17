import asyncio
import logging
from typing import Any, Dict, Optional

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from src.agents.commands import AgentTaskCommand
from src.core.config import settings
from src.workers.main import process_agent_task

logger = logging.getLogger(__name__)

_arq_pool: Optional[ArqRedis] = None


async def get_queue_pool() -> Optional[ArqRedis]:
    """Get or create arq Redis connection pool."""
    global _arq_pool
    if _arq_pool is not None:
        return _arq_pool

    redis_url = settings.REDIS_URL or "redis://localhost:6379/0"
    try:
        pool = await create_pool(RedisSettings.from_dsn(redis_url))
        _arq_pool = pool
        return _arq_pool
    except Exception as exc:
        logger.warning(f"[QUEUE] Could not connect to external arq Redis ({exc}). Direct async worker fallback will be used.")
        return None


async def enqueue_agent_task(command: AgentTaskCommand, max_retries: int = 3, provider: Optional[Any] = None) -> Dict[str, Any]:
    """
    Retry-safe task dispatch:
    - Attempts to enqueue the AgentTaskCommand into the arq Redis queue.
    - If no external queue worker is connected, dispatches via retry-safe async execution with exponential backoff.
    """
    command_dict = command.to_dict()
    import os
    use_external = os.getenv("USE_EXTERNAL_WORKER", "false").lower() in ("1", "true", "yes")

    if provider is None and use_external:
        pool = await get_queue_pool()
        if pool is not None:
            try:
                job = await pool.enqueue_job(
                    "process_agent_task",
                    command_dict,
                    _max_tries=max_retries,
                )
                logger.info(f"[QUEUE] Enqueued job {job.job_id} for command {command.command_id}")
                # Await result if job is tracked
                result = await job.result(timeout=60, poll_delay=0.5)
                return result
            except Exception as exc:
                logger.warning(f"[QUEUE] Error via arq enqueue ({exc}), falling back to direct retry-safe execution.")

    # In-process retry-safe execution with exponential backoff
    last_error = None
    for attempt in range(max_retries):
        try:
            command.retry_count = attempt
            return await process_agent_task(ctx=None, command_data=command.to_dict(), provider=provider)
        except Exception as exc:
            last_error = exc
            if command.is_retryable(exc) and attempt < max_retries - 1:
                delay = 0.5 * (2 ** attempt)
                logger.warning(
                    f"[QUEUE] Task attempt {attempt + 1}/{max_retries} failed: {exc}. Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
            else:
                break

    raise RuntimeError(f"Task dispatch failed after {max_retries} retries: {last_error}") from last_error
