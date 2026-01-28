"""rename storage_endpoint to storage_url

Revision ID: m4n5o6p7q8r9
Revises: l3m4n5o6p7q8
Create Date: 2026-01-28 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "m4n5o6p7q8r9"
down_revision: Union[str, None] = "l3m4n5o6p7q8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename storage_endpoint to storage_url in instance_settings
    # SQLite doesn't support RENAME COLUMN directly in all versions, so we:
    # 1. Add the new column
    # 2. Copy data from old column
    # 3. The old column will remain but be ignored by the model
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "instance_settings" not in tables:
        return  # Table doesn't exist, skip migration

    columns = [col["name"] for col in inspector.get_columns("instance_settings")]

    if "storage_endpoint" in columns and "storage_url" not in columns:
        # Add new column
        op.add_column(
            "instance_settings",
            sa.Column("storage_url", sa.String(length=500), nullable=True),
        )

        # Copy data from old column to new column
        conn.execute(
            text(
                "UPDATE instance_settings SET storage_url = storage_endpoint WHERE storage_endpoint IS NOT NULL"
            )
        )
        conn.commit()

    # Also update app_settings table if it exists
    if "app_settings" in tables:
        # Update the key from core.storage.endpoint to core.storage.url
        conn.execute(
            text(
                "UPDATE app_settings SET key = 'core.storage.url' WHERE key = 'core.storage.endpoint'"
            )
        )
        conn.commit()


def downgrade() -> None:
    # Revert: copy data back
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "instance_settings" not in tables:
        return  # Table doesn't exist, skip migration

    columns = [col["name"] for col in inspector.get_columns("instance_settings")]

    if "storage_url" in columns and "storage_endpoint" in columns:
        # Copy data back to old column
        conn.execute(
            text(
                "UPDATE instance_settings SET storage_endpoint = storage_url WHERE storage_url IS NOT NULL"
            )
        )
        conn.commit()

    # Also revert app_settings table if it exists
    if "app_settings" in tables:
        # Update the key from core.storage.url back to core.storage.endpoint
        conn.execute(
            text(
                "UPDATE app_settings SET key = 'core.storage.endpoint' WHERE key = 'core.storage.url'"
            )
        )
        conn.commit()
