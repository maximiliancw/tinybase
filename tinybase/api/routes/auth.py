"""
Authentication API routes.

Provides endpoints for:
- User registration
- User login (token issuance)
- Current user info retrieval
"""

import asyncio
import os

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlmodel import select

from tinybase.auth import (
    CurrentUser,
    DbSession,
    create_auth_token,
    hash_password,
    verify_password,
)
from tinybase.db.models import InstanceSettings, User
from tinybase.extensions.hooks import (
    UserLoginEvent,
    UserRegisterEvent,
    run_user_login_hooks,
    run_user_register_hooks,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Rate limiter for auth routes
# Uses environment variable TINYBASE_RATE_LIMIT_ENABLED to disable in tests
_rate_limit_enabled = os.environ.get("TINYBASE_RATE_LIMIT_ENABLED", "true").lower() != "false"
limiter = Limiter(key_func=get_remote_address, enabled=_rate_limit_enabled)


# =============================================================================
# Request/Response Schemas
# =============================================================================


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr = Field(description="User email address")
    password: str = Field(min_length=8, description="Password (min 8 characters)")


class RegisterResponse(BaseModel):
    """User registration response."""

    id: str = Field(description="User ID")
    email: str = Field(description="User email address")
    message: str = Field(default="User registered successfully")


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr = Field(description="User email address")
    password: str = Field(description="User password")


class LoginResponse(BaseModel):
    """User login response with token."""

    token: str = Field(description="Bearer token for API authentication")
    token_type: str = Field(default="bearer")
    user_id: str = Field(description="Authenticated user ID")
    email: str = Field(description="Authenticated user email")
    is_admin: bool = Field(description="Whether user has admin privileges")
    admin_created: bool = Field(default=False, description="Whether an admin user was auto-created")


class UserInfo(BaseModel):
    """Current user information."""

    id: str = Field(description="User ID")
    email: str = Field(description="User email address")
    is_admin: bool = Field(description="Whether user has admin privileges")
    created_at: str = Field(description="User creation timestamp")


class SetupStatusResponse(BaseModel):
    """Setup status response."""

    needs_setup: bool = Field(description="Whether initial setup is needed (no users exist)")


class InstanceInfoResponse(BaseModel):
    """Public instance information."""

    instance_name: str = Field(description="The name of this TinyBase instance")


# =============================================================================
# Routes
# =============================================================================


@router.get(
    "/instance-info",
    response_model=InstanceInfoResponse,
    summary="Get public instance info",
    description="Get public information about this TinyBase instance (no auth required).",
)
def get_instance_info(session: DbSession) -> InstanceInfoResponse:
    """
    Get public instance information.

    Returns the instance name configured in settings.
    This endpoint does not require authentication.
    """
    settings = session.get(InstanceSettings, 1)
    instance_name = settings.instance_name if settings else "TinyBase"
    return InstanceInfoResponse(instance_name=instance_name)


@router.get(
    "/setup-status",
    response_model=SetupStatusResponse,
    summary="Check setup status",
    description="Check if initial setup is needed (no users exist yet).",
)
def get_setup_status(session: DbSession) -> SetupStatusResponse:
    """
    Check if the system needs initial setup.

    Returns needs_setup=True if no users exist in the database,
    indicating that the first login will create an admin user.
    """
    from sqlalchemy import func

    user_count = session.exec(select(func.count(User.id))).one()
    return SetupStatusResponse(needs_setup=user_count == 0)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email and password.",
)
@limiter.limit("5/minute")
def register(
    request: Request,
    body: RegisterRequest,
    session: DbSession,
    background_tasks: BackgroundTasks,
) -> RegisterResponse:
    """
    Register a new user account.

    Creates a new user with the provided email and password. The password
    is hashed before storage using bcrypt.

    Registration may be disabled via instance settings.
    """
    # Check if public registration is allowed
    instance_settings = session.get(InstanceSettings, 1)
    if instance_settings and not instance_settings.allow_public_registration:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration is disabled",
        )

    # Check if email already exists
    existing = session.exec(select(User).where(User.email == body.email)).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    # Run user register hooks in background
    event = UserRegisterEvent(user_id=user.id, email=user.email)
    background_tasks.add_task(asyncio.run, run_user_register_hooks(event))

    return RegisterResponse(
        id=str(user.id),
        email=user.email,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login and get access token",
    description="Authenticate with email and password to receive a bearer token.",
)
@limiter.limit("10/minute")
def login(
    request: Request,
    body: LoginRequest,
    session: DbSession,
    background_tasks: BackgroundTasks,
) -> LoginResponse:
    """
    Authenticate user and issue access token.

    Verifies the provided email and password, then creates and returns
    a new bearer token for API authentication.

    If no users exist in the system, automatically creates an admin user
    with the provided credentials.
    """
    from sqlalchemy import func

    admin_created = False

    # Check if any users exist
    user_count = session.exec(select(func.count(User.id))).one()

    if user_count == 0:
        # No users exist - create admin user with provided credentials
        user = User(
            email=body.email,
            password_hash=hash_password(body.password),
            is_admin=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        admin_created = True

        # Also run register hooks for auto-created admin
        register_event = UserRegisterEvent(user_id=user.id, email=user.email)
        background_tasks.add_task(asyncio.run, run_user_register_hooks(register_event))
    else:
        # Find user by email
        user = session.exec(select(User).where(User.email == body.email)).first()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # Verify password
        if not verify_password(body.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

    # Create and return token
    auth_token = create_auth_token(session, user)

    # Run user login hooks in background
    login_event = UserLoginEvent(user_id=user.id, email=user.email, is_admin=user.is_admin)
    background_tasks.add_task(asyncio.run, run_user_login_hooks(login_event))

    return LoginResponse(
        token=auth_token.token,
        user_id=str(user.id),
        email=user.email,
        is_admin=user.is_admin,
        admin_created=admin_created,
    )


@router.get(
    "/me",
    response_model=UserInfo,
    summary="Get current user info",
    description="Retrieve information about the currently authenticated user.",
)
def get_me(user: CurrentUser) -> UserInfo:
    """
    Get information about the current authenticated user.

    Requires a valid bearer token in the Authorization header.
    """
    return UserInfo(
        id=str(user.id),
        email=user.email,
        is_admin=user.is_admin,
        created_at=user.created_at.isoformat(),
    )
