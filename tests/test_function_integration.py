"""
Integration tests for end-to-end function execution workflow.

Tests the complete flow from function registration to execution via API.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests.utils import get_admin_token, get_user_token


class TestFunctionIntegration:
    """Integration tests for function execution workflow."""

    def test_end_to_end_function_execution(self, client):
        """Test complete function execution workflow."""
        # Create a function file
        with tempfile.TemporaryDirectory() as tmpdir:
            functions_dir = Path(tmpdir)

            # Create function file
            func_file = functions_dir / "test_func.py"
            func_file.write_text("""# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from tinybase_sdk import register
from tinybase_sdk.cli import run

@register(name="integration_test", description="Integration test function")
def test_func(client, payload: dict) -> dict:
    value = payload.get("value", 0)
    return {"result": value * 2, "doubled": True}

if __name__ == "__main__":
    run()
""")

            # Set functions path in config and mock subprocess calls
            with patch("tinybase.config.settings") as mock_settings:
                # Create a proper mock config object
                mock_config = MagicMock()
                mock_config.functions_path = str(functions_dir)
                mock_config.function_logging_enabled = False
                mock_config.server_port = 8000
                mock_config.scheduler_function_timeout_seconds = 30
                mock_config.auth_token_ttl_hours = 24
                mock_settings.return_value = mock_config

                # Also need to clear the settings cache
                import tinybase.config

                tinybase.config._settings = None

                # Mock subprocess for metadata extraction
                with patch("tinybase.functions.loader.subprocess.run") as mock_subprocess:
                    with patch("tinybase.functions.pool.get_pool") as mock_get_pool:
                        mock_pool = MagicMock()
                        mock_get_pool.return_value = mock_pool

                        def mock_subprocess_side_effect(cmd, *args, **kwargs):
                            mock_result = MagicMock()
                            if isinstance(cmd, list) and "--metadata" in cmd:
                                file_path = str(cmd[3]) if len(cmd) > 3 else ""
                                if "integration_test" in file_path or "test_func" in file_path:
                                    mock_result.stdout = '{"name": "integration_test", "description": "Integration test function", "auth": "auth", "tags": [], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                                    mock_result.returncode = 0
                                    mock_result.stderr = ""
                                else:
                                    mock_result.returncode = 0
                                    mock_result.stdout = ""
                                    mock_result.stderr = ""
                            else:
                                mock_result.returncode = 0
                                mock_result.stdout = ""
                                mock_result.stderr = ""
                            return mock_result

                        mock_subprocess.side_effect = mock_subprocess_side_effect

                        # Load functions
                        from tinybase.functions.loader import load_functions_from_settings

                        loaded = load_functions_from_settings()
                        assert loaded == 1

            # Clear settings cache AFTER exiting the patch to ensure real settings are used
            import tinybase.config

            tinybase.config._settings = None

            # Get tokens with real settings
            admin_token = get_admin_token(client)
            user_token = get_user_token(client)

            # List functions via API (with admin token to see all functions)
            response = client.get(
                "/api/functions", headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200
            functions = response.json()
            assert len(functions) == 1
            assert functions[0]["name"] == "integration_test"

            # Call function via API - need to mock subprocess for execution too
            with patch("tinybase.functions.core.subprocess.run") as mock_exec_subprocess:
                mock_exec_result = MagicMock()
                mock_exec_result.returncode = 0
                mock_exec_result.stdout = (
                    '{"status": "succeeded", "result": {"result": 10, "doubled": true}}'
                )
                mock_exec_result.stderr = ""
                mock_exec_subprocess.return_value = mock_exec_result

                response = client.post(
                    "/api/functions/integration_test",
                    headers={"Authorization": f"Bearer {user_token}"},
                    json={"value": 5},
                )

                assert response.status_code == 200
                result = response.json()
                assert result["status"] == "succeeded"
                assert result["result"]["result"] == 10
                assert result["result"]["doubled"] is True

    def test_function_call_history(self, client):
        """Test function call history tracking."""
        admin_token = get_admin_token(client)
        user_token = get_user_token(client)

        with tempfile.TemporaryDirectory() as tmpdir:
            functions_dir = Path(tmpdir)

            func_file = functions_dir / "history_test.py"
            func_file.write_text("""# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from tinybase_sdk import register
from tinybase_sdk.cli import run

@register(name="history_test", description="History test")
def test_func(client, payload: dict) -> dict:
    return {"result": "ok"}

if __name__ == "__main__":
    run()
""")

            with patch("tinybase.config.settings") as mock_settings:
                # Create a proper mock config object
                mock_config = MagicMock()
                mock_config.functions_path = str(functions_dir)
                mock_config.function_logging_enabled = False
                mock_config.server_port = 8000
                mock_config.scheduler_function_timeout_seconds = 30
                mock_config.auth_token_ttl_hours = 24
                mock_settings.return_value = mock_config

                # Also need to clear the settings cache
                import tinybase.config

                tinybase.config._settings = None

                with patch("tinybase.functions.loader.subprocess.run") as mock_subprocess:
                    with patch("tinybase.functions.pool.get_pool") as mock_get_pool:
                        mock_pool = MagicMock()
                        mock_get_pool.return_value = mock_pool

                        def mock_subprocess_side_effect(cmd, *args, **kwargs):
                            mock_result = MagicMock()
                            if isinstance(cmd, list) and "--metadata" in cmd:
                                file_path = str(cmd[3]) if len(cmd) > 3 else ""
                                if "pydantic_func" in file_path:
                                    mock_result.stdout = '{"name": "pydantic_func", "description": "Pydantic function", "auth": "auth", "tags": [], "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}, "required": ["name", "age"]}, "output_schema": {"type": "object"}}'
                                elif "public_func" in file_path:
                                    mock_result.stdout = '{"name": "public_func", "description": "Public function", "auth": "public", "tags": [], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                                elif "auth_func" in file_path:
                                    mock_result.stdout = '{"name": "auth_func", "description": "Auth function", "auth": "auth", "tags": [], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                                elif "admin_func" in file_path:
                                    mock_result.stdout = '{"name": "admin_func", "description": "Admin function", "auth": "admin", "tags": [], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                                elif "history_test" in file_path:
                                    mock_result.stdout = '{"name": "history_test", "description": "History test", "auth": "auth", "tags": [], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                                else:
                                    mock_result.returncode = 1
                                    mock_result.stdout = ""
                                    mock_result.stderr = "No metadata"
                                    return mock_result
                                mock_result.returncode = 0
                                mock_result.stderr = ""
                            else:
                                mock_result.returncode = 0
                                mock_result.stdout = ""
                                mock_result.stderr = ""
                            return mock_result

                        mock_subprocess.side_effect = mock_subprocess_side_effect

                        from tinybase.functions.loader import load_functions_from_settings

                        load_functions_from_settings()

                        # Mock subprocess for function execution too
                        with patch("subprocess.run") as mock_exec_subprocess:
                            mock_exec_result = MagicMock()
                            mock_exec_result.returncode = 0
                            mock_exec_result.stdout = (
                                '{"status": "succeeded", "result": {"result": "ok"}}'
                            )
                            mock_exec_result.stderr = ""
                            mock_exec_subprocess.return_value = mock_exec_result

                # Call function multiple times
                for i in range(3):
                    response = client.post(
                        "/api/functions/history_test",
                        headers={"Authorization": f"Bearer {user_token}"},
                        json={"iteration": i},
                    )
                    assert response.status_code == 200

                # Check call history
                response = client.get(
                    "/api/admin/functions/calls",
                    headers={"Authorization": f"Bearer {admin_token}"},
                )

                assert response.status_code == 200
                data = response.json()
                assert "calls" in data
                assert "total" in data
                assert data["total"] >= 3

                # Verify calls are for our function
                history_test_calls = [
                    call for call in data["calls"] if call["function_name"] == "history_test"
                ]
                assert len(history_test_calls) >= 3

    def test_function_auth_levels(self, client):
        """Test function execution with different auth levels."""
        with tempfile.TemporaryDirectory() as tmpdir:
            functions_dir = Path(tmpdir)

            # Create public function
            public_file = functions_dir / "public_func.py"
            public_file.write_text("""# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from tinybase_sdk import register
from tinybase_sdk.cli import run

@register(name="public_func", auth="public")
def public_func(client, payload: dict) -> dict:
    return {"result": "public"}

if __name__ == "__main__":
    run()
""")

            # Create auth function
            auth_file = functions_dir / "auth_func.py"
            auth_file.write_text("""# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from tinybase_sdk import register
from tinybase_sdk.cli import run

@register(name="auth_func", auth="auth")
def auth_func(client, payload: dict) -> dict:
    return {"result": "auth"}

if __name__ == "__main__":
    run()
""")

            # Create admin function
            admin_file = functions_dir / "admin_func.py"
            admin_file.write_text("""# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from tinybase_sdk import register
from tinybase_sdk.cli import run

@register(name="admin_func", auth="admin")
def admin_func(client, payload: dict) -> dict:
    return {"result": "admin"}

if __name__ == "__main__":
    run()
""")

            with patch("tinybase.config.settings") as mock_settings:
                # Create a proper mock config object
                mock_config = MagicMock()
                mock_config.functions_path = str(functions_dir)
                mock_config.function_logging_enabled = False
                mock_config.server_port = 8000
                mock_config.scheduler_function_timeout_seconds = 30
                mock_config.auth_token_ttl_hours = 24
                mock_settings.return_value = mock_config

                # Also need to clear the settings cache
                import tinybase.config

                tinybase.config._settings = None

                with patch("tinybase.functions.loader.subprocess.run") as mock_subprocess:
                    with patch("tinybase.functions.pool.get_pool") as mock_get_pool:
                        mock_pool = MagicMock()
                        mock_get_pool.return_value = mock_pool

                        def mock_subprocess_side_effect(cmd, *args, **kwargs):
                            mock_result = MagicMock()
                            if isinstance(cmd, list) and "--metadata" in cmd:
                                file_path = str(cmd[3]) if len(cmd) > 3 else ""
                                if "pydantic_func" in file_path:
                                    mock_result.stdout = '{"name": "pydantic_func", "description": "Pydantic function", "auth": "auth", "tags": [], "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}, "required": ["name", "age"]}, "output_schema": {"type": "object"}}'
                                elif "public_func" in file_path:
                                    mock_result.stdout = '{"name": "public_func", "description": "Public function", "auth": "public", "tags": [], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                                elif "auth_func" in file_path:
                                    mock_result.stdout = '{"name": "auth_func", "description": "Auth function", "auth": "auth", "tags": [], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                                elif "admin_func" in file_path:
                                    mock_result.stdout = '{"name": "admin_func", "description": "Admin function", "auth": "admin", "tags": [], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                                else:
                                    mock_result.stdout = '{"name": "history_test", "description": "History test", "auth": "auth", "tags": [], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                                mock_result.returncode = 0
                                mock_result.stderr = ""
                            else:
                                mock_result.returncode = 0
                                mock_result.stdout = ""
                                mock_result.stderr = ""
                            return mock_result

                        mock_subprocess.side_effect = mock_subprocess_side_effect

                        from tinybase.functions.loader import load_functions_from_settings

                        load_functions_from_settings()

            # Clear settings cache AFTER exiting the patch to ensure real settings are used
            import tinybase.config

            tinybase.config._settings = None

            # Get tokens with real settings
            admin_token = get_admin_token(client)
            user_token = get_user_token(client)

            # Mock subprocess for function execution
            with patch("tinybase.functions.core.subprocess.run") as mock_exec_subprocess:

                def mock_exec_side_effect(cmd, *args, **kwargs):
                    mock_exec_result = MagicMock()
                    mock_exec_result.returncode = 0
                    file_path = str(cmd[-1]) if isinstance(cmd, list) else ""
                    if "public_func" in file_path:
                        mock_exec_result.stdout = (
                            '{"status": "succeeded", "result": {"result": "public"}}'
                        )
                    elif "auth_func" in file_path:
                        mock_exec_result.stdout = (
                            '{"status": "succeeded", "result": {"result": "auth"}}'
                        )
                    elif "admin_func" in file_path:
                        mock_exec_result.stdout = (
                            '{"status": "succeeded", "result": {"result": "admin"}}'
                        )
                    else:
                        mock_exec_result.stdout = (
                            '{"status": "succeeded", "result": {"result": "ok"}}'
                        )
                    mock_exec_result.stderr = ""
                    return mock_exec_result

                mock_exec_subprocess.side_effect = mock_exec_side_effect

                # Public function should work without auth
                response = client.post("/api/functions/public_func", json={})
                assert response.status_code == 200

                # Auth function should require auth
                response = client.post("/api/functions/auth_func", json={})
                assert response.status_code == 401

                response = client.post(
                    "/api/functions/auth_func",
                    headers={"Authorization": f"Bearer {user_token}"},
                    json={},
                )
                assert response.status_code == 200

                # Admin function should require admin
                response = client.post(
                    "/api/functions/admin_func",
                    headers={"Authorization": f"Bearer {user_token}"},
                    json={},
                )
                assert response.status_code == 403

                response = client.post(
                    "/api/functions/admin_func",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    json={},
                )
                assert response.status_code == 200

    def test_function_error_handling(self, client):
        """Test error handling in function execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            functions_dir = Path(tmpdir)

            error_file = functions_dir / "error_func.py"
            error_file.write_text("""# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from tinybase_sdk import register
from tinybase_sdk.cli import run

@register(name="error_func", description="Error function")
def error_func(client, payload: dict) -> dict:
    raise ValueError("Test error message")

if __name__ == "__main__":
    run()
""")

            with patch("tinybase.config.settings") as mock_settings:
                # Create a proper mock config object
                mock_config = MagicMock()
                mock_config.functions_path = str(functions_dir)
                mock_config.function_logging_enabled = False
                mock_config.server_port = 8000
                mock_config.scheduler_function_timeout_seconds = 30
                mock_config.auth_token_ttl_hours = 24
                mock_settings.return_value = mock_config

                # Also need to clear the settings cache
                import tinybase.config

                tinybase.config._settings = None

                with patch("tinybase.functions.loader.subprocess.run") as mock_subprocess:
                    with patch("tinybase.functions.pool.get_pool") as mock_get_pool:
                        mock_pool = MagicMock()
                        mock_get_pool.return_value = mock_pool

                        def mock_subprocess_side_effect(cmd, *args, **kwargs):
                            mock_result = MagicMock()
                            if isinstance(cmd, list) and "--metadata" in cmd:
                                file_path = str(cmd[3]) if len(cmd) > 3 else ""
                                if "error_func" in file_path or "error" in file_path.lower():
                                    mock_result.stdout = '{"name": "error_func", "description": "Error function", "auth": "auth", "tags": [], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                                elif "pydantic_func" in file_path:
                                    mock_result.stdout = '{"name": "pydantic_func", "description": "Pydantic function", "auth": "auth", "tags": [], "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}, "required": ["name", "age"]}, "output_schema": {"type": "object"}}'
                                elif "public_func" in file_path:
                                    mock_result.stdout = '{"name": "public_func", "description": "Public function", "auth": "public", "tags": [], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                                elif "auth_func" in file_path:
                                    mock_result.stdout = '{"name": "auth_func", "description": "Auth function", "auth": "auth", "tags": [], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                                elif "admin_func" in file_path:
                                    mock_result.stdout = '{"name": "admin_func", "description": "Admin function", "auth": "admin", "tags": [], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                                else:
                                    mock_result.stdout = '{"name": "history_test", "description": "History test", "auth": "auth", "tags": [], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                                mock_result.returncode = 0
                                mock_result.stderr = ""
                            else:
                                mock_result.returncode = 0
                                mock_result.stdout = ""
                                mock_result.stderr = ""
                            return mock_result

                        mock_subprocess.side_effect = mock_subprocess_side_effect

                        from tinybase.functions.loader import load_functions_from_settings

                        load_functions_from_settings()

            # Clear settings cache AFTER exiting the patch to ensure real settings are used
            import tinybase.config

            tinybase.config._settings = None

            # Get token with real settings
            user_token = get_user_token(client)

            # Mock subprocess for function execution - return error
            with patch("tinybase.functions.core.subprocess.run") as mock_exec_subprocess:
                mock_exec_result = MagicMock()
                mock_exec_result.returncode = 0
                mock_exec_result.stdout = '{"status": "failed", "error": "Test error message", "error_type": "ValueError"}'
                mock_exec_result.stderr = ""
                mock_exec_subprocess.return_value = mock_exec_result

                # Call function that raises error
                response = client.post(
                    "/api/functions/error_func",
                    headers={"Authorization": f"Bearer {user_token}"},
                    json={},
                )

                assert response.status_code == 200
                result = response.json()
                assert result["status"] == "failed"
                assert "error" in result
                assert "error_type" in result

    def test_function_with_pydantic_models(self, client):
        """Test function execution with Pydantic models."""
        with tempfile.TemporaryDirectory() as tmpdir:
            functions_dir = Path(tmpdir)

            pydantic_file = functions_dir / "pydantic_func.py"
            pydantic_file.write_text("""# /// script
# dependencies = [
#   "tinybase-sdk",
#   "pydantic>=2.0.0",
# ]
# ///

from pydantic import BaseModel
from tinybase_sdk import register
from tinybase_sdk.cli import run

class InputModel(BaseModel):
    name: str
    age: int

class OutputModel(BaseModel):
    message: str
    age_next_year: int

@register(name="pydantic_func", description="Pydantic test")
def pydantic_func(client, payload: InputModel) -> OutputModel:
    return OutputModel(
        message=f"Hello {payload.name}",
        age_next_year=payload.age + 1
    )

if __name__ == "__main__":
    run()
""")

            with patch("tinybase.config.settings") as mock_settings:
                # Create a proper mock config object
                mock_config = MagicMock()
                mock_config.functions_path = str(functions_dir)
                mock_config.function_logging_enabled = False
                mock_config.server_port = 8000
                mock_config.scheduler_function_timeout_seconds = 30
                mock_config.auth_token_ttl_hours = 24
                mock_settings.return_value = mock_config

                # Also need to clear the settings cache
                import tinybase.config

                tinybase.config._settings = None

                with patch("tinybase.functions.loader.subprocess.run") as mock_subprocess:
                    with patch("tinybase.functions.pool.get_pool") as mock_get_pool:
                        mock_pool = MagicMock()
                        mock_get_pool.return_value = mock_pool

                        def mock_subprocess_side_effect(cmd, *args, **kwargs):
                            mock_result = MagicMock()
                            if isinstance(cmd, list) and "--metadata" in cmd:
                                file_path = str(cmd[3]) if len(cmd) > 3 else ""
                                if "pydantic_func" in file_path:
                                    mock_result.stdout = '{"name": "pydantic_func", "description": "Pydantic function", "auth": "auth", "tags": [], "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}, "required": ["name", "age"]}, "output_schema": {"type": "object"}}'
                                elif "public_func" in file_path:
                                    mock_result.stdout = '{"name": "public_func", "description": "Public function", "auth": "public", "tags": [], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                                elif "auth_func" in file_path:
                                    mock_result.stdout = '{"name": "auth_func", "description": "Auth function", "auth": "auth", "tags": [], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                                elif "admin_func" in file_path:
                                    mock_result.stdout = '{"name": "admin_func", "description": "Admin function", "auth": "admin", "tags": [], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                                else:
                                    mock_result.stdout = '{"name": "history_test", "description": "History test", "auth": "auth", "tags": [], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                                mock_result.returncode = 0
                                mock_result.stderr = ""
                            else:
                                mock_result.returncode = 0
                                mock_result.stdout = ""
                                mock_result.stderr = ""
                            return mock_result

                        mock_subprocess.side_effect = mock_subprocess_side_effect

                        from tinybase.functions.loader import load_functions_from_settings

                        load_functions_from_settings()

            # Clear settings cache AFTER exiting the patch to ensure real settings are used
            import tinybase.config

            tinybase.config._settings = None

            # Get token with real settings
            user_token = get_user_token(client)

            # Mock subprocess for function execution too
            with patch("subprocess.run") as mock_exec_subprocess:
                mock_exec_result = MagicMock()
                mock_exec_result.returncode = 0
                mock_exec_result.stdout = '{"status": "succeeded", "result": {"message": "Hello Alice", "age_next_year": 31}}'
                mock_exec_result.stderr = ""
                mock_exec_subprocess.return_value = mock_exec_result

            # Call function with Pydantic model
            response = client.post(
                "/api/functions/pydantic_func",
                headers={"Authorization": f"Bearer {user_token}"},
                json={"name": "Alice", "age": 30},
            )

            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "succeeded"
            assert result["result"]["message"] == "Hello Alice"
            assert result["result"]["age_next_year"] == 31

            # Test validation error
            response = client.post(
                "/api/functions/pydantic_func",
                headers={"Authorization": f"Bearer {user_token}"},
                json={"name": "Bob"},  # Missing age
            )

            # Should fail validation
            assert response.status_code in [400, 422]
