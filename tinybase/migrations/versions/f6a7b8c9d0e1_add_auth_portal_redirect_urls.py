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
    # Add new columns for redirect URLs
    op.add_column(
        "instance_settings",
        sa.Column("auth_portal_login_redirect_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "instance_settings",
        sa.Column("auth_portal_register_redirect_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    # Remove columns
    op.drop_column("instance_settings", "auth_portal_register_redirect_url")
    op.drop_column("instance_settings", "auth_portal_login_redirect_url")
