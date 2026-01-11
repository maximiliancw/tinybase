"""
Tests for internal token generation.

Tests token creation, expiration, and usage for subprocess callbacks.
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlmodel import Session, select

from tinybase.auth import create_internal_token, get_auth_token
from tinybase.db.core import create_db_and_tables, get_engine
from tinybase.db.models import AuthToken
from tinybase.utils import utcnow


class TestInternalTokens:
    """Test internal token generation and validation."""

    @pytest.fixture
    def session(self):
        """Create a test database session."""
        create_db_and_tables()
        engine = get_engine()
        with Session(engine) as session:
            yield session

    def test_create_internal_token_basic(self, session):
        """Test creating a basic internal token."""
        token_str = create_internal_token(
            session=session,
            user_id=None,
            is_admin=False,
            expires_minutes=5,
        )

        assert token_str is not None
        assert isinstance(token_str, str)
        assert len(token_str) > 0

        # Verify token exists in database
        token = session.exec(select(AuthToken).where(AuthToken.token == token_str)).first()

        assert token is not None
        assert token.user_id is None
        assert token.expires_at > utcnow()

    def test_create_internal_token_with_user(self, session):
        """Test creating internal token with user ID."""
        user_id = uuid4()

        token_str = create_internal_token(
            session=session,
            user_id=user_id,
            is_admin=False,
            expires_minutes=5,
        )

        # Verify token has user_id
        token = session.exec(select(AuthToken).where(AuthToken.token == token_str)).first()

        assert token is not None
        assert token.user_id == user_id

    def test_create_internal_token_admin(self, session):
        """Test creating internal token for admin user."""
        user_id = uuid4()

        token_str = create_internal_token(
            session=session,
            user_id=user_id,
            is_admin=True,
            expires_minutes=5,
        )

        # Token should be created (admin flag is passed but stored in token context)
        token = session.exec(select(AuthToken).where(AuthToken.token == token_str)).first()

        assert token is not None
        assert token.user_id == user_id

    def test_create_internal_token_expiration(self, session):
        """Test token expiration time."""
        token_str = create_internal_token(
            session=session,
            user_id=None,
            is_admin=False,
            expires_minutes=10,
        )

        token = session.exec(select(AuthToken).where(AuthToken.token == token_str)).first()

        assert token is not None
        # Expiration should be approximately 10 minutes from now
        expected_expiry = utcnow() + timedelta(minutes=10)
        time_diff = abs((token.expires_at - expected_expiry).total_seconds())
        assert time_diff < 60  # Within 1 minute tolerance

    def test_create_internal_token_default_expiration(self, session):
        """Test default token expiration (5 minutes)."""
        token_str = create_internal_token(
            session=session,
            user_id=None,
            is_admin=False,
        )

        token = session.exec(select(AuthToken).where(AuthToken.token == token_str)).first()

        assert token is not None
        # Should expire in approximately 5 minutes
        expected_expiry = utcnow() + timedelta(minutes=5)
        time_diff = abs((token.expires_at - expected_expiry).total_seconds())
        assert time_diff < 60  # Within 1 minute tolerance

    def test_create_internal_token_custom_expiration(self, session):
        """Test custom token expiration."""
        token_str = create_internal_token(
            session=session,
            user_id=None,
            is_admin=False,
            expires_minutes=1,
        )

        token = session.exec(select(AuthToken).where(AuthToken.token == token_str)).first()

        assert token is not None
        # Should expire in approximately 1 minute
        expected_expiry = utcnow() + timedelta(minutes=1)
        time_diff = abs((token.expires_at - expected_expiry).total_seconds())
        assert time_diff < 60  # Within 1 minute tolerance

    def test_create_internal_token_for_scheduled_function(self, session):
        """Test creating token for scheduled function (no user)."""
        token_str = create_internal_token(
            session=session,
            user_id=None,
            is_admin=False,
            expires_minutes=5,
        )

        token = session.exec(select(AuthToken).where(AuthToken.token == token_str)).first()

        assert token is not None
        assert token.user_id is None  # Scheduled functions have no user

    def test_internal_token_can_be_validated(self, session):
        """Test that internal token can be validated via get_auth_token."""
        user_id = uuid4()

        token_str = create_internal_token(
            session=session,
            user_id=user_id,
            is_admin=False,
            expires_minutes=5,
        )

        # Token should be valid
        validated_token = get_auth_token(session, token_str)

        assert validated_token is not None
        assert validated_token.user_id == user_id
        assert validated_token.token == token_str

    def test_internal_token_multiple_tokens(self, session):
        """Test creating multiple internal tokens."""
        user_id = uuid4()

        token1 = create_internal_token(
            session=session,
            user_id=user_id,
            is_admin=False,
            expires_minutes=5,
        )

        token2 = create_internal_token(
            session=session,
            user_id=user_id,
            is_admin=False,
            expires_minutes=5,
        )

        assert token1 != token2

        # Both should be valid
        validated1 = get_auth_token(session, token1)
        validated2 = get_auth_token(session, token2)

        assert validated1 is not None
        assert validated2 is not None
        assert validated1.token == token1
        assert validated2.token == token2

    def test_internal_token_different_users(self, session):
        """Test creating tokens for different users."""
        user1_id = uuid4()
        user2_id = uuid4()

        token1 = create_internal_token(
            session=session,
            user_id=user1_id,
            is_admin=False,
            expires_minutes=5,
        )

        token2 = create_internal_token(
            session=session,
            user_id=user2_id,
            is_admin=False,
            expires_minutes=5,
        )

        # Both tokens should be valid
        validated1 = get_auth_token(session, token1)
        validated2 = get_auth_token(session, token2)

        assert validated1 is not None
        assert validated2 is not None
        assert validated1.user_id == user1_id
        assert validated2.user_id == user2_id

    def test_internal_token_expires(self, session):
        """Test that internal tokens expire."""
        # Create token with very short expiration
        token_str = create_internal_token(
            session=session,
            user_id=None,
            is_admin=False,
            expires_minutes=0.01,  # 0.6 seconds
        )

        # Token should be valid initially
        token = get_auth_token(session, token_str)
        assert token is not None

        # Wait for expiration
        import time

        time.sleep(1)

        # Token should be expired
        expired_token = get_auth_token(session, token_str)
        assert expired_token is None
