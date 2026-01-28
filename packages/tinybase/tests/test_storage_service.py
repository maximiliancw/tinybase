"""
Tests for S3-compatible file storage service.

Tests the StorageService class including:
- File upload (bytes and streams)
- File download
- File deletion
- Presigned URL generation
- File existence checks
- Error handling
"""

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from tinybase.storage import StorageError, StorageService

# =============================================================================
# Mock Settings
# =============================================================================


class MockStorageSettings:
    """Mock storage settings for testing."""

    def __init__(
        self,
        enabled=True,
        url="http://localhost:9000",
        bucket="test-bucket",
        access_key="test-access-key",
        secret_key="test-secret-key",
        region="us-east-1",
    ):
        self.enabled = enabled
        self.url = url
        self.bucket = bucket
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region


class MockSettings:
    """Mock settings object."""

    def __init__(self, storage_settings=None):
        self.storage = storage_settings or MockStorageSettings()


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_settings():
    """Create mock settings with storage enabled."""
    return MockSettings()


@pytest.fixture
def mock_settings_disabled():
    """Create mock settings with storage disabled."""
    return MockSettings(MockStorageSettings(enabled=False))


@pytest.fixture
def mock_settings_partial():
    """Create mock settings with incomplete configuration."""
    return MockSettings(MockStorageSettings(url=None, bucket=None))


@pytest.fixture
def mock_s3_client():
    """Create a mock boto3 S3 client."""
    return MagicMock()


@pytest.fixture
def storage_service(mock_settings, mock_s3_client):
    """Create a StorageService with mocked dependencies."""
    with patch("tinybase.storage.settings", mock_settings):
        with patch("tinybase.storage.boto3.client", return_value=mock_s3_client):
            service = StorageService()
            service._client = mock_s3_client
            yield service


# =============================================================================
# is_enabled Tests
# =============================================================================


def test_is_enabled_true(mock_settings):
    """Test is_enabled returns True when properly configured."""
    with patch("tinybase.storage.settings", mock_settings):
        service = StorageService()
        assert service.is_enabled() is True


def test_is_enabled_false_when_disabled(mock_settings_disabled):
    """Test is_enabled returns False when storage is disabled."""
    with patch("tinybase.storage.settings", mock_settings_disabled):
        service = StorageService()
        assert service.is_enabled() is False


def test_is_enabled_false_missing_url(mock_settings):
    """Test is_enabled returns False when URL is missing."""
    mock_settings.storage.url = None
    with patch("tinybase.storage.settings", mock_settings):
        service = StorageService()
        assert service.is_enabled() is False


def test_is_enabled_false_missing_bucket(mock_settings):
    """Test is_enabled returns False when bucket is missing."""
    mock_settings.storage.bucket = None
    with patch("tinybase.storage.settings", mock_settings):
        service = StorageService()
        assert service.is_enabled() is False


def test_is_enabled_false_missing_access_key(mock_settings):
    """Test is_enabled returns False when access key is missing."""
    mock_settings.storage.access_key = None
    with patch("tinybase.storage.settings", mock_settings):
        service = StorageService()
        assert service.is_enabled() is False


def test_is_enabled_false_missing_secret_key(mock_settings):
    """Test is_enabled returns False when secret key is missing."""
    mock_settings.storage.secret_key = None
    with patch("tinybase.storage.settings", mock_settings):
        service = StorageService()
        assert service.is_enabled() is False


# =============================================================================
# _get_client Tests
# =============================================================================


def test_get_client_creates_client(mock_settings):
    """Test _get_client creates boto3 client with correct config."""
    with patch("tinybase.storage.settings", mock_settings):
        with patch("tinybase.storage.boto3.client") as mock_boto_client:
            mock_boto_client.return_value = MagicMock()

            service = StorageService()
            service._get_client()

            mock_boto_client.assert_called_once()
            call_kwargs = mock_boto_client.call_args[1]
            assert call_kwargs["endpoint_url"] == "http://localhost:9000"
            assert call_kwargs["aws_access_key_id"] == "test-access-key"
            assert call_kwargs["aws_secret_access_key"] == "test-secret-key"


def test_get_client_reuses_client(mock_settings, mock_s3_client):
    """Test _get_client reuses existing client."""
    with patch("tinybase.storage.settings", mock_settings):
        with patch("tinybase.storage.boto3.client") as mock_boto_client:
            service = StorageService()
            service._client = mock_s3_client

            client = service._get_client()

            # Should not create new client
            mock_boto_client.assert_not_called()
            assert client is mock_s3_client


def test_get_client_raises_when_disabled(mock_settings_disabled):
    """Test _get_client raises StorageError when disabled."""
    with patch("tinybase.storage.settings", mock_settings_disabled):
        service = StorageService()

        with pytest.raises(StorageError, match="Storage not configured"):
            service._get_client()


# =============================================================================
# _get_bucket Tests
# =============================================================================


def test_get_bucket_returns_bucket(mock_settings):
    """Test _get_bucket returns configured bucket name."""
    with patch("tinybase.storage.settings", mock_settings):
        service = StorageService()
        bucket = service._get_bucket()
        assert bucket == "test-bucket"


def test_get_bucket_raises_when_not_configured(mock_settings):
    """Test _get_bucket raises StorageError when bucket not configured."""
    mock_settings.storage.bucket = None
    with patch("tinybase.storage.settings", mock_settings):
        service = StorageService()

        with pytest.raises(StorageError, match="Storage bucket not configured"):
            service._get_bucket()


# =============================================================================
# upload_file Tests
# =============================================================================


def test_upload_file_bytes(storage_service, mock_s3_client, mock_settings):
    """Test uploading file as bytes."""
    with patch("tinybase.storage.settings", mock_settings):
        file_data = b"Hello, World!"
        key = storage_service.upload_file(file_data, "test.txt")

        assert key.endswith(".txt")
        mock_s3_client.upload_fileobj.assert_called_once()


def test_upload_file_stream(storage_service, mock_s3_client, mock_settings):
    """Test uploading file as stream/file-like object."""
    with patch("tinybase.storage.settings", mock_settings):
        file_stream = BytesIO(b"Stream content")
        key = storage_service.upload_file(file_stream, "document.pdf")

        assert key.endswith(".pdf")
        mock_s3_client.upload_fileobj.assert_called_once()


def test_upload_file_preserves_extension(storage_service, mock_s3_client, mock_settings):
    """Test upload preserves file extension."""
    with patch("tinybase.storage.settings", mock_settings):
        key1 = storage_service.upload_file(b"data", "image.PNG")
        assert key1.endswith(".png")  # Should be lowercased

        mock_s3_client.upload_fileobj.reset_mock()

        key2 = storage_service.upload_file(b"data", "document.PDF")
        assert key2.endswith(".pdf")


def test_upload_file_no_extension(storage_service, mock_s3_client, mock_settings):
    """Test upload handles files without extension."""
    with patch("tinybase.storage.settings", mock_settings):
        key = storage_service.upload_file(b"data", "filename_no_ext")

        # Should not have extension
        assert "." not in key.split("/")[-1].rsplit("-", 1)[0]  # UUID doesn't have dots


def test_upload_file_with_prefix(storage_service, mock_s3_client, mock_settings):
    """Test upload with path prefix."""
    with patch("tinybase.storage.settings", mock_settings):
        key = storage_service.upload_file(b"data", "test.txt", path_prefix="uploads/images/")

        assert key.startswith("uploads/images/")
        assert key.endswith(".txt")


def test_upload_file_with_content_type(storage_service, mock_s3_client, mock_settings):
    """Test upload with custom content type."""
    with patch("tinybase.storage.settings", mock_settings):
        storage_service.upload_file(b"data", "test.json", content_type="application/json")

        call_args = mock_s3_client.upload_fileobj.call_args
        extra_args = call_args[1]["ExtraArgs"]
        assert extra_args["ContentType"] == "application/json"


def test_upload_file_disabled(mock_settings_disabled):
    """Test upload raises error when storage disabled."""
    with patch("tinybase.storage.settings", mock_settings_disabled):
        service = StorageService()

        with pytest.raises(StorageError, match="Storage is not enabled"):
            service.upload_file(b"data", "test.txt")


def test_upload_file_client_error(storage_service, mock_s3_client, mock_settings):
    """Test upload handles ClientError."""
    with patch("tinybase.storage.settings", mock_settings):
        mock_s3_client.upload_fileobj.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Server error"}},
            "upload_fileobj",
        )

        with pytest.raises(StorageError, match="Failed to upload file"):
            storage_service.upload_file(b"data", "test.txt")


# =============================================================================
# download_file Tests
# =============================================================================


def test_download_file_success(storage_service, mock_s3_client, mock_settings):
    """Test downloading file successfully."""
    with patch("tinybase.storage.settings", mock_settings):
        expected_content = b"Downloaded content"

        def mock_download(bucket, key, buffer):
            buffer.write(expected_content)

        mock_s3_client.download_fileobj.side_effect = mock_download

        content = storage_service.download_file("test-key")

        assert content == expected_content
        mock_s3_client.download_fileobj.assert_called_once()


def test_download_file_not_found(storage_service, mock_s3_client, mock_settings):
    """Test download handles 404 error."""
    with patch("tinybase.storage.settings", mock_settings):
        mock_s3_client.download_fileobj.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}},
            "download_fileobj",
        )

        with pytest.raises(StorageError, match="File not found"):
            storage_service.download_file("nonexistent-key")


def test_download_file_other_error(storage_service, mock_s3_client, mock_settings):
    """Test download handles other errors."""
    with patch("tinybase.storage.settings", mock_settings):
        mock_s3_client.download_fileobj.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Server error"}},
            "download_fileobj",
        )

        with pytest.raises(StorageError, match="Failed to download file"):
            storage_service.download_file("test-key")


def test_download_file_disabled(mock_settings_disabled):
    """Test download raises error when storage disabled."""
    with patch("tinybase.storage.settings", mock_settings_disabled):
        service = StorageService()

        with pytest.raises(StorageError, match="Storage is not enabled"):
            service.download_file("test-key")


# =============================================================================
# delete_file Tests
# =============================================================================


def test_delete_file_success(storage_service, mock_s3_client, mock_settings):
    """Test deleting file successfully."""
    with patch("tinybase.storage.settings", mock_settings):
        storage_service.delete_file("test-key")

        mock_s3_client.delete_object.assert_called_once_with(Bucket="test-bucket", Key="test-key")


def test_delete_file_error(storage_service, mock_s3_client, mock_settings):
    """Test delete handles errors."""
    with patch("tinybase.storage.settings", mock_settings):
        mock_s3_client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Server error"}},
            "delete_object",
        )

        with pytest.raises(StorageError, match="Failed to delete file"):
            storage_service.delete_file("test-key")


def test_delete_file_disabled(mock_settings_disabled):
    """Test delete raises error when storage disabled."""
    with patch("tinybase.storage.settings", mock_settings_disabled):
        service = StorageService()

        with pytest.raises(StorageError, match="Storage is not enabled"):
            service.delete_file("test-key")


# =============================================================================
# get_presigned_url Tests
# =============================================================================


def test_get_presigned_url_download(storage_service, mock_s3_client, mock_settings):
    """Test generating presigned URL for download."""
    with patch("tinybase.storage.settings", mock_settings):
        mock_s3_client.generate_presigned_url.return_value = (
            "https://s3.example.com/test-bucket/key?signature=xxx"
        )

        url = storage_service.get_presigned_url("test-key")

        assert "https://s3.example.com" in url
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": "test-key"},
            ExpiresIn=3600,
        )


def test_get_presigned_url_upload(storage_service, mock_s3_client, mock_settings):
    """Test generating presigned URL for upload."""
    with patch("tinybase.storage.settings", mock_settings):
        mock_s3_client.generate_presigned_url.return_value = (
            "https://s3.example.com/test-bucket/key?signature=xxx"
        )

        storage_service.get_presigned_url("test-key", method="put_object")

        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "put_object",
            Params={"Bucket": "test-bucket", "Key": "test-key"},
            ExpiresIn=3600,
        )


def test_get_presigned_url_custom_expiry(storage_service, mock_s3_client, mock_settings):
    """Test generating presigned URL with custom expiry."""
    with patch("tinybase.storage.settings", mock_settings):
        mock_s3_client.generate_presigned_url.return_value = "https://url"

        storage_service.get_presigned_url("test-key", expires_in=7200)

        call_args = mock_s3_client.generate_presigned_url.call_args
        assert call_args[1]["ExpiresIn"] == 7200


def test_get_presigned_url_error(storage_service, mock_s3_client, mock_settings):
    """Test presigned URL handles errors."""
    with patch("tinybase.storage.settings", mock_settings):
        mock_s3_client.generate_presigned_url.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Server error"}},
            "generate_presigned_url",
        )

        with pytest.raises(StorageError, match="Failed to generate presigned URL"):
            storage_service.get_presigned_url("test-key")


def test_get_presigned_url_disabled(mock_settings_disabled):
    """Test presigned URL raises error when storage disabled."""
    with patch("tinybase.storage.settings", mock_settings_disabled):
        service = StorageService()

        with pytest.raises(StorageError, match="Storage is not enabled"):
            service.get_presigned_url("test-key")


# =============================================================================
# file_exists Tests
# =============================================================================


def test_file_exists_true(storage_service, mock_s3_client, mock_settings):
    """Test file_exists returns True when file exists."""
    with patch("tinybase.storage.settings", mock_settings):
        mock_s3_client.head_object.return_value = {}

        result = storage_service.file_exists("existing-key")

        assert result is True
        mock_s3_client.head_object.assert_called_once_with(Bucket="test-bucket", Key="existing-key")


def test_file_exists_false(storage_service, mock_s3_client, mock_settings):
    """Test file_exists returns False when file doesn't exist."""
    with patch("tinybase.storage.settings", mock_settings):
        mock_s3_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}},
            "head_object",
        )

        result = storage_service.file_exists("nonexistent-key")

        assert result is False


def test_file_exists_disabled(mock_settings_disabled):
    """Test file_exists returns False when storage disabled."""
    with patch("tinybase.storage.settings", mock_settings_disabled):
        service = StorageService()

        result = service.file_exists("any-key")

        assert result is False


# =============================================================================
# Integration-style Tests
# =============================================================================


def test_upload_download_roundtrip(storage_service, mock_s3_client, mock_settings):
    """Test uploading and downloading a file."""
    with patch("tinybase.storage.settings", mock_settings):
        original_content = b"Round trip content"

        # Upload
        key = storage_service.upload_file(original_content, "roundtrip.txt")

        # Mock download to return what was uploaded
        def mock_download(bucket, key_arg, buffer):
            buffer.write(original_content)

        mock_s3_client.download_fileobj.side_effect = mock_download

        # Download
        downloaded = storage_service.download_file(key)

        assert downloaded == original_content


def test_storage_error_exception():
    """Test StorageError exception."""
    error = StorageError("Test error message")
    assert str(error) == "Test error message"
    assert isinstance(error, Exception)
