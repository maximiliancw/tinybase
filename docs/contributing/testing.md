# Testing Guide

This guide covers writing and running tests for TinyBase.

## Test Stack

- **pytest** - Test framework
- **pytest-asyncio** - Async test support
- **httpx** - HTTP client for API tests

## Running Tests

### All Tests

```bash
pytest
```

### With Coverage

```bash
pytest --cov=tinybase --cov-report=html
```

Coverage report is generated in `htmlcov/`.

### Specific Tests

```bash
# Run a specific file
pytest tests/test_functions.py

# Run a specific test
pytest tests/test_functions.py::test_register_function

# Run tests matching a pattern
pytest -k "test_auth"

# Run with verbose output
pytest -v
```

### Watch Mode

```bash
# Using pytest-watch (install separately)
ptw -- tests/
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures
├── test_access_control.py
├── test_basic.py
├── test_collections.py
├── test_function_execution.py     # Function execution via subprocess
├── test_function_integration.py   # End-to-end function workflows
├── test_function_loader.py        # Function metadata extraction
├── test_function_pool.py          # Cold start optimization
├── test_functions.py              # Basic function tests
├── test_internal_tokens.py        # Internal token generation
└── test_settings.py

tinybase-sdk/tests/                # SDK package tests
├── __init__.py
├── test_cli.py                    # CLI runner tests
├── test_context.py                # Context dataclass tests
├── test_decorator.py              # Decorator and type conversion tests
└── test_logging.py                # Structured logging tests
```

## Fixtures

Common fixtures are defined in `conftest.py`:

```python title="tests/conftest.py"
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel

from tinybase.api.app import create_app
from tinybase.db.models import User


@pytest.fixture
def engine():
    """Create an in-memory SQLite database."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create a database session."""
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(engine):
    """Create a test client."""
    app = create_app()
    # Override database dependency
    def get_test_session():
        with Session(engine) as session:
            yield session
    
    app.dependency_overrides[get_session] = get_test_session
    return TestClient(app)


@pytest.fixture
def admin_user(session):
    """Create an admin user."""
    from tinybase.auth import hash_password
    
    user = User(
        email="admin@test.com",
        password_hash=hash_password("password"),
        is_admin=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def auth_headers(client, admin_user):
    """Get auth headers for admin user."""
    response = client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "password",
    })
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}
```

## Writing Tests

### Unit Tests

Test individual functions/methods in isolation:

```python
"""Unit tests for authentication."""

from tinybase.auth import hash_password, verify_password


class TestPasswordHashing:
    """Tests for password hashing functions."""
    
    def test_hash_password_returns_hash(self):
        """Test that hash_password returns a hash."""
        password = "testpassword123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
    
    def test_verify_password_correct(self):
        """Test verifying correct password."""
        password = "testpassword123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        hashed = hash_password("correctpassword")
        
        assert verify_password("wrongpassword", hashed) is False
```

### Integration Tests

Test components working together:

```python
"""Integration tests for collection service."""

from tinybase.collections.service import CollectionService


class TestCollectionService:
    """Tests for CollectionService."""
    
    def test_create_and_list_collection(self, session):
        """Test creating and listing collections."""
        service = CollectionService(session)
        
        # Create collection
        schema = {"fields": [{"name": "title", "type": "string"}]}
        collection = service.create_collection(
            name="posts",
            label="Blog Posts",
            schema=schema,
        )
        
        assert collection.name == "posts"
        assert collection.label == "Blog Posts"
        
        # List collections
        collections = service.list_collections()
        assert len(collections) == 1
        assert collections[0].name == "posts"
    
    def test_create_record_with_validation(self, session):
        """Test that records are validated against schema."""
        service = CollectionService(session)
        
        # Create collection with required field
        schema = {
            "fields": [
                {"name": "title", "type": "string", "required": True}
            ]
        }
        collection = service.create_collection(
            name="posts",
            label="Posts",
            schema=schema,
        )
        
        # Valid record
        record = service.create_record(collection, {"title": "Test"})
        assert record.data["title"] == "Test"
        
        # Invalid record (missing required field)
        with pytest.raises(Exception):  # ValidationError
            service.create_record(collection, {})
```

### API Tests

Test HTTP endpoints:

```python
"""API tests for authentication."""


class TestAuthAPI:
    """Tests for authentication endpoints."""
    
    def test_register_user(self, client):
        """Test user registration."""
        response = client.post("/api/auth/register", json={
            "email": "new@test.com",
            "password": "testpassword123",
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new@test.com"
        assert data["is_admin"] is False
    
    def test_register_duplicate_email(self, client):
        """Test registration with existing email."""
        # Register first user
        client.post("/api/auth/register", json={
            "email": "test@test.com",
            "password": "password",
        })
        
        # Try to register same email
        response = client.post("/api/auth/register", json={
            "email": "test@test.com",
            "password": "password",
        })
        
        assert response.status_code == 400
    
    def test_login_success(self, client, admin_user):
        """Test successful login."""
        response = client.post("/api/auth/login", json={
            "email": "admin@test.com",
            "password": "password",
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == "admin@test.com"
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post("/api/auth/login", json={
            "email": "nobody@test.com",
            "password": "wrongpassword",
        })
        
        assert response.status_code == 401
    
    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token."""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 401
    
    def test_protected_endpoint_with_token(self, client, auth_headers):
        """Test accessing protected endpoint with valid token."""
        response = client.get("/api/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["email"] == "admin@test.com"
```

### Function Tests

Test registered functions using the SDK:

```python
"""Tests for function execution."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from tinybase.functions.core import FunctionMeta, execute_function
from tinybase.utils import AuthLevel, TriggerType


class TestFunctionExecution:
    """Tests for function execution."""
    
    def test_execute_function_success(self, session):
        """Test successful function execution."""
        # Create a temporary function file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            function_code = """# /// script
# dependencies = ["tinybase-sdk"]
# ///
from tinybase_sdk import register
from tinybase_sdk.cli import run

@register(name="test_function")
def test_func(client, payload: dict) -> dict:
    return {"result": payload.get("value", 0) * 2}

if __name__ == "__main__":
    run()
"""
            f.write(function_code)
            f.flush()
            function_file = Path(f.name)
        
        try:
            meta = FunctionMeta(
                name="test_function",
                auth=AuthLevel.AUTH,
                file_path=str(function_file),
            )
            
            result = execute_function(
                meta=meta,
                payload={"value": 5},
                session=session,
            )
            
            assert result.status == FunctionCallStatus.SUCCEEDED
            assert result.result["result"] == 10
        finally:
            function_file.unlink()
```

### SDK Tests

Test the TinyBase SDK components:

```python
"""Tests for SDK decorator."""

from pydantic import BaseModel
from tinybase_sdk.decorator import get_registered_function, register


class TestDecorator:
    """Test the @register decorator."""
    
    def test_register_basic_function(self):
        """Test registering a basic function."""
        import tinybase_sdk.decorator as decorator_module
        decorator_module._registered_function = None
        
        @register(name="test_function")
        def test_func(client, payload: dict) -> dict:
            return {"result": "ok"}
        
        func = get_registered_function()
        assert func["name"] == "test_function"
        assert func["input_schema"] is not None
```

## Testing Patterns

### Parametrized Tests

Test multiple cases efficiently:

```python
import pytest


@pytest.mark.parametrize("email,valid", [
    ("user@example.com", True),
    ("user@domain.co.uk", True),
    ("invalid-email", False),
    ("@nodomain.com", False),
    ("", False),
])
def test_email_validation(email, valid):
    """Test email validation with various inputs."""
    result = is_valid_email(email)
    assert result == valid
```

### Async Tests

For async functions:

```python
import pytest


@pytest.mark.asyncio
async def test_async_operation():
    """Test an async function."""
    result = await some_async_function()
    assert result == expected
```

### Mocking

Mock external services:

```python
from unittest.mock import patch, MagicMock


def test_send_email(session):
    """Test email sending is called."""
    with patch("tinybase.notifications.send_email") as mock_send:
        mock_send.return_value = True
        
        # Trigger code that sends email
        create_user("test@example.com")
        
        mock_send.assert_called_once_with(
            to="test@example.com",
            subject="Welcome!",
        )
```

### Testing Exceptions

```python
import pytest


def test_invalid_input_raises():
    """Test that invalid input raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        process_data(invalid_data)
    
    assert "Invalid format" in str(exc_info.value)
```

## Test Configuration

### pytest.ini Options

In `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
filterwarnings = [
    "ignore::DeprecationWarning",
]
```

### Markers

Define custom markers:

```python
# conftest.py
def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: integration tests")
```

Use markers:

```python
@pytest.mark.slow
def test_large_dataset():
    ...

@pytest.mark.integration
def test_external_api():
    ...
```

Run specific markers:

```bash
pytest -m "not slow"
pytest -m integration
```

## Best Practices

### 1. Test Isolation

Each test should be independent:

```python
# Good - creates its own data
def test_update_user(session):
    user = create_test_user(session)
    update_user(user.id, {"name": "New Name"})
    assert user.name == "New Name"

# Bad - depends on other tests
def test_update_user(session):
    # Assumes user from previous test exists
    update_user(1, {"name": "New Name"})
```

### 2. Descriptive Names

```python
# Good
def test_login_with_expired_token_returns_401():
    ...

# Bad
def test_login_4():
    ...
```

### 3. Arrange-Act-Assert

```python
def test_create_record():
    # Arrange
    collection = create_collection("posts", schema)
    data = {"title": "Test Post"}
    
    # Act
    record = service.create_record(collection, data)
    
    # Assert
    assert record.data["title"] == "Test Post"
    assert record.collection_id == collection.id
```

### 4. Test Edge Cases

```python
class TestPagination:
    def test_first_page(self): ...
    def test_last_page(self): ...
    def test_empty_result(self): ...
    def test_single_item(self): ...
    def test_exactly_page_size(self): ...
    def test_page_beyond_results(self): ...
```

## Test Performance

TinyBase includes optimizations for fast test execution. The test suite of ~265 tests can run in approximately **1-2 minutes** with parallel execution.

### Quick Commands

```bash
# Full parallel suite (recommended)
uv run pytest -n auto

# Fast dev loop - only last failed tests
uv run pytest --lf

# Failed first, then rest
uv run pytest --ff

# Stop on first failure (quick sanity check)
uv run pytest -x -n auto

# Skip slow tests during development
uv run pytest -m "not slow"

# Change-based testing (runs only tests affected by changes)
uv run pytest --testmon
```

### Performance Comparison

| Command | Description | Typical Time |
|---------|-------------|--------------|
| `pytest` | Serial execution | ~15-19 min |
| `pytest -n auto` | Parallel execution | ~1-2 min |
| `pytest --lf` | Last failed only | seconds |
| `pytest --testmon` | Change-based | seconds |

### Test Markers

Tests can be categorized with markers:

```python
@pytest.mark.slow
def test_long_running_operation():
    """Tests marked slow can be skipped during rapid iteration."""
    ...

@pytest.mark.integration
def test_external_service():
    """Integration tests that may require external services."""
    ...
```

Run or skip by marker:

```bash
# Skip slow tests
pytest -m "not slow"

# Run only integration tests
pytest -m integration

# Run everything except slow and integration
pytest -m "not slow and not integration"
```

### Parallel Execution

The test suite uses `pytest-xdist` for parallel execution:

```bash
# Auto-detect CPU cores
pytest -n auto

# Specific number of workers
pytest -n 4

# With coverage
pytest -n auto --cov=tinybase
```

**Note**: All tests are isolated and safe for parallel execution. Each test gets:

- Unique temporary workspace directory
- Isolated database instance
- Reset global state (settings, registries, pools)

### Change-Based Testing with testmon

`pytest-testmon` tracks which tests depend on which source files:

```bash
# First run - builds dependency database
uv run pytest --testmon

# Subsequent runs - only runs affected tests
uv run pytest --testmon
```

The `.testmondata` file stores the dependency information and should be added to `.gitignore`.

## See Also

- [Development Setup](development.md)
- [Architecture](architecture.md)
- [Code Style](code-style.md)

