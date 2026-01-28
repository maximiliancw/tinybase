"""
JWT authentication utilities for TinyBase.

Provides JWT token generation, verification, and management using PyJWT.
Replaces the legacy opaque token system with industry-standard JWT tokens.
"""

import logging
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import jwt
from sqlmodel import Session

from tinybase.db.models import AuthToken, User
from tinybase.settings import config
from tinybase.utils import utcnow

logger = logging.getLogger(__name__)


# =============================================================================
# JWT Token Creation
# =============================================================================


def create_jwt_token(
    user_id: UUID | None,
    is_admin: bool,
    token_type: str,
    scope: str,
    expires_delta: timedelta | None = None,
) -> tuple[str, UUID]:
    """
    Generate a JWT token with standard claims.

    Args:
        user_id: User ID (None for application/internal tokens).
        is_admin: Whether the user has admin privileges.
        token_type: Token type ("access" or "refresh").
        scope: Token scope ("user", "application", or "internal").
        expires_delta: Token expiration time delta. If None, defaults based on token_type.

    Returns:
        Tuple of (jwt_string, jti) where jti is the unique token ID.
    """
    # Set default expiration based on token type
    if expires_delta is None:
        if token_type == "refresh":
            expires_delta = timedelta(days=config.jwt_refresh_token_expire_days)
        else:  # access token
            expires_delta = timedelta(minutes=config.jwt_access_token_expire_minutes)

    now = utcnow()
    exp = now + expires_delta
    jti = uuid4()

    # Build JWT payload with standard claims
    payload = {
        "sub": str(user_id) if user_id else None,
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": str(jti),
        "is_admin": is_admin,
        "type": token_type,
        "scope": scope,
    }

    # Encode JWT
    jwt_string = jwt.encode(
        payload,
        config.jwt_secret_key,
        algorithm=config.jwt_algorithm,
    )

    return jwt_string, jti


def decode_jwt_token(token: str) -> dict:
    """
    Decode and verify a JWT token.

    Args:
        token: The JWT token string to decode.

    Returns:
        Dictionary of decoded claims.

    Raises:
        jwt.InvalidTokenError: If token is invalid or expired.
        jwt.ExpiredSignatureError: If token is expired.
    """
    # Decode and verify JWT signature
    payload = jwt.decode(
        token,
        config.jwt_secret_key,
        algorithms=[config.jwt_algorithm],
    )

    return payload


# =============================================================================
# Token Creation Utilities
# =============================================================================


def create_access_token(session: Session, user: User) -> tuple[AuthToken, str]:
    """
    Create a JWT access token for a user.

    Args:
        session: Database session.
        user: The user to create a token for.

    Returns:
        Tuple of (AuthToken, jwt_string).
    """
    jwt_string, jti = create_jwt_token(
        user_id=user.id,
        is_admin=user.is_admin,
        token_type="access",
        scope="user",
    )

    expires_at = utcnow() + timedelta(minutes=config.jwt_access_token_expire_minutes)

    token = AuthToken(
        user_id=user.id,
        token=jwt_string,
        token_type="access",
        scope="user",
        jti=jti,
        expires_at=expires_at,
    )
    session.add(token)
    session.commit()
    session.refresh(token)

    return token, jwt_string


def create_refresh_token(session: Session, user: User) -> tuple[AuthToken, str]:
    """
    Create a JWT refresh token for a user.

    Args:
        session: Database session.
        user: The user to create a token for.

    Returns:
        Tuple of (AuthToken, jwt_string).
    """
    jwt_string, jti = create_jwt_token(
        user_id=user.id,
        is_admin=user.is_admin,
        token_type="refresh",
        scope="user",
    )

    expires_at = utcnow() + timedelta(days=config.jwt_refresh_token_expire_days)

    token = AuthToken(
        user_id=user.id,
        token=jwt_string,
        token_type="refresh",
        scope="user",
        jti=jti,
        expires_at=expires_at,
    )
    session.add(token)
    session.commit()
    session.refresh(token)

    return token, jwt_string


def create_application_token(
    session: Session,
    name: str,
    description: str | None = None,
    expires_at: datetime | None = None,
) -> tuple[AuthToken, str]:
    """
    Create a long-lived JWT application token.

    Args:
        session: Database session.
        name: Human-readable name for this token.
        description: Optional description of the token's purpose.
        expires_at: Optional expiration datetime. If None, defaults to 1 year.

    Returns:
        Tuple of (AuthToken, jwt_string).
    """
    # Default to 1 year expiration for application tokens
    if expires_at is None:
        expires_at = utcnow() + timedelta(days=365)

    expires_delta = expires_at - utcnow()
    jwt_string, jti = create_jwt_token(
        user_id=None,  # Application tokens don't have a user
        is_admin=True,  # Application tokens have admin privileges
        token_type="access",
        scope="application",
        expires_delta=expires_delta,
    )

    token = AuthToken(
        user_id=None,
        token=jwt_string,
        token_type="access",
        scope="application",
        jti=jti,
        expires_at=expires_at,
        name=name,
        description=description,
        is_active=True,
    )
    session.add(token)
    session.commit()
    session.refresh(token)

    return token, jwt_string


def create_internal_token(
    session: Session,
    user_id: UUID | None,
    is_admin: bool,
    expires_minutes: int = 5,
) -> str:
    """
    Create a short-lived internal JWT token for subprocess HTTP callbacks.

    Args:
        session: Database session.
        user_id: ID of the user (None for scheduled/system calls).
        is_admin: Whether the user has admin privileges.
        expires_minutes: Token expiration time in minutes (default: 5).

    Returns:
        The JWT token string.
    """
    jwt_string, jti = create_jwt_token(
        user_id=user_id,
        is_admin=is_admin,
        token_type="access",
        scope="internal",
        expires_delta=timedelta(minutes=expires_minutes),
    )

    expires_at = utcnow() + timedelta(minutes=expires_minutes)

    token = AuthToken(
        user_id=user_id,
        token=jwt_string,
        token_type="access",
        scope="internal",
        jti=jti,
        expires_at=expires_at,
    )
    session.add(token)
    session.commit()
    session.refresh(token)

    return jwt_string


# =============================================================================
# Token Verification
# =============================================================================


def verify_jwt_token(session: Session, token_str: str) -> tuple[dict, AuthToken] | None:
    """
    Verify a JWT token's signature and check if it's been revoked.

    Args:
        session: Database session.
        token_str: The JWT token string to verify.

    Returns:
        Tuple of (claims, db_token) if valid, None if invalid/revoked.
    """
    try:
        # Decode and verify JWT signature
        claims = decode_jwt_token(token_str)

        # Extract JTI from claims
        jti_str = claims.get("jti")
        if not jti_str:
            logger.warning("JWT token missing jti claim")
            return None

        jti = UUID(jti_str)

        # Check if token exists in database (not revoked)
        from sqlmodel import select

        statement = select(AuthToken).where(AuthToken.jti == jti)
        db_token = session.exec(statement).first()

        if db_token is None:
            logger.warning(f"JWT token with jti {jti} not found in database (revoked)")
            return None

        # Check if application token is active
        if db_token.scope == "application" and not db_token.is_active:
            logger.warning(f"Application token with jti {jti} is inactive")
            return None

        # Update last_used_at for application tokens
        if db_token.scope == "application":
            db_token.last_used_at = utcnow()
            session.add(db_token)
            session.commit()

        return claims, db_token

    except jwt.ExpiredSignatureError:
        logger.debug("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None
    except ValueError as e:
        logger.warning(f"Invalid JTI format in JWT: {e}")
        return None


def get_user_from_token(session: Session, token_str: str) -> User | None:
    """
    Get the user associated with a JWT token.

    Args:
        session: Database session.
        token_str: The JWT token string.

    Returns:
        The User if token is valid, None otherwise.
    """
    result = verify_jwt_token(session, token_str)
    if result is None:
        return None

    claims, db_token = result

    # Extract user_id from claims
    user_id_str = claims.get("sub")
    if not user_id_str:
        # Application or internal tokens without a user
        return None

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        logger.warning(f"Invalid user ID format in JWT: {user_id_str}")
        return None

    # Fetch the user from database
    user = session.get(User, user_id)
    return user


# =============================================================================
# Token Revocation
# =============================================================================


def revoke_token(session: Session, jti: UUID) -> bool:
    """
    Revoke a JWT token by deleting it from the database.

    Args:
        session: Database session.
        jti: The JWT ID to revoke.

    Returns:
        True if token was found and revoked, False otherwise.
    """
    from sqlmodel import select

    statement = select(AuthToken).where(AuthToken.jti == jti)
    token = session.exec(statement).first()

    if token is None:
        return False

    session.delete(token)
    session.commit()
    logger.info(f"Revoked JWT token with jti {jti}")
    return True


def revoke_all_user_tokens(session: Session, user_id: UUID, token_type: str | None = None) -> int:
    """
    Revoke all tokens for a specific user.

    Args:
        session: Database session.
        user_id: The user ID whose tokens to revoke.
        token_type: Optional token type filter ("access" or "refresh"). If None, revokes all types.

    Returns:
        Number of tokens revoked.
    """
    from sqlmodel import select

    statement = select(AuthToken).where(AuthToken.user_id == user_id)
    if token_type:
        statement = statement.where(AuthToken.token_type == token_type)

    tokens = session.exec(statement).all()
    count = len(tokens)

    for token in tokens:
        session.delete(token)

    if count > 0:
        session.commit()
        logger.info(f"Revoked {count} tokens for user {user_id}")

    return count
