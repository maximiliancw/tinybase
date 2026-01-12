"""
Tests for internal token generation.

Tests token creation, expiration, and usage for subprocess callbacks.
"""

from datetime import timedelta

import pytest
from sqlmodel import Session, select

from tinybase.auth import create_internal_token
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
        # Handle timezone-aware vs naive datetime comparison
        from datetime import timezone

        expires = token.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        now = utcnow()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        assert expires > now

    def test_create_internal_token_with_user(self, session):
        """Test creating internal token with user ID."""
        from tinybase.auth import hash_password
        from tinybase.db.models import User

        # Create a test user first
        test_user = User(
            email="testuser@example.com",
            password_hash=hash_password("password"),
            is_admin=False,
        )
        session.add(test_user)
        session.commit()
        session.refresh(test_user)
        user_id = test_user.id

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
        from tinybase.auth import hash_password
        from tinybase.db.models import User

        # Create a test admin user first
        test_user = User(
            email="admin@example.com",
            password_hash=hash_password("password"),
            is_admin=True,
        )
        session.add(test_user)
        session.commit()
        session.refresh(test_user)
        user_id = test_user.id

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
        from datetime import timezone

        expected_expiry = utcnow() + timedelta(minutes=10)
        expires = token.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expected_expiry.tzinfo is None:
            expected_expiry = expected_expiry.replace(tzinfo=timezone.utc)
        time_diff = abs((expires - expected_expiry).total_seconds())
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
        from datetime import timezone

        expected_expiry = utcnow() + timedelta(minutes=5)
        expires = token.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expected_expiry.tzinfo is None:
            expected_expiry = expected_expiry.replace(tzinfo=timezone.utc)
        time_diff = abs((expires - expected_expiry).total_seconds())
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
        from datetime import timezone

        expected_expiry = utcnow() + timedelta(minutes=1)
        expires = token.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expected_expiry.tzinfo is None:
            expected_expiry = expected_expiry.replace(tzinfo=timezone.utc)
        time_diff = abs((expires - expected_expiry).total_seconds())
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
        """Test that internal token can be validated."""
        from tinybase.auth import hash_password
        from tinybase.db.models import User

        # Create a test user first
        test_user = User(
            email="testuser@example.com",
            password_hash=hash_password("password"),
            is_admin=False,
        )
        session.add(test_user)
        session.commit()
        session.refresh(test_user)
        user_id = test_user.id

        token_str = create_internal_token(
            session=session,
            user_id=user_id,
            is_admin=False,
            expires_minutes=5,
        )

        # Token should be valid - query directly
        validated_token = session.exec(
            select(AuthToken).where(AuthToken.token == token_str)
        ).first()

        assert validated_token is not None
        assert validated_token.user_id == user_id
        assert validated_token.token == token_str
        assert not validated_token.is_expired()

    def test_internal_token_multiple_tokens(self, session):
        """Test creating multiple internal tokens."""
        from tinybase.auth import hash_password
        from tinybase.db.models import User

        # Create a test user first
        test_user = User(
            email="testuser@example.com",
            password_hash=hash_password("password"),
            is_admin=False,
        )
        session.add(test_user)
        session.commit()
        session.refresh(test_user)
        user_id = test_user.id

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
        validated1 = session.exec(select(AuthToken).where(AuthToken.token == token1)).first()
        validated2 = session.exec(select(AuthToken).where(AuthToken.token == token2)).first()

        assert validated1 is not None
        assert validated2 is not None
        assert validated1.token == token1
        assert validated2.token == token2

    def test_internal_token_different_users(self, session):
        """Test creating tokens for different users."""
        from tinybase.auth import hash_password
        from tinybase.db.models import User

        # Create test users first
        user1 = User(
            email="user1@example.com",
            password_hash=hash_password("password"),
            is_admin=False,
        )
        user2 = User(
            email="user2@example.com",
            password_hash=hash_password("password"),
            is_admin=False,
        )
        session.add(user1)
        session.add(user2)
        session.commit()
        session.refresh(user1)
        session.refresh(user2)
        user1_id = user1.id
        user2_id = user2.id

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
        validated1 = session.exec(select(AuthToken).where(AuthToken.token == token1)).first()
        validated2 = session.exec(select(AuthToken).where(AuthToken.token == token2)).first()

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
        token = session.exec(select(AuthToken).where(AuthToken.token == token_str)).first()
        assert token is not None
        assert not token.is_expired()

        # Wait for expiration
        import time

        time.sleep(1)

        # Token should be expired
        expired_token = session.exec(select(AuthToken).where(AuthToken.token == token_str)).first()
        assert expired_token is None or expired_token.is_expired()
