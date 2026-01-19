"""
Authentication utilities for TinyBase.

Provides password hashing, JWT token management, and FastAPI dependencies
for authenticating API requests.
"""

import logging
from typing import Annotated
from uuid import UUID

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from tinybase.auth_jwt import (
    create_access_token as jwt_create_access_token,
    create_application_token as jwt_create_application_token,
    create_internal_token as jwt_create_internal_token,
    create_refresh_token as jwt_create_refresh_token,
    get_user_from_token,
    revoke_all_user_tokens,
    revoke_token,
)
from tinybase.db.core import get_session
from tinybase.db.models import AuthToken, User
from datetime import datetime
from tinybase.utils import utcnow

logger = logging.getLogger(__name__)

# Bearer token security scheme for FastAPI
bearer_scheme = HTTPBearer(auto_error=False)


# =============================================================================
# Password Utilities
# =============================================================================


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Args:
        password: The plaintext password to hash.

    Returns:
        The bcrypt hash of the password.
    """
    # bcrypt requires bytes and has a 72-byte limit
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a bcrypt hash.

    Args:
        plain_password: The plaintext password to verify.
        hashed_password: The bcrypt hash to verify against.

    Returns:
        True if the password matches, False otherwise.
    """
    try:
        password_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception:
        return False


# =============================================================================
# Token Utilities (JWT-based)
# =============================================================================


def create_auth_token(session: Session, user: User) -> tuple[AuthToken, str]:
    """
    Create and persist a new JWT access token for a user.

    Args:
        session: Database session.
        user: The user to create a token for.

    Returns:
        Tuple of (AuthToken, jwt_string).
    """
    return jwt_create_access_token(session, user)


def get_token_user(session: Session, token_str: str) -> User | None:
    """
    Get the user associated with a JWT token string.

    Args:
        session: Database session.
        token_str: The JWT token string to look up.

    Returns:
        The User if the token is valid and not expired, None otherwise.
    """
    return get_user_from_token(session, token_str)


# =============================================================================
# FastAPI Dependencies
# =============================================================================


def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_session)],
) -> User | None:
    """
    Get the current authenticated user, if any.

    This dependency does not raise an error if no valid token is provided.
    Use this for endpoints that support both authenticated and anonymous access.

    Args:
        credentials: The HTTP Bearer credentials (may be None).
        session: Database session.

    Returns:
        The authenticated User, or None if not authenticated.
    """
    if credentials is None:
        return None

    return get_token_user(session, credentials.credentials)


def get_current_user(
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    """
    Get the current authenticated user (required).

    Raises HTTP 401 if no valid authentication is provided.

    Args:
        user: The user from get_current_user_optional.

    Returns:
        The authenticated User.

    Raises:
        HTTPException: 401 if not authenticated.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_admin_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Get the current authenticated admin user.

    Raises HTTP 403 if the authenticated user is not an admin.

    Args:
        user: The authenticated user.

    Returns:
        The authenticated admin User.

    Raises:
        HTTPException: 403 if the user is not an admin.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# Type aliases for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserOptional = Annotated[User | None, Depends(get_current_user_optional)]
CurrentAdminUser = Annotated[User, Depends(get_current_admin_user)]
DbSession = Annotated[Session, Depends(get_session)]


# =============================================================================
# Token Cleanup
# =============================================================================


def cleanup_expired_tokens(session: Session) -> int:
    """
    Remove expired JWT authentication tokens from the database.

    Args:
        session: Database session.

    Returns:
        Number of tokens deleted.
    """
    now = utcnow()

    # Find and delete expired tokens
    expired_tokens = session.exec(
        select(AuthToken).where(
            AuthToken.expires_at != None,  # noqa: E711
            AuthToken.expires_at < now,
        )
    ).all()

    count = len(expired_tokens)
    for token in expired_tokens:
        session.delete(token)

    if count > 0:
        session.commit()
        logger.info(f"Cleaned up {count} expired JWT tokens")

    return count


# =============================================================================
# Application Token Utilities (JWT-based)
# =============================================================================


def create_application_token(
    session: Session,
    name: str,
    description: str | None = None,
    expires_at: datetime | None = None,
) -> tuple[AuthToken, str]:
    """
    Create and persist a new JWT application token for system-to-system authentication.

    Args:
        session: Database session.
        name: Human-readable name for this token.
        description: Optional description of the token's purpose.
        expires_at: Optional expiration datetime. If None, defaults to 1 year.

    Returns:
        Tuple of (AuthToken, jwt_string).
    """
    return jwt_create_application_token(session, name, description, expires_at)


def create_internal_token(
    session: Session,
    user_id: UUID | None = None,
    is_admin: bool = False,
    expires_minutes: int = 5,
) -> str:
    """
    Create a short-lived internal JWT token for subprocess HTTP callbacks.

    This token allows function subprocesses to make authenticated HTTP requests
    back to the TinyBase API. The token has the same permissions as the calling user.

    Args:
        session: Database session.
        user_id: ID of the user (None for scheduled/system calls).
        is_admin: Whether the user has admin privileges.
        expires_minutes: Token expiration time in minutes (default: 5).

    Returns:
        The JWT token string to use for authentication.
    """
    return jwt_create_internal_token(session, user_id, is_admin, expires_minutes)


def revoke_application_token(session: Session, token_id: UUID) -> bool:
    """
    Revoke (deactivate) an application token by marking it inactive.

    Args:
        session: Database session.
        token_id: The ID of the token to revoke.

    Returns:
        True if token was found and revoked, False otherwise.
    """
    token = session.get(AuthToken, token_id)
    if token is None or token.scope != "application":
        return False

    token.is_active = False
    session.add(token)
    session.commit()
    return True
