"""
Tests for SDK deployment functionality.

Note: These tests require the OpenAPI client to be generated first.
Since we enforce usage of the auto-generated client, these tests
should be run after running: python scripts/generate_client.py
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# These imports will fail if client hasn't been generated
# That's intentional - we enforce client generation
try:
    from tinybase_sdk.deployment import DeploymentClient, DeploymentError, DeploymentResult

    CLIENT_AVAILABLE = True
except ImportError:
    CLIENT_AVAILABLE = False
    pytestmark = pytest.mark.skip(
        reason="OpenAPI client not generated. Run: python scripts/generate_client.py"
    )


@pytest.fixture
def mock_client():
    """Fixture providing a mocked TinyBase client."""
    return MagicMock()


@pytest.fixture
def deployment_client(mock_client):
    """Fixture providing a DeploymentClient with mocked API client."""
    with patch("tinybase_sdk.deployment.Client", return_value=mock_client):
        client = DeploymentClient(base_url="https://test.api.com", token="test-token", timeout=30.0)
        client.client = mock_client  # Ensure the mock is used
        return client


@pytest.fixture
def sample_function_file():
    """Fixture providing a temporary function file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        func_file = Path(tmpdir) / "test_func.py"
        func_file.write_text(
            """# /// script
# dependencies = ["tinybase-sdk"]
# ///

from tinybase_sdk import register

@register(name="test_func")
def test_func(client, payload):
    return {"result": "ok"}
"""
        )
        yield func_file


class TestDeploymentClient:
    """Tests for DeploymentClient."""

    def test_initialization(self):
        """Test client initialization."""
        with patch("tinybase_sdk.deployment.Client") as mock_client_class:
            client = DeploymentClient(
                base_url="https://test.api.com", token="test-token", timeout=45.0
            )

            assert client.base_url == "https://test.api.com"
            assert client.token == "test-token"
            assert client.timeout == 45.0
            mock_client_class.assert_called_once_with(
                base_url="https://test.api.com", token="test-token", timeout=45.0
            )

    def test_context_manager(self, deployment_client):
        """Test client can be used as context manager."""
        with deployment_client as client:
            assert client is not None

        # close should have been called
        if hasattr(deployment_client.client, "close"):
            deployment_client.client.close.assert_called_once()

    def test_deploy_function_file_not_found(self, deployment_client):
        """Test deploy_function with non-existent file."""
        result = deployment_client.deploy_function(Path("/nonexistent/file.py"))

        assert isinstance(result, DeploymentError)
        assert result.function_name == "file"
        assert "not found" in result.error.lower()

    def test_deploy_function_not_python_file(self, deployment_client):
        """Test deploy_function with non-Python file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            txt_file = Path(tmpdir) / "test.txt"
            txt_file.write_text("not python")

            result = deployment_client.deploy_function(txt_file)

            assert isinstance(result, DeploymentError)
            assert result.function_name == "test"
            assert "not a python file" in result.error.lower()

    def test_deploy_function_success(self, deployment_client, sample_function_file):
        """Test successful function deployment."""
        # Mock the upload_function API call
        mock_response = MagicMock()
        mock_response.function_name = "test_func"
        mock_response.version_id = "version-123"
        mock_response.content_hash = "abc123"
        mock_response.is_new_version = True
        mock_response.message = "Deployed successfully"
        mock_response.warnings = []

        with patch("tinybase_sdk.deployment.upload_function") as mock_upload:
            mock_upload.sync.return_value = mock_response

            result = deployment_client.deploy_function(sample_function_file, notes="Test deploy")

            assert isinstance(result, DeploymentResult)
            assert result.function_name == "test_func"
            assert result.version_id == "version-123"
            assert result.content_hash == "abc123"
            assert result.is_new_version is True
            assert result.message == "Deployed successfully"
            assert result.warnings == []

    def test_deploy_function_api_error(self, deployment_client, sample_function_file):
        """Test deploy_function handling API errors."""
        with patch("tinybase_sdk.deployment.upload_function") as mock_upload:
            mock_upload.sync.side_effect = Exception("API error")

            result = deployment_client.deploy_function(sample_function_file)

            assert isinstance(result, DeploymentError)
            assert result.function_name == "test_func"
            assert "api error" in result.error.lower()

    def test_deploy_batch_success(self, deployment_client):
        """Test successful batch deployment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple function files
            func1 = Path(tmpdir) / "func1.py"
            func1.write_text("# function 1\nfrom tinybase_sdk import register")

            func2 = Path(tmpdir) / "func2.py"
            func2.write_text("# function 2\nfrom tinybase_sdk import register")

            # Mock batch upload response
            mock_response1 = MagicMock()
            mock_response1.function_name = "func1"
            mock_response1.version_id = "v1"
            mock_response1.content_hash = "hash1"
            mock_response1.is_new_version = True
            mock_response1.message = "Success"
            mock_response1.warnings = []

            mock_response2 = MagicMock()
            mock_response2.function_name = "func2"
            mock_response2.version_id = "v2"
            mock_response2.content_hash = "hash2"
            mock_response2.is_new_version = True
            mock_response2.message = "Success"
            mock_response2.warnings = []

            with patch("tinybase_sdk.deployment.upload_functions_batch") as mock_batch:
                mock_batch.sync.return_value = [mock_response1, mock_response2]

                results = deployment_client.deploy_batch([func1, func2])

                assert len(results) == 2
                assert all(isinstance(r, DeploymentResult) for r in results)
                assert results[0].function_name == "func1"
                assert results[1].function_name == "func2"

    def test_deploy_batch_with_file_errors(self, deployment_client):
        """Test batch deployment with some invalid files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            func1 = Path(tmpdir) / "func1.py"
            func1.write_text("# valid function")

            nonexistent = Path(tmpdir) / "nonexistent.py"
            txt_file = Path(tmpdir) / "test.txt"
            txt_file.write_text("not python")

            results = deployment_client.deploy_batch([func1, nonexistent, txt_file])

            # Should have 1 attempt to upload + 2 errors for invalid files
            assert len(results) >= 2
            errors = [r for r in results if isinstance(r, DeploymentError)]
            assert len(errors) == 2

    def test_list_versions_success(self, deployment_client):
        """Test listing function versions."""
        mock_version = MagicMock()
        mock_version.function_name = "test_func"
        mock_version.content_hash = "abc123"
        mock_version.file_size = 1024
        mock_version.deployed_at = "2026-01-20T00:00:00"
        mock_version.notes = "Test deployment"
        mock_version.execution_count = 5

        with patch("tinybase_sdk.deployment.list_function_versions") as mock_list:
            mock_list.sync.return_value = [mock_version]

            versions = deployment_client.list_versions("test_func", limit=10)

            assert versions is not None
            assert len(versions) == 1
            assert versions[0]["function_name"] == "test_func"
            assert versions[0]["content_hash"] == "abc123"
            assert versions[0]["execution_count"] == 5

    def test_list_versions_api_error(self, deployment_client):
        """Test list_versions handling API errors."""
        with patch("tinybase_sdk.deployment.list_function_versions") as mock_list:
            mock_list.sync.side_effect = Exception("API error")

            versions = deployment_client.list_versions("test_func")

            assert versions is None


class TestDeploymentResult:
    """Tests for DeploymentResult dataclass."""

    def test_deployment_result_creation(self):
        """Test creating a DeploymentResult."""
        result = DeploymentResult(
            function_name="test",
            version_id="v123",
            content_hash="abc",
            is_new_version=True,
            message="Success",
            warnings=["warning1"],
        )

        assert result.function_name == "test"
        assert result.version_id == "v123"
        assert result.content_hash == "abc"
        assert result.is_new_version is True
        assert result.message == "Success"
        assert result.warnings == ["warning1"]


class TestDeploymentError:
    """Tests for DeploymentError dataclass."""

    def test_deployment_error_creation(self):
        """Test creating a DeploymentError."""
        error = DeploymentError(function_name="test", error="Something went wrong")

        assert error.function_name == "test"
        assert error.error == "Something went wrong"
