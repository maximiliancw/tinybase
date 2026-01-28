"""
Tests for token scoping functionality.
"""

import pytest
from sqlmodel import Session, select
from tinybase.auth import create_auth_token, create_internal_token, hash_password
from tinybase.db.core import get_db_engine, init_db
from tinybase.db.models import AuthToken, User


class TestTokenScoping:
    """Test token scope field and internal token creation."""

    @pytest.fixture
    def session(self):
        """Create a test session with a fresh database."""
        engine = get_db_engine()
        init_db()

        with Session(engine) as session:
            yield session

    def test_internal_token_has_scope(self, session):
        """Test that internal tokens are created with 'internal' scope."""
        token_str = create_internal_token(
            session=session,
            user_id=None,
            is_admin=False,
            expires_minutes=5,
        )

        # Query the token
        token = session.exec(select(AuthToken).where(AuthToken.token == token_str)).first()

        assert token is not None
        assert token.scope == "internal"

    def test_internal_token_with_user_has_scope(self, session):
        """Test that internal tokens with user_id have 'internal' scope."""
        # Create a test user
        import uuid

        test_user = User(
            email=f"test-{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("testpass"),
            is_admin=False,
        )
        session.add(test_user)
        session.commit()
        session.refresh(test_user)

        token_str = create_internal_token(
            session=session,
            user_id=test_user.id,
            is_admin=False,
            expires_minutes=5,
        )

        # Query the token
        token = session.exec(select(AuthToken).where(AuthToken.token == token_str)).first()

        assert token is not None
        assert token.scope == "internal"
        assert token.user_id == test_user.id

    def test_internal_token_admin_has_scope(self, session):
        """Test that internal tokens for admin users have 'internal' scope."""
        # Create a test admin
        import uuid

        test_admin = User(
            email=f"admin-{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("adminpass"),
            is_admin=True,
        )
        session.add(test_admin)
        session.commit()
        session.refresh(test_admin)

        token_str = create_internal_token(
            session=session,
            user_id=test_admin.id,
            is_admin=True,
            expires_minutes=5,
        )

        # Query the token
        token = session.exec(select(AuthToken).where(AuthToken.token == token_str)).first()

        assert token is not None
        assert token.scope == "internal"
        assert token.user_id == test_admin.id

    def test_regular_auth_token_has_no_scope(self, session):
        """Test that regular auth tokens have 'user' scope."""
        # Create a test user
        import uuid

        test_user = User(
            email=f"user-{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("userpass"),
            is_admin=False,
        )
        session.add(test_user)
        session.commit()
        session.refresh(test_user)

        # Create regular auth token
        auth_token_obj, auth_token_str = create_auth_token(session, test_user)

        assert auth_token_obj.scope == "user"

    def test_scope_field_persists(self, session):
        """Test that scope field persists correctly."""
        token_str = create_internal_token(
            session=session,
            user_id=None,
            is_admin=False,
            expires_minutes=5,
        )

        # Close session and open new one to ensure persistence
        session.close()

        with Session(get_db_engine()) as new_session:
            token = new_session.exec(select(AuthToken).where(AuthToken.token == token_str)).first()

            assert token is not None
            assert token.scope == "internal"

    def test_multiple_scopes(self, session):
        """Test creating tokens with different scopes."""
        # Create user for regular token
        import uuid

        test_user = User(
            email=f"user2-{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("userpass2"),
            is_admin=False,
        )
        session.add(test_user)
        session.commit()
        session.refresh(test_user)

        # Create regular token
        regular_token_obj, regular_token_str = create_auth_token(session, test_user)

        # Create internal token
        internal_token_str = create_internal_token(
            session=session,
            user_id=test_user.id,
            is_admin=False,
            expires_minutes=5,
        )

        internal_token = session.exec(
            select(AuthToken).where(AuthToken.token == internal_token_str)
        ).first()

        # Verify different scopes
        assert regular_token_obj.scope == "user"
        assert internal_token.scope == "internal"

    def test_scope_field_optional(self):
        """Test that scope field is optional (can be None)."""
        from tinybase.db.models import AuthToken

        # Should be able to create AuthToken without scope
        token = AuthToken(token="test-token")
        assert token.scope is None
