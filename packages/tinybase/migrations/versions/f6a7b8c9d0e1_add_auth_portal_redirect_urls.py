"""add_auth_portal_redirect_urls

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2024-01-01 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns for redirect URLs (only if they don't exist)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "instance_settings" not in tables:
        return  # Table doesn't exist, nothing to migrate

    columns = {col["name"]: col for col in inspector.get_columns("instance_settings")}

    if "auth_portal_login_redirect_url" not in columns:
        op.add_column(
            "instance_settings",
            sa.Column("auth_portal_login_redirect_url", sa.String(length=500), nullable=True),
        )

    if "auth_portal_register_redirect_url" not in columns:
        op.add_column(
            "instance_settings",
            sa.Column("auth_portal_register_redirect_url", sa.String(length=500), nullable=True),
        )


def downgrade() -> None:
    # Remove columns (only if they exist)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "instance_settings" not in tables:
        return  # Table doesn't exist, nothing to migrate

    columns = {col["name"]: col for col in inspector.get_columns("instance_settings")}

    if "auth_portal_register_redirect_url" in columns:
        op.drop_column("instance_settings", "auth_portal_register_redirect_url")

    if "auth_portal_login_redirect_url" in columns:
        op.drop_column("instance_settings", "auth_portal_login_redirect_url")
