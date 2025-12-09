"""
Authentication utilities for TinyBase.

Provides password hashing, token generation, and FastAPI dependencies
for authenticating API requests.
"""

import logging
import secrets
from datetime import timedelta
from typing import Annotated

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from tinybase.config import settings
from tinybase.db.core import get_session
from tinybase.db.models import AuthToken, User
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
# Token Utilities
# =============================================================================


def generate_token() -> str:
    """
    Generate a cryptographically secure random token.

    Returns:
        A 64-character hexadecimal token string.
    """
    return secrets.token_hex(32)


def create_auth_token(session: Session, user: User) -> AuthToken:
    """
    Create and persist a new authentication token for a user.

    Args:
        session: Database session.
        user: The user to create a token for.

    Returns:
        The created AuthToken instance.
    """
    ttl_hours = settings().auth_token_ttl_hours
    expires_at = utcnow() + timedelta(hours=ttl_hours) if ttl_hours > 0 else None

    token = AuthToken(
        user_id=user.id,
        token=generate_token(),
        expires_at=expires_at,
    )
    session.add(token)
    session.commit()
    session.refresh(token)
    return token


def get_token_user(session: Session, token_str: str) -> User | None:
    """
    Get the user associated with a token string.

    Args:
        session: Database session.
        token_str: The token string to look up.

    Returns:
        The User if the token is valid and not expired, None otherwise.
    """
    statement = select(AuthToken).where(AuthToken.token == token_str)
    auth_token = session.exec(statement).first()

    if auth_token is None:
        return None

    if auth_token.is_expired():
        return None

    # Fetch the associated user
    user = session.get(User, auth_token.user_id)
    return user


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
    Remove expired authentication tokens from the database.

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
        logger.info(f"Cleaned up {count} expired auth tokens")

    return count
