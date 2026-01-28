"""
Authentication utilities for TinyBase.

Provides password hashing, JWT token management, and FastAPI dependencies
for authenticating API requests.
"""

from .core import (
    CurrentAdminUser,
    CurrentUser,
    CurrentUserOptional,
    DBSession,
    bearer_scheme,
    cleanup_expired_tokens,
    create_application_token,
    create_auth_token,
    create_internal_token,
    get_current_admin_user,
    get_current_user,
    get_current_user_optional,
    get_token_user,
    hash_password,
    revoke_application_token,
    verify_password,
)
from .jwt import create_refresh_token, revoke_all_user_tokens, revoke_token, verify_jwt_token

__all__ = [
    # Password utilities
    "hash_password",
    "verify_password",
    # Token creation
    "create_auth_token",
    "create_application_token",
    "create_internal_token",
    "create_refresh_token",
    # Token verification
    "get_token_user",
    "verify_jwt_token",
    # Token revocation
    "revoke_token",
    "revoke_all_user_tokens",
    "revoke_application_token",
    # FastAPI dependencies
    "get_current_user",
    "get_current_user_optional",
    "get_current_admin_user",
    "CurrentUser",
    "CurrentUserOptional",
    "CurrentAdminUser",
    "DBSession",
    "bearer_scheme",
    # Token cleanup
    "cleanup_expired_tokens",
]
