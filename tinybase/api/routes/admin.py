"""
Admin API routes.

Provides admin-only endpoints for:
- Function call history
- User management
"""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlmodel import select

from tinybase.auth import CurrentAdminUser, DbSession, hash_password
from tinybase.db.models import FunctionCall, User

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
    status_filter: Literal["running", "succeeded", "failed"] | None = Query(
        default=None,
        alias="status",
        description="Filter by status"
    ),
    trigger_type: Literal["manual", "schedule"] | None = Query(
        default=None,
        description="Filter by trigger type"
    ),
    limit: int = Query(default=100, ge=1, le=1000, description="Page size"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
) -> FunctionCallListResponse:
    """List function calls with filtering and pagination."""
    # Build query
    query = select(FunctionCall)
    
    if function_name:
        query = query.where(FunctionCall.function_name == function_name)
    if status_filter:
        query = query.where(FunctionCall.status == status_filter)
    if trigger_type:
        query = query.where(FunctionCall.trigger_type == trigger_type)
    
    # Get total count (before pagination)
    count_query = query
    all_results = list(session.exec(count_query).all())
    total = len(all_results)
    
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
    # Get total count
    all_users = list(session.exec(select(User)).all())
    total = len(all_users)
    
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
    existing = session.exec(
        select(User).where(User.email == request.email)
    ).first()
    
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
    
    session.delete(user)
    session.commit()

