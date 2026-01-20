"""
Admin API routes.

Provides admin-only endpoints for:
- Function call history
- User management
- Instance settings
"""

from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlmodel import select

from tinybase.auth import (
    CurrentAdminUser,
    DbSession,
    create_application_token,
    hash_password,
    revoke_application_token,
)
from tinybase.db.models import (
    ApplicationToken,
    FunctionCall,
    FunctionVersion,
    InstanceSettings,
    Metrics,
    User,
)
from tinybase.utils import FunctionCallStatus, TriggerType, utcnow

router = APIRouter(prefix="/admin", tags=["Admin"])


# =============================================================================
# Response Schemas
# =============================================================================


class FunctionCallInfo(BaseModel):
    """Function call metadata."""

    id: str = Field(description="Call ID")
    function_name: str = Field(description="Function name")
    status: str = Field(description="Execution status")
    trigger_type: str = Field(description="Trigger type (manual/schedule)")
    trigger_id: str | None = Field(default=None, description="Schedule ID if scheduled")
    requested_by_user_id: str | None = Field(default=None, description="User ID")
    started_at: str | None = Field(default=None, description="Start time")
    finished_at: str | None = Field(default=None, description="End time")
    duration_ms: int | None = Field(default=None, description="Duration in ms")
    error_message: str | None = Field(default=None, description="Error message")
    error_type: str | None = Field(default=None, description="Error type")
    created_at: str = Field(description="Created timestamp")


class FunctionCallListResponse(BaseModel):
    """Paginated function call list."""

    calls: list[FunctionCallInfo] = Field(description="Function calls")
    total: int = Field(description="Total count")
    limit: int = Field(description="Page size")
    offset: int = Field(description="Page offset")


class UserInfo(BaseModel):
    """User information for admin."""

    id: str = Field(description="User ID")
    email: str = Field(description="Email address")
    is_admin: bool = Field(description="Admin status")
    created_at: str = Field(description="Created timestamp")
    updated_at: str = Field(description="Updated timestamp")


class UserListResponse(BaseModel):
    """Paginated user list."""

    users: list[UserInfo] = Field(description="Users")
    total: int = Field(description="Total count")
    limit: int = Field(description="Page size")
    offset: int = Field(description="Page offset")


class UserCreate(BaseModel):
    """Create user request."""

    email: str = Field(description="Email address")
    password: str = Field(min_length=8, description="Password")
    is_admin: bool = Field(default=False, description="Admin status")


class UserUpdate(BaseModel):
    """Update user request."""

    email: str | None = Field(default=None, description="New email")
    password: str | None = Field(default=None, min_length=8, description="New password")
    is_admin: bool | None = Field(default=None, description="New admin status")


class FunctionUploadRequest(BaseModel):
    """Function upload request."""

    filename: str = Field(description="Function filename (e.g., my_func.py)")
    content: str = Field(description="Function file content")
    notes: str | None = Field(default=None, description="Optional deployment notes")


class FunctionUploadResponse(BaseModel):
    """Function upload response."""

    function_name: str = Field(description="Function name")
    version_id: str = Field(description="Version ID")
    content_hash: str = Field(description="Content hash")
    is_new_version: bool = Field(description="Whether this is a new version")
    message: str = Field(description="Status message")
    warnings: list[str] = Field(default_factory=list, description="Security/validation warnings")


class FunctionVersionInfo(BaseModel):
    """Function version information."""

    id: str = Field(description="Version ID")
    function_name: str = Field(description="Function name")
    content_hash: str = Field(description="Content hash")
    file_size: int = Field(description="File size in bytes")
    deployed_by_email: str | None = Field(default=None, description="Email of deploying user")
    deployed_at: str = Field(description="Deployment timestamp")
    notes: str | None = Field(default=None, description="Deployment notes")
    execution_count: int = Field(description="Number of executions using this version")


class BatchUploadRequest(BaseModel):
    """Batch function upload request."""

    functions: list[FunctionUploadRequest] = Field(description="List of functions to upload")


# =============================================================================
# Helper Functions
# =============================================================================


def call_to_response(call: FunctionCall) -> FunctionCallInfo:
    """Convert a FunctionCall model to response schema."""
    return FunctionCallInfo(
        id=str(call.id),
        function_name=call.function_name,
        status=call.status,
        trigger_type=call.trigger_type,
        trigger_id=str(call.trigger_id) if call.trigger_id else None,
        requested_by_user_id=str(call.requested_by_user_id) if call.requested_by_user_id else None,
        started_at=call.started_at.isoformat() if call.started_at else None,
        finished_at=call.finished_at.isoformat() if call.finished_at else None,
        duration_ms=call.duration_ms,
        error_message=call.error_message,
        error_type=call.error_type,
        created_at=call.created_at.isoformat(),
    )


def user_to_response(user: User) -> UserInfo:
    """Convert a User model to response schema."""
    return UserInfo(
        id=str(user.id),
        email=user.email,
        is_admin=user.is_admin,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )


# =============================================================================
# Function Call Routes
# =============================================================================


@router.get(
    "/functions/calls",
    response_model=FunctionCallListResponse,
    summary="List function calls",
    description="Get a paginated list of function call records.",
)
def list_function_calls(
    session: DbSession,
    _admin: CurrentAdminUser,
    function_name: str | None = Query(default=None, description="Filter by function name"),
    status_filter: FunctionCallStatus | None = Query(
        default=None, alias="status", description="Filter by status"
    ),
    trigger_type_filter: TriggerType | None = Query(
        default=None, alias="trigger_type", description="Filter by trigger type"
    ),
    limit: int = Query(default=100, ge=1, le=1000, description="Page size"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
) -> FunctionCallListResponse:
    """List function calls with filtering and pagination."""
    # Build count query with filters
    count_stmt = select(func.count(FunctionCall.id))

    if function_name:
        count_stmt = count_stmt.where(FunctionCall.function_name == function_name)
    if status_filter:
        count_stmt = count_stmt.where(FunctionCall.status == status_filter)
    if trigger_type_filter:
        count_stmt = count_stmt.where(FunctionCall.trigger_type == trigger_type_filter)

    total = session.exec(count_stmt).one()

    # Build data query with filters
    query = select(FunctionCall)

    if function_name:
        query = query.where(FunctionCall.function_name == function_name)
    if status_filter:
        query = query.where(FunctionCall.status == status_filter)
    if trigger_type_filter:
        query = query.where(FunctionCall.trigger_type == trigger_type_filter)

    # Apply pagination and ordering
    query = query.order_by(FunctionCall.created_at.desc())  # type: ignore
    query = query.offset(offset).limit(limit)

    calls = list(session.exec(query).all())

    return FunctionCallListResponse(
        calls=[call_to_response(c) for c in calls],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/functions/calls/{call_id}",
    response_model=FunctionCallInfo,
    summary="Get function call details",
    description="Get details of a specific function call.",
)
def get_function_call(
    call_id: UUID,
    session: DbSession,
    _admin: CurrentAdminUser,
) -> FunctionCallInfo:
    """Get a specific function call by ID."""
    call = session.get(FunctionCall, call_id)

    if call is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Function call '{call_id}' not found",
        )

    return call_to_response(call)


@router.get(
    "/functions/metrics",
    summary="Get function execution metrics",
    description="Get aggregated function execution metrics over a time period.",
)
def get_function_metrics(
    session: DbSession,
    _admin: CurrentAdminUser,
    hours: int = Query(default=24, ge=1, le=720, description="Time period in hours"),
) -> dict:
    """Get aggregated function execution metrics."""
    cutoff = utcnow() - timedelta(hours=hours)

    calls = session.exec(select(FunctionCall).where(FunctionCall.started_at >= cutoff)).all()

    # Aggregate by function name
    metrics = {}
    for call in calls:
        if call.function_name not in metrics:
            metrics[call.function_name] = {
                "total_calls": 0,
                "succeeded": 0,
                "failed": 0,
                "avg_duration_ms": 0,
                "durations": [],
            }

        m = metrics[call.function_name]
        m["total_calls"] += 1
        if call.status == FunctionCallStatus.SUCCEEDED:
            m["succeeded"] += 1
        else:
            m["failed"] += 1

        if call.duration_ms:
            m["durations"].append(call.duration_ms)

    # Calculate averages
    for name, m in metrics.items():
        if m["durations"]:
            m["avg_duration_ms"] = sum(m["durations"]) / len(m["durations"])
            del m["durations"]

    return {
        "period_hours": hours,
        "functions": metrics,
    }


# =============================================================================
# User Management Routes
# =============================================================================


@router.get(
    "/users",
    response_model=UserListResponse,
    summary="List users",
    description="Get a paginated list of users.",
)
def list_users(
    session: DbSession,
    _admin: CurrentAdminUser,
    limit: int = Query(default=100, ge=1, le=1000, description="Page size"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
) -> UserListResponse:
    """List all users with pagination."""
    # Get total count efficiently
    total = session.exec(select(func.count(User.id))).one()

    # Get paginated results
    query = select(User).offset(offset).limit(limit)
    users = list(session.exec(query).all())

    return UserListResponse(
        users=[user_to_response(u) for u in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/users",
    response_model=UserInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Create a new user (admin can create admin users).",
)
def create_user(
    request: UserCreate,
    session: DbSession,
    _admin: CurrentAdminUser,
) -> UserInfo:
    """Create a new user."""
    # Check if email exists
    existing = session.exec(select(User).where(User.email == request.email)).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        is_admin=request.is_admin,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    return user_to_response(user)


@router.get(
    "/users/{user_id}",
    response_model=UserInfo,
    summary="Get user details",
    description="Get details of a specific user.",
)
def get_user(
    user_id: UUID,
    session: DbSession,
    _admin: CurrentAdminUser,
) -> UserInfo:
    """Get a specific user by ID."""
    user = session.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )

    return user_to_response(user)


@router.patch(
    "/users/{user_id}",
    response_model=UserInfo,
    summary="Update user",
    description="Update a user's details.",
)
def update_user(
    user_id: UUID,
    request: UserUpdate,
    session: DbSession,
    _admin: CurrentAdminUser,
) -> UserInfo:
    """Update a user's details."""
    user = session.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )

    if request.email is not None:
        # Check if new email is already taken
        existing = session.exec(
            select(User).where(User.email == request.email, User.id != user_id)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        user.email = request.email

    if request.password is not None:
        user.password_hash = hash_password(request.password)

    if request.is_admin is not None:
        # Prevent demoting the last admin
        if user.is_admin and not request.is_admin:
            admin_count = session.exec(select(func.count(User.id)).where(User.is_admin)).one()
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot demote the last admin user",
                )
        user.is_admin = request.is_admin

    session.add(user)
    session.commit()
    session.refresh(user)

    return user_to_response(user)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Delete a user.",
)
def delete_user(
    user_id: UUID,
    session: DbSession,
    admin: CurrentAdminUser,
) -> None:
    """Delete a user."""
    # Prevent self-deletion
    if admin.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    user = session.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )

    # Prevent deleting the last admin
    if user.is_admin:
        admin_count = session.exec(select(func.count(User.id)).where(User.is_admin)).one()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last admin user",
            )

    session.delete(user)
    session.commit()


# =============================================================================
# Instance Settings Routes
# =============================================================================


class InstanceSettingsResponse(BaseModel):
    """Instance settings response."""

    instance_name: str = Field(description="Instance name")
    allow_public_registration: bool = Field(description="Allow public registration")
    server_timezone: str = Field(description="Server timezone")
    token_cleanup_interval: int = Field(description="Token cleanup interval in scheduler ticks")
    metrics_collection_interval: int = Field(
        description="Metrics collection interval in scheduler ticks"
    )
    scheduler_function_timeout_seconds: int | None = Field(
        default=None, description="Function execution timeout in seconds"
    )
    scheduler_max_schedules_per_tick: int | None = Field(
        default=None, description="Max schedules per tick"
    )
    scheduler_max_concurrent_executions: int | None = Field(
        default=None, description="Max concurrent executions"
    )
    max_concurrent_functions_per_user: int | None = Field(
        default=None, description="Max concurrent function executions per user"
    )
    storage_enabled: bool = Field(description="File storage enabled")
    storage_endpoint: str | None = Field(default=None, description="S3 endpoint")
    storage_bucket: str | None = Field(default=None, description="S3 bucket name")
    storage_region: str | None = Field(default=None, description="S3 region")
    # Note: access_key and secret_key are not returned for security
    auth_portal_enabled: bool = Field(description="Auth portal enabled")
    auth_portal_logo_url: str | None = Field(default=None, description="Auth portal logo URL")
    auth_portal_primary_color: str | None = Field(
        default=None, description="Auth portal primary color"
    )
    auth_portal_background_image_url: str | None = Field(
        default=None, description="Auth portal background image URL"
    )
    auth_portal_login_redirect_url: str | None = Field(
        default=None, description="Auth portal login redirect URL"
    )
    auth_portal_register_redirect_url: str | None = Field(
        default=None, description="Auth portal register redirect URL"
    )
    updated_at: str = Field(description="Last update time")


class InstanceSettingsUpdate(BaseModel):
    """Instance settings update request."""

    instance_name: str | None = Field(default=None, max_length=100)
    allow_public_registration: bool | None = Field(default=None)
    server_timezone: str | None = Field(default=None, max_length=50)
    token_cleanup_interval: int | None = Field(
        default=None, ge=1, description="Token cleanup interval in scheduler ticks"
    )
    metrics_collection_interval: int | None = Field(
        default=None, ge=1, description="Metrics collection interval in scheduler ticks"
    )
    scheduler_function_timeout_seconds: int | None = Field(
        default=None, ge=1, description="Function execution timeout in seconds"
    )
    scheduler_max_schedules_per_tick: int | None = Field(
        default=None, ge=1, description="Max schedules per tick"
    )
    scheduler_max_concurrent_executions: int | None = Field(
        default=None, ge=1, description="Max concurrent executions"
    )
    max_concurrent_functions_per_user: int | None = Field(
        default=None, ge=1, description="Max concurrent function executions per user"
    )
    storage_enabled: bool | None = Field(default=None)
    storage_endpoint: str | None = Field(default=None, max_length=500)
    storage_bucket: str | None = Field(default=None, max_length=100)
    storage_access_key: str | None = Field(default=None, max_length=200)
    storage_secret_key: str | None = Field(default=None, max_length=200)
    storage_region: str | None = Field(default=None, max_length=50)
    auth_portal_enabled: bool | None = Field(default=None)
    auth_portal_logo_url: str | None = Field(default=None, max_length=500)
    auth_portal_primary_color: str | None = Field(default=None, max_length=50)
    auth_portal_background_image_url: str | None = Field(default=None, max_length=500)
    auth_portal_login_redirect_url: str | None = Field(default=None, max_length=500)
    auth_portal_register_redirect_url: str | None = Field(default=None, max_length=500)


def settings_to_response(settings: InstanceSettings) -> InstanceSettingsResponse:
    """Convert InstanceSettings model to response schema."""
    return InstanceSettingsResponse(
        instance_name=settings.instance_name,
        allow_public_registration=settings.allow_public_registration,
        server_timezone=settings.server_timezone,
        token_cleanup_interval=settings.token_cleanup_interval,
        metrics_collection_interval=settings.metrics_collection_interval,
        scheduler_function_timeout_seconds=settings.scheduler_function_timeout_seconds,
        scheduler_max_schedules_per_tick=settings.scheduler_max_schedules_per_tick,
        scheduler_max_concurrent_executions=settings.scheduler_max_concurrent_executions,
        max_concurrent_functions_per_user=settings.max_concurrent_functions_per_user,
        storage_enabled=settings.storage_enabled,
        storage_endpoint=settings.storage_endpoint,
        storage_bucket=settings.storage_bucket,
        storage_region=settings.storage_region,
        auth_portal_enabled=settings.auth_portal_enabled,
        auth_portal_logo_url=settings.auth_portal_logo_url,
        auth_portal_primary_color=settings.auth_portal_primary_color,
        auth_portal_background_image_url=settings.auth_portal_background_image_url,
        auth_portal_login_redirect_url=settings.auth_portal_login_redirect_url,
        auth_portal_register_redirect_url=settings.auth_portal_register_redirect_url,
        updated_at=settings.updated_at.isoformat(),
    )


def get_or_create_settings(session: DbSession) -> InstanceSettings:
    """Get the singleton settings instance, creating it if it doesn't exist."""
    from tinybase.config import settings as app_settings

    settings = session.get(InstanceSettings, 1)
    if settings is None:
        # Initialize with defaults from config if available
        config = app_settings()
        settings = InstanceSettings(
            id=1,
            token_cleanup_interval=getattr(config, "scheduler_token_cleanup_interval", 60),
            metrics_collection_interval=getattr(
                config, "scheduler_metrics_collection_interval", 360
            ),
            scheduler_function_timeout_seconds=getattr(
                config, "scheduler_function_timeout_seconds", None
            ),
            scheduler_max_schedules_per_tick=getattr(
                config, "scheduler_max_schedules_per_tick", None
            ),
            scheduler_max_concurrent_executions=getattr(
                config, "scheduler_max_concurrent_executions", None
            ),
        )
        session.add(settings)
        session.commit()
        session.refresh(settings)
    return settings


@router.get(
    "/settings",
    response_model=InstanceSettingsResponse,
    summary="Get instance settings",
    description="Get the current instance configuration.",
)
def get_settings(
    session: DbSession,
    _admin: CurrentAdminUser,
) -> InstanceSettingsResponse:
    """Get current instance settings."""
    settings = get_or_create_settings(session)
    return settings_to_response(settings)


@router.patch(
    "/settings",
    response_model=InstanceSettingsResponse,
    summary="Update instance settings",
    description="Update the instance configuration.",
)
def update_settings(
    request: InstanceSettingsUpdate,
    session: DbSession,
    _admin: CurrentAdminUser,
) -> InstanceSettingsResponse:
    """Update instance settings."""
    settings = get_or_create_settings(session)

    # Update only provided fields
    if request.instance_name is not None:
        settings.instance_name = request.instance_name
    if request.allow_public_registration is not None:
        settings.allow_public_registration = request.allow_public_registration
    if request.server_timezone is not None:
        # Validate timezone
        import zoneinfo

        try:
            zoneinfo.ZoneInfo(request.server_timezone)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid timezone: {request.server_timezone}",
            )
        settings.server_timezone = request.server_timezone
    if request.token_cleanup_interval is not None:
        if request.token_cleanup_interval < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="token_cleanup_interval must be at least 1",
            )
        settings.token_cleanup_interval = request.token_cleanup_interval
    if request.metrics_collection_interval is not None:
        if request.metrics_collection_interval < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="metrics_collection_interval must be at least 1",
            )
        settings.metrics_collection_interval = request.metrics_collection_interval
    if request.scheduler_function_timeout_seconds is not None:
        if request.scheduler_function_timeout_seconds < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scheduler_function_timeout_seconds must be at least 1",
            )
        settings.scheduler_function_timeout_seconds = request.scheduler_function_timeout_seconds
    if request.scheduler_max_schedules_per_tick is not None:
        if request.scheduler_max_schedules_per_tick < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scheduler_max_schedules_per_tick must be at least 1",
            )
        settings.scheduler_max_schedules_per_tick = request.scheduler_max_schedules_per_tick
    if request.scheduler_max_concurrent_executions is not None:
        if request.scheduler_max_concurrent_executions < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scheduler_max_concurrent_executions must be at least 1",
            )
        settings.scheduler_max_concurrent_executions = request.scheduler_max_concurrent_executions
    if request.max_concurrent_functions_per_user is not None:
        if request.max_concurrent_functions_per_user < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="max_concurrent_functions_per_user must be at least 1",
            )
        settings.max_concurrent_functions_per_user = request.max_concurrent_functions_per_user
    if request.storage_enabled is not None:
        settings.storage_enabled = request.storage_enabled
    if request.storage_endpoint is not None:
        settings.storage_endpoint = request.storage_endpoint
    if request.storage_bucket is not None:
        settings.storage_bucket = request.storage_bucket
    if request.storage_access_key is not None:
        settings.storage_access_key = request.storage_access_key
    if request.storage_secret_key is not None:
        settings.storage_secret_key = request.storage_secret_key
    if request.storage_region is not None:
        settings.storage_region = request.storage_region
    # Determine if auth portal will be enabled after this update
    # (either already enabled and not being disabled, or being enabled in this request)
    auth_portal_will_be_enabled = (
        request.auth_portal_enabled
        if request.auth_portal_enabled is not None
        else settings.auth_portal_enabled
    )

    if request.auth_portal_enabled is not None:
        settings.auth_portal_enabled = request.auth_portal_enabled
    if request.auth_portal_logo_url is not None:
        settings.auth_portal_logo_url = request.auth_portal_logo_url
    if request.auth_portal_primary_color is not None:
        settings.auth_portal_primary_color = request.auth_portal_primary_color
    if request.auth_portal_background_image_url is not None:
        settings.auth_portal_background_image_url = request.auth_portal_background_image_url
    if request.auth_portal_login_redirect_url is not None:
        # Only validate redirect URL format if auth portal is (or will be) enabled
        if auth_portal_will_be_enabled:
            # Validate that it's an absolute URL and not pointing to /admin
            if not request.auth_portal_login_redirect_url.startswith(("http://", "https://")):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Login redirect URL must be an absolute URL (e.g., https://app.example.com/dashboard)",
                )
            # Prevent redirecting to /admin URLs (those are for TinyBase Admin UI)
            if "/admin" in request.auth_portal_login_redirect_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Login redirect URL must not point to /admin URLs. Use your application's URL instead.",
                )
        settings.auth_portal_login_redirect_url = request.auth_portal_login_redirect_url
    if request.auth_portal_register_redirect_url is not None:
        # Only validate redirect URL format if auth portal is (or will be) enabled
        if auth_portal_will_be_enabled:
            # Validate that it's an absolute URL and not pointing to /admin
            if not request.auth_portal_register_redirect_url.startswith(("http://", "https://")):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Register redirect URL must be an absolute URL (e.g., https://app.example.com/welcome)",
                )
            # Prevent redirecting to /admin URLs (those are for TinyBase Admin UI)
            if "/admin" in request.auth_portal_register_redirect_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Register redirect URL must not point to /admin URLs. Use your application's URL instead.",
                )
        settings.auth_portal_register_redirect_url = request.auth_portal_register_redirect_url

    # If auth portal is enabled, require redirect URLs to be set
    if settings.auth_portal_enabled:
        if not settings.auth_portal_login_redirect_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Login redirect URL is required when auth portal is enabled",
            )
        if not settings.auth_portal_register_redirect_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Register redirect URL is required when auth portal is enabled",
            )

    settings.updated_at = utcnow()
    session.add(settings)
    session.commit()
    session.refresh(settings)

    return settings_to_response(settings)


# =============================================================================
# Metrics Routes
# =============================================================================


class CollectionSizesResponse(BaseModel):
    """Collection sizes metrics response."""

    collection_name: str = Field(description="Collection name")
    record_count: int = Field(description="Number of records")


class FunctionStatsResponse(BaseModel):
    """Function statistics metrics response."""

    function_name: str = Field(description="Function name")
    avg_runtime_ms: float | None = Field(description="Average runtime in milliseconds")
    error_rate: float = Field(description="Error rate as percentage")
    total_calls: int = Field(description="Total number of calls")


class MetricsResponse(BaseModel):
    """Metrics response."""

    collection_sizes: list[CollectionSizesResponse] = Field(description="Collection sizes")
    function_stats: list[FunctionStatsResponse] = Field(description="Function statistics")
    collected_at: str = Field(description="When metrics were collected")


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Get latest metrics",
    description="Get the most recent collected metrics (collection sizes and function statistics).",
)
def get_metrics(
    session: DbSession,
    _admin: CurrentAdminUser,
) -> MetricsResponse:
    """Get the latest collected metrics."""
    # Get most recent collection_sizes metric
    collection_sizes_stmt = (
        select(Metrics)
        .where(Metrics.metric_type == "collection_sizes")
        .order_by(Metrics.collected_at.desc())
        .limit(1)
    )
    collection_sizes_metric = session.exec(collection_sizes_stmt).first()

    # Get most recent function_stats metric
    function_stats_stmt = (
        select(Metrics)
        .where(Metrics.metric_type == "function_stats")
        .order_by(Metrics.collected_at.desc())
        .limit(1)
    )
    function_stats_metric = session.exec(function_stats_stmt).first()

    # Build response
    collection_sizes = []
    if collection_sizes_metric and collection_sizes_metric.data:
        collection_sizes = [
            CollectionSizesResponse(collection_name=name, record_count=count)
            for name, count in collection_sizes_metric.data.items()
        ]

    function_stats = []
    collected_at = None
    if function_stats_metric and function_stats_metric.data:
        function_stats = [
            FunctionStatsResponse(
                function_name=name,
                avg_runtime_ms=stats.get("avg_runtime_ms"),
                error_rate=stats.get("error_rate", 0.0),
                total_calls=stats.get("total_calls", 0),
            )
            for name, stats in function_stats_metric.data.items()
        ]
        collected_at = function_stats_metric.collected_at.isoformat()
    elif collection_sizes_metric:
        collected_at = collection_sizes_metric.collected_at.isoformat()

    return MetricsResponse(
        collection_sizes=collection_sizes,
        function_stats=function_stats,
        collected_at=collected_at or utcnow().isoformat(),
    )


# =============================================================================
# Application Token Routes
# =============================================================================


class ApplicationTokenInfo(BaseModel):
    """Application token information."""

    id: str = Field(description="Token ID")
    name: str = Field(description="Token name")
    description: str | None = Field(default=None, description="Token description")
    created_at: str = Field(description="Created timestamp")
    last_used_at: str | None = Field(default=None, description="Last used timestamp")
    expires_at: str | None = Field(default=None, description="Expiration timestamp")
    is_active: bool = Field(description="Whether token is active")
    is_valid: bool = Field(description="Whether token is valid (active and not expired)")


class ApplicationTokenListResponse(BaseModel):
    """Application token list response."""

    tokens: list[ApplicationTokenInfo] = Field(description="Application tokens")


class ApplicationTokenCreate(BaseModel):
    """Create application token request."""

    name: str = Field(max_length=200, description="Token name")
    description: str | None = Field(default=None, max_length=500, description="Token description")
    expires_days: int | None = Field(
        default=None, ge=1, description="Expiration in days (None = never expires)"
    )


class ApplicationTokenCreateResponse(BaseModel):
    """Application token creation response."""

    token: ApplicationTokenInfo = Field(description="Token information")
    token_value: str = Field(description="The actual token value (only shown once)")


class ApplicationTokenUpdate(BaseModel):
    """Update application token request."""

    name: str | None = Field(default=None, max_length=200, description="Token name")
    description: str | None = Field(default=None, max_length=500, description="Token description")
    is_active: bool | None = Field(default=None, description="Active status")


def token_to_response(token: ApplicationToken) -> ApplicationTokenInfo:
    """Convert an ApplicationToken model to response schema."""
    return ApplicationTokenInfo(
        id=str(token.id),
        name=token.name,
        description=token.description,
        created_at=token.created_at.isoformat(),
        last_used_at=token.last_used_at.isoformat() if token.last_used_at else None,
        expires_at=token.expires_at.isoformat() if token.expires_at else None,
        is_active=token.is_active,
        is_valid=token.is_valid(),
    )


@router.get(
    "/application-tokens",
    response_model=ApplicationTokenListResponse,
    summary="List application tokens",
    description="Get a list of all application tokens.",
)
def list_application_tokens(
    session: DbSession,
    _admin: CurrentAdminUser,
) -> ApplicationTokenListResponse:
    """List all application tokens."""
    tokens = list(
        session.exec(select(ApplicationToken).order_by(ApplicationToken.created_at.desc())).all()
    )
    return ApplicationTokenListResponse(tokens=[token_to_response(t) for t in tokens])


@router.post(
    "/application-tokens",
    response_model=ApplicationTokenCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create application token",
    description="Create a new application token for client applications.",
)
def create_application_token_endpoint(
    request: ApplicationTokenCreate,
    session: DbSession,
    _admin: CurrentAdminUser,
) -> ApplicationTokenCreateResponse:
    """Create a new application token."""
    expires_at = None
    if request.expires_days:
        expires_at = utcnow() + timedelta(days=request.expires_days)

    token = create_application_token(
        session=session,
        name=request.name,
        description=request.description,
        expires_at=expires_at,
    )

    return ApplicationTokenCreateResponse(
        token=token_to_response(token),
        token_value=token.token,
    )


@router.patch(
    "/application-tokens/{token_id}",
    response_model=ApplicationTokenInfo,
    summary="Update application token",
    description="Update an application token's details.",
)
def update_application_token(
    token_id: UUID,
    request: ApplicationTokenUpdate,
    session: DbSession,
    _admin: CurrentAdminUser,
) -> ApplicationTokenInfo:
    """Update an application token."""
    token = session.get(ApplicationToken, token_id)

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application token '{token_id}' not found",
        )

    if request.name is not None:
        token.name = request.name
    if request.description is not None:
        token.description = request.description
    if request.is_active is not None:
        token.is_active = request.is_active

    session.add(token)
    session.commit()
    session.refresh(token)

    return token_to_response(token)


@router.delete(
    "/application-tokens/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke application token",
    description="Revoke (deactivate) an application token.",
)
def revoke_application_token_endpoint(
    token_id: UUID,
    session: DbSession,
    _admin: CurrentAdminUser,
) -> None:
    """Revoke an application token."""
    if not revoke_application_token(session, token_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application token '{token_id}' not found",
        )


# =============================================================================
# Function Deployment Routes
# =============================================================================


@router.post(
    "/functions/upload",
    response_model=FunctionUploadResponse,
    summary="Upload function file",
    description="Upload a function file and trigger hot-reload. Admin only.",
)
def upload_function(
    request: FunctionUploadRequest,
    admin: CurrentAdminUser,
    session: DbSession,
) -> FunctionUploadResponse:
    """
    Upload a function file and trigger hot-reload.

    Process:
    1. Validate filename and content
    2. Calculate content hash
    3. Check if version already exists
    4. Write file to functions directory
    5. Create version record
    6. Trigger hot-reload

    Returns:
        Upload response with version information and warnings
    """
    from pathlib import Path

    from tinybase.config import settings
    from tinybase.functions.deployment import (
        FunctionValidationError,
        calculate_content_hash,
        get_or_create_version,
        validate_function_file,
        write_function_file,
    )
    from tinybase.functions.loader import extract_function_metadata, reload_single_function

    config = settings()

    # Step 1: Validate function file
    try:
        function_name, warnings = validate_function_file(
            request.filename, request.content, config.max_function_payload_bytes
        )
    except FunctionValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Step 2: Calculate content hash
    content_hash = calculate_content_hash(request.content)
    file_size = len(request.content.encode("utf-8"))

    # Step 3: Check if version already exists (idempotent)
    version, is_new = get_or_create_version(
        session, function_name, content_hash, file_size, admin.id, request.notes
    )

    if not is_new:
        # Version already exists, just return it
        return FunctionUploadResponse(
            function_name=function_name,
            version_id=str(version.id),
            content_hash=content_hash,
            is_new_version=False,
            message=f"Function '{function_name}' already at this version (hash: {content_hash[:8]}...)",
            warnings=warnings,
        )

    # Step 4: Write file to functions directory
    functions_dir = Path(config.functions_path)
    try:
        file_path = write_function_file(functions_dir, request.filename, request.content)
    except Exception as e:
        # Rollback version creation
        session.delete(version)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write function file: {e}",
        )

    # Step 5: Validate metadata can be extracted
    try:
        metadata = extract_function_metadata(file_path)
        if not metadata:
            raise Exception("Metadata extraction returned None")
    except Exception as e:
        # Rollback: delete file and version
        try:
            file_path.unlink()
        except Exception:
            pass
        session.delete(version)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract function metadata: {e}. Function may have runtime errors.",
        )

    # Step 6: Trigger hot-reload
    try:
        success = reload_single_function(file_path)
        if not success:
            raise Exception("reload_single_function returned False")
    except Exception as e:
        # Warn but don't fail - file is written and version is created
        warnings.append(f"Hot-reload failed: {e}. Server restart may be required.")

    return FunctionUploadResponse(
        function_name=function_name,
        version_id=str(version.id),
        content_hash=content_hash,
        is_new_version=True,
        message=f"Successfully uploaded function '{function_name}' (version {content_hash[:8]}...)",
        warnings=warnings,
    )


@router.post(
    "/functions/upload-batch",
    response_model=list[FunctionUploadResponse],
    summary="Upload multiple functions",
    description="Upload multiple function files at once. Admin only.",
)
def upload_functions_batch(
    request: BatchUploadRequest,
    admin: CurrentAdminUser,
    session: DbSession,
) -> list[FunctionUploadResponse]:
    """
    Upload multiple functions at once.

    Each function is processed independently. If one fails, others continue.
    Returns a list of responses with success/failure for each function.
    """
    responses = []

    for func_request in request.functions:
        try:
            # Call upload_function for each
            response = upload_function(func_request, admin, session)
            responses.append(response)
        except HTTPException as e:
            # Extract function name from filename (strip .py)
            func_name = (
                func_request.filename[:-3]
                if func_request.filename.endswith(".py")
                else func_request.filename
            )
            # Convert exception to response with error
            responses.append(
                FunctionUploadResponse(
                    function_name=func_name,
                    version_id="",
                    content_hash="",
                    is_new_version=False,
                    message=f"Upload failed: {e.detail}",
                    warnings=[],
                )
            )

    return responses


@router.get(
    "/functions/{function_name}/versions",
    response_model=list[FunctionVersionInfo],
    summary="List function versions",
    description="Get deployment history for a function. Admin only.",
)
def list_function_versions(
    function_name: str,
    _admin: CurrentAdminUser,
    session: DbSession,
    limit: int = Query(50, ge=1, le=100, description="Number of versions to return"),
) -> list[FunctionVersionInfo]:
    """
    List deployment history for a function.

    Returns versions ordered by deployment time (newest first),
    along with execution count for each version.
    """
    # Get versions
    stmt = (
        select(FunctionVersion)
        .where(FunctionVersion.function_name == function_name)
        .order_by(FunctionVersion.deployed_at.desc())
        .limit(limit)
    )
    versions = session.exec(stmt).all()

    if not versions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No versions found for '{function_name}'"
        )

    result = []
    for version in versions:
        # Get execution count for this version
        exec_count_stmt = select(func.count(FunctionCall.id)).where(
            FunctionCall.version_id == version.id
        )
        exec_count = session.exec(exec_count_stmt).one()

        # Get deployer email
        deployer_email = None
        if version.deployed_by_user_id:
            user_stmt = select(User.email).where(User.id == version.deployed_by_user_id)
            deployer_email = session.exec(user_stmt).first()

        result.append(
            FunctionVersionInfo(
                id=str(version.id),
                function_name=version.function_name,
                content_hash=version.content_hash,
                file_size=version.file_size,
                deployed_by_email=deployer_email,
                deployed_at=version.deployed_at.isoformat(),
                notes=version.notes,
                execution_count=exec_count,
            )
        )

    return result
