import http
import logging
import os
import sys
import time
from typing import Any, TypedDict
from urllib.parse import quote

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


class AccessLoggerMiddleware:
    def __init__(
        self,
        app: ASGI3Application,
        logger: logging.Logger | None = None,
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

        log_info = AccessInfo(response={})

        async def inner_send(message: ASGISendEvent) -> None:
            if message["type"] == "http.response.start":
                log_info["response"] = message
            await send(message)

        try:
            log_info["start_time"] = time.monotonic()
            await self.app(scope, receive, inner_send)
        except Exception as ex:
            log_info["response"]["status"] = 500
            raise ex
        finally:
            log_info["end_time"] = time.monotonic()
            self.logger.info("request", **AccessLogAtoms(scope, log_info))


class AccessLogAtoms(dict):
    def __init__(self, scope: HTTPScope, info: AccessInfo) -> None:
        for name, value in scope["headers"]:
            self[f"{{{name.decode('latin1').lower()}}}i"] = value.decode("latin1")
        for name, value in info["response"].get("headers", []):
            self[f"{{{name.decode('latin1').lower()}}}o"] = value.decode("latin1")
        # for name, value in os.environ.items():
        #     self[f"{{{name.lower()!r}}}e"] = value

        protocol = f"HTTP/{scope['http_version']}"

        status = info["response"]["status"]
        try:
            status_phrase = http.HTTPStatus(status).phrase
        except ValueError:
            status_phrase = "-"

        path = scope["root_path"] + scope["path"]
        full_path = get_path_with_query_string(scope)
        request_line = f"{scope['method']} {path} {protocol}"
        full_request_line = f"{scope['method']} {full_path} {protocol}"

        request_time = info["end_time"] - info["start_time"]
        client_addr = get_client_addr(scope)
        self.update(
            {
                "h": client_addr,
                "client_addr": client_addr,
                "l": "-",
                "u": "-",  # Not available on ASGI.
                "t": time.strftime("[%d/%b/%Y:%H:%M:%S %z]"),
                "r": request_line,
                "request_line": full_request_line,
                "R": full_request_line,
                "m": scope["method"],
                "U": scope["path"],
                "q": scope["query_string"].decode(),
                "H": protocol,
                "s": status,
                "status_code": f"{status} {status_phrase}",
                "st": status_phrase,
                "B": self["{Content-Length}o"],
                "b": self.get("{Content-Length}o", "-"),
                "f": self["{Referer}i"],
                "a": self["{User-Agent}i"],
                "T": int(request_time),
                "M": int(request_time * 1_000),
                "D": int(request_time * 1_000_000),
                "L": f"{request_time:.6f}",
                "p": f"<{os.getpid()}>",
            }
        )

    def __getitem__(self, key: str) -> str:
        try:
            if key.startswith("{"):
                return super().__getitem__(key.lower())
            else:
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

    # Capture warnings
    logging.captureWarnings(True)


def get_logger(name: str | None = None) -> Any:
    """Get a structlog logger instance."""
    return structlog.get_logger(name)


def get_client_addr(scope: HTTPScope):
    if scope["client"] is None:
        return "-"  # pragma: no cover
    return f"{scope['client'][0]}:{scope['client'][1]}"


def get_path_with_query_string(scope: HTTPScope) -> str:
    path_with_query_string = quote(scope.get("root_path", "") + scope["path"])
    if scope["query_string"]:  # pragma: no cover
        return f"{path_with_query_string}?{scope['query_string'].decode('ascii')}"
    return path_with_query_string
