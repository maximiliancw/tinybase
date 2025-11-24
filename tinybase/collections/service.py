"""
Collection and Record business logic service.

Provides CRUD operations for collections and records, with validation
against dynamic Pydantic models.
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlmodel import Session, select

from tinybase.collections.schemas import (
    build_pydantic_model_from_schema,
    get_registry,
)
from tinybase.db.models import Collection, Record, utcnow


class CollectionService:
    """
    Service class for collection and record operations.
    
    Provides methods for:
    - Collection CRUD
    - Record CRUD with schema validation
    - Registry management
    """
    
    def __init__(self, session: Session) -> None:
        """
        Initialize the service with a database session.
        
        Args:
            session: SQLModel database session
        """
        self.session = session
        self.registry = get_registry()
    
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
        return self.session.exec(
            select(Collection).where(Collection.name == name)
        ).first()
    
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
        try:
            model = build_pydantic_model_from_schema(name, schema)
        except Exception as e:
            raise ValueError(f"Invalid schema: {e}")
        
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
        """
        if label is not None:
            collection.label = label
        
        if schema is not None:
            # Validate new schema
            try:
                model = build_pydantic_model_from_schema(collection.name, schema)
            except Exception as e:
                raise ValueError(f"Invalid schema: {e}")
            
            collection.schema_ = schema
            self.registry.register(collection.name, model)
        
        if options is not None:
            collection.options = options
        
        collection.updated_at = utcnow()
        self.session.add(collection)
        self.session.commit()
        self.session.refresh(collection)
        
        return collection
    
    def delete_collection(self, collection: Collection) -> None:
        """
        Delete a collection and all its records.
        
        Args:
            collection: Collection to delete
        """
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
    ) -> tuple[list[Record], int]:
        """
        List records in a collection with optional filtering.
        
        Args:
            collection: The collection to query
            owner_id: Filter by owner user ID
            limit: Maximum records to return
            offset: Number of records to skip
            filters: Simple field filters (field_name: value)
        
        Returns:
            Tuple of (records list, total count).
        """
        # Base query
        query = select(Record).where(Record.collection_id == collection.id)
        
        if owner_id is not None:
            query = query.where(Record.owner_id == owner_id)
        
        # Get total count
        count_query = select(Record).where(Record.collection_id == collection.id)
        if owner_id is not None:
            count_query = count_query.where(Record.owner_id == owner_id)
        total = len(list(self.session.exec(count_query).all()))
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        records = list(self.session.exec(query).all())
        
        # Apply in-memory filters if specified
        # Note: For production, this should be done in SQL for large datasets
        if filters:
            filtered_records = []
            for record in records:
                match = True
                for key, value in filters.items():
                    if record.data.get(key) != value:
                        match = False
                        break
                if match:
                    filtered_records.append(record)
            records = filtered_records
        
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
    
    def get_record_in_collection(
        self,
        collection: Collection,
        record_id: UUID
    ) -> Record | None:
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
        """
        # Get and validate against schema
        model = self.get_or_build_model(collection)
        try:
            validated = model.model_validate(data)
            validated_data = validated.model_dump()
        except ValidationError as e:
            raise e
        
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
        """
        # Merge or replace data
        if partial:
            merged_data = {**record.data, **data}
        else:
            merged_data = data
        
        # Validate against schema
        model = self.get_or_build_model(collection)
        try:
            validated = model.model_validate(merged_data)
            validated_data = validated.model_dump()
        except ValidationError as e:
            raise e
        
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
    registry = get_registry()
    collections = session.exec(select(Collection)).all()
    
    for collection in collections:
        try:
            model = build_pydantic_model_from_schema(
                collection.name,
                collection.schema_
            )
            registry.register(collection.name, model)
        except Exception as e:
            # Log error but continue loading other collections
            print(f"Warning: Failed to load collection '{collection.name}': {e}")

