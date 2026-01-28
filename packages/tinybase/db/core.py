"""
Database engine and session management for TinyBase.

Provides SQLite database connectivity using SQLModel/SQLAlchemy.
"""

from collections.abc import Generator
from typing import Any

from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from tinybase.settings import settings

# Global engine instance (initialized lazily)
_db_engine: Engine | None = None


def get_db_engine() -> Engine:
    """
    Get or create the SQLAlchemy engine.

    Uses the database URL from settings. For SQLite, enables
    foreign key support and configures appropriate connection arguments.

    Returns:
        SQLAlchemy Engine instance.
    """
    global _db_engine

    if _db_engine is None:
        # Import config here to get the current instance (may be reset during testing)
        from tinybase.settings.static import config

        db_url = config.db_url

        # Configure connection arguments based on database type
        connect_args: dict[str, Any] = {}

        if db_url.startswith("sqlite"):
            # SQLite-specific settings
            # check_same_thread=False allows usage across threads (safe with proper session management)
            connect_args["check_same_thread"] = False

        _db_engine = create_engine(
            db_url,
            echo=config.debug,  # Log SQL statements in debug mode
            connect_args=connect_args,
        )

        # Enable foreign keys for SQLite
        if db_url.startswith("sqlite"):
            from sqlalchemy import event

            @event.listens_for(_db_engine, "connect")
            def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

    return _db_engine


def get_db_session() -> Generator[Session, None, None]:
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
    engine = get_db_engine()
    with Session(engine) as session:
        yield session


def init_db() -> None:
    """
    Create all database tables and load settings from database.

    This function should be called during application startup to ensure
    all required tables exist in the database.
    """
    # Import models to ensure they're registered with SQLModel
    from tinybase.db import models  # noqa: F401

    engine = get_db_engine()
    SQLModel.metadata.create_all(engine)

    # Load settings from database after tables are created
    settings.load()


def reset_db_engine() -> None:
    """
    Reset the global database engine instance.

    This is primarily useful for testing when you need to switch databases.
    """
    global _db_engine
    if _db_engine is not None:
        _db_engine.dispose()
        _db_engine = None
