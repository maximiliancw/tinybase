"""
Tests for the SDK logging module.

Tests structured logging, JSON formatting, and different log levels.
"""

import json
import logging
import sys
from io import StringIO

from tinybase_sdk.logging import JSONFormatter, StructuredLogger


class TestStructuredLogger:
    """Test StructuredLogger class."""

    def test_logger_initialization(self):
        """Test logger initialization with default parameters."""
        logger = StructuredLogger(
            function_name="test_func",
            request_id="req-123",
        )

        assert logger.function_name == "test_func"
        assert logger.request_id == "req-123"
        assert logger.user_id is None
        assert logger.format_type == "json"

    def test_logger_initialization_with_user_id(self):
        """Test logger initialization with user ID."""
        logger = StructuredLogger(
            function_name="test_func",
            request_id="req-123",
            user_id="user-456",
        )

        assert logger.user_id == "user-456"

    def test_logger_initialization_with_level(self):
        """Test logger initialization with custom level."""
        logger = StructuredLogger(
            function_name="test_func",
            request_id="req-123",
            level="DEBUG",
        )

        assert logger.logger.level == logging.DEBUG

    def test_logger_initialization_text_format(self):
        """Test logger initialization with text format."""
        logger = StructuredLogger(
            function_name="test_func",
            request_id="req-123",
            format_type="text",
        )

        assert logger.format_type == "text"
        # Check that handler has text formatter
        assert len(logger.logger.handlers) > 0
        handler = logger.logger.handlers[0]
        assert not isinstance(handler.formatter, JSONFormatter)

    def test_logger_debug(self):
        """Test debug logging."""
        logger = StructuredLogger(
            function_name="test_func",
            request_id="req-123",
            level="DEBUG",
        )

        # Capture stderr
        original_stderr = sys.stderr
        sys.stderr = StringIO()

        try:
            logger.debug("Debug message", extra_field="value")

            output = sys.stderr.getvalue()
            # Should contain the log message
            assert "Debug message" in output or len(output) > 0
        finally:
            sys.stderr = original_stderr

    def test_logger_info(self):
        """Test info logging."""
        logger = StructuredLogger(
            function_name="test_func",
            request_id="req-123",
            level="INFO",
        )

        original_stderr = sys.stderr
        sys.stderr = StringIO()

        try:
            logger.info("Info message", extra_field="value")

            output = sys.stderr.getvalue()
            assert len(output) > 0
        finally:
            sys.stderr = original_stderr

    def test_logger_warning(self):
        """Test warning logging."""
        logger = StructuredLogger(
            function_name="test_func",
            request_id="req-123",
            level="WARNING",
        )

        original_stderr = sys.stderr
        sys.stderr = StringIO()

        try:
            logger.warning("Warning message", extra_field="value")

            output = sys.stderr.getvalue()
            assert len(output) > 0
        finally:
            sys.stderr = original_stderr

    def test_logger_error(self):
        """Test error logging."""
        logger = StructuredLogger(
            function_name="test_func",
            request_id="req-123",
            level="ERROR",
        )

        original_stderr = sys.stderr
        sys.stderr = StringIO()

        try:
            logger.error("Error message", extra_field="value")

            output = sys.stderr.getvalue()
            assert len(output) > 0
        finally:
            sys.stderr = original_stderr

    def test_logger_critical(self):
        """Test critical logging."""
        logger = StructuredLogger(
            function_name="test_func",
            request_id="req-123",
            level="CRITICAL",
        )

        original_stderr = sys.stderr
        sys.stderr = StringIO()

        try:
            logger.critical("Critical message", extra_field="value")

            output = sys.stderr.getvalue()
            assert len(output) > 0
        finally:
            sys.stderr = original_stderr

    def test_logger_custom_level(self):
        """Test custom level logging."""
        logger = StructuredLogger(
            function_name="test_func",
            request_id="req-123",
            level="INFO",
        )

        original_stderr = sys.stderr
        sys.stderr = StringIO()

        try:
            logger.log("WARNING", "Custom level message", extra_field="value")

            output = sys.stderr.getvalue()
            assert len(output) > 0
        finally:
            sys.stderr = original_stderr

    def test_logger_with_exception(self):
        """Test logging with exception info."""
        logger = StructuredLogger(
            function_name="test_func",
            request_id="req-123",
            level="ERROR",
        )

        original_stderr = sys.stderr
        sys.stderr = StringIO()

        try:
            try:
                raise ValueError("Test exception")
            except Exception:
                logger.error("Error with exception", exc_info=True)

            output = sys.stderr.getvalue()
            assert len(output) > 0
        finally:
            sys.stderr = original_stderr


class TestJSONFormatter:
    """Test JSONFormatter class."""

    def test_json_formatter_basic(self):
        """Test JSON formatter with basic log record."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add custom attributes
        record.function_name = "test_func"
        record.request_id = "req-123"

        output = formatter.format(record)
        data = json.loads(output)

        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert data["function"] == "test_func"
        assert data["request_id"] == "req-123"
        assert "timestamp" in data

    def test_json_formatter_with_user_id(self):
        """Test JSON formatter with user ID."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        record.function_name = "test_func"
        record.request_id = "req-123"
        record.user_id = "user-456"

        output = formatter.format(record)
        data = json.loads(output)

        assert data["user_id"] == "user-456"

    def test_json_formatter_with_extra_fields(self):
        """Test JSON formatter with extra fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        record.function_name = "test_func"
        record.request_id = "req-123"
        record.custom_field = "custom_value"
        record.another_field = 42

        output = formatter.format(record)
        data = json.loads(output)

        assert data["custom_field"] == "custom_value"
        assert data["another_field"] == 42

    def test_json_formatter_with_exception(self):
        """Test JSON formatter with exception info."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        record.function_name = "test_func"
        record.request_id = "req-123"

        # Simulate exception info
        try:
            raise ValueError("Test exception")
        except Exception:
            record.exc_info = sys.exc_info()

        output = formatter.format(record)
        data = json.loads(output)

        assert data["level"] == "ERROR"
        assert "exception" in data
        assert "ValueError" in data["exception"]

    def test_json_formatter_filters_standard_fields(self):
        """Test that standard logging fields are filtered out."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        record.function_name = "test_func"
        record.request_id = "req-123"

        output = formatter.format(record)
        data = json.loads(output)

        # Standard fields should not be in output (except those we explicitly include)
        assert "name" not in data
        assert "pathname" not in data
        assert "lineno" not in data
        assert "args" not in data
        assert "created" not in data

    def test_json_formatter_different_levels(self):
        """Test JSON formatter with different log levels."""
        formatter = JSONFormatter()

        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level_name in levels:
            level = getattr(logging, level_name)
            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="test.py",
                lineno=1,
                msg=f"{level_name} message",
                args=(),
                exc_info=None,
            )

            record.function_name = "test_func"
            record.request_id = "req-123"

            output = formatter.format(record)
            data = json.loads(output)

            assert data["level"] == level_name
            assert data["message"] == f"{level_name} message"
