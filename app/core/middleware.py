import os
import time
from typing import TypedDict

import structlog
from asgiref.typing import (
    ASGI3Application,
    ASGIReceiveCallable,
    ASGIReceiveEvent,
    ASGISendCallable,
    ASGISendEvent,
    HTTPScope,
)

from app.core.logging import get_logger


class AccessInfo(TypedDict, total=False):
    response: ASGISendEvent
    response_body: ASGISendEvent
    request: ASGIReceiveEvent
    start_time: float
    end_time: float
    status: int


class AccessLoggerMiddleware:
    """Represents information about access to a resource.

    This class encapsulates details about the access to a resource, such as the
    response, response body, request, start time, end time, and status.

    Attributes:
        response (ASGISendEvent): The response sent by the server.
        response_body (ASGISendEvent): The body of the response sent by the server.
        request (ASGIReceiveEvent): The request received by the server.
        start_time (float): The timestamp when the request was received.
        end_time (float): The timestamp when the response was sent.
        status (int): The HTTP status code of the response.

    Notes:
        This class is used to store information about access to a resource, and
        is typically used in logging and monitoring applications.
    """

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
        log_info = AccessInfo()

        async def inner_send(message: ASGISendEvent) -> None:
            if message["type"] == "http.response.start":
                log_info["response"] = message
            if message["type"] == "http.response.body":
                log_info["response_body"] = message
            await send(message)

        async def inner_receive() -> ASGIReceiveEvent:
            message = await receive()
            if message["type"] == "http.request":
                log_info["request"] = message
            return message

        try:
            log_info["start_time"] = time.monotonic()
            await self.app(scope, inner_receive, inner_send)
        except Exception as ex:
            log_info["status"] = 500
            raise ex
        finally:
            log_info["end_time"] = time.monotonic()
            await self.logger.ainfo("request", **AccessLogAtoms(scope, log_info))


class AccessLogAtoms(dict[str, object]):
    """Represents a collection of atoms that can be used to construct an access log.

    This class encapsulates the data and metadata necessary to generate an access log,
    including information about the request, response, and client.

    Attributes:
        client_addr (str): The IP address of the client that made the request.
        timestamp (str): The timestamp when the request was received.
        method (str): The HTTP method used in the request (e.g. GET, POST, etc.).
        path (str): The path of the request.
        query (str): The query string of the request.
        scheme (str): The scheme used in the request (e.g. HTTP, HTTPS, etc.).
        status_code (int): The HTTP status code of the response.
        request_time_ms (float): The time it took to process the request in milliseconds.
        response_body (str): The body of the response sent by the server.
        request_body (str): The body of the request received by the server.
        pid (int): The process ID of the server that handled the request.

    Methods:

        __getitem__(key): Returns the value of the specified atom.

    Notes:
        This class is used to store the data and metadata necessary to generate an access log,
        and is typically used in logging and monitoring applications.
    """

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
        self.update(
            {
                "client_addr": ":".join(map(str, scope["client"]))
                if scope["client"]
                else "-",
                "timestamp": time.strftime("[%d/%b/%Y:%H:%M:%S %z]"),
                "method": scope["method"],
                "path": scope["path"],
                "query": scope["query_string"].decode(),
                "scheme": protocol,
                "status_code": status,
                "request_time_ms": request_time * 1000,
                "response_body": info.get("response_body", {})
                .get("body", b"")
                .decode(),
                "request_body": info.get("request", {}).get("body", b"").decode(),
                "pid": os.getpid(),
            }
        )

    def __getitem__(self, key: str) -> object:
        try:
            return super().__getitem__(key)
        except KeyError:
            return "-"
