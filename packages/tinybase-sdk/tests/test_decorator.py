"""
Tests for the SDK decorator module.

Tests function registration, type conversion to JSON schema, and metadata extraction.
"""

from pydantic import BaseModel
from tinybase_sdk.decorator import _type_to_json_schema, get_registered_function, register


class TestTypeToJSONSchema:
    """Test type conversion to JSON Schema."""

    def test_string_type(self):
        """Test string type conversion."""
        schema = _type_to_json_schema(str)
        assert schema == {"type": "string"}

    def test_int_type(self):
        """Test integer type conversion."""
        schema = _type_to_json_schema(int)
        assert schema == {"type": "integer"}

    def test_float_type(self):
        """Test number type conversion."""
        schema = _type_to_json_schema(float)
        assert schema == {"type": "number"}

    def test_bool_type(self):
        """Test boolean type conversion."""
        schema = _type_to_json_schema(bool)
        assert schema == {"type": "boolean"}

    def test_dict_type(self):
        """Test dict type conversion."""
        schema = _type_to_json_schema(dict)
        assert schema == {"type": "object"}

    def test_list_type(self):
        """Test list type conversion."""
        schema = _type_to_json_schema(list)
        assert schema == {"type": "array"}

    def test_list_with_item_type(self):
        """Test list[str] type conversion."""
        from typing import get_args, get_origin

        list_type = list[str]
        origin = get_origin(list_type)
        args = get_args(list_type)
        assert origin is list
        assert args[0] is str

        schema = _type_to_json_schema(list_type)
        assert schema == {"type": "array", "items": {"type": "string"}}

    def test_dict_with_value_type(self):
        """Test dict[str, int] type conversion."""
        from typing import get_args, get_origin

        dict_type = dict[str, int]
        origin = get_origin(dict_type)
        args = get_args(dict_type)
        assert origin is dict
        assert args[0] is str
        assert args[1] is int

        schema = _type_to_json_schema(dict_type)
        assert schema == {
            "type": "object",
            "additionalProperties": {"type": "integer"},
        }

    def test_nested_types(self):
        """Test nested type conversion."""

        nested_type = list[dict[str, int]]
        schema = _type_to_json_schema(nested_type)
        assert schema == {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": {"type": "integer"},
            },
        }

    def test_unknown_type(self):
        """Test unknown type falls back to object."""

        class CustomType:
            pass

        schema = _type_to_json_schema(CustomType)
        assert schema == {"type": "object"}


class TestRegisterDecorator:
    """Test the @register decorator."""

    def test_register_basic_function(self):
        """Test registering a basic function with minimal metadata."""
        # Reset registry
        import tinybase_sdk.decorator as decorator_module

        decorator_module._registered_function = None

        @register(name="test_function")
        def test_func(client, payload: dict):
            return {"result": "ok"}

        func = get_registered_function()
        assert func is not None
        assert func["name"] == "test_function"
        assert func["description"] is None
        assert func["auth"] == "auth"
        assert func["tags"] == []
        assert func["callable"] == test_func

    def test_register_with_description(self):
        """Test registering with description."""
        import tinybase_sdk.decorator as decorator_module

        decorator_module._registered_function = None

        @register(name="test_func", description="A test function")
        def test_func(client, payload: dict):
            return {"result": "ok"}

        func = get_registered_function()
        assert func["description"] == "A test function"

    def test_register_with_auth_level(self):
        """Test registering with different auth levels."""
        import tinybase_sdk.decorator as decorator_module

        decorator_module._registered_function = None

        @register(name="public_func", auth="public")
        def public_func(client, payload: dict):
            return {"result": "ok"}

        func = get_registered_function()
        assert func["auth"] == "public"

        _registered_function = None

        @register(name="admin_func", auth="admin")
        def admin_func(client, payload: dict):
            return {"result": "ok"}

        func = get_registered_function()
        assert func["auth"] == "admin"

    def test_register_with_tags(self):
        """Test registering with tags."""
        import tinybase_sdk.decorator as decorator_module

        decorator_module._registered_function = None

        @register(name="test_func", tags=["test", "example"])
        def test_func(client, payload: dict):
            return {"result": "ok"}

        func = get_registered_function()
        assert func["tags"] == ["test", "example"]

    def test_register_with_basic_type_hints(self):
        """Test registering with basic type hints."""
        import tinybase_sdk.decorator as decorator_module

        decorator_module._registered_function = None

        @register(name="test_func")
        def test_func(client, payload: str) -> str:
            return "result"

        func = get_registered_function()
        assert func["input_schema"] == {"type": "string"}
        assert func["output_schema"] == {"type": "string"}

    def test_register_with_list_type_hints(self):
        """Test registering with list type hints."""
        import tinybase_sdk.decorator as decorator_module

        decorator_module._registered_function = None

        @register(name="test_func")
        def test_func(client, payload: list[str]) -> list[int]:
            return [1, 2, 3]

        func = get_registered_function()
        assert func["input_schema"] == {
            "type": "array",
            "items": {"type": "string"},
        }
        assert func["output_schema"] == {
            "type": "array",
            "items": {"type": "integer"},
        }

    def test_register_with_pydantic_model(self):
        """Test registering with Pydantic models."""
        import tinybase_sdk.decorator as decorator_module

        decorator_module._registered_function = None

        class InputModel(BaseModel):
            name: str
            age: int

        class OutputModel(BaseModel):
            result: str
            count: int

        @register(name="test_func")
        def test_func(client, payload: InputModel) -> OutputModel:
            return OutputModel(result="ok", count=1)

        func = get_registered_function()
        assert func["input_schema"] is not None
        assert "properties" in func["input_schema"]
        assert "name" in func["input_schema"]["properties"]
        assert "age" in func["input_schema"]["properties"]

        assert func["output_schema"] is not None
        assert "properties" in func["output_schema"]
        assert "result" in func["output_schema"]["properties"]
        assert "count" in func["output_schema"]["properties"]

    def test_register_with_no_input(self):
        """Test registering function with no input parameter."""
        import tinybase_sdk.decorator as decorator_module

        decorator_module._registered_function = None

        @register(name="test_func")
        def test_func(client) -> dict:
            return {"result": "ok"}

        func = get_registered_function()
        assert func["input_schema"] is None
        assert func["input_type"] is None

    def test_register_with_no_output_type_hint(self):
        """Test registering function with no return type hint."""
        import tinybase_sdk.decorator as decorator_module

        decorator_module._registered_function = None

        @register(name="test_func")
        def test_func(client, payload: dict):
            return {"result": "ok"}

        func = get_registered_function()
        assert func["output_schema"] is None

    def test_register_preserves_callable(self):
        """Test that the decorator preserves the original function."""
        import tinybase_sdk.decorator as decorator_module

        decorator_module._registered_function = None

        @register(name="test_func")
        def test_func(client, payload: dict):
            return {"result": "ok"}

        func = get_registered_function()
        assert func["callable"] == test_func
        # Can still call it directly
        result = test_func(None, {"test": "data"})
        assert result == {"result": "ok"}
