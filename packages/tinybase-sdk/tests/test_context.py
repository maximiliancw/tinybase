"""
Tests for the SDK context module.

Tests FunctionContext dataclass.
"""

from uuid import UUID, uuid4

from tinybase_sdk.context import FunctionContext


class TestFunctionContext:
    """Test FunctionContext dataclass."""

    def test_context_creation(self):
        """Test creating a FunctionContext."""
        request_id = uuid4()
        context = FunctionContext(
            api_base_url="http://localhost:8000/api",
            auth_token="test-token",
            user_id=uuid4(),
            is_admin=False,
            request_id=request_id,
            function_name="test_func",
        )

        assert context.api_base_url == "http://localhost:8000/api"
        assert context.auth_token == "test-token"
        assert isinstance(context.user_id, UUID)
        assert context.is_admin is False
        assert context.request_id == request_id
        assert context.function_name == "test_func"

    def test_context_with_none_user_id(self):
        """Test creating a context with None user_id."""
        request_id = uuid4()
        context = FunctionContext(
            api_base_url="http://localhost:8000/api",
            auth_token="test-token",
            user_id=None,
            is_admin=False,
            request_id=request_id,
            function_name="test_func",
        )

        assert context.user_id is None

    def test_context_admin_user(self):
        """Test creating a context for admin user."""
        request_id = uuid4()
        context = FunctionContext(
            api_base_url="http://localhost:8000/api",
            auth_token="test-token",
            user_id=uuid4(),
            is_admin=True,
            request_id=request_id,
            function_name="test_func",
        )

        assert context.is_admin is True
