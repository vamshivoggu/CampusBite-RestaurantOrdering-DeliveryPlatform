"""Request logging / timing middleware."""
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("campusbite.http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs method, path, status and duration of every request; adds X-Request-ID and
    X-Process-Time headers; converts unhandled exceptions into a JSON 500 response."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception("%s %s -> 500 (%.1f ms) [req %s]", request.method, request.url.path, elapsed_ms, request_id)
            response = JSONResponse({"detail": "Internal server error", "request_id": request_id}, status_code=500)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{elapsed_ms:.2f}ms"
        level = logging.WARNING if elapsed_ms > 1000 else logging.INFO
        logger.log(level, "%s %s -> %s (%.1f ms) [req %s]", request.method, request.url.path,
                   response.status_code, elapsed_ms, request_id)
        return response
