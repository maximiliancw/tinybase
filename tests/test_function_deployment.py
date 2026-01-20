"""
Tests for function deployment, validation, and versioning.
"""

import pytest
from sqlmodel import Session, select

from tinybase.functions.deployment import (
    FunctionValidationError,
    calculate_content_hash,
    get_or_create_version,
    validate_filename,
    validate_function_file,
)
from tests.utils import get_admin_token, get_user_token

# =============================================================================
# Validation Tests
# =============================================================================


def test_calculate_content_hash():
    """Test content hash calculation."""
    content1 = "hello world"
    content2 = "hello world"
    content3 = "different content"

    hash1 = calculate_content_hash(content1)
    hash2 = calculate_content_hash(content2)
    hash3 = calculate_content_hash(content3)

    # Same content should produce same hash
    assert hash1 == hash2
    # Different content should produce different hash
    assert hash1 != hash3
    # Hash should be 64 character hex string (SHA256)
    assert len(hash1) == 64
    assert all(c in "0123456789abcdef" for c in hash1)


def test_validate_filename_valid():
    """Test filename validation with valid names."""
    assert validate_filename("my_function.py") == "my_function"
    assert validate_filename("test123.py") == "test123"
    assert validate_filename("hello_world_v2.py") == "hello_world_v2"


def test_validate_filename_invalid_extension():
    """Test filename validation rejects non-.py files."""
    with pytest.raises(FunctionValidationError, match="must end with .py"):
        validate_filename("myfile.txt")


def test_validate_filename_path_traversal():
    """Test filename validation rejects path traversal."""
    with pytest.raises(FunctionValidationError, match="path traversal"):
        validate_filename("../evil.py")

    with pytest.raises(FunctionValidationError, match="path traversal"):
        validate_filename("foo/bar.py")


def test_validate_filename_invalid_identifier():
    """Test filename validation rejects invalid Python identifiers."""
    with pytest.raises(FunctionValidationError, match="valid Python identifier"):
        validate_filename("123invalid.py")

    with pytest.raises(FunctionValidationError, match="valid Python identifier"):
        validate_filename("my-function.py")


def test_validate_filename_reserved_names():
    """Test filename validation rejects reserved names."""
    with pytest.raises(FunctionValidationError, match="reserved"):
        validate_filename("__init__.py")

    with pytest.raises(FunctionValidationError, match="reserved"):
        validate_filename("test.py")


def test_validate_function_file_valid():
    """Test full validation of a valid function file."""
    content = """# /// script
# dependencies = ["tinybase-sdk"]
# ///

from pydantic import BaseModel
from tinybase_sdk import register

class MyInput(BaseModel):
    value: str

class MyOutput(BaseModel):
    result: str

@register(name="test_func", description="Test function")
def test_func(client, payload: MyInput) -> MyOutput:
    return MyOutput(result=f"Got: {payload.value}")
"""

    function_name, warnings = validate_function_file("test_func.py", content)
    assert function_name == "test_func"
    assert isinstance(warnings, list)


def test_validate_function_file_missing_sdk_import():
    """Test validation fails without SDK import."""
    content = """
def my_func():
    pass
"""

    with pytest.raises(FunctionValidationError, match="must import tinybase_sdk"):
        validate_function_file("my_func.py", content)


def test_validate_function_file_missing_register():
    """Test validation fails without @register decorator."""
    content = """
import tinybase_sdk

def my_func():
    pass
"""

    with pytest.raises(FunctionValidationError, match="must contain @register decorator"):
        validate_function_file("my_func.py", content)


def test_validate_function_file_name_mismatch():
    """Test validation fails when function name doesn't match filename."""
    content = """
from tinybase_sdk import register

@register(name="wrong_name")
def my_func(client, payload):
    pass
"""

    with pytest.raises(FunctionValidationError, match="must match filename"):
        validate_function_file("my_func.py", content)


def test_validate_function_file_syntax_error():
    """Test validation fails with invalid Python syntax."""
    content = """
from tinybase_sdk import register

@register(name="my_func")
def my_func(client, payload):
    invalid syntax here!!!
"""

    with pytest.raises(FunctionValidationError, match="Invalid Python syntax"):
        validate_function_file("my_func.py", content)


def test_validate_function_file_dangerous_imports():
    """Test dangerous import detection."""
    content = """
from tinybase_sdk import register
import subprocess
import eval

@register(name="test_func")
def test_func(client, payload):
    subprocess.run(["ls"])
    eval("print('dangerous')")
    return {}
"""

    function_name, warnings = validate_function_file("test_func.py", content)
    assert function_name == "test_func"
    # Should have warnings for subprocess and eval
    assert len(warnings) > 0
    assert any("subprocess" in w.lower() for w in warnings)


def test_validate_function_file_size_limit():
    """Test file size validation."""
    # Create a large content string
    large_content = "x" * (2 * 1024 * 1024)  # 2MB

    with pytest.raises(FunctionValidationError, match="exceeds maximum"):
        validate_function_file("large_file.py", large_content, max_size_bytes=1048576)  # 1MB limit


# =============================================================================
# Version Management Tests
# =============================================================================


def test_get_or_create_version_new(client):
    """Test creating a new function version."""
    from tinybase.db.core import get_engine
    from tinybase.db.models import User

    engine = get_engine()
    with Session(engine) as session:
        # Get the admin user created by the client fixture
        stmt = select(User).where(User.email == "admin@test.com")
        admin = session.exec(stmt).first()
        assert admin is not None

        version, is_new = get_or_create_version(
            session,
            function_name="test_func",
            content_hash="abc123",
            file_size=1000,
            deployed_by_user_id=admin.id,
            notes="Initial deployment",
        )

        assert is_new is True
        assert version.function_name == "test_func"
        assert version.content_hash == "abc123"
        assert version.file_size == 1000
        assert version.deployed_by_user_id == admin.id
        assert version.notes == "Initial deployment"


def test_get_or_create_version_existing(client):
    """Test getting an existing function version."""
    from tinybase.db.core import get_engine
    from tinybase.db.models import User

    engine = get_engine()
    with Session(engine) as session:
        admin = session.query(User).filter_by(email="admin@test.com").first()

        # Create first version
        version1, is_new1 = get_or_create_version(
            session,
            function_name="test_func_existing",
            content_hash="abc123",
            file_size=1000,
            deployed_by_user_id=admin.id,
        )

        assert is_new1 is True

        # Try to create same version again
        version2, is_new2 = get_or_create_version(
            session,
            function_name="test_func_existing",
            content_hash="abc123",
            file_size=1000,
            deployed_by_user_id=admin.id,
        )

        assert is_new2 is False
        assert version1.id == version2.id


def test_get_or_create_version_different_hash(client):
    """Test creating a new version with different content hash."""
    from tinybase.db.core import get_engine
    from tinybase.db.models import User

    engine = get_engine()
    with Session(engine) as session:
        stmt = select(User).where(User.email == "admin@test.com")
        admin = session.exec(stmt).first()

        # Create first version
        version1, is_new1 = get_or_create_version(
            session,
            function_name="test_func_diff",
            content_hash="abc123",
            file_size=1000,
            deployed_by_user_id=admin.id,
        )

        # Create second version with different hash
        version2, is_new2 = get_or_create_version(
            session,
            function_name="test_func_diff",
            content_hash="def456",
            file_size=1200,
            deployed_by_user_id=admin.id,
        )

        assert is_new1 is True
        assert is_new2 is True
        assert version1.id != version2.id
        assert version1.content_hash != version2.content_hash


# =============================================================================
# API Endpoint Tests
# =============================================================================


def test_upload_function_valid(client):
    """Test uploading a valid function via API."""
    admin_token = get_admin_token(client)

    function_content = """# /// script
# dependencies = ["tinybase-sdk"]
# ///

from pydantic import BaseModel
from tinybase_sdk import register

class TestInput(BaseModel):
    value: str

class TestOutput(BaseModel):
    result: str

@register(name="api_test", description="API test function", auth="auth")
def api_test(client, payload: TestInput) -> TestOutput:
    return TestOutput(result=f"Got: {payload.value}")
"""

    response = client.post(
        "/api/admin/functions/upload",
        json={"filename": "api_test.py", "content": function_content, "notes": "Test upload"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["function_name"] == "api_test"
    assert data["is_new_version"] is True
    assert "version_id" in data
    assert "content_hash" in data
    assert isinstance(data["warnings"], list)


def test_upload_function_invalid_syntax(client):
    """Test uploading a function with invalid syntax."""
    admin_token = get_admin_token(client)

    function_content = """
from tinybase_sdk import register

@register(name="bad_func")
def bad_func(client, payload):
    this is not valid python!!!
"""

    response = client.post(
        "/api/admin/functions/upload",
        json={"filename": "bad_func.py", "content": function_content},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 400
    assert "syntax" in response.json()["detail"].lower()


def test_upload_function_name_mismatch(client):
    """Test uploading a function where name doesn't match filename."""
    admin_token = get_admin_token(client)

    function_content = """
from tinybase_sdk import register

@register(name="wrong_name")
def func(client, payload):
    return {}
"""

    response = client.post(
        "/api/admin/functions/upload",
        json={"filename": "correct_name.py", "content": function_content},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 400
    assert "must match filename" in response.json()["detail"]


def test_upload_function_idempotent(client):
    """Test that uploading the same function twice is idempotent."""
    admin_token = get_admin_token(client)

    function_content = """# /// script
# dependencies = ["tinybase-sdk"]
# ///

from tinybase_sdk import register

@register(name="idempotent_test")
def idempotent_test(client, payload):
    return {"result": "ok"}
"""

    # First upload
    response1 = client.post(
        "/api/admin/functions/upload",
        json={"filename": "idempotent_test.py", "content": function_content},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["is_new_version"] is True

    # Second upload (same content)
    response2 = client.post(
        "/api/admin/functions/upload",
        json={"filename": "idempotent_test.py", "content": function_content},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["is_new_version"] is False
    assert data2["version_id"] == data1["version_id"]


def test_list_function_versions(client):
    """Test listing function versions."""
    admin_token = get_admin_token(client)

    # Upload a function
    function_content = """# /// script
# dependencies = ["tinybase-sdk"]
# ///

from tinybase_sdk import register

@register(name="versioned_func")
def versioned_func(client, payload):
    return {"result": "v1"}
"""

    client.post(
        "/api/admin/functions/upload",
        json={"filename": "versioned_func.py", "content": function_content},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # List versions
    response = client.get(
        "/api/admin/functions/versioned_func/versions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    versions = response.json()
    assert len(versions) >= 1
    assert versions[0]["function_name"] == "versioned_func"
    assert "content_hash" in versions[0]
    assert "deployed_at" in versions[0]


def test_batch_upload(client):
    """Test batch upload of multiple functions."""
    admin_token = get_admin_token(client)

    func1 = """# /// script
# dependencies = ["tinybase-sdk"]
# ///

from tinybase_sdk import register

@register(name="batch_func1")
def batch_func1(client, payload):
    return {"result": "1"}
"""

    func2 = """# /// script
# dependencies = ["tinybase-sdk"]
# ///

from tinybase_sdk import register

@register(name="batch_func2")
def batch_func2(client, payload):
    return {"result": "2"}
"""

    response = client.post(
        "/api/admin/functions/upload-batch",
        json={
            "functions": [
                {"filename": "batch_func1.py", "content": func1},
                {"filename": "batch_func2.py", "content": func2},
            ]
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 2
    assert results[0]["function_name"] == "batch_func1"
    assert results[1]["function_name"] == "batch_func2"


def test_upload_requires_admin(client):
    """Test that function upload requires admin privileges."""
    # Get regular user token
    user_token = get_user_token(client)

    function_content = """
from tinybase_sdk import register

@register(name="test")
def test(client, payload):
    return {}
"""

    response = client.post(
        "/api/admin/functions/upload",
        json={"filename": "test.py", "content": function_content},
        headers={"Authorization": f"Bearer {user_token}"},
    )

    # Should be forbidden (403) or unauthorized (401)
    assert response.status_code in [401, 403]
