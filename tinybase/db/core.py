"""
Database engine and session management for TinyBase.

Provides SQLite database connectivity using SQLModel/SQLAlchemy.
"""

from collections.abc import Generator
from typing import Any

from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from tinybase.config import settings

# Global engine instance (initialized lazily)
_engine: Engine | None = None


def get_engine() -> Engine:
    """
    Get or create the SQLAlchemy engine.
    
    Uses the database URL from settings. For SQLite, enables
    foreign key support and configures appropriate connection arguments.
    
    Returns:
        SQLAlchemy Engine instance.
    """
    global _engine
    
    if _engine is None:
        db_url = settings().db_url
        
        # Configure connection arguments based on database type
        connect_args: dict[str, Any] = {}
        
        if db_url.startswith("sqlite"):
            # SQLite-specific settings
            # check_same_thread=False allows usage across threads (safe with proper session management)
            connect_args["check_same_thread"] = False
        
        _engine = create_engine(
            db_url,
            echo=settings().debug,  # Log SQL statements in debug mode
            connect_args=connect_args,
        )
        
        # Enable foreign keys for SQLite
        if db_url.startswith("sqlite"):
            from sqlalchemy import event
            
            @event.listens_for(_engine, "connect")
            def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
    
    return _engine


def get_session() -> Generator[Session, None, None]:
    """
    Get a database session as a context manager / generator.
    
    This function is designed to be used with FastAPI's Depends() for
    dependency injection, or as a context manager in regular code.
    
    Yields:
        SQLModel Session instance.
    
    Example:
        # With FastAPI dependency injection
        @app.get("/items")
        def get_items(session: Session = Depends(get_session)):
            return session.exec(select(Item)).all()
        
        # As context manager
        with next(get_session()) as session:
            session.add(item)
            session.commit()
    """
    engine = get_engine()
    with Session(engine) as session:
        yield session


def create_db_and_tables() -> None:
    """
    Create all database tables defined in SQLModel models.
    
    This function should be called during application startup to ensure
    all required tables exist in the database.
    """
    # Import models to ensure they're registered with SQLModel
    from tinybase.db import models  # noqa: F401
    
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    
    # Run schema migrations for adding new columns to existing tables
    _run_migrations(engine)


def _run_migrations(engine: Engine) -> None:
    """
    Run schema migrations for existing databases.
    
    SQLModel.metadata.create_all() only creates new tables, it doesn't
    add new columns to existing tables. This function handles adding
    new columns introduced in schema updates.
    """
    from sqlalchemy import inspect, text
    
    inspector = inspect(engine)
    
    # Migration: Add input_data column to function_schedule table
    if "function_schedule" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("function_schedule")]
        if "input_data" not in columns:
            with engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE function_schedule ADD COLUMN input_data JSON DEFAULT '{}'"
                ))
                conn.commit()


def reset_engine() -> None:
    """
    Reset the global engine instance.
    
    This is primarily useful for testing when you need to switch databases.
    """
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None

