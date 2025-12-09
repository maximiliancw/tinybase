"""
TinyBase Collections module.

Provides dynamic collection schema management and record CRUD operations.
Collections are defined with JSON schemas that are used to generate
Pydantic models at runtime for validation and OpenAPI documentation.
"""

from tinybase.collections.schemas import (
    CollectionModelRegistry,
    build_pydantic_model_from_schema,
    get_registry,
)
from tinybase.collections.service import CollectionService

__all__ = [
    "CollectionModelRegistry",
    "CollectionService",
    "build_pydantic_model_from_schema",
    "get_registry",
]
