"""
Authentication API routes.

Provides endpoints for:
- User registration
- User login (token issuance)
- Current user info retrieval
"""

import asyncio
import os
import secrets

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlmodel import select

from tinybase.auth import (
    CurrentUser,
    CurrentUserOptional,
    DBSession,
    create_auth_token,
    create_refresh_token,
    hash_password,
    revoke_all_user_tokens,
    revoke_token,
    verify_jwt_token,
    verify_password,
)
from tinybase.db.models import InstanceSettings, PasswordResetToken, User
from tinybase.email import send_password_reset_email
from tinybase.extensions.hooks import (
    UserLoginEvent,
    UserRegisterEvent,
    run_user_login_hooks,
    run_user_register_hooks,
)
from tinybase.utils import utcnow

router = APIRouter(prefix="/auth", tags=["auth"])

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
    """User login response with JWT tokens."""

    access_token: str = Field(description="JWT access token for API authentication")
    refresh_token: str = Field(description="JWT refresh token for obtaining new access tokens")
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


class PasswordResetRequest(BaseModel):
    """Password reset request."""

    email: EmailStr = Field(description="User email address")


class PasswordResetRequestResponse(BaseModel):
    """Password reset request response."""

    message: str = Field(
        default="If the email exists, a password reset link has been sent",
        description="Response message (always the same for security)",
    )


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""

    token: str = Field(description="Password reset token")
    password: str = Field(min_length=8, description="New password (min 8 characters)")


class PasswordResetConfirmResponse(BaseModel):
    """Password reset confirmation response."""

    message: str = Field(default="Password reset successful")


class PortalConfigResponse(BaseModel):
    """Auth portal configuration."""

    instance_name: str = Field(description="Instance name")
    logo_url: str | None = Field(default=None, description="Logo URL")
    primary_color: str | None = Field(default=None, description="Primary color")
    background_image_url: str | None = Field(default=None, description="Background image URL")
    registration_enabled: bool = Field(description="Whether registration is enabled")
    login_redirect_url: str | None = Field(
        default=None, description="Default redirect URL after login"
    )
    register_redirect_url: str | None = Field(
        default=None, description="Default redirect URL after registration"
    )


# =============================================================================
# Routes
# =============================================================================


@router.get(
    "/instance-info",
    response_model=InstanceInfoResponse,
    summary="Get public instance info",
    description="Get public information about this TinyBase instance (no auth required).",
)
def get_instance_info(session: DBSession) -> InstanceInfoResponse:
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
def get_setup_status(session: DBSession) -> SetupStatusResponse:
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
    session: DBSession,
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
    session: DBSession,
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

    # Create access and refresh tokens
    access_token_obj, access_token_str = create_auth_token(session, user)
    refresh_token_obj, refresh_token_str = create_refresh_token(session, user)

    # Run user login hooks in background
    login_event = UserLoginEvent(user_id=user.id, email=user.email, is_admin=user.is_admin)
    background_tasks.add_task(asyncio.run, run_user_login_hooks(login_event))

    return LoginResponse(
        access_token=access_token_str,
        refresh_token=refresh_token_str,
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


@router.post(
    "/password-reset/request",
    response_model=PasswordResetRequestResponse,
    summary="Request password reset",
    description="Request a password reset email. Always returns success for security.",
)
@limiter.limit("5/minute")
def request_password_reset(
    request: Request,
    body: PasswordResetRequest,
    session: DBSession,
    background_tasks: BackgroundTasks,
) -> PasswordResetRequestResponse:
    """
    Request a password reset.

    If the email exists, generates a reset token and sends an email.
    Always returns the same response for security (prevents email enumeration).
    """
    # Find user by email
    user = session.exec(select(User).where(User.email == body.email)).first()

    if user:
        # Generate reset token
        token_str = secrets.token_hex(32)
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token_str,
        )
        session.add(reset_token)
        session.commit()

        # Build reset URL
        base_url = str(request.base_url).rstrip("/")
        reset_url = f"{base_url}/auth/password-reset/{token_str}"

        # Send email in background
        background_tasks.add_task(send_password_reset_email, user.email, token_str, reset_url)

    # Always return the same response (security best practice)
    return PasswordResetRequestResponse()


@router.post(
    "/password-reset/confirm",
    response_model=PasswordResetConfirmResponse,
    summary="Confirm password reset",
    description="Reset password using a valid reset token.",
)
@limiter.limit("10/minute")
def confirm_password_reset(
    request: Request,
    body: PasswordResetConfirm,
    session: DBSession,
) -> PasswordResetConfirmResponse:
    """
    Confirm password reset with token.

    Validates the token, checks it hasn't expired or been used,
    then updates the user's password.
    """
    # Find token
    reset_token = session.exec(
        select(PasswordResetToken).where(PasswordResetToken.token == body.token)
    ).first()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Check if token is valid
    if not reset_token.is_valid():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Get user
    user = session.get(User, reset_token.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Update password
    user.password_hash = hash_password(body.password)
    user.updated_at = utcnow()

    # Mark token as used
    reset_token.used_at = utcnow()

    session.add(user)
    session.add(reset_token)
    session.commit()

    return PasswordResetConfirmResponse()


@router.post(
    "/refresh",
    response_model=LoginResponse,
    summary="Refresh access token",
    description="Use a refresh token to obtain new access and refresh tokens.",
)
@limiter.limit("20/minute")
def refresh_token(
    request: Request,
    session: DBSession,
    user: CurrentUser,
) -> LoginResponse:
    """
    Refresh access token using a refresh token.

    Validates the provided refresh token and issues new access and refresh tokens.
    The old refresh token is revoked.
    """
    # The user is already authenticated via the refresh token through CurrentUser dependency
    # We need to verify it's actually a refresh token
    from fastapi.security import HTTPBearer

    # Get the token from the request
    bearer_scheme = HTTPBearer(auto_error=False)
    credentials = bearer_scheme(request)

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided",
        )

    # Verify it's a refresh token
    result = verify_jwt_token(session, credentials.credentials)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    claims, db_token = result

    if claims.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not a refresh token",
        )

    # Revoke the old refresh token
    revoke_token(session, db_token.jti)

    # Create new access and refresh tokens
    access_token_obj, access_token_str = create_auth_token(session, user)
    refresh_token_obj, refresh_token_str = create_refresh_token(session, user)

    return LoginResponse(
        access_token=access_token_str,
        refresh_token=refresh_token_str,
        user_id=str(user.id),
        email=user.email,
        is_admin=user.is_admin,
    )


class LogoutResponse(BaseModel):
    """Logout response."""

    message: str = Field(default="Successfully logged out")


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Logout and revoke tokens",
    description="Revoke all access and refresh tokens for the current user.",
)
def logout(
    user: CurrentUser,
    session: DBSession,
) -> LogoutResponse:
    """
    Logout the current user by revoking all their tokens.

    This revokes all access and refresh tokens for the user, forcing
    them to log in again to obtain new tokens.
    """
    # Revoke all user tokens (both access and refresh)
    count = revoke_all_user_tokens(session, user.id)

    return LogoutResponse(message=f"Successfully logged out ({count} tokens revoked)")


@router.get(
    "/portal-config",
    response_model=PortalConfigResponse,
    summary="Get portal configuration",
    description="Get public portal configuration. Supports preview mode for admins.",
)
def get_portal_config(
    session: DBSession,
    preview: bool = Query(default=False, description="Enable preview mode (admin only)"),
    logo_url: str | None = Query(default=None, description="Preview logo URL"),
    primary_color: str | None = Query(default=None, description="Preview primary color"),
    background_image_url: str | None = Query(
        default=None, description="Preview background image URL"
    ),
    user: CurrentUserOptional = None,  # type: ignore[assignment]
) -> PortalConfigResponse:
    """
    Get portal configuration for the auth portal UI.

    Returns instance name, logo, colors, and registration status.
    When preview=true, requires admin authentication and returns preview values
    if provided, otherwise falls back to saved settings.
    """
    instance_settings = session.get(InstanceSettings, 1)
    if not instance_settings:
        return PortalConfigResponse(
            instance_name="TinyBase",
            registration_enabled=True,
        )

    # If preview mode is requested, require admin authentication
    if preview:
        if not user or not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required for preview mode",
            )
        # Use preview values if explicitly provided (including empty string to clear),
        # otherwise fall back to saved settings
        # Note: logo_url, primary_color, background_image_url can be None (not provided)
        # or empty string (explicitly cleared), so we check for None specifically
        return PortalConfigResponse(
            instance_name=instance_settings.instance_name,
            logo_url=logo_url if logo_url is not None else instance_settings.auth_portal_logo_url,
            primary_color=primary_color
            if primary_color is not None
            else instance_settings.auth_portal_primary_color,
            background_image_url=background_image_url
            if background_image_url is not None
            else instance_settings.auth_portal_background_image_url,
            registration_enabled=instance_settings.allow_public_registration,
            login_redirect_url=instance_settings.auth_portal_login_redirect_url,
            register_redirect_url=instance_settings.auth_portal_register_redirect_url,
        )

    # Normal mode: return saved settings (no auth required)
    return PortalConfigResponse(
        instance_name=instance_settings.instance_name,
        logo_url=instance_settings.auth_portal_logo_url,
        primary_color=instance_settings.auth_portal_primary_color,
        background_image_url=instance_settings.auth_portal_background_image_url,
        registration_enabled=instance_settings.allow_public_registration,
        login_redirect_url=instance_settings.auth_portal_login_redirect_url,
        register_redirect_url=instance_settings.auth_portal_register_redirect_url,
    )
