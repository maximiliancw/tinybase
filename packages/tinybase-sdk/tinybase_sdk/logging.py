"""Structured logging utilities for TinyBase functions."""

import json
import logging
import sys
from typing import Any


class StructuredLogger:
    """
    Structured logger for TinyBase functions.

    Logs are sent to stderr in JSON format for capture by the main process.
    Each log entry includes function context (name, request_id, user_id).
    """

    def __init__(
        self,
        function_name: str,
        request_id: str,
        user_id: str | None = None,
        level: str = "INFO",
        format_type: str = "json",
    ):
        """
        Initialize structured logger.

        Args:
            function_name: Name of the function
            request_id: Unique request ID for this execution
            user_id: User ID (if available)
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format_type: 'json' for structured logs, 'text' for human-readable
        """
        self.function_name = function_name
        self.request_id = request_id
        self.user_id = user_id
        self.format_type = format_type

        # Create logger
        self.logger = logging.getLogger(f"tinybase.function.{function_name}")
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))

        # Remove existing handlers
        self.logger.handlers.clear()

        # Add stderr handler
        handler = logging.StreamHandler(sys.stderr)
        if format_type == "json":
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
        self.logger.addHandler(handler)

    def _log(self, level: str, message: str, **kwargs: Any) -> None:
        """Internal logging method with context."""
        # Extract exc_info and stack_info if present (logging module handles these specially)
        exc_info = kwargs.pop("exc_info", None)
        stack_info = kwargs.pop("stack_info", None)
        stacklevel = kwargs.pop("stacklevel", 1)

        extra = {
            "function_name": self.function_name,
            "request_id": self.request_id,
            "user_id": self.user_id,
            **kwargs,
        }
        getattr(self.logger, level.lower())(
            message, extra=extra, exc_info=exc_info, stack_info=stack_info, stacklevel=stacklevel
        )

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._log("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self._log("ERROR", message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message."""
        self._log("CRITICAL", message, **kwargs)

    def log(self, level: str, message: str, **kwargs: Any) -> None:
        """Log with custom level."""
        self._log(level.upper(), message, **kwargs)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "function": getattr(record, "function_name", "unknown"),
            "request_id": getattr(record, "request_id", "unknown"),
            "message": record.getMessage(),
        }

        # Add user_id if available
        if hasattr(record, "user_id") and record.user_id:
            log_data["user_id"] = record.user_id

        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "function_name",
                "request_id",
                "user_id",
            }:
                log_data[key] = value

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)
