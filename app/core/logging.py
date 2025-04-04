import logging
import sys
from typing import Any

import structlog


def configure_logging(debug: bool = False) -> None:
    """Configures the logging system for the application.

    This function sets up the logging configuration, including the log level, log format,
    and log file (if specified).

    Args:
        log_level (str): The log level to use (e.g. DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format (str): The format to use for log messages.
        log_file (str, optional): The file to write log messages to. If not specified, log messages will be written to the console.

    Returns:
        None

    Raises:
        ValueError: If the log level or log format is invalid.

    Notes:
        This function should be called early in the application's startup process to ensure that logging is properly configured.
        The log level and log format can be customized to suit the needs of the application.
        If a log file is specified, log messages will be written to that file instead of the console.
    """
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
