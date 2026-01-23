"""
Extension management API routes.

Provides admin-only endpoints for:
- Listing installed extensions
- Installing extensions from GitHub
- Uninstalling extensions
- Enabling/disabling extensions
- Checking for updates
"""

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlmodel import select

from tinybase.auth import CurrentAdminUser, DBSession
from tinybase.db.models import Extension
from tinybase.extensions import (
    InstallError,
    check_for_updates,
    install_extension,
    uninstall_extension,
)
from tinybase.utils import utcnow

router = APIRouter(prefix="/admin/extensions", tags=["extensions"])


# =============================================================================
# Request/Response Schemas
# =============================================================================


class ExtensionInfo(BaseModel):
    """Extension information response."""

    id: str = Field(description="Extension ID")
    name: str = Field(description="Extension name")
    version: str = Field(description="Extension version")
    description: str | None = Field(default=None, description="Extension description")
    author: str | None = Field(default=None, description="Extension author")
    repo_url: str = Field(description="GitHub repository URL")
    is_enabled: bool = Field(description="Whether extension is enabled")
    installed_at: str = Field(description="Installation timestamp")
    updated_at: str = Field(description="Last update timestamp")
    update_available: str | None = Field(
        default=None, description="Latest version if update available"
    )


class ExtensionListResponse(BaseModel):
    """Paginated extension list response."""

    extensions: list[ExtensionInfo] = Field(description="Extensions")
    total: int = Field(description="Total count")
    limit: int = Field(description="Page size")
    offset: int = Field(description="Page offset")


class ExtensionInstallRequest(BaseModel):
    """Extension installation request."""

    repo_url: str = Field(
        description="GitHub repository URL", examples=["https://github.com/user/tinybase-extension"]
    )


class ExtensionUpdateRequest(BaseModel):
    """Extension update request."""

    is_enabled: bool | None = Field(default=None, description="Enable/disable extension")


# =============================================================================
# Helper Functions
# =============================================================================


def extension_to_response(ext: Extension, update_version: str | None = None) -> ExtensionInfo:
    """Convert Extension model to response schema."""
    return ExtensionInfo(
        id=str(ext.id),
        name=ext.name,
        version=ext.version,
        description=ext.description,
        author=ext.author,
        repo_url=ext.repo_url,
        is_enabled=ext.is_enabled,
        installed_at=ext.installed_at.isoformat(),
        updated_at=ext.updated_at.isoformat(),
        update_available=update_version,
    )


# =============================================================================
# Extension Routes
# =============================================================================


@router.get(
    "",
    response_model=ExtensionListResponse,
    summary="List extensions",
    description="Get a paginated list of installed extensions.",
)
def list_extensions(
    session: DBSession,
    _admin: CurrentAdminUser,
    enabled_only: bool = Query(default=False, description="Only show enabled extensions"),
    check_updates: bool = Query(default=False, description="Check for available updates"),
    limit: int = Query(default=100, ge=1, le=1000, description="Page size"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
) -> ExtensionListResponse:
    """List installed extensions with pagination."""
    # Build count query
    count_stmt = select(func.count(Extension.id))
    if enabled_only:
        count_stmt = count_stmt.where(Extension.is_enabled)
    total = session.exec(count_stmt).one()

    # Build data query
    query = select(Extension)
    if enabled_only:
        query = query.where(Extension.is_enabled)
    query = query.order_by(Extension.name).offset(offset).limit(limit)

    extensions = list(session.exec(query).all())

    # Optionally check for updates
    extension_infos = []
    for ext in extensions:
        update_version = None
        if check_updates:
            result = check_for_updates(session, ext.name)
            if result:
                _, update_version = result
        extension_infos.append(extension_to_response(ext, update_version))

    return ExtensionListResponse(
        extensions=extension_infos,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=ExtensionInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Install extension",
    description="Install an extension from a GitHub repository.",
)
def create_extension(
    request: ExtensionInstallRequest,
    session: DBSession,
    admin: CurrentAdminUser,
) -> ExtensionInfo:
    """Install an extension from GitHub."""
    try:
        extension = install_extension(
            session=session,
            repo_url=request.repo_url,
            user_id=admin.id,
        )
        return extension_to_response(extension)
    except InstallError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{extension_name}",
    response_model=ExtensionInfo,
    summary="Get extension details",
    description="Get details of a specific extension.",
)
def get_extension(
    extension_name: str,
    session: DBSession,
    _admin: CurrentAdminUser,
    check_updates: bool = Query(default=False, description="Check for available updates"),
) -> ExtensionInfo:
    """Get extension details by name."""
    extension = session.exec(select(Extension).where(Extension.name == extension_name)).first()

    if not extension:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Extension '{extension_name}' not found",
        )

    update_version = None
    if check_updates:
        result = check_for_updates(session, extension.name)
        if result:
            _, update_version = result

    return extension_to_response(extension, update_version)


@router.patch(
    "/{extension_name}",
    response_model=ExtensionInfo,
    summary="Update extension",
    description="Enable or disable an extension.",
)
def update_extension(
    extension_name: str,
    request: ExtensionUpdateRequest,
    session: DBSession,
    _admin: CurrentAdminUser,
) -> ExtensionInfo:
    """Update extension settings (enable/disable)."""
    extension = session.exec(select(Extension).where(Extension.name == extension_name)).first()

    if not extension:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Extension '{extension_name}' not found",
        )

    if request.is_enabled is not None:
        extension.is_enabled = request.is_enabled

    extension.updated_at = utcnow()
    session.add(extension)
    session.commit()
    session.refresh(extension)

    return extension_to_response(extension)


@router.delete(
    "/{extension_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Uninstall extension",
    description="Uninstall an extension and remove its files.",
)
def delete_extension(
    extension_name: str,
    session: DBSession,
    _admin: CurrentAdminUser,
) -> None:
    """Uninstall an extension."""
    if not uninstall_extension(session, extension_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Extension '{extension_name}' not found",
        )
