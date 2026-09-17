import json
import logging
import time
import uuid
from collections.abc import Callable
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class StructuredJSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects for production ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        req_id = getattr(record, "request_id", None) or request_id_ctx.get()
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if req_id:
            log_entry["request_id"] = req_id

        if hasattr(record, "agent_role"):
            log_entry["agent_role"] = record.agent_role

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging(level: int = logging.INFO) -> None:
    """Configures root logger with structured JSON output."""
    root = logging.getLogger()
    root.setLevel(level)

    # Avoid duplicate handlers on reloads
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredJSONFormatter())
        root.addHandler(handler)
    else:
        for h in root.handlers:
            h.setFormatter(StructuredJSONFormatter())


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Assigns a unique correlation ID to every incoming request.
    Correlates logs, measures latency, and propagates X-Request-ID.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract or generate unique request ID
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(req_id)
        request.state.request_id = req_id

        start_time = time.perf_counter()
        logger = logging.getLogger("quorum.api.access")

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            response.headers["X-Request-ID"] = req_id

            # Log completion as structured log entry
            logger.info(
                f"{request.method} {request.url.path} {response.status_code} - {duration_ms}ms",
                extra={
                    "request_id": req_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            return response
        except Exception:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception(
                f"Unhandled exception on {request.method} {request.url.path}",
                extra={
                    "request_id": req_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
            raise
        finally:
            request_id_ctx.reset(token)
