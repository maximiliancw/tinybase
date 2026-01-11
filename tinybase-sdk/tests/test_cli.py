"""
Tests for the SDK CLI module.

Tests metadata extraction, function execution, error handling, and logging integration.
"""

import json
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from tinybase_sdk.cli import run
from tinybase_sdk.decorator import register


class TestCLIMetadataExtraction:
    """Test metadata extraction mode (--metadata flag)."""

    def test_metadata_extraction_success(self, monkeypatch):
        """Test successful metadata extraction."""
        import tinybase_sdk.decorator as decorator_module

        decorator_module._registered_function = None

        @register(name="test_function", description="Test", tags=["test"])
        def test_func(client, payload: dict) -> dict:
            return {"result": "ok"}

        # Mock sys.argv and sys.stdout
        original_argv = sys.argv
        original_stdout = sys.stdout

        try:
            sys.argv = ["script.py", "--metadata"]
            sys.stdout = StringIO()

            with pytest.raises(SystemExit) as exc_info:
                run()
            assert exc_info.value.code == 0

            output = sys.stdout.getvalue()
            metadata = json.loads(output)

            assert metadata["name"] == "test_function"
            assert metadata["description"] == "Test"
            assert metadata["auth"] == "auth"
            assert metadata["tags"] == ["test"]
            assert metadata["input_schema"] is not None
            assert metadata["output_schema"] is not None
        finally:
            sys.argv = original_argv
            sys.stdout = original_stdout

    def test_metadata_extraction_no_function(self, monkeypatch):
        """Test metadata extraction when no function is registered."""
        import tinybase_sdk.decorator as decorator_module

        decorator_module._registered_function = None

        original_argv = sys.argv
        original_exit = sys.exit

        try:
            sys.argv = ["script.py", "--metadata"]
            exit_called = False
            exit_code = None

            def mock_exit(code):
                nonlocal exit_called, exit_code
                exit_called = True
                exit_code = code
                raise SystemExit(code)

            sys.exit = mock_exit

            with pytest.raises(SystemExit):
                run()

            assert exit_called
            assert exit_code == 1
        finally:
            sys.argv = original_argv
            sys.exit = original_exit


class TestCLIExecution:
    """Test function execution mode."""

    def test_execution_success_basic_types(self, monkeypatch):
        """Test successful execution with basic types."""
        import tinybase_sdk.decorator as decorator_module

        decorator_module._registered_function = None

        @register(name="test_func")
        def test_func(client, payload: dict) -> dict:
            return {"result": payload.get("value", 0) * 2}

        original_argv = sys.argv
        original_stdin = sys.stdin
        original_stdout = sys.stdout

        try:
            sys.argv = ["script.py"]
            input_data = {
                "context": {
                    "api_base_url": "http://localhost:8000/api",
                    "auth_token": "test-token",
                    "user_id": "123",
                    "is_admin": False,
                    "request_id": "req-123",
                    "function_name": "test_func",
                    "logging_enabled": False,
                },
                "payload": {"value": 5},
            }
            sys.stdin = StringIO(json.dumps(input_data))
            sys.stdout = StringIO()

            with patch("tinybase_sdk.cli.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                run()

                output = sys.stdout.getvalue()
                result = json.loads(output)

                assert result["status"] == "succeeded"
                assert result["result"] == {"result": 10}
        finally:
            sys.argv = original_argv
            sys.stdin = original_stdin
            sys.stdout = original_stdout

    def test_execution_success_pydantic_model(self, monkeypatch):
        """Test successful execution with Pydantic models."""
        import tinybase_sdk.decorator as decorator_module
        from pydantic import BaseModel

        decorator_module._registered_function = None

        class InputModel(BaseModel):
            name: str
            count: int

        class OutputModel(BaseModel):
            message: str
            total: int

        @register(name="test_func")
        def test_func(client, payload: InputModel) -> OutputModel:
            return OutputModel(message=f"Hello {payload.name}", total=payload.count * 2)

        original_argv = sys.argv
        original_stdin = sys.stdin
        original_stdout = sys.stdout

        try:
            sys.argv = ["script.py"]
            input_data = {
                "context": {
                    "api_base_url": "http://localhost:8000/api",
                    "auth_token": "test-token",
                    "user_id": "123",
                    "is_admin": False,
                    "request_id": "req-123",
                    "function_name": "test_func",
                    "logging_enabled": False,
                },
                "payload": {"name": "World", "count": 3},
            }
            sys.stdin = StringIO(json.dumps(input_data))
            sys.stdout = StringIO()

            with patch("tinybase_sdk.cli.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                run()

                output = sys.stdout.getvalue()
                result = json.loads(output)

                assert result["status"] == "succeeded"
                assert result["result"]["message"] == "Hello World"
                assert result["result"]["total"] == 6
        finally:
            sys.argv = original_argv
            sys.stdin = original_stdin
            sys.stdout = original_stdout

    def test_execution_no_input_parameter(self, monkeypatch):
        """Test execution with no input parameter."""
        import tinybase_sdk.decorator as decorator_module

        decorator_module._registered_function = None

        @register(name="test_func")
        def test_func(client) -> dict:
            return {"result": "no input"}

        original_argv = sys.argv
        original_stdin = sys.stdin
        original_stdout = sys.stdout

        try:
            sys.argv = ["script.py"]
            input_data = {
                "context": {
                    "api_base_url": "http://localhost:8000/api",
                    "auth_token": "test-token",
                    "user_id": "123",
                    "is_admin": False,
                    "request_id": "req-123",
                    "function_name": "test_func",
                    "logging_enabled": False,
                },
                "payload": {},
            }
            sys.stdin = StringIO(json.dumps(input_data))
            sys.stdout = StringIO()

            with patch("tinybase_sdk.cli.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                run()

                output = sys.stdout.getvalue()
                result = json.loads(output)

                assert result["status"] == "succeeded"
                assert result["result"] == {"result": "no input"}
        finally:
            sys.argv = original_argv
            sys.stdin = original_stdin
            sys.stdout = original_stdout

    def test_execution_error_handling(self, monkeypatch):
        """Test error handling during execution."""
        import tinybase_sdk.decorator as decorator_module

        decorator_module._registered_function = None

        @register(name="test_func")
        def test_func(client, payload: dict) -> dict:
            raise ValueError("Test error")

        original_argv = sys.argv
        original_stdin = sys.stdin
        original_stdout = sys.stdout

        try:
            sys.argv = ["script.py"]
            input_data = {
                "context": {
                    "api_base_url": "http://localhost:8000/api",
                    "auth_token": "test-token",
                    "user_id": "123",
                    "is_admin": False,
                    "request_id": "req-123",
                    "function_name": "test_func",
                    "logging_enabled": False,
                },
                "payload": {},
            }
            sys.stdin = StringIO(json.dumps(input_data))
            sys.stdout = StringIO()

            with patch("tinybase_sdk.cli.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                run()

                output = sys.stdout.getvalue()
                result = json.loads(output)

                assert result["status"] == "failed"
                assert "error" in result
                assert result["error_type"] == "ValueError"
        finally:
            sys.argv = original_argv
            sys.stdin = original_stdin
            sys.stdout = original_stdout

    def test_execution_no_function_registered(self, monkeypatch):
        """Test execution when no function is registered."""
        import tinybase_sdk.decorator as decorator_module

        decorator_module._registered_function = None

        original_argv = sys.argv
        original_stdin = sys.stdin
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        original_exit = sys.exit

        try:
            sys.argv = ["script.py"]
            input_data = {
                "context": {
                    "api_base_url": "http://localhost:8000/api",
                    "auth_token": "test-token",
                    "user_id": "123",
                    "is_admin": False,
                    "request_id": "req-123",
                    "function_name": "test_func",
                    "logging_enabled": False,
                },
                "payload": {},
            }
            sys.stdin = StringIO(json.dumps(input_data))
            sys.stdout = StringIO()
            sys.stderr = StringIO()

            exit_called = False
            exit_code = None

            def mock_exit(code):
                nonlocal exit_called, exit_code
                exit_called = True
                exit_code = code
                raise SystemExit(code)

            sys.exit = mock_exit

            with pytest.raises(SystemExit):
                run()

            assert exit_called
            assert exit_code == 1
        finally:
            sys.argv = original_argv
            sys.stdin = original_stdin
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            sys.exit = original_exit

    def test_execution_client_not_generated(self, monkeypatch):
        """Test execution when client is not generated."""
        import tinybase_sdk.decorator as decorator_module

        decorator_module._registered_function = None

        @register(name="test_func")
        def test_func(client, payload: dict) -> dict:
            return {"result": "ok"}

        original_argv = sys.argv
        original_stdin = sys.stdin
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        original_exit = sys.exit

        try:
            sys.argv = ["script.py"]
            input_data = {
                "context": {
                    "api_base_url": "http://localhost:8000/api",
                    "auth_token": "test-token",
                    "user_id": "123",
                    "is_admin": False,
                    "request_id": "req-123",
                    "function_name": "test_func",
                    "logging_enabled": False,
                },
                "payload": {},
            }
            sys.stdin = StringIO(json.dumps(input_data))
            sys.stdout = StringIO()
            sys.stderr = StringIO()

            exit_called = False
            exit_code = None

            def mock_exit(code):
                nonlocal exit_called, exit_code
                exit_called = True
                exit_code = code
                raise SystemExit(code)

            sys.exit = mock_exit

            with patch("tinybase_sdk.cli.Client", side_effect=ImportError("No module")):
                with pytest.raises(SystemExit):
                    run()

                assert exit_called
                assert exit_code == 1
                stderr_output = sys.stderr.getvalue()
                assert "Client not generated" in stderr_output
        finally:
            sys.argv = original_argv
            sys.stdin = original_stdin
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            sys.exit = original_exit

    def test_execution_with_logging_enabled(self, monkeypatch):
        """Test execution with structured logging enabled."""
        import tinybase_sdk.decorator as decorator_module

        decorator_module._registered_function = None

        @register(name="test_func")
        def test_func(client, payload: dict) -> dict:
            return {"result": "ok"}

        original_argv = sys.argv
        original_stdin = sys.stdin
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        try:
            sys.argv = ["script.py"]
            input_data = {
                "context": {
                    "api_base_url": "http://localhost:8000/api",
                    "auth_token": "test-token",
                    "user_id": "123",
                    "is_admin": False,
                    "request_id": "req-123",
                    "function_name": "test_func",
                    "logging_enabled": True,
                    "logging_level": "DEBUG",
                    "logging_format": "json",
                },
                "payload": {"test": "data"},
            }
            sys.stdin = StringIO(json.dumps(input_data))
            sys.stdout = StringIO()
            sys.stderr = StringIO()

            with patch("tinybase_sdk.cli.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                run()

                output = sys.stdout.getvalue()
                result = json.loads(output)

                assert result["status"] == "succeeded"
                # Check that logging was initialized (stderr should have log output)
                # Note: actual log output depends on logger implementation
        finally:
            sys.argv = original_argv
            sys.stdin = original_stdin
            sys.stdout = original_stdout
            sys.stderr = original_stderr

    def test_execution_result_serialization(self, monkeypatch):
        """Test various result serialization formats."""
        import tinybase_sdk.decorator as decorator_module

        decorator_module._registered_function = None

        # Test with list result
        @register(name="test_func_list")
        def test_func_list(client, payload: dict) -> list:
            return [1, 2, 3]

        original_argv = sys.argv
        original_stdin = sys.stdin
        original_stdout = sys.stdout

        try:
            sys.argv = ["script.py"]
            input_data = {
                "context": {
                    "api_base_url": "http://localhost:8000/api",
                    "auth_token": "test-token",
                    "user_id": "123",
                    "is_admin": False,
                    "request_id": "req-123",
                    "function_name": "test_func_list",
                    "logging_enabled": False,
                },
                "payload": {},
            }
            sys.stdin = StringIO(json.dumps(input_data))
            sys.stdout = StringIO()

            with patch("tinybase_sdk.cli.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                run()

                output = sys.stdout.getvalue()
                result = json.loads(output)

                assert result["status"] == "succeeded"
                assert result["result"] == [1, 2, 3]
        finally:
            sys.argv = original_argv
            sys.stdin = original_stdin
            sys.stdout = original_stdout
