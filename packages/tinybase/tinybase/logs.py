"""
Logging configuration for TinyBase.

Provides unified, clean logging for all TinyBase and Uvicorn loggers.
"""

import logging


class TinyBaseFormatter(logging.Formatter):
    """Custom formatter for clean, consistent TinyBase logs with colors."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[1;31m",  # Bold Red
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        # Format: [YYYY-MM-DD HH:MM:SS] – LEVEL – message
        level = record.levelname
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        message = record.getMessage()

        # Apply color to log level
        color = self.COLORS.get(level, "")
        colored_level = f"{color}{level}{self.RESET}" if color else level

        return f"[{timestamp}] – {colored_level} – {message}"


def setup_logging() -> None:
    """Configure logging for all TinyBase modules and Uvicorn."""
    from tinybase.settings import config

    # Create formatter
    formatter = TinyBaseFormatter()

    # Configure handler
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    # Configure root logger for tinybase.* loggers
    tinybase_logger = logging.getLogger("tinybase")
    tinybase_logger.setLevel(logging.DEBUG if config.debug else logging.INFO)
    tinybase_logger.handlers.clear()
    tinybase_logger.addHandler(handler)
    tinybase_logger.propagate = False

    # Configure Uvicorn loggers to use our formatter
    # Access logs always show (INFO level), other uvicorn logs only in debug mode
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers.clear()
    uvicorn_logger.addHandler(handler)
    uvicorn_logger.setLevel(logging.DEBUG if config.debug else logging.WARNING)
    uvicorn_logger.propagate = False

    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers.clear()
    uvicorn_access_logger.addHandler(handler)
    uvicorn_access_logger.setLevel(logging.INFO)  # Always show access logs
    uvicorn_access_logger.propagate = False

    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.handlers.clear()
    uvicorn_error_logger.addHandler(handler)
    uvicorn_error_logger.setLevel(logging.DEBUG if config.debug else logging.WARNING)
    uvicorn_error_logger.propagate = False
