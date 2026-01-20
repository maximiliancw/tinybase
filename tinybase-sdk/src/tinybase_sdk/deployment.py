"""
Function deployment helpers for TinyBase SDK.

Provides Python API for deploying functions to a remote TinyBase instance.
Uses the auto-generated OpenAPI client for all API calls.

Note: This module requires the OpenAPI client to be generated first.
Run: python tinybase-sdk/scripts/generate_client.py
"""

from dataclasses import dataclass
from pathlib import Path

from tinybase_sdk.client import Client
from tinybase_sdk.client.api.admin import (
    list_function_versions,
    upload_function,
    upload_functions_batch,
)
from tinybase_sdk.client.models import BatchUploadRequest, FunctionUploadRequest


@dataclass
class DeploymentResult:
    """Result of a function deployment."""

    function_name: str
    version_id: str
    content_hash: str
    is_new_version: bool
    message: str
    warnings: list[str]


@dataclass
class DeploymentError:
    """Error during function deployment."""

    function_name: str
    error: str


class DeploymentClient:
    """
    Client for deploying functions to TinyBase.

    Wraps the auto-generated OpenAPI client with deployment-specific helpers.
    """

    def __init__(self, base_url: str, token: str, timeout: float = 30.0):
        """
        Initialize deployment client.

        Args:
            base_url: Base URL of TinyBase instance (e.g., "https://api.tinybase.com")
            token: Admin authentication token
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.client = Client(base_url=self.base_url, token=token, timeout=timeout)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def close(self):
        """Close the HTTP client."""
        if hasattr(self.client, "close"):
            self.client.close()

    def deploy_function(
        self, file_path: Path, notes: str | None = None
    ) -> DeploymentResult | DeploymentError:
        """
        Deploy a single function file.

        Args:
            file_path: Path to the function Python file
            notes: Optional deployment notes

        Returns:
            DeploymentResult on success, DeploymentError on failure
        """
        if not file_path.exists():
            return DeploymentError(
                function_name=file_path.stem, error=f"File not found: {file_path}"
            )

        if not file_path.suffix == ".py":
            return DeploymentError(
                function_name=file_path.stem,
                error=f"Not a Python file: {file_path}",
            )

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            return DeploymentError(function_name=file_path.stem, error=f"Failed to read file: {e}")

        try:
            request = FunctionUploadRequest(
                filename=file_path.name,
                content=content,
                notes=notes,
            )
            response = upload_function.sync(client=self.client, body=request)

            if response is None:
                return DeploymentError(
                    function_name=file_path.stem, error="No response from server"
                )

            return DeploymentResult(
                function_name=response.function_name,
                version_id=response.version_id,
                content_hash=response.content_hash,
                is_new_version=response.is_new_version,
                message=response.message,
                warnings=response.warnings or [],
            )
        except Exception as e:
            return DeploymentError(function_name=file_path.stem, error=f"Upload failed: {e}")

    def deploy_batch(
        self, file_paths: list[Path], notes: str | None = None
    ) -> list[DeploymentResult | DeploymentError]:
        """
        Deploy multiple function files in a single batch request.

        Args:
            file_paths: List of paths to function Python files
            notes: Optional deployment notes (applies to all functions)

        Returns:
            List of DeploymentResult or DeploymentError for each function
        """
        function_requests = []
        errors = []

        # Read all files first
        for file_path in file_paths:
            if not file_path.exists():
                errors.append(
                    DeploymentError(
                        function_name=file_path.stem, error=f"File not found: {file_path}"
                    )
                )
                continue

            if not file_path.suffix == ".py":
                errors.append(
                    DeploymentError(
                        function_name=file_path.stem,
                        error=f"Not a Python file: {file_path}",
                    )
                )
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
                func_request = FunctionUploadRequest(
                    filename=file_path.name,
                    content=content,
                    notes=notes,
                )
                function_requests.append(func_request)
            except Exception as e:
                errors.append(
                    DeploymentError(function_name=file_path.stem, error=f"Failed to read file: {e}")
                )

        # If all files had errors, return early
        if not function_requests:
            return errors

        # Send batch request
        try:
            request = BatchUploadRequest(functions=function_requests)
            responses = upload_functions_batch.sync(client=self.client, body=request)

            if responses is None:
                # Convert all to errors
                for req in function_requests:
                    func_name = req.filename[:-3] if req.filename.endswith(".py") else req.filename
                    errors.append(
                        DeploymentError(
                            function_name=func_name,
                            error="Batch upload failed: No response from server",
                        )
                    )
                return errors

            results = []
            for response in responses:
                if "error" in response.message.lower() or "failed" in response.message.lower():
                    results.append(
                        DeploymentError(
                            function_name=response.function_name,
                            error=response.message,
                        )
                    )
                else:
                    results.append(
                        DeploymentResult(
                            function_name=response.function_name,
                            version_id=response.version_id,
                            content_hash=response.content_hash,
                            is_new_version=response.is_new_version,
                            message=response.message,
                            warnings=response.warnings or [],
                        )
                    )

            return errors + results
        except Exception as e:
            # Convert all pending uploads to errors
            for req in function_requests:
                func_name = req.filename[:-3] if req.filename.endswith(".py") else req.filename
                errors.append(
                    DeploymentError(function_name=func_name, error=f"Batch upload failed: {e}")
                )
            return errors

    def list_versions(self, function_name: str, limit: int = 50) -> list[dict] | None:
        """
        List deployed versions of a function.

        Args:
            function_name: Name of the function
            limit: Maximum number of versions to return (1-100)

        Returns:
            List of version info dicts, or None on error
        """
        try:
            versions = list_function_versions.sync(
                client=self.client,
                function_name=function_name,
                limit=limit,
            )

            if versions is None:
                return None

            # Convert to dicts for simpler CLI usage
            return [
                {
                    "function_name": v.function_name,
                    "content_hash": v.content_hash,
                    "file_size": v.file_size,
                    "deployed_at": v.deployed_at,
                    "notes": v.notes,
                    "execution_count": v.execution_count,
                }
                for v in versions
            ]
        except Exception:
            return None
