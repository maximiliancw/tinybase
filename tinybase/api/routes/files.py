"""
File storage API routes.

Provides endpoints for:
- File upload
- File download
- File deletion
- Presigned URL generation
"""

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from tinybase.auth import CurrentUser, DBSession
from tinybase.storage import StorageError, StorageService

router = APIRouter(prefix="/files", tags=["files"])


# =============================================================================
# Response Schemas
# =============================================================================


class FileUploadResponse(BaseModel):
    """Response after successful file upload."""

    key: str = Field(description="Storage key (path) of the uploaded file")
    filename: str = Field(description="Original filename")
    content_type: str = Field(description="MIME type")
    size: int = Field(description="File size in bytes")


class PresignedUrlResponse(BaseModel):
    """Response with presigned URL."""

    url: str = Field(description="Presigned URL for file access")
    expires_in: int = Field(description="URL expiration time in seconds")


class StorageStatusResponse(BaseModel):
    """Storage status response."""

    enabled: bool = Field(description="Whether storage is enabled and configured")


# =============================================================================
# Routes
# =============================================================================


@router.get(
    "/status",
    response_model=StorageStatusResponse,
    summary="Check storage status",
    description="Check if file storage is enabled and configured.",
)
def get_storage_status(
    session: DBSession,
    _user: CurrentUser,
) -> StorageStatusResponse:
    """Check if storage is enabled."""
    service = StorageService()
    return StorageStatusResponse(enabled=service.is_enabled())


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    summary="Upload a file",
    description="Upload a file to storage. Returns the storage key.",
)
async def upload_file(
    session: DBSession,
    user: CurrentUser,
    file: UploadFile = File(...),
    path_prefix: str = Query(default="", description="Optional path prefix"),
) -> FileUploadResponse:
    """Upload a file to storage."""
    service = StorageService()

    if not service.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File storage is not enabled",
        )

    # Read file content
    content = await file.read()

    try:
        key = service.upload_file(
            file_data=content,
            filename=file.filename or "unknown",
            content_type=file.content_type or "application/octet-stream",
            path_prefix=path_prefix,
        )

        return FileUploadResponse(
            key=key,
            filename=file.filename or "unknown",
            content_type=file.content_type or "application/octet-stream",
            size=len(content),
        )

    except StorageError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/download/{key:path}",
    summary="Download a file",
    description="Download a file from storage by its key.",
)
def download_file(
    key: str,
    session: DBSession,
    _user: CurrentUser,
) -> Response:
    """Download a file from storage."""
    service = StorageService()

    if not service.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File storage is not enabled",
        )

    try:
        content = service.download_file(key)

        # Try to determine content type from extension
        content_type = "application/octet-stream"
        if "." in key:
            ext = key.rsplit(".", 1)[-1].lower()
            ext_map = {
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "png": "image/png",
                "gif": "image/gif",
                "webp": "image/webp",
                "pdf": "application/pdf",
                "json": "application/json",
                "txt": "text/plain",
                "csv": "text/csv",
                "html": "text/html",
                "css": "text/css",
                "js": "application/javascript",
            }
            content_type = ext_map.get(ext, content_type)

        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{key.split("/")[-1]}"',
            },
        )

    except StorageError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {key}",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete(
    "/{key:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a file",
    description="Delete a file from storage by its key.",
)
def delete_file(
    key: str,
    session: DBSession,
    _user: CurrentUser,
) -> None:
    """Delete a file from storage."""
    service = StorageService()

    if not service.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File storage is not enabled",
        )

    try:
        service.delete_file(key)
    except StorageError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/presigned/{key:path}",
    response_model=PresignedUrlResponse,
    summary="Get presigned URL",
    description="Generate a presigned URL for direct file access.",
)
def get_presigned_url(
    key: str,
    session: DBSession,
    _user: CurrentUser,
    expires_in: int = Query(default=3600, ge=60, le=86400, description="Expiration in seconds"),
) -> PresignedUrlResponse:
    """Generate a presigned URL for a file."""
    service = StorageService()

    if not service.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File storage is not enabled",
        )

    try:
        url = service.get_presigned_url(key, expires_in)
        return PresignedUrlResponse(url=url, expires_in=expires_in)
    except StorageError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
