"""
Collection schema management and dynamic Pydantic model generation.

This module handles:
- Parsing collection schema JSON
- Building Pydantic models from schemas
- Managing a registry of collection models
"""

from typing import Any

from pydantic import BaseModel, Field, create_model
from pydantic.fields import FieldInfo

# =============================================================================
# Schema Field Types
# =============================================================================

# Mapping from schema type strings to Python types
TYPE_MAPPING: dict[str, type] = {
    "string": str,
    "int": int,
    "integer": int,
    "float": float,
    "number": float,
    "bool": bool,
    "boolean": bool,
    "list[string]": list[str],
    "list[int]": list[int],
    "list[float]": list[float],
    "list[bool]": list[bool],
    "dict": dict,
    "object": dict,
}


# =============================================================================
# Schema Definition Models
# =============================================================================


class FieldDefinition(BaseModel):
    """
    Definition of a single field in a collection schema.

    Attributes:
        name: Field name (must be valid Python identifier)
        type: Field type (string, int, float, bool, list[string], etc.)
        required: Whether the field is required
        default: Default value if not provided
        min_length: Minimum string length
        max_length: Maximum string length
        min: Minimum numeric value
        max: Maximum numeric value
        pattern: Regex pattern for string validation
        description: Human-readable field description
    """

    name: str = Field(description="Field name")
    type: str = Field(default="string", description="Field type")
    required: bool = Field(default=False, description="Whether field is required")
    default: Any = Field(default=None, description="Default value")
    min_length: int | None = Field(default=None, description="Min string length")
    max_length: int | None = Field(default=None, description="Max string length")
    min: float | int | None = Field(default=None, description="Min numeric value")
    max: float | int | None = Field(default=None, description="Max numeric value")
    pattern: str | None = Field(default=None, description="Regex pattern")
    description: str | None = Field(default=None, description="Field description")


class CollectionSchema(BaseModel):
    """
    Complete schema definition for a collection.

    Attributes:
        fields: List of field definitions
    """

    fields: list[FieldDefinition] = Field(
        default_factory=list, description="List of field definitions"
    )


# =============================================================================
# Dynamic Model Generation
# =============================================================================


def build_field_info(field_def: FieldDefinition) -> tuple[type, FieldInfo]:
    """
    Build a Pydantic field type and FieldInfo from a field definition.

    Args:
        field_def: The field definition.

    Returns:
        Tuple of (python_type, FieldInfo) for use with create_model.
    """
    # Get the Python type
    python_type = TYPE_MAPPING.get(field_def.type.lower(), str)

    # Build field constraints
    field_kwargs: dict[str, Any] = {}

    if field_def.description:
        field_kwargs["description"] = field_def.description

    # Handle default value
    if not field_def.required:
        if field_def.default is not None:
            field_kwargs["default"] = field_def.default
        else:
            # Set appropriate default based on type
            if field_def.type.startswith("list"):
                field_kwargs["default_factory"] = list
            elif field_def.type in ("dict", "object"):
                field_kwargs["default_factory"] = dict
            else:
                field_kwargs["default"] = None
                # Make the type optional
                python_type = python_type | None  # type: ignore

    # String constraints
    if field_def.min_length is not None:
        field_kwargs["min_length"] = field_def.min_length
    if field_def.max_length is not None:
        field_kwargs["max_length"] = field_def.max_length
    if field_def.pattern is not None:
        field_kwargs["pattern"] = field_def.pattern

    # Numeric constraints
    if field_def.min is not None:
        field_kwargs["ge"] = field_def.min
    if field_def.max is not None:
        field_kwargs["le"] = field_def.max

    return python_type, Field(**field_kwargs)


def build_pydantic_model_from_schema(
    collection_name: str,
    schema_dict: dict[str, Any],
    base_class: type[BaseModel] = BaseModel,
) -> type[BaseModel]:
    """
    Build a Pydantic model from a collection schema dictionary.

    Args:
        collection_name: Name of the collection (used in model class name)
        schema_dict: Schema dictionary with "fields" key
        base_class: Base class for the generated model

    Returns:
        A dynamically created Pydantic model class.

    Example:
        schema = {
            "fields": [
                {"name": "title", "type": "string", "required": True, "max_length": 200},
                {"name": "published", "type": "boolean", "default": False}
            ]
        }
        model = build_pydantic_model_from_schema("posts", schema)
        # model is now a Pydantic model with title and published fields
    """
    # Parse schema
    collection_schema = CollectionSchema.model_validate(schema_dict)

    # Build field definitions for create_model
    field_definitions: dict[str, tuple[type, FieldInfo]] = {}

    for field_def in collection_schema.fields:
        python_type, field_info = build_field_info(field_def)
        field_definitions[field_def.name] = (python_type, field_info)

    # Create model name from collection name (CamelCase)
    model_name = "".join(word.capitalize() for word in collection_name.split("_")) + "Data"

    # Create the dynamic model
    return create_model(
        model_name,
        __base__=base_class,
        **field_definitions,  # type: ignore
    )


# =============================================================================
# Collection Model Registry
# =============================================================================


class CollectionModelRegistry:
    """
    Registry for collection Pydantic models.

    Maintains a mapping from collection names to their dynamically generated
    Pydantic models for use in validation and OpenAPI documentation.
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._models: dict[str, type[BaseModel]] = {}

    def register(self, name: str, model: type[BaseModel]) -> None:
        """
        Register a model for a collection.

        Args:
            name: Collection name
            model: Pydantic model class
        """
        self._models[name] = model

    def get(self, name: str) -> type[BaseModel] | None:
        """
        Get the model for a collection.

        Args:
            name: Collection name

        Returns:
            The registered Pydantic model, or None if not found.
        """
        return self._models.get(name)

    def unregister(self, name: str) -> None:
        """
        Remove a collection's model from the registry.

        Args:
            name: Collection name to remove
        """
        self._models.pop(name, None)

    def all(self) -> dict[str, type[BaseModel]]:
        """
        Get all registered models.

        Returns:
            Dictionary mapping collection names to models.
        """
        return self._models.copy()

    def clear(self) -> None:
        """Clear all registered models."""
        self._models.clear()


# Global registry instance
_registry: CollectionModelRegistry | None = None


def get_registry() -> CollectionModelRegistry:
    """Get the global collection model registry."""
    global _registry
    if _registry is None:
        _registry = CollectionModelRegistry()
    return _registry


def reset_registry() -> None:
    """Reset the global registry (primarily for testing)."""
    global _registry
    if _registry is not None:
        _registry.clear()
    _registry = None
