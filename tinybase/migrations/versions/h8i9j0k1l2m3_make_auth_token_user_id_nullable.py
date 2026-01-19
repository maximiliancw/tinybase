"""make auth_token user_id nullable

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2025-01-12 15:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "h8i9j0k1l2m3"
down_revision: Union[str, None] = "g7h8i9j0k1l2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make auth_token.user_id nullable to support internal tokens for scheduled functions."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "auth_token" not in tables:
        return  # Table doesn't exist, nothing to migrate

    columns = {col["name"]: col for col in inspector.get_columns("auth_token")}

    if "user_id" not in columns:
        return  # Column doesn't exist, nothing to migrate

    # Check if column is already nullable
    if columns["user_id"]["nullable"]:
        return  # Already nullable, nothing to do

    # Check if we're using SQLite (which requires table recreation)
    if conn.dialect.name == "sqlite":
        # SQLite: Recreate table with nullable user_id
        existing_tables = inspector.get_table_names()

        if "auth_token_new" in existing_tables:
            op.drop_table("auth_token_new")

        # Get all columns from existing table
        {col["name"]: col for col in inspector.get_columns("auth_token")}

        # Get foreign keys
        inspector.get_foreign_keys("auth_token")

        # Build column list with user_id as nullable
        table_columns = [
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=True),  # Changed to nullable
            sa.Column("token", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["user.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
        ]

        # Create new table with foreign key constraint included
        op.create_table("auth_token_new", *table_columns)

        # Copy data from old table to new table
        old_columns = [col["name"] for col in inspector.get_columns("auth_token")]
        new_columns = [col["name"] for col in inspector.get_columns("auth_token_new")]

        insert_sql = f"""
            INSERT INTO auth_token_new ({", ".join(new_columns)})
            SELECT {", ".join(old_columns)} FROM auth_token
        """

        conn.execute(text(insert_sql))
        conn.commit()

        # Get indexes from old table
        indexes = inspector.get_indexes("auth_token")
        index_names = [idx["name"] for idx in indexes]

        # Drop old table
        for idx_name in index_names:
            if idx_name and idx_name.startswith("ix_auth_token_"):
                try:
                    op.drop_index(idx_name, table_name="auth_token")
                except Exception:
                    pass  # Index might not exist

        op.drop_table("auth_token")

        # Rename new table to original name
        op.rename_table("auth_token_new", "auth_token")

        # Recreate indexes
        for idx in indexes:
            if idx["name"] and idx["name"].startswith("ix_auth_token_"):
                op.create_index(
                    idx["name"],
                    "auth_token",
                    idx["column_names"],
                    unique=idx.get("unique", False),
                )
    else:
        # For other databases (PostgreSQL, MySQL, etc.), use ALTER COLUMN
        op.alter_column("auth_token", "user_id", nullable=True)


def downgrade() -> None:
    """Revert auth_token.user_id back to NOT NULL."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "auth_token" not in tables:
        return  # Table doesn't exist, nothing to migrate

    columns = {col["name"]: col for col in inspector.get_columns("auth_token")}

    if "user_id" not in columns:
        return  # Column doesn't exist, nothing to migrate

    # Check if column is already NOT NULL
    if not columns["user_id"]["nullable"]:
        return  # Already NOT NULL, nothing to do

    # Check if there are any NULL values - if so, we can't downgrade
    result = conn.execute(text("SELECT COUNT(*) FROM auth_token WHERE user_id IS NULL"))
    null_count = result.scalar()
    if null_count > 0:
        raise ValueError(
            f"Cannot downgrade: {null_count} auth_token records have NULL user_id. "
            "Please update or delete these records before downgrading."
        )

    # Check if we're using SQLite (which requires table recreation)
    if conn.dialect.name == "sqlite":
        # SQLite: Recreate table with NOT NULL user_id
        existing_tables = inspector.get_table_names()

        if "auth_token_new" in existing_tables:
            op.drop_table("auth_token_new")

        # Get all columns from existing table
        {col["name"]: col for col in inspector.get_columns("auth_token")}

        # Get foreign keys
        inspector.get_foreign_keys("auth_token")

        # Build column list with user_id as NOT NULL
        table_columns = [
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=False),  # Reverted to NOT NULL
            sa.Column("token", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["user.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
        ]

        # Create new table with foreign key constraint included
        op.create_table("auth_token_new", *table_columns)

        # Copy data from old table to new table (only rows with non-NULL user_id)
        old_columns = [col["name"] for col in inspector.get_columns("auth_token")]
        new_columns = [col["name"] for col in inspector.get_columns("auth_token_new")]

        insert_sql = f"""
            INSERT INTO auth_token_new ({", ".join(new_columns)})
            SELECT {", ".join(old_columns)} FROM auth_token
            WHERE user_id IS NOT NULL
        """

        conn.execute(text(insert_sql))
        conn.commit()

        # Get indexes from old table
        indexes = inspector.get_indexes("auth_token")
        index_names = [idx["name"] for idx in indexes]

        # Drop old table
        for idx_name in index_names:
            if idx_name and idx_name.startswith("ix_auth_token_"):
                try:
                    op.drop_index(idx_name, table_name="auth_token")
                except Exception:
                    pass  # Index might not exist

        op.drop_table("auth_token")

        # Rename new table to original name
        op.rename_table("auth_token_new", "auth_token")

        # Recreate indexes
        for idx in indexes:
            if idx["name"] and idx["name"].startswith("ix_auth_token_"):
                op.create_index(
                    idx["name"],
                    "auth_token",
                    idx["column_names"],
                    unique=idx.get("unique", False),
                )
    else:
        # For other databases, use ALTER COLUMN
        op.alter_column("auth_token", "user_id", nullable=False)
