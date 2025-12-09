"""
Shared pytest fixtures for TinyBase tests.
"""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.utils import create_collection, create_record, get_admin_token, get_user_token


@pytest.fixture(scope="function")
def client():
    """Create a test client with a fresh database."""
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    # Set environment variables before importing tinybase modules
    os.environ["TINYBASE_DB_URL"] = f"sqlite:///{db_path}"
    os.environ["TINYBASE_SCHEDULER_ENABLED"] = "false"
    os.environ["TINYBASE_RATE_LIMIT_ENABLED"] = "false"

    # Import after setting env vars
    from tinybase.api.app import create_app
    from tinybase.auth import hash_password
    from tinybase.collections.schemas import reset_registry
    from tinybase.config import reload_settings
    from tinybase.db.core import create_db_and_tables, get_engine, reset_engine
    from tinybase.db.models import User
    from tinybase.functions.core import reset_global_registry

    # Reset everything
    reset_engine()
    reset_global_registry()
    reset_registry()
    reload_settings()

    # Create tables
    create_db_and_tables()

    # Create test admin user
    engine = get_engine()
    with Session(engine) as session:
        admin = User(
            email="admin@test.com",
            password_hash=hash_password("testpassword"),
            is_admin=True,
        )
        session.add(admin)
        session.commit()

    # Create app
    app = create_app()

    with TestClient(app) as test_client:
        yield test_client

    # Cleanup
    reset_engine()
    reset_global_registry()
    reset_registry()

    # Remove temp database
    try:
        os.unlink(db_path)
    except Exception:
        pass

    # Reset env vars
    os.environ.pop("TINYBASE_DB_URL", None)
    os.environ.pop("TINYBASE_SCHEDULER_ENABLED", None)
    os.environ.pop("TINYBASE_RATE_LIMIT_ENABLED", None)


@pytest.fixture
def admin_token(client):
    """Fixture providing admin authentication token."""
    return get_admin_token(client)


@pytest.fixture
def user_token(client):
    """Fixture providing regular user authentication token."""
    return get_user_token(client)


@pytest.fixture
def test_collection(client, admin_token):
    """Fixture providing a test collection."""
    return create_collection(
        client,
        admin_token,
        name="test_collection",
        label="Test Collection",
        schema={"fields": [{"name": "title", "type": "string"}]},
    )


@pytest.fixture
def test_record(client, admin_token, test_collection):
    """Fixture providing a test record in test_collection."""
    return create_record(
        client,
        admin_token,
        "test_collection",
        {"title": "Test Record"},
    )
