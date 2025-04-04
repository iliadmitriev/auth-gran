import logging
import os
import sys
import time
from typing import Any, TypedDict

import structlog
from asgiref.typing import (
    ASGI3Application,
    ASGIReceiveCallable,
    ASGISendCallable,
    ASGISendEvent,
    HTTPScope,
)


class AccessInfo(TypedDict, total=False):
    response: ASGISendEvent
    start_time: float
    end_time: float
    status: int


class AccessLoggerMiddleware:
    def __init__(
        self,
        app: ASGI3Application,
        logger: structlog.BoundLogger | None = None,
    ) -> None:
        self.app = app
        if logger is None:
            logger = get_logger("access")

        self.logger = logger

    async def __call__(
        self, scope: HTTPScope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        log_info = AccessInfo()

        async def inner_send(message: ASGISendEvent) -> None:
            if message["type"] == "http.response.start":
                log_info["response"] = message
            await send(message)

        try:
            log_info["start_time"] = time.monotonic()
            await self.app(scope, receive, inner_send)
        except Exception as ex:
            log_info["status"] = 500
            raise ex
        finally:
            log_info["end_time"] = time.monotonic()
            await self.logger.ainfo("request", **AccessLogAtoms(scope, log_info))


class AccessLogAtoms(dict[str, object]):
    def __init__(self, scope: HTTPScope, info: AccessInfo) -> None:
        for name, value in scope["headers"]:
            key = name.decode("latin1").lower().replace("-", "_")
            self[f"{key}_input"] = value.decode("latin1")

        for name, value in info.get("response", {}).get("headers", []):
            key = name.decode("latin1").lower().replace("-", "_")
            self[f"{key}_output"] = value.decode("latin1")

        protocol = f"HTTP/{scope['http_version']}"

        status = info.get("response", {}).get("status")

        request_time = info.get("end_time", 0) - info.get("start_time", 0)
        client_addr = get_client_addr(scope)
        self.update(
            {
                "client_addr": client_addr,
                "timestamp": time.strftime("[%d/%b/%Y:%H:%M:%S %z]"),
                "method": scope["method"],
                "path": scope["path"],
                "query": scope["query_string"].decode(),
                "scheme": protocol,
                "status_code": status,
                "request_time_ms": request_time * 1000,
                "pid": os.getpid(),
            }
        )

    def __getitem__(self, key: str) -> object:
        try:
            return super().__getitem__(key)
        except KeyError:
            return "-"


def configure_logging(debug: bool = False) -> None:
    """Configure structlog with console rendering."""
    timestamper = structlog.processors.TimeStamper(fmt="iso")

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if debug:
        processors = shared_processors + [structlog.dev.ConsoleRenderer()]
    else:
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # disable multipart logger
    multipart_logger = logging.getLogger("python_multipart.multipart")
    multipart_logger.setLevel(logging.ERROR)
    multipart_logger.addHandler(handler)

    # uvcorn loggers erase handlers
    uvicorn_logger = logging.getLogger("uvcorn.access")
    uvicorn_logger.handlers = []
    uvicorn_error = logging.getLogger("uvicorn.error")
    uvicorn_error.handlers = []

    # Capture warnings
    logging.captureWarnings(True)


def get_logger(name: str | None = None) -> Any:
    """Get a structlog logger instance."""
    return structlog.get_logger(name)


def get_client_addr(scope: HTTPScope):
    if scope["client"] is None:
        return "-"  # pragma: no cover
    return f"{scope['client'][0]}:{scope['client'][1]}"
