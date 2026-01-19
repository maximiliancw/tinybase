"""
Tests for resource limits (payload and result size validation).
"""

import json
from unittest.mock import MagicMock, patch


class TestPayloadSizeValidation:
    """Test payload size validation at API layer."""

    def test_payload_within_limit(self, client, mock_functions, user_token):
        """Test that payloads within the size limit are accepted."""
        with patch("tinybase.functions.core.subprocess.run") as mock_exec:
            mock_exec.return_value = MagicMock(
                returncode=0,
                stdout='{"status": "succeeded", "result": {"data": "ok"}}',
                stderr="",
            )

            # Small payload (should succeed)
            response = client.post(
                "/api/functions/auth_test",
                headers={"Authorization": f"Bearer {user_token}"},
                json={"test": "data"},
            )

            assert response.status_code == 200
            assert response.json()["status"] == "succeeded"

    def test_payload_exceeds_limit(self, client, mock_functions, user_token):
        """Test that oversized payloads are rejected."""
        # Create a large payload (>10MB)
        large_data = "x" * (11 * 1024 * 1024)  # 11 MB

        response = client.post(
            "/api/functions/auth_test",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"data": large_data},
        )

        assert response.status_code == 413
        assert "exceeds maximum size" in response.json()["detail"]

    def test_payload_size_configurable(self, client, mock_functions, monkeypatch):
        """Test that payload size limit is configurable."""
        # Set a small limit (must be >= 1024)
        monkeypatch.setenv("TINYBASE_MAX_FUNCTION_PAYLOAD_BYTES", "2048")

        # Reload settings to pick up new env var
        from tinybase.config import reload_settings

        reload_settings()

        # Get a fresh user token after reloading settings
        from tests.utils import get_user_token

        user_token = get_user_token(client)

        # Payload larger than 2048 bytes
        large_data = "x" * 3000
        response = client.post(
            "/api/functions/auth_test",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"test": large_data},
        )

        assert response.status_code == 413


class TestResultSizeValidation:
    """Test result size validation in execute_function."""

    def test_result_within_limit(self, client, mock_functions, user_token):
        """Test that results within the size limit are returned."""
        with patch("tinybase.functions.core.subprocess.run") as mock_exec:
            # Small result
            mock_exec.return_value = MagicMock(
                returncode=0,
                stdout='{"status": "succeeded", "result": {"data": "ok"}}',
                stderr="",
            )

            response = client.post(
                "/api/functions/auth_test",
                headers={"Authorization": f"Bearer {user_token}"},
                json={},
            )

            assert response.status_code == 200
            assert response.json()["status"] == "succeeded"

    def test_result_exceeds_limit(self, client, mock_functions, user_token):
        """Test that oversized results trigger an error."""
        with patch("tinybase.functions.core.subprocess.run") as mock_exec:
            # Create a large result (>10MB)
            large_result = "x" * (11 * 1024 * 1024)
            mock_exec.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps({"status": "succeeded", "result": {"data": large_result}}),
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
            assert result["error_type"] == "ResultSizeError"
            assert "exceeds maximum size" in result["error_message"]

    def test_result_size_limit_boundary(self, client, mock_functions, user_token):
        """Test result size validation at the boundary."""
        with patch("tinybase.functions.core.subprocess.run") as mock_exec:
            from tinybase.config import settings

            config = settings()
            # Create result exactly at the limit
            max_size = config.max_function_result_bytes
            # Account for JSON overhead
            boundary_data = "x" * (max_size - 100)

            mock_exec.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps({"status": "succeeded", "result": {"data": boundary_data}}),
                stderr="",
            )

            response = client.post(
                "/api/functions/auth_test",
                headers={"Authorization": f"Bearer {user_token}"},
                json={},
            )

            # Should succeed (within limit)
            assert response.status_code == 200


class TestResourceLimitDefaults:
    """Test default resource limit configuration."""

    def test_default_payload_limit(self):
        """Test default payload limit is 10MB."""
        from tinybase.config import settings

        config = settings()
        assert config.max_function_payload_bytes == 10_485_760

    def test_default_result_limit(self):
        """Test default result limit is 10MB."""
        from tinybase.config import settings

        config = settings()
        assert config.max_function_result_bytes == 10_485_760

    def test_default_concurrent_limit(self):
        """Test default concurrent executions limit."""
        from tinybase.config import settings

        config = settings()
        assert config.max_concurrent_functions_per_user == 10
