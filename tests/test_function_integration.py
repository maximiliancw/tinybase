"""
Integration tests for end-to-end function execution workflow.

Tests the complete flow from function registration to execution via API.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.utils import get_admin_token, get_user_token


class TestFunctionIntegration:
    """Integration tests for function execution workflow."""

    def test_end_to_end_function_execution(self, client):
        """Test complete function execution workflow."""
        admin_token = get_admin_token(client)

        # Create a function file
        with tempfile.TemporaryDirectory() as tmpdir:
            functions_dir = Path(tmpdir)

            # Create function file
            func_file = functions_dir / "test_func.py"
            func_file.write_text('''# /// script
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
''')

            # Set functions path in config
            with patch("tinybase.config.settings") as mock_settings:
                mock_config = mock_settings.return_value
                mock_config.functions_path = str(functions_dir)
                mock_config.function_logging_enabled = False

                # Load functions
                from tinybase.functions.loader import load_functions_from_settings

                loaded = load_functions_from_settings()
                assert loaded == 1

                # List functions via API
                response = client.get("/api/functions")
                assert response.status_code == 200
                functions = response.json()
                assert len(functions) == 1
                assert functions[0]["name"] == "integration_test"

                # Call function via API
                user_token = get_user_token(client)
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
            func_file.write_text('''# /// script
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
''')

            with patch("tinybase.config.settings") as mock_settings:
                mock_config = mock_settings.return_value
                mock_config.functions_path = str(functions_dir)
                mock_config.function_logging_enabled = False

                from tinybase.functions.loader import load_functions_from_settings

                load_functions_from_settings()

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
        admin_token = get_admin_token(client)
        user_token = get_user_token(client)

        with tempfile.TemporaryDirectory() as tmpdir:
            functions_dir = Path(tmpdir)

            # Create public function
            public_file = functions_dir / "public_func.py"
            public_file.write_text('''# /// script
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
''')

            # Create auth function
            auth_file = functions_dir / "auth_func.py"
            auth_file.write_text('''# /// script
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
''')

            # Create admin function
            admin_file = functions_dir / "admin_func.py"
            admin_file.write_text('''# /// script
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
''')

            with patch("tinybase.config.settings") as mock_settings:
                mock_config = mock_settings.return_value
                mock_config.functions_path = str(functions_dir)
                mock_config.function_logging_enabled = False

                from tinybase.functions.loader import load_functions_from_settings

                load_functions_from_settings()

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
        user_token = get_user_token(client)

        with tempfile.TemporaryDirectory() as tmpdir:
            functions_dir = Path(tmpdir)

            error_file = functions_dir / "error_func.py"
            error_file.write_text('''# /// script
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
''')

            with patch("tinybase.config.settings") as mock_settings:
                mock_config = mock_settings.return_value
                mock_config.functions_path = str(functions_dir)
                mock_config.function_logging_enabled = False

                from tinybase.functions.loader import load_functions_from_settings

                load_functions_from_settings()

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
        user_token = get_user_token(client)

        with tempfile.TemporaryDirectory() as tmpdir:
            functions_dir = Path(tmpdir)

            pydantic_file = functions_dir / "pydantic_func.py"
            pydantic_file.write_text('''# /// script
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
''')

            with patch("tinybase.config.settings") as mock_settings:
                mock_config = mock_settings.return_value
                mock_config.functions_path = str(functions_dir)
                mock_config.function_logging_enabled = False

                from tinybase.functions.loader import load_functions_from_settings

                load_functions_from_settings()

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
