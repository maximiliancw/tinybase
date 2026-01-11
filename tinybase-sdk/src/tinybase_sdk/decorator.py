"""Function registration decorator for TinyBase SDK."""

import inspect
from typing import Any, Callable, get_args, get_origin, get_type_hints

# Global registry for this script
_registered_function: dict | None = None


def _type_to_json_schema(python_type: type) -> dict:
    """Convert Python type hints to JSON Schema."""
    origin = get_origin(python_type)
    args = get_args(python_type)

    if origin is dict:
        # dict[str, int] -> {"type": "object", "additionalProperties": {"type": "integer"}}
        key_type, value_type = args if args else (str, Any)
        return {
            "type": "object",
            "additionalProperties": _type_to_json_schema(value_type),
        }
    elif origin is list:
        # list[str] -> {"type": "array", "items": {"type": "string"}}
        item_type = args[0] if args else Any
        return {
            "type": "array",
            "items": _type_to_json_schema(item_type),
        }
    elif python_type is str:
        return {"type": "string"}
    elif python_type is int:
        return {"type": "integer"}
    elif python_type is float:
        return {"type": "number"}
    elif python_type is bool:
        return {"type": "boolean"}
    elif python_type is dict:
        return {"type": "object"}
    elif python_type is list:
        return {"type": "array"}
    else:
        # Fallback for unknown types
        return {"type": "object"}


def register(
    name: str,
    description: str | None = None,
    auth: str = "auth",
    tags: list[str] | None = None,
):
    """Register a function with metadata."""

    def decorator(func: Callable) -> Callable:
        global _registered_function

        # Extract input/output models from type hints
        hints = get_type_hints(func)

        # Get input: could be a Pydantic model, dict, or basic type
        # Function signature: func(client: Client, payload: Type) or func(client: Client, arg: Type)
        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        if len(params) >= 2:  # client + payload/args
            input_type = hints.get(params[1].name)
        else:
            input_type = None

        output_model = hints.get("return")

        # Generate JSON schema from type hints
        # Pydantic models have model_json_schema(), basic types need conversion
        input_schema = None
        if input_type:
            if hasattr(input_type, "model_json_schema"):
                # Pydantic model
                input_schema = input_type.model_json_schema()
            else:
                # Basic type - convert to JSON schema
                input_schema = _type_to_json_schema(input_type)

        output_schema = None
        if output_model:
            if hasattr(output_model, "model_json_schema"):
                # Pydantic model
                output_schema = output_model.model_json_schema()
            else:
                # Basic type - convert to JSON schema
                output_schema = _type_to_json_schema(output_model)

        _registered_function = {
            "name": name,
            "description": description,
            "auth": auth,
            "tags": tags or [],
            "input_schema": input_schema,
            "output_schema": output_schema,
            "callable": func,
            "input_type": input_type,  # Keep original type for validation
            "output_type": output_model,
        }
        return func

    return decorator


def get_registered_function() -> dict | None:
    """Get the registered function metadata."""
    return _registered_function
