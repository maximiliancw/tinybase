"""
Collection schema management and dynamic Pydantic model generation.

This module handles:
- Parsing collection schema JSON
- Building Pydantic models from schemas
- Managing a registry of collection models
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, create_model, model_validator
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
    "list": list,
    "array": list,
    "list[string]": list[str],
    "list[int]": list[int],
    "list[float]": list[float],
    "list[bool]": list[bool],
    "dict": dict,
    "object": dict,
    "date": datetime,
    "datetime": datetime,
    "reference": str,  # Stores UUID string pointing to another collection's record
}


# =============================================================================
# Schema Definition Models
# =============================================================================


class FieldDefinition(BaseModel):
    """
    Definition of a single field in a collection schema.

    Attributes:
        name: Field name (must be valid Python identifier)
        type: Field type (string, number, boolean, object, array, date, reference)
        required: Whether the field is required
        unique: Whether field values must be unique within the collection
        default: Default value if not provided
        min_length: Minimum string length (string type only)
        max_length: Maximum string length (string type only)
        min: Minimum numeric value (number type only)
        max: Maximum numeric value (number type only)
        pattern: Regex pattern for string validation (string type only)
        description: Human-readable field description
        collection: Target collection name for reference fields (reference type only)
    """

    name: str = Field(description="Field name")
    type: str = Field(default="string", description="Field type")
    required: bool = Field(default=False, description="Whether field is required")
    unique: bool = Field(default=False, description="Whether field values must be unique")
    default: Any = Field(default=None, description="Default value")
    min_length: int | None = Field(default=None, description="Min string length")
    max_length: int | None = Field(default=None, description="Max string length")
    min: float | int | None = Field(default=None, description="Min numeric value")
    max: float | int | None = Field(default=None, description="Max numeric value")
    pattern: str | None = Field(default=None, description="Regex pattern")
    description: str | None = Field(default=None, description="Field description")
    collection: str | None = Field(
        default=None, description="Target collection name for reference fields"
    )

    @model_validator(mode="after")
    def validate_type_specific_properties(self) -> "FieldDefinition":
        """Validate that field properties are appropriate for the field type."""
        numeric_types = {"int", "integer", "float", "number"}
        string_types = {"string"}
        complex_types = {"object", "array", "dict", "list"}

        # min/max only for numeric types
        if self.min is not None or self.max is not None:
            if self.type.lower() not in numeric_types:
                raise ValueError(
                    f"min/max can only be used with numeric types "
                    f"(int, integer, float, number), not '{self.type}'"
                )

        # min_length/max_length/pattern only for string type
        if self.min_length is not None or self.max_length is not None or self.pattern:
            if self.type.lower() not in string_types:
                raise ValueError(
                    f"min_length/max_length/pattern can only be used with "
                    f"string type, not '{self.type}'"
                )

        # unique cannot be used with complex types
        if self.unique and self.type.lower() in complex_types:
            raise ValueError(
                f"unique cannot be used with '{self.type}' type "
                f"(complex types require deep comparison)"
            )

        # reference type requires collection property
        if self.type.lower() == "reference" and not self.collection:
            raise ValueError("reference type requires 'collection' property specifying target collection")

        # collection property only valid for reference type
        if self.collection and self.type.lower() != "reference":
            raise ValueError(
                f"'collection' property can only be used with reference type, not '{self.type}'"
            )

        return self


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

    Note:
        Pydantic handles all validation via Field() constraints:
        - ge/le for min/max (numeric)
        - min_length/max_length for string length
        - pattern for regex validation
        - default/default_factory for defaults
    """
    field_type_lower = field_def.type.lower()

    # Get the Python type from mapping
    python_type = TYPE_MAPPING.get(field_type_lower, str)

    # Build field constraints - Pydantic does the heavy lifting
    field_kwargs: dict[str, Any] = {}

    if field_def.description:
        field_kwargs["description"] = field_def.description

    # Handle default value
    if not field_def.required:
        if field_def.default is not None:
            field_kwargs["default"] = field_def.default
        else:
            # Set appropriate default based on type
            if field_type_lower in ("list", "array") or field_type_lower.startswith("list["):
                field_kwargs["default_factory"] = list
            elif field_type_lower in ("dict", "object"):
                field_kwargs["default_factory"] = dict
            else:
                field_kwargs["default"] = None
                # Make the type optional
                python_type = python_type | None  # type: ignore

    # String constraints - Pydantic validates these automatically
    if field_def.min_length is not None:
        field_kwargs["min_length"] = field_def.min_length
    if field_def.max_length is not None:
        field_kwargs["max_length"] = field_def.max_length
    if field_def.pattern is not None:
        field_kwargs["pattern"] = field_def.pattern

    # Numeric constraints - Pydantic validates these automatically
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
_collections: CollectionModelRegistry | None = None


def get_collection_registry() -> CollectionModelRegistry:
    """Get the global collection model registry."""
    global _collections
    if _collections is None:
        _collections = CollectionModelRegistry()
    return _collections


def reset_collection_registry() -> None:
    """Reset the global collection registry (primarily for testing)."""
    global _collections
    if _collections is not None:
        _collections.clear()
    _collections = None
