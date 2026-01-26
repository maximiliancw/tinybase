"""
Collection and Record business logic service.

Provides CRUD operations for collections and records, with validation
against dynamic Pydantic models.
"""

import logging
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlalchemy import func, text
from sqlmodel import Session, select

from tinybase.collections.schemas import (
    CollectionSchema,
    build_pydantic_model_from_schema,
    get_collection_registry,
)
from tinybase.db.models import Collection, Record
from tinybase.utils import AccessRule, utcnow

logger = logging.getLogger(__name__)


def check_access(
    collection: Collection,
    operation: str,
    user_id: UUID | None = None,
    is_admin: bool = False,
    record_owner_id: UUID | None = None,
) -> bool:
    """
    Check if an operation is allowed on a collection.

    Args:
        collection: The collection to check
        operation: The operation (list, read, create, update, delete)
        user_id: The current user's ID (None for anonymous)
        is_admin: Whether the user is an admin
        record_owner_id: For record operations, the record's owner ID

    Returns:
        True if access is allowed, False otherwise.
    """
    # Admins always have access
    if is_admin:
        return True

    # Get access rules from collection options
    options = collection.options or {}
    access_rules = options.get("access", {})

    # Default access rules:
    # - list/read: public (anyone can read)
    # - create: auth (authenticated users)
    # - update/delete: owner (only record owner)
    default_rules = {
        "list": AccessRule.PUBLIC,
        "read": AccessRule.PUBLIC,
        "create": AccessRule.AUTH,
        "update": AccessRule.OWNER,
        "delete": AccessRule.OWNER,
    }

    rule_str = access_rules.get(operation, default_rules.get(operation, AccessRule.AUTH))

    # Convert string to enum if needed
    if isinstance(rule_str, str):
        try:
            rule = AccessRule(rule_str)
        except ValueError:
            rule = AccessRule.AUTH
    else:
        rule = rule_str

    # Check rule
    if rule == AccessRule.PUBLIC:
        return True
    elif rule == AccessRule.AUTH:
        return user_id is not None
    elif rule == AccessRule.OWNER:
        if user_id is None:
            return False
        # For list/create, owner check doesn't make sense, treat as auth
        if record_owner_id is None:
            return True
        return record_owner_id == user_id
    elif rule == AccessRule.ADMIN:
        return is_admin

    return False


class CollectionService:
    """
    Service class for collection and record operations.

    Provides methods for:
    - Collection CRUD
    - Record CRUD with schema validation
    - Registry management
    - Unique constraint validation
    - Reference/relationship validation
    - Automatic index management
    """

    def __init__(self, session: Session) -> None:
        """
        Initialize the service with a database session.

        Args:
            session: SQLModel database session
        """
        self.session = session
        self.registry = get_collection_registry()

    # =========================================================================
    # Validation Helpers
    # =========================================================================

    def _check_unique_constraints(
        self,
        collection: Collection,
        data: dict[str, Any],
        exclude_record_id: UUID | None = None,
    ) -> None:
        """
        Check unique constraints using SQLite JSON functions.

        Args:
            collection: The collection to check
            data: Record data to validate
            exclude_record_id: Record ID to exclude (for updates)

        Raises:
            ValueError: If a unique constraint is violated.
        """
        try:
            schema = CollectionSchema.model_validate(collection.schema_)
        except Exception:
            # If schema is invalid, skip unique checks
            return

        unique_fields = [f for f in schema.fields if f.unique]

        for field_def in unique_fields:
            value = data.get(field_def.name)
            if value is None:
                continue

            # Use SQLite json_extract for efficient querying
            stmt = select(Record.id).where(
                Record.collection_id == collection.id,
                func.json_extract(Record.data, f"$.{field_def.name}") == value,
            )

            if exclude_record_id:
                stmt = stmt.where(Record.id != exclude_record_id)

            existing = self.session.exec(stmt).first()
            if existing:
                raise ValueError(
                    f"Field '{field_def.name}' must be unique. "
                    f"A record with value '{value}' already exists."
                )

    def _validate_references(
        self,
        collection: Collection,
        data: dict[str, Any],
    ) -> None:
        """
        Validate that reference fields point to existing records.

        Args:
            collection: The collection containing the schema
            data: Record data to validate

        Raises:
            ValueError: If a reference is invalid.
        """
        try:
            schema = CollectionSchema.model_validate(collection.schema_)
        except Exception:
            return

        reference_fields = [f for f in schema.fields if f.type.lower() == "reference"]

        for field_def in reference_fields:
            value = data.get(field_def.name)
            if value is None:
                continue

            # Get target collection
            target_collection = self.get_collection_by_name(field_def.collection)
            if not target_collection:
                raise ValueError(
                    f"Referenced collection '{field_def.collection}' does not exist"
                )

            # Check if record exists
            try:
                record_id = UUID(value) if isinstance(value, str) else value
            except (ValueError, TypeError):
                raise ValueError(
                    f"Invalid reference value for '{field_def.name}': "
                    f"'{value}' is not a valid UUID"
                )

            record = self.get_record_in_collection(target_collection, record_id)
            if not record:
                raise ValueError(
                    f"Referenced record '{value}' does not exist "
                    f"in collection '{field_def.collection}'"
                )

    # =========================================================================
    # Index Management
    # =========================================================================

    def _get_index_name(self, collection_name: str, field_name: str) -> str:
        """Generate index name for a unique field."""
        return f"idx_{collection_name}_{field_name}_unique"

    def _get_existing_indexes(self, collection: Collection) -> set[str]:
        """Get existing indexes for a collection's unique fields."""
        # Query SQLite for indexes matching our naming convention
        result = self.session.exec(
            text(
                "SELECT name FROM sqlite_master WHERE type='index' "
                f"AND name LIKE 'idx_{collection.name}_%_unique'"
            )
        )
        return {row[0] for row in result}

    def _sync_collection_indexes(
        self,
        collection: Collection,
        old_schema: dict[str, Any] | None = None,
    ) -> None:
        """
        Synchronize database indexes with collection schema.

        Creates indexes for new unique fields, drops indexes for removed ones.
        This runs automatically when collections are created/updated.

        Args:
            collection: The collection to sync indexes for
            old_schema: Previous schema (for updates) to diff against
        """
        try:
            new_schema = CollectionSchema.model_validate(collection.schema_)
        except Exception as e:
            logger.warning(
                "Cannot sync indexes - invalid schema",
                extra={"collection": collection.name, "error": str(e)},
            )
            return

        # Get unique fields from new schema
        new_unique_fields = {f.name for f in new_schema.fields if f.unique}

        # Get unique fields from old schema (if updating)
        old_unique_fields: set[str] = set()
        if old_schema:
            try:
                old_parsed = CollectionSchema.model_validate(old_schema)
                old_unique_fields = {f.name for f in old_parsed.fields if f.unique}
            except Exception:
                pass

        # Calculate indexes to create and drop
        fields_to_index = new_unique_fields - old_unique_fields
        fields_to_unindex = old_unique_fields - new_unique_fields

        # Create new indexes
        for field_name in fields_to_index:
            self._create_unique_index(collection, field_name)

        # Drop removed indexes
        for field_name in fields_to_unindex:
            self._drop_unique_index(collection, field_name)

    def _create_unique_index(self, collection: Collection, field_name: str) -> None:
        """
        Create an expression index for a unique field.

        Args:
            collection: The collection
            field_name: The field to index
        """
        index_name = self._get_index_name(collection.name, field_name)

        # Check for duplicates before creating index
        duplicate_check = self.session.exec(
            text(
                f"""
                SELECT json_extract(data, '$.{field_name}') as val, COUNT(*) as cnt
                FROM record
                WHERE collection_id = :collection_id
                AND json_extract(data, '$.{field_name}') IS NOT NULL
                GROUP BY val
                HAVING cnt > 1
                LIMIT 1
                """
            ).bindparams(collection_id=str(collection.id))
        ).first()

        if duplicate_check:
            logger.error(
                "Failed to create unique index - duplicates exist",
                extra={
                    "collection": collection.name,
                    "field": field_name,
                    "index_name": index_name,
                    "operation": "create_index",
                    "duplicate_value": duplicate_check[0],
                    "duplicate_count": duplicate_check[1],
                },
            )
            raise ValueError(
                f"Cannot add unique constraint to field '{field_name}': "
                f"duplicate values exist. Please remove duplicates first."
            )

        # Create the index
        try:
            self.session.exec(
                text(
                    f"""
                    CREATE INDEX IF NOT EXISTS "{index_name}"
                    ON record (json_extract(data, '$.{field_name}'))
                    WHERE collection_id = :collection_id
                    """
                ).bindparams(collection_id=str(collection.id))
            )
            self.session.commit()

            logger.info(
                "Created index for unique field",
                extra={
                    "collection": collection.name,
                    "field": field_name,
                    "index_name": index_name,
                    "operation": "create_index",
                },
            )
        except Exception as e:
            logger.error(
                "Failed to create index",
                extra={
                    "collection": collection.name,
                    "field": field_name,
                    "index_name": index_name,
                    "operation": "create_index",
                    "error": str(e),
                },
            )

    def _drop_unique_index(self, collection: Collection, field_name: str) -> None:
        """
        Drop an expression index for a unique field.

        Args:
            collection: The collection
            field_name: The field whose index to drop
        """
        index_name = self._get_index_name(collection.name, field_name)

        try:
            self.session.exec(text(f'DROP INDEX IF EXISTS "{index_name}"'))
            self.session.commit()

            logger.info(
                "Dropped index for removed unique field",
                extra={
                    "collection": collection.name,
                    "field": field_name,
                    "index_name": index_name,
                    "operation": "drop_index",
                },
            )
        except Exception as e:
            logger.warning(
                "Failed to drop index",
                extra={
                    "collection": collection.name,
                    "field": field_name,
                    "index_name": index_name,
                    "operation": "drop_index",
                    "error": str(e),
                },
            )

    def get_collection_index_status(self, collection: Collection) -> dict[str, Any]:
        """
        Get the status of indexes for a collection.

        Args:
            collection: The collection to check

        Returns:
            Dictionary with index status information.
        """
        try:
            schema = CollectionSchema.model_validate(collection.schema_)
        except Exception:
            return {"error": "Invalid schema"}

        unique_fields = [f.name for f in schema.fields if f.unique]
        existing_indexes = self._get_existing_indexes(collection)

        indexes = []
        for field_name in unique_fields:
            index_name = self._get_index_name(collection.name, field_name)
            indexes.append(
                {
                    "field": field_name,
                    "index_name": index_name,
                    "has_index": index_name in existing_indexes,
                    "status": "active" if index_name in existing_indexes else "missing",
                }
            )

        return {
            "collection": collection.name,
            "unique_fields": unique_fields,
            "indexes": indexes,
        }

    # =========================================================================
    # Collection Operations
    # =========================================================================

    def list_collections(self) -> list[Collection]:
        """
        List all collections.

        Returns:
            List of Collection objects.
        """
        return list(self.session.exec(select(Collection)).all())

    def get_collection_by_name(self, name: str) -> Collection | None:
        """
        Get a collection by name.

        Args:
            name: Collection name

        Returns:
            Collection object or None if not found.
        """
        return self.session.exec(select(Collection).where(Collection.name == name)).first()

    def get_collection_by_id(self, collection_id: UUID) -> Collection | None:
        """
        Get a collection by ID.

        Args:
            collection_id: Collection UUID

        Returns:
            Collection object or None if not found.
        """
        return self.session.get(Collection, collection_id)

    def create_collection(
        self,
        name: str,
        label: str,
        schema: dict[str, Any],
        options: dict[str, Any] | None = None,
    ) -> Collection:
        """
        Create a new collection.

        Args:
            name: Unique collection name (used in URLs)
            label: Human-readable label
            schema: JSON schema defining collection fields
            options: Additional options (access rules, etc.)

        Returns:
            The created Collection object.

        Raises:
            ValueError: If collection name already exists or schema is invalid.
        """
        # Check for existing collection
        existing = self.get_collection_by_name(name)
        if existing:
            raise ValueError(f"Collection '{name}' already exists")

        # Validate schema by attempting to build a model
        # This also validates type-specific field properties via Pydantic
        try:
            model = build_pydantic_model_from_schema(name, schema)
        except Exception as e:
            raise ValueError(f"Invalid schema: {e}")

        # Validate reference fields point to existing collections
        try:
            parsed_schema = CollectionSchema.model_validate(schema)
            for field_def in parsed_schema.fields:
                if field_def.type.lower() == "reference" and field_def.collection:
                    target = self.get_collection_by_name(field_def.collection)
                    if not target:
                        logger.warning(
                            "Reference field points to non-existent collection",
                            extra={
                                "collection": name,
                                "field": field_def.name,
                                "target_collection": field_def.collection,
                            },
                        )
        except Exception:
            pass

        # Create collection
        collection = Collection(
            name=name,
            label=label,
            schema_=schema,
            options=options or {},
        )
        self.session.add(collection)
        self.session.commit()
        self.session.refresh(collection)

        # Register the model
        self.registry.register(name, model)

        # Sync indexes for unique fields (automatic, no user intervention needed)
        self._sync_collection_indexes(collection)

        return collection

    def update_collection(
        self,
        collection: Collection,
        label: str | None = None,
        schema: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> Collection:
        """
        Update an existing collection.

        Args:
            collection: Collection to update
            label: New label (optional)
            schema: New schema (optional)
            options: New options (optional)

        Returns:
            The updated Collection object.

        Raises:
            ValueError: If schema is invalid or unique constraint cannot be added.
        """
        old_schema = collection.schema_ if schema is not None else None

        if label is not None:
            collection.label = label

        if schema is not None:
            # Validate new schema (includes type-specific property validation via Pydantic)
            try:
                model = build_pydantic_model_from_schema(collection.name, schema)
            except Exception as e:
                raise ValueError(f"Invalid schema: {e}")

            # Validate reference fields point to existing collections
            try:
                parsed_schema = CollectionSchema.model_validate(schema)
                for field_def in parsed_schema.fields:
                    if field_def.type.lower() == "reference" and field_def.collection:
                        target = self.get_collection_by_name(field_def.collection)
                        if not target:
                            logger.warning(
                                "Reference field points to non-existent collection",
                                extra={
                                    "collection": collection.name,
                                    "field": field_def.name,
                                    "target_collection": field_def.collection,
                                },
                            )
            except Exception:
                pass

            collection.schema_ = schema
            self.registry.register(collection.name, model)

        if options is not None:
            collection.options = options

        collection.updated_at = utcnow()
        self.session.add(collection)
        self.session.commit()
        self.session.refresh(collection)

        # Sync indexes if schema changed (automatic, no user intervention needed)
        if schema is not None:
            self._sync_collection_indexes(collection, old_schema)

        return collection

    def delete_collection(self, collection: Collection) -> None:
        """
        Delete a collection and all its records.

        Args:
            collection: Collection to delete
        """
        # Drop all indexes for this collection first
        try:
            schema = CollectionSchema.model_validate(collection.schema_)
            for field_def in schema.fields:
                if field_def.unique:
                    self._drop_unique_index(collection, field_def.name)
        except Exception:
            pass

        # Delete all records in the collection
        records = self.session.exec(
            select(Record).where(Record.collection_id == collection.id)
        ).all()
        for record in records:
            self.session.delete(record)

        # Delete the collection
        self.session.delete(collection)
        self.session.commit()

        # Unregister the model
        self.registry.unregister(collection.name)

    def get_or_build_model(self, collection: Collection) -> type[BaseModel]:
        """
        Get the Pydantic model for a collection, building it if needed.

        Args:
            collection: The collection

        Returns:
            Pydantic model class for the collection.
        """
        model = self.registry.get(collection.name)
        if model is None:
            model = build_pydantic_model_from_schema(collection.name, collection.schema_)
            self.registry.register(collection.name, model)
        return model

    # =========================================================================
    # Record Operations
    # =========================================================================

    def list_records(
        self,
        collection: Collection,
        owner_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[Record], int]:
        """
        List records in a collection with optional filtering and sorting.

        Args:
            collection: The collection to query
            owner_id: Filter by owner user ID
            limit: Maximum records to return
            offset: Number of records to skip
            filters: Simple field filters (field_name: value) - uses SQLite JSON functions
            sort_by: Field to sort by (created_at, updated_at, or JSON field name)
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (records list, total count).
        """
        # Base query
        query = select(Record).where(Record.collection_id == collection.id)
        count_stmt = select(func.count(Record.id)).where(Record.collection_id == collection.id)

        if owner_id is not None:
            query = query.where(Record.owner_id == owner_id)
            count_stmt = count_stmt.where(Record.owner_id == owner_id)

        # Apply filters using SQLite JSON functions (much more efficient than in-memory)
        if filters:
            for key, value in filters.items():
                json_expr = func.json_extract(Record.data, f"$.{key}")
                query = query.where(json_expr == value)
                count_stmt = count_stmt.where(json_expr == value)

        # Get total count efficiently using SQL COUNT
        total = self.session.exec(count_stmt).one()

        # Apply sorting
        if sort_by == "created_at":
            order_col = (
                Record.created_at.desc() if sort_order == "desc" else Record.created_at.asc()
            )
            query = query.order_by(order_col)
        elif sort_by == "updated_at":
            order_col = (
                Record.updated_at.desc() if sort_order == "desc" else Record.updated_at.asc()
            )
            query = query.order_by(order_col)
        elif sort_by:
            # Sort by JSON field using json_extract
            json_sort = func.json_extract(Record.data, f"$.{sort_by}")
            if sort_order == "desc":
                query = query.order_by(json_sort.desc())
            else:
                query = query.order_by(json_sort.asc())
        else:
            # Default to created_at desc
            query = query.order_by(Record.created_at.desc())

        # Apply pagination
        query = query.offset(offset).limit(limit)

        records = list(self.session.exec(query).all())

        return records, total

    def get_record(self, record_id: UUID) -> Record | None:
        """
        Get a single record by ID.

        Args:
            record_id: Record UUID

        Returns:
            Record object or None if not found.
        """
        return self.session.get(Record, record_id)

    def get_record_in_collection(self, collection: Collection, record_id: UUID) -> Record | None:
        """
        Get a record ensuring it belongs to the specified collection.

        Args:
            collection: The expected collection
            record_id: Record UUID

        Returns:
            Record object or None if not found or wrong collection.
        """
        record = self.get_record(record_id)
        if record is None or record.collection_id != collection.id:
            return None
        return record

    def create_record(
        self,
        collection: Collection,
        data: dict[str, Any],
        owner_id: UUID | None = None,
    ) -> Record:
        """
        Create a new record in a collection.

        Args:
            collection: The collection to add the record to
            data: Record data (will be validated against schema)
            owner_id: Optional owner user ID

        Returns:
            The created Record object.

        Raises:
            ValidationError: If data doesn't match the collection schema.
            ValueError: If unique constraint is violated or reference is invalid.
        """
        # Get and validate against schema (Pydantic handles all field validation)
        model = self.get_or_build_model(collection)
        try:
            validated = model.model_validate(data)
            # Use mode='json' to ensure datetime and other types are JSON-serializable
            validated_data = validated.model_dump(mode="json")
        except ValidationError as e:
            raise e

        # Check unique constraints using SQLite JSON functions
        self._check_unique_constraints(collection, validated_data)

        # Validate reference fields
        self._validate_references(collection, validated_data)

        # Create record
        record = Record(
            collection_id=collection.id,
            owner_id=owner_id,
            data=validated_data,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)

        return record

    def update_record(
        self,
        collection: Collection,
        record: Record,
        data: dict[str, Any],
        partial: bool = True,
    ) -> Record:
        """
        Update an existing record.

        Args:
            collection: The collection the record belongs to
            record: The record to update
            data: New data (partial or full based on `partial` flag)
            partial: If True, merge with existing data; if False, replace

        Returns:
            The updated Record object.

        Raises:
            ValidationError: If data doesn't match the collection schema.
            ValueError: If unique constraint is violated or reference is invalid.
        """
        # Merge or replace data
        if partial:
            merged_data = {**record.data, **data}
        else:
            merged_data = data

        # Validate against schema (Pydantic handles all field validation)
        model = self.get_or_build_model(collection)
        try:
            validated = model.model_validate(merged_data)
            # Use mode='json' to ensure datetime and other types are JSON-serializable
            validated_data = validated.model_dump(mode="json")
        except ValidationError as e:
            raise e

        # Check unique constraints (exclude current record)
        self._check_unique_constraints(collection, validated_data, exclude_record_id=record.id)

        # Validate reference fields
        self._validate_references(collection, validated_data)

        # Update record
        record.data = validated_data
        record.updated_at = utcnow()
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)

        return record

    def delete_record(self, record: Record) -> None:
        """
        Delete a record.

        Args:
            record: The record to delete
        """
        self.session.delete(record)
        self.session.commit()


def load_collections_into_registry(session: Session) -> None:
    """
    Load all collections from database and register their models.

    This should be called at application startup to populate the
    collection model registry.

    Args:
        session: Database session
    """
    registry = get_collection_registry()
    collections = session.exec(select(Collection)).all()

    for collection in collections:
        try:
            model = build_pydantic_model_from_schema(collection.name, collection.schema_)
            registry.register(collection.name, model)
        except Exception as e:
            # Log error but continue loading other collections
            print(f"Warning: Failed to load collection '{collection.name}': {e}")
