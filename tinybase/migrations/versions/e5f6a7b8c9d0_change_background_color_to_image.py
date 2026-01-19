"""change auth portal background color to background image

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2025-01-16 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change auth_portal_background_color to auth_portal_background_image_url
    # SQLite doesn't support ALTER COLUMN, so we need to:
    # 1. Add the new column
    # 2. Copy data from old column
    # 3. The old column will remain but be ignored by the model
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "instance_settings" not in tables:
        return  # Table doesn't exist, skip migration

    columns = [col["name"] for col in inspector.get_columns("instance_settings")]

    if (
        "auth_portal_background_color" in columns
        and "auth_portal_background_image_url" not in columns
    ):
        # Add new column
        op.add_column(
            "instance_settings",
            sa.Column("auth_portal_background_image_url", sa.String(length=500), nullable=True),
        )

        # Copy data from old column to new column
        conn.execute(
            text(
                "UPDATE instance_settings SET auth_portal_background_image_url = auth_portal_background_color WHERE auth_portal_background_color IS NOT NULL"
            )
        )
        conn.commit()


def downgrade() -> None:
    # Revert: copy data back and drop new column
    # Note: We can't easily drop columns in SQLite, so we'll just copy data back
    # The new column will remain but be ignored if we revert the model
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "instance_settings" not in tables:
        return  # Table doesn't exist, skip migration

    columns = [col["name"] for col in inspector.get_columns("instance_settings")]

    if "auth_portal_background_image_url" in columns and "auth_portal_background_color" in columns:
        # Copy data back to old column
        conn.execute(
            text(
                "UPDATE instance_settings SET auth_portal_background_color = auth_portal_background_image_url WHERE auth_portal_background_image_url IS NOT NULL"
            )
        )
        conn.commit()

        # Drop the new column (requires recreating table in SQLite, so we'll skip it)
        # The column will remain but be ignored if model is reverted
