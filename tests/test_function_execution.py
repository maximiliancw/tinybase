"""
Extended tests for function execution.

Tests subprocess execution, internal tokens, structured logging, error handling,
and integration with the SDK.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session

from tinybase.db.core import get_engine
from tinybase.db.models import FunctionCall, FunctionCallStatus
from tinybase.functions.core import (
    FunctionMeta,
    FunctionRegistry,
    execute_function,
    get_global_registry,
    reset_global_registry,
)
from tinybase.utils import AuthLevel, TriggerType, utcnow


class TestFunctionExecution:
    """Test function execution via subprocess."""

    @pytest.fixture
    def session(self):
        """Create a test database session."""
        from tinybase.db.core import create_db_and_tables, get_engine

        create_db_and_tables()
        engine = get_engine()
        with Session(engine) as session:
            yield session

    @pytest.fixture
    def test_function_file(self):
        """Create a temporary function file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            function_code = '''# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from tinybase_sdk import register
from tinybase_sdk.cli import run

@register(name="test_function", description="Test function")
def test_func(client, payload: dict) -> dict:
    return {"result": payload.get("value", 0) * 2, "message": "success"}

if __name__ == "__main__":
    run()
'''
            f.write(function_code)
            f.flush()
            yield Path(f.name)

        # Cleanup
        try:
            Path(f.name).unlink()
        except Exception:
            pass

    def test_execute_function_success(self, session, test_function_file):
        """Test successful function execution."""
        meta = FunctionMeta(
            name="test_function",
            description="Test function",
            auth=AuthLevel.AUTH,
            file_path=str(test_function_file),
        )

        payload = {"value": 5}

        with patch("tinybase.functions.core.settings") as mock_settings:
            mock_config = MagicMock()
            mock_config.server_port = 8000
            mock_config.function_logging_enabled = False
            mock_config.scheduler_function_timeout_seconds = 30
            mock_settings.return_value = mock_config

            with patch("tinybase.functions.core.create_internal_token") as mock_token:
                mock_token.return_value = "internal-token-123"

                with patch("tinybase.functions.core.get_pool") as mock_pool:
                    mock_pool_instance = MagicMock()
                    mock_pool_instance.get_warm_process.return_value = None
                    mock_pool.return_value = mock_pool_instance

                    result = execute_function(
                        meta=meta,
                        payload=payload,
                        session=session,
                        user_id=None,
                        is_admin=False,
                        trigger_type=TriggerType.MANUAL,
                    )

                    assert result.status == FunctionCallStatus.SUCCEEDED
                    assert result.result is not None
                    assert result.error_message is None
                    assert result.duration_ms is not None

    def test_execute_function_with_error(self, session, test_function_file):
        """Test function execution with error."""
        # Create a function that raises an error
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            function_code = '''# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from tinybase_sdk import register
from tinybase_sdk.cli import run

@register(name="error_function")
def error_func(client, payload: dict) -> dict:
    raise ValueError("Test error")

if __name__ == "__main__":
    run()
'''
            f.write(function_code)
            f.flush()
            error_file = Path(f.name)

        try:
            meta = FunctionMeta(
                name="error_function",
                description="Error function",
                auth=AuthLevel.AUTH,
                file_path=str(error_file),
            )

            payload = {}

            with patch("tinybase.functions.core.settings") as mock_settings:
                mock_config = MagicMock()
                mock_config.server_port = 8000
                mock_config.function_logging_enabled = False
                mock_config.scheduler_function_timeout_seconds = 30
                mock_settings.return_value = mock_config

                with patch("tinybase.functions.core.create_internal_token") as mock_token:
                    mock_token.return_value = "internal-token-123"

                    with patch("tinybase.functions.core.get_pool") as mock_pool:
                        mock_pool_instance = MagicMock()
                        mock_pool_instance.get_warm_process.return_value = None
                        mock_pool.return_value = mock_pool_instance

                        result = execute_function(
                            meta=meta,
                            payload=payload,
                            session=session,
                            user_id=None,
                            is_admin=False,
                            trigger_type=TriggerType.MANUAL,
                        )

                        assert result.status == FunctionCallStatus.FAILED
                        assert result.error_message is not None
                        assert "error" in result.error_message.lower() or "ValueError" in result.error_message
        finally:
            try:
                error_file.unlink()
            except Exception:
                pass

    def test_execute_function_creates_call_record(self, session, test_function_file):
        """Test that function execution creates a call record."""
        meta = FunctionMeta(
            name="test_function",
            description="Test function",
            auth=AuthLevel.AUTH,
            file_path=str(test_function_file),
        )

        payload = {"value": 3}

        with patch("tinybase.functions.core.settings") as mock_settings:
            mock_config = MagicMock()
            mock_config.server_port = 8000
            mock_config.function_logging_enabled = False
            mock_config.scheduler_function_timeout_seconds = 30
            mock_settings.return_value = mock_config

            with patch("tinybase.functions.core.create_internal_token") as mock_token:
                mock_token.return_value = "internal-token-123"

                with patch("tinybase.functions.core.get_pool") as mock_pool:
                    mock_pool_instance = MagicMock()
                    mock_pool_instance.get_warm_process.return_value = None
                    mock_pool.return_value = mock_pool_instance

                    result = execute_function(
                        meta=meta,
                        payload=payload,
                        session=session,
                        user_id=None,
                        is_admin=False,
                        trigger_type=TriggerType.MANUAL,
                    )

                    # Check that a call record was created
                    from sqlmodel import select

                    call = session.exec(
                        select(FunctionCall).where(FunctionCall.id == result.call_id)
                    ).first()

                    assert call is not None
                    assert call.function_name == "test_function"
                    assert call.status == result.status
                    assert call.duration_ms == result.duration_ms

    def test_execute_function_with_internal_token(self, session, test_function_file):
        """Test that internal token is created for subprocess."""
        meta = FunctionMeta(
            name="test_function",
            description="Test function",
            auth=AuthLevel.AUTH,
            file_path=str(test_function_file),
        )

        payload = {"value": 1}

        with patch("tinybase.functions.core.settings") as mock_settings:
            mock_config = MagicMock()
            mock_config.server_port = 8000
            mock_config.function_logging_enabled = False
            mock_config.scheduler_function_timeout_seconds = 30
            mock_settings.return_value = mock_config

            with patch("tinybase.functions.core.create_internal_token") as mock_token:
                mock_token.return_value = "internal-token-456"

                with patch("tinybase.functions.core.get_pool") as mock_pool:
                    mock_pool_instance = MagicMock()
                    mock_pool_instance.get_warm_process.return_value = None
                    mock_pool.return_value = mock_pool_instance

                    execute_function(
                        meta=meta,
                        payload=payload,
                        session=session,
                        user_id=None,
                        is_admin=False,
                        trigger_type=TriggerType.MANUAL,
                    )

                    # Verify token was created
                    mock_token.assert_called_once()
                    call_args = mock_token.call_args
                    assert call_args[1]["expires_minutes"] == 5

    def test_execute_function_with_logging(self, session, test_function_file):
        """Test function execution with structured logging enabled."""
        meta = FunctionMeta(
            name="test_function",
            description="Test function",
            auth=AuthLevel.AUTH,
            file_path=str(test_function_file),
        )

        payload = {"value": 2}

        with patch("tinybase.functions.core.settings") as mock_settings:
            mock_config = MagicMock()
            mock_config.server_port = 8000
            mock_config.function_logging_enabled = True
            mock_config.function_logging_level = "INFO"
            mock_config.function_logging_format = "json"
            mock_config.scheduler_function_timeout_seconds = 30
            mock_settings.return_value = mock_config

            with patch("tinybase.functions.core.create_internal_token") as mock_token:
                mock_token.return_value = "internal-token-123"

                with patch("tinybase.functions.core.get_pool") as mock_pool:
                    mock_pool_instance = MagicMock()
                    mock_pool_instance.get_warm_process.return_value = None
                    mock_pool.return_value = mock_pool_instance

                    result = execute_function(
                        meta=meta,
                        payload=payload,
                        session=session,
                        user_id=None,
                        is_admin=False,
                        trigger_type=TriggerType.MANUAL,
                    )

                    # Function should still execute successfully
                    assert result.status == FunctionCallStatus.SUCCEEDED

    def test_execute_function_timeout(self, session):
        """Test function execution timeout."""
        # Create a function that hangs
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            function_code = '''# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

import time
from tinybase_sdk import register
from tinybase_sdk.cli import run

@register(name="slow_function")
def slow_func(client, payload: dict) -> dict:
    time.sleep(10)  # Sleep longer than timeout
    return {"result": "ok"}

if __name__ == "__main__":
    run()
'''
            f.write(function_code)
            f.flush()
            slow_file = Path(f.name)

        try:
            meta = FunctionMeta(
                name="slow_function",
                description="Slow function",
                auth=AuthLevel.AUTH,
                file_path=str(slow_file),
            )

            payload = {}

            with patch("tinybase.functions.core.settings") as mock_settings:
                mock_config = MagicMock()
                mock_config.server_port = 8000
                mock_config.function_logging_enabled = False
                mock_config.scheduler_function_timeout_seconds = 1  # Short timeout
                mock_settings.return_value = mock_config

                with patch("tinybase.functions.core.create_internal_token") as mock_token:
                    mock_token.return_value = "internal-token-123"

                    with patch("tinybase.functions.core.get_pool") as mock_pool:
                        mock_pool_instance = MagicMock()
                        mock_pool_instance.get_warm_process.return_value = None
                        mock_pool.return_value = mock_pool_instance

                        result = execute_function(
                            meta=meta,
                            payload=payload,
                            session=session,
                            user_id=None,
                            is_admin=False,
                            trigger_type=TriggerType.MANUAL,
                        )

                        assert result.status == FunctionCallStatus.FAILED
                        assert "timeout" in result.error_message.lower() or "Timeout" in result.error_message
        finally:
            try:
                slow_file.unlink()
            except Exception:
                pass

    def test_execute_function_with_user_context(self, session, test_function_file):
        """Test function execution with user context."""
        from uuid import uuid4

        meta = FunctionMeta(
            name="test_function",
            description="Test function",
            auth=AuthLevel.AUTH,
            file_path=str(test_function_file),
        )

        payload = {"value": 4}
        user_id = uuid4()

        with patch("tinybase.functions.core.settings") as mock_settings:
            mock_config = MagicMock()
            mock_config.server_port = 8000
            mock_config.function_logging_enabled = False
            mock_config.scheduler_function_timeout_seconds = 30
            mock_settings.return_value = mock_config

            with patch("tinybase.functions.core.create_internal_token") as mock_token:
                mock_token.return_value = "internal-token-123"

                with patch("tinybase.functions.core.get_pool") as mock_pool:
                    mock_pool_instance = MagicMock()
                    mock_pool_instance.get_warm_process.return_value = None
                    mock_pool.return_value = mock_pool_instance

                    result = execute_function(
                        meta=meta,
                        payload=payload,
                        session=session,
                        user_id=user_id,
                        is_admin=True,
                        trigger_type=TriggerType.MANUAL,
                    )

                    assert result.status == FunctionCallStatus.SUCCEEDED

                    # Verify token was created with correct user context
                    mock_token.assert_called_once()
                    call_args = mock_token.call_args
                    assert call_args[1]["user_id"] == user_id
                    assert call_args[1]["is_admin"] is True
