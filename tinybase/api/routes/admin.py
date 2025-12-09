"""
Admin API routes.

Provides admin-only endpoints for:
- Function call history
- User management
- Instance settings
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlmodel import select

from tinybase.auth import CurrentAdminUser, DbSession, hash_password
from tinybase.db.models import FunctionCall, InstanceSettings, User
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
    scheduler_function_timeout_seconds: int | None = Field(
        default=None, description="Function execution timeout in seconds"
    )
    scheduler_max_schedules_per_tick: int | None = Field(
        default=None, description="Max schedules per tick"
    )
    scheduler_max_concurrent_executions: int | None = Field(
        default=None, description="Max concurrent executions"
    )
    storage_enabled: bool = Field(description="File storage enabled")
    storage_endpoint: str | None = Field(default=None, description="S3 endpoint")
    storage_bucket: str | None = Field(default=None, description="S3 bucket name")
    storage_region: str | None = Field(default=None, description="S3 region")
    # Note: access_key and secret_key are not returned for security
    updated_at: str = Field(description="Last update time")


class InstanceSettingsUpdate(BaseModel):
    """Instance settings update request."""

    instance_name: str | None = Field(default=None, max_length=100)
    allow_public_registration: bool | None = Field(default=None)
    server_timezone: str | None = Field(default=None, max_length=50)
    token_cleanup_interval: int | None = Field(
        default=None, ge=1, description="Token cleanup interval in scheduler ticks"
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
    storage_enabled: bool | None = Field(default=None)
    storage_endpoint: str | None = Field(default=None, max_length=500)
    storage_bucket: str | None = Field(default=None, max_length=100)
    storage_access_key: str | None = Field(default=None, max_length=200)
    storage_secret_key: str | None = Field(default=None, max_length=200)
    storage_region: str | None = Field(default=None, max_length=50)


def settings_to_response(settings: InstanceSettings) -> InstanceSettingsResponse:
    """Convert InstanceSettings model to response schema."""
    return InstanceSettingsResponse(
        instance_name=settings.instance_name,
        allow_public_registration=settings.allow_public_registration,
        server_timezone=settings.server_timezone,
        token_cleanup_interval=settings.token_cleanup_interval,
        scheduler_function_timeout_seconds=settings.scheduler_function_timeout_seconds,
        scheduler_max_schedules_per_tick=settings.scheduler_max_schedules_per_tick,
        scheduler_max_concurrent_executions=settings.scheduler_max_concurrent_executions,
        storage_enabled=settings.storage_enabled,
        storage_endpoint=settings.storage_endpoint,
        storage_bucket=settings.storage_bucket,
        storage_region=settings.storage_region,
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

    settings.updated_at = utcnow()
    session.add(settings)
    session.commit()
    session.refresh(settings)

    return settings_to_response(settings)
