"""add application token table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2025-01-16 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create application_token table (only if it doesn't exist)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "application_token" not in tables:
        op.create_table(
            "application_token",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("token", sa.String(length=255), nullable=False),
            sa.Column("description", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_application_token_token"), "application_token", ["token"], unique=True
        )


def downgrade() -> None:
    # Drop application_token table (only if it exists)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "application_token" in tables:
        # Check if indexes exist before dropping
        indexes = inspector.get_indexes("application_token")
        index_names = [idx["name"] for idx in indexes]

        if "ix_application_token_token" in index_names:
            op.drop_index(op.f("ix_application_token_token"), table_name="application_token")
        op.drop_table("application_token")
