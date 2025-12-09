"""
S3-compatible file storage for TinyBase.

Provides a simple interface for uploading and downloading files
to S3-compatible storage (AWS S3, MinIO, DigitalOcean Spaces, etc.).
"""

import logging
from io import BytesIO
from typing import BinaryIO
from uuid import uuid4

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from sqlmodel import Session

from tinybase.db.models import InstanceSettings

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Exception raised for storage operations."""

    pass


class StorageService:
    """
    S3-compatible storage service.

    Handles file uploads, downloads, and deletions using boto3.
    Configuration is read from InstanceSettings.
    """

    def __init__(self, session: Session) -> None:
        """
        Initialize the storage service.

        Args:
            session: Database session to read settings from
        """
        self.session = session
        self._client = None
        self._settings = None

    def _get_settings(self) -> InstanceSettings | None:
        """Get instance settings from database."""
        if self._settings is None:
            self._settings = self.session.get(InstanceSettings, 1)
        return self._settings

    def is_enabled(self) -> bool:
        """Check if storage is enabled and configured."""
        settings = self._get_settings()
        if not settings or not settings.storage_enabled:
            return False
        if not settings.storage_endpoint or not settings.storage_bucket:
            return False
        if not settings.storage_access_key or not settings.storage_secret_key:
            return False
        return True

    def _get_client(self):
        """Get or create the boto3 S3 client."""
        if self._client is not None:
            return self._client

        settings = self._get_settings()
        if not settings:
            raise StorageError("Storage not configured")

        # Configure boto3 client
        config = BotoConfig(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
        )

        self._client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint,
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
            region_name=settings.storage_region or "us-east-1",
            config=config,
        )

        return self._client

    def _get_bucket(self) -> str:
        """Get the configured bucket name."""
        settings = self._get_settings()
        if not settings or not settings.storage_bucket:
            raise StorageError("Storage bucket not configured")
        return settings.storage_bucket

    def upload_file(
        self,
        file_data: BinaryIO | bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        path_prefix: str = "",
    ) -> str:
        """
        Upload a file to storage.

        Args:
            file_data: File data as bytes or file-like object
            filename: Original filename (used for extension)
            content_type: MIME type of the file
            path_prefix: Optional path prefix (e.g., "uploads/images/")

        Returns:
            The storage key (path) of the uploaded file

        Raises:
            StorageError: If upload fails
        """
        if not self.is_enabled():
            raise StorageError("Storage is not enabled")

        client = self._get_client()
        bucket = self._get_bucket()

        # Generate unique key with original extension
        file_id = uuid4()
        ext = ""
        if "." in filename:
            ext = "." + filename.rsplit(".", 1)[-1].lower()

        key = f"{path_prefix}{file_id}{ext}".lstrip("/")

        try:
            # Convert bytes to file-like object if needed
            if isinstance(file_data, bytes):
                file_data = BytesIO(file_data)

            client.upload_fileobj(
                file_data,
                bucket,
                key,
                ExtraArgs={
                    "ContentType": content_type,
                },
            )

            logger.info(f"Uploaded file to storage: {key}")
            return key

        except ClientError as e:
            logger.exception(f"Failed to upload file: {e}")
            raise StorageError(f"Failed to upload file: {e}")

    def download_file(self, key: str) -> bytes:
        """
        Download a file from storage.

        Args:
            key: The storage key (path) of the file

        Returns:
            The file contents as bytes

        Raises:
            StorageError: If download fails
        """
        if not self.is_enabled():
            raise StorageError("Storage is not enabled")

        client = self._get_client()
        bucket = self._get_bucket()

        try:
            buffer = BytesIO()
            client.download_fileobj(bucket, key, buffer)
            buffer.seek(0)
            return buffer.read()

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise StorageError(f"File not found: {key}")
            logger.exception(f"Failed to download file: {e}")
            raise StorageError(f"Failed to download file: {e}")

    def delete_file(self, key: str) -> None:
        """
        Delete a file from storage.

        Args:
            key: The storage key (path) of the file

        Raises:
            StorageError: If deletion fails
        """
        if not self.is_enabled():
            raise StorageError("Storage is not enabled")

        client = self._get_client()
        bucket = self._get_bucket()

        try:
            client.delete_object(Bucket=bucket, Key=key)
            logger.info(f"Deleted file from storage: {key}")

        except ClientError as e:
            logger.exception(f"Failed to delete file: {e}")
            raise StorageError(f"Failed to delete file: {e}")

    def get_presigned_url(
        self,
        key: str,
        expires_in: int = 3600,
        method: str = "get_object",
    ) -> str:
        """
        Generate a presigned URL for a file.

        Args:
            key: The storage key (path) of the file
            expires_in: URL expiration time in seconds (default: 1 hour)
            method: S3 method ('get_object' for download, 'put_object' for upload)

        Returns:
            Presigned URL string

        Raises:
            StorageError: If URL generation fails
        """
        if not self.is_enabled():
            raise StorageError("Storage is not enabled")

        client = self._get_client()
        bucket = self._get_bucket()

        try:
            url = client.generate_presigned_url(
                method,
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in,
            )
            return url

        except ClientError as e:
            logger.exception(f"Failed to generate presigned URL: {e}")
            raise StorageError(f"Failed to generate presigned URL: {e}")

    def file_exists(self, key: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            key: The storage key (path) of the file

        Returns:
            True if file exists, False otherwise
        """
        if not self.is_enabled():
            return False

        client = self._get_client()
        bucket = self._get_bucket()

        try:
            client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError:
            return False
