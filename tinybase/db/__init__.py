"""
TinyBase database module.

Provides database engine management, session handling, and SQLModel models
for all core entities: User, AuthToken, Collection, Record, FunctionCall, FunctionSchedule.
"""

from tinybase.db.core import (
    create_db_and_tables,
    get_engine,
    get_session,
)
from tinybase.db.models import (
    AuthToken,
    Collection,
    FunctionCall,
    FunctionSchedule,
    Record,
    User,
)

__all__ = [
    # Core functions
    "get_engine",
    "get_session",
    "create_db_and_tables",
    # Models
    "User",
    "AuthToken",
    "Collection",
    "Record",
    "FunctionCall",
    "FunctionSchedule",
]
