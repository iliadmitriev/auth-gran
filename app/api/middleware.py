import time
from uuid import uuid4

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger("http")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
        )

        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000

        # Skip logging for health checks
        if request.url.path != "/health":
            await logger.adebug(
                "HTTP request",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time=process_time,
                client_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )

        response.headers["x-request-id"] = request_id

        return response
