import time
import logging
from typing import Optional
from fastapi import HTTPException, status

from src.core.config import settings
from src.core.redis import get_redis_client
from src.db.models import User

logger = logging.getLogger("quorum.rate_limiter")


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter using Redis sorted sets (ZSET).
    Tracks request timestamps within a sliding time window.
    """

    def __init__(self, limit: int = 10, window_seconds: int = 3600):
        self.limit = limit
        self.window_seconds = window_seconds

    async def check_rate_limit(self, identifier: str, custom_limit: Optional[int] = None) -> bool:
        """
        Check if the identifier has exceeded the allowed rate limit.
        Returns True if request is allowed, False if exceeded.
        """
        max_requests = custom_limit or self.limit
        redis = await get_redis_client()
        key = f"ratelimit:report_create:{identifier}"
        now = time.time()
        window_start = now - self.window_seconds

        try:
            # 1. Remove entries older than sliding window
            await redis.zremrangebyscore(key, 0, window_start)

            # 2. Count requests currently in window
            current_count = await redis.zcard(key)

            if current_count >= max_requests:
                logger.warning(
                    f"[RATE_LIMIT] Identifier {identifier} exceeded limit {max_requests} ({current_count} requests in window)"
                )
                return False

            # 3. Add current request timestamp (using timestamp as score and unique string as member)
            unique_member = f"{now}:{time.time_ns()}"
            await redis.zadd(key, {unique_member: now})

            # 4. Set TTL on the key to ensure it automatically expires
            await redis.expire(key, self.window_seconds)
            return True

        except Exception as exc:
            logger.error(f"[RATE_LIMIT] Redis error during rate limit check: {exc}. Permitting request.")
            # Fail open if Redis has a transient error to avoid breaking legitimate user flows
            return True


# Global default rate limiter instance
report_rate_limiter = SlidingWindowRateLimiter(
    limit=settings.REPORT_RATE_LIMIT_PER_HOUR,
    window_seconds=3600,
)


from fastapi import Depends
from src.core.security import get_current_user


async def check_report_creation_rate_limit(user: User = Depends(get_current_user)) -> None:
    """FastAPI dependency to enforce sliding window rate limiting on report creation."""
    is_allowed = await report_rate_limiter.check_rate_limit(str(user.id))
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: maximum {settings.REPORT_RATE_LIMIT_PER_HOUR} report creations per hour.",
        )

