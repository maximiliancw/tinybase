"""
Shared pytest fixtures for TinyBase tests.
"""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.utils import create_collection, create_record, get_admin_token, get_user_token


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear settings cache and reset config before and after each test.
    
    This prevents state leakage between tests, especially when one test
    uses the `client` fixture (which sets a temp DB path) and another test
    uses its own `session` fixture.
    """
    from tinybase.db.core import reset_db_engine
    from tinybase.rate_limit import reset_rate_limit_backend
    from tinybase.settings import settings
    from tinybase.settings.static import _reset_config

    # Reset everything before the test
    settings._cache = {}
    settings._loaded = False
    reset_db_engine()
    reset_rate_limit_backend()
    _reset_config()
    
    yield
    
    # Reset everything after the test
    settings._cache = {}
    settings._loaded = False
    reset_db_engine()
    reset_rate_limit_backend()
    _reset_config()


@pytest.fixture(scope="function")
def client():
    """Create a test client with a fresh initialized workspace."""
    import shutil
    import subprocess

    # Create a temporary workspace directory
    workspace_dir = tempfile.mkdtemp(prefix="tinybase_test_workspace_")
    original_cwd = os.getcwd()

    try:
        # Change to workspace directory (tinybase init uses cwd)
        os.chdir(workspace_dir)

        # Run tinybase init to set up workspace properly
        subprocess.run(
            ["uv", "run", "tinybase", "init", "."],
            check=True,
            capture_output=True,
        )

        # Set environment variables for the test
        db_path = os.path.join(workspace_dir, "tinybase.db")
        functions_dir = os.path.join(workspace_dir, "functions")
        rate_limit_cache_dir = os.path.join(workspace_dir, ".tinybase", "rate_limit_cache")

        os.environ["TINYBASE_DB_URL"] = f"sqlite:///{db_path}"
        os.environ["TINYBASE_FUNCTIONS_PATH"] = functions_dir
        os.environ["TINYBASE_SCHEDULER_ENABLED"] = "false"
        os.environ["TINYBASE_RATE_LIMIT_ENABLED"] = "false"
        os.environ["TINYBASE_RATE_LIMIT_CACHE_DIR"] = rate_limit_cache_dir

        # Import after setting env vars
        from tinybase.api.app import create_app
        from tinybase.auth import hash_password
        from tinybase.collections.schemas import reset_collection_registry
        from tinybase.db.core import get_db_engine, init_db, reset_db_engine
        from tinybase.db.models import User
        from tinybase.functions.core import reset_function_registry
        from tinybase.rate_limit import reset_rate_limit_backend
        from tinybase.settings import settings

        # Reset everything
        reset_db_engine()
        reset_function_registry()
        reset_collection_registry()
        reset_rate_limit_backend()

        # Reset static config to pick up new env vars
        from tinybase.settings.static import _reset_config

        _reset_config()

        # Reset settings cache
        settings._loaded = False
        settings._cache = {}

        # Create tables
        init_db()

        # Create test admin user
        engine = get_db_engine()
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
        reset_db_engine()
        reset_function_registry()
        reset_collection_registry()
        reset_rate_limit_backend()

    finally:
        # Restore original working directory
        os.chdir(original_cwd)

        # Remove temp workspace directory
        try:
            shutil.rmtree(workspace_dir)
        except Exception:
            pass

        # Reset env vars
        os.environ.pop("TINYBASE_DB_URL", None)
        os.environ.pop("TINYBASE_FUNCTIONS_PATH", None)
        os.environ.pop("TINYBASE_SCHEDULER_ENABLED", None)
        os.environ.pop("TINYBASE_RATE_LIMIT_ENABLED", None)
        os.environ.pop("TINYBASE_RATE_LIMIT_CACHE_DIR", None)


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


@pytest.fixture
def mock_functions(client):
    """Register mock functions for API testing."""
    from tinybase.functions.core import FunctionMeta, get_function_registry
    from tinybase.utils import AuthLevel

    registry = get_function_registry()

    # Public function
    registry.register(
        FunctionMeta(
            name="public_test",
            description="Public test function",
            auth=AuthLevel.PUBLIC,
            tags=["test"],
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            file_path="/mock/public_test.py",
        )
    )

    # Auth-required function
    registry.register(
        FunctionMeta(
            name="auth_test",
            description="Auth test function",
            auth=AuthLevel.AUTH,
            tags=["test"],
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            file_path="/mock/auth_test.py",
        )
    )

    # Admin-only function
    registry.register(
        FunctionMeta(
            name="admin_test",
            description="Admin test function",
            auth=AuthLevel.ADMIN,
            tags=["test"],
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            file_path="/mock/admin_test.py",
        )
    )

    # Function with Pydantic schema
    registry.register(
        FunctionMeta(
            name="validated_test",
            description="Function with validation",
            auth=AuthLevel.AUTH,
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer", "minimum": 0},
                },
                "required": ["name", "age"],
            },
            output_schema={"type": "object"},
            file_path="/mock/validated_test.py",
        )
    )

    yield

    # Cleanup handled by reset_function_registry in client fixture
