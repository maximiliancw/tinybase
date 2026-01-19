"""
Integration tests for function API endpoints.

Tests the HTTP API behavior including authentication, authorization,
input validation, and error handling.
"""

import subprocess
from unittest.mock import MagicMock, patch


class TestFunctionIntegration:
    """Integration tests for function API endpoints."""

    def test_list_functions_anonymous(self, client, mock_functions):
        """Anonymous users see only public functions."""
        response = client.get("/api/functions")
        assert response.status_code == 200

        functions = response.json()
        names = [f["name"] for f in functions]

        assert "public_test" in names
        assert "auth_test" not in names
        assert "admin_test" not in names

    def test_list_functions_authenticated(self, client, mock_functions, user_token):
        """Authenticated users see public + auth functions."""
        response = client.get("/api/functions", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 200

        functions = response.json()
        names = [f["name"] for f in functions]

        assert "public_test" in names
        assert "auth_test" in names
        assert "admin_test" not in names

    def test_list_functions_admin(self, client, mock_functions, admin_token):
        """Admin users see all functions."""
        response = client.get("/api/functions", headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200

        functions = response.json()
        names = [f["name"] for f in functions]

        assert "public_test" in names
        assert "auth_test" in names
        assert "admin_test" in names

    def test_call_public_function_no_auth(self, client, mock_functions):
        """Public functions work without authentication."""
        with patch("tinybase.functions.core.subprocess.run") as mock_exec:
            mock_exec.return_value = MagicMock(
                returncode=0,
                stdout='{"status": "succeeded", "result": {"data": "test"}}',
                stderr="",
            )

            response = client.post("/api/functions/public_test", json={})

            assert response.status_code == 200
            assert response.json()["status"] == "succeeded"

    def test_call_auth_function_requires_token(self, client, mock_functions):
        """Auth functions require authentication."""
        response = client.post("/api/functions/auth_test", json={})
        assert response.status_code == 401

    def test_call_auth_function_with_token(self, client, mock_functions, user_token):
        """Auth functions work with valid authentication."""
        with patch("tinybase.functions.core.subprocess.run") as mock_exec:
            mock_exec.return_value = MagicMock(
                returncode=0,
                stdout='{"status": "succeeded", "result": {"data": "test"}}',
                stderr="",
            )

            response = client.post(
                "/api/functions/auth_test",
                headers={"Authorization": f"Bearer {user_token}"},
                json={},
            )

            assert response.status_code == 200
            assert response.json()["status"] == "succeeded"

    def test_call_admin_function_requires_admin(self, client, mock_functions, user_token):
        """Admin functions require admin role."""
        response = client.post(
            "/api/functions/admin_test",
            headers={"Authorization": f"Bearer {user_token}"},
            json={},
        )
        assert response.status_code == 403

    def test_call_admin_function_with_admin(self, client, mock_functions, admin_token):
        """Admin functions work with admin role."""
        with patch("tinybase.functions.core.subprocess.run") as mock_exec:
            mock_exec.return_value = MagicMock(
                returncode=0,
                stdout='{"status": "succeeded", "result": {"data": "test"}}',
                stderr="",
            )

            response = client.post(
                "/api/functions/admin_test",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={},
            )

            assert response.status_code == 200
            assert response.json()["status"] == "succeeded"

    def test_call_nonexistent_function(self, client, mock_functions):
        """Calling non-existent function returns 404."""
        response = client.post("/api/functions/does_not_exist", json={})
        assert response.status_code == 404

    def test_call_function_with_invalid_input(self, client, mock_functions, user_token):
        """Invalid input causes validation error in subprocess."""
        with patch("tinybase.functions.core.subprocess.run") as mock_exec:
            # SDK validation fails in subprocess
            mock_exec.return_value = MagicMock(
                returncode=0,
                stdout='{"status": "failed", "error": "Validation error: age is required", "error_type": "ValidationError"}',
                stderr="",
            )

            response = client.post(
                "/api/functions/validated_test",
                headers={"Authorization": f"Bearer {user_token}"},
                json={"name": "Alice"},  # Missing required 'age' field
            )

            # Function executes but fails with validation error
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "failed"
            assert result["error_type"] == "ValidationError"

    def test_call_function_with_valid_input(self, client, mock_functions, user_token):
        """Valid input passes validation."""
        with patch("tinybase.functions.core.subprocess.run") as mock_exec:
            mock_exec.return_value = MagicMock(
                returncode=0,
                stdout='{"status": "succeeded", "result": {"greeting": "Hello Alice"}}',
                stderr="",
            )

            response = client.post(
                "/api/functions/validated_test",
                headers={"Authorization": f"Bearer {user_token}"},
                json={"name": "Alice", "age": 30},
            )

            assert response.status_code == 200
            assert response.json()["status"] == "succeeded"

    def test_call_function_execution_error(self, client, mock_functions, user_token):
        """Function execution errors are properly reported."""
        with patch("tinybase.functions.core.subprocess.run") as mock_exec:
            mock_exec.return_value = MagicMock(
                returncode=0,
                stdout='{"status": "failed", "error": "Division by zero", "error_type": "ZeroDivisionError"}',
                stderr="",
            )

            response = client.post(
                "/api/functions/auth_test",
                headers={"Authorization": f"Bearer {user_token}"},
                json={},
            )

            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "failed"
            assert result["error_type"] == "ZeroDivisionError"
            assert "Division by zero" in result["error_message"]

    def test_function_call_history_tracking(self, client, mock_functions, user_token, admin_token):
        """Function calls are tracked in history."""
        with patch("tinybase.functions.core.subprocess.run") as mock_exec:
            mock_exec.return_value = MagicMock(
                returncode=0,
                stdout='{"status": "succeeded", "result": {}}',
                stderr="",
            )

            # Make 3 function calls
            for i in range(3):
                client.post(
                    "/api/functions/auth_test",
                    headers={"Authorization": f"Bearer {user_token}"},
                    json={"iteration": i},
                )

            # Check call history
            response = client.get(
                "/api/admin/functions/calls",
                headers={"Authorization": f"Bearer {admin_token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] >= 3

            # Verify at least 3 calls to auth_test
            auth_calls = [c for c in data["calls"] if c["function_name"] == "auth_test"]
            assert len(auth_calls) >= 3

    def test_function_with_empty_payload(self, client, mock_functions, user_token):
        """Functions handle empty payloads correctly."""
        with patch("tinybase.functions.core.subprocess.run") as mock_exec:
            mock_exec.return_value = MagicMock(
                returncode=0,
                stdout='{"status": "succeeded", "result": {}}',
                stderr="",
            )

            response = client.post(
                "/api/functions/auth_test",
                headers={"Authorization": f"Bearer {user_token}"},
                json={},
            )
            assert response.status_code == 200

    def test_function_timeout_handling(self, client, mock_functions, user_token):
        """Function timeouts are handled gracefully."""
        with patch("tinybase.functions.core.subprocess.run") as mock_exec:
            mock_exec.side_effect = subprocess.TimeoutExpired(["uv"], timeout=30)

            response = client.post(
                "/api/functions/auth_test",
                headers={"Authorization": f"Bearer {user_token}"},
                json={},
            )

            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "failed"
            assert result["error_type"] == "TimeoutError"

    def test_admin_list_extended_fields(self, client, mock_functions, admin_token):
        """Admin endpoint returns extended function metadata."""
        response = client.get(
            "/api/functions/admin/list",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        functions = response.json()
        assert len(functions) >= 4

        func = functions[0]
        assert "file_path" in func
        assert "last_loaded_at" in func
        assert "has_input_model" in func
        assert "has_output_model" in func
