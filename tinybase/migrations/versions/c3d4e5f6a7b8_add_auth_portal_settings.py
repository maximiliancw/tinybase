"""add auth portal settings to instance settings

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2025-01-16 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add auth portal settings to instance_settings (only if they don't exist)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "instance_settings" not in tables:
        return  # Table doesn't exist, skip migration

    columns = [col["name"] for col in inspector.get_columns("instance_settings")]

    if "auth_portal_enabled" not in columns:
        op.add_column(
            "instance_settings",
            sa.Column("auth_portal_enabled", sa.Boolean(), nullable=True, server_default="1"),
        )

    if "auth_portal_logo_url" not in columns:
        op.add_column(
            "instance_settings",
            sa.Column("auth_portal_logo_url", sa.String(length=500), nullable=True),
        )

    if "auth_portal_primary_color" not in columns:
        op.add_column(
            "instance_settings",
            sa.Column("auth_portal_primary_color", sa.String(length=50), nullable=True),
        )

    if "auth_portal_background_color" not in columns:
        op.add_column(
            "instance_settings",
            sa.Column("auth_portal_background_color", sa.String(length=50), nullable=True),
        )


def downgrade() -> None:
    # Remove auth portal settings from instance_settings (only if they exist)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "instance_settings" not in tables:
        return  # Table doesn't exist, skip migration

    columns = [col["name"] for col in inspector.get_columns("instance_settings")]

    if "auth_portal_background_color" in columns:
        op.drop_column("instance_settings", "auth_portal_background_color")
    if "auth_portal_primary_color" in columns:
        op.drop_column("instance_settings", "auth_portal_primary_color")
    if "auth_portal_logo_url" in columns:
        op.drop_column("instance_settings", "auth_portal_logo_url")
    if "auth_portal_enabled" in columns:
        op.drop_column("instance_settings", "auth_portal_enabled")
