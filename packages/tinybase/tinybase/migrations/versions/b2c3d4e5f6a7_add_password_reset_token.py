"""add password reset token table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-01-16 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create password_reset_token table (only if it doesn't exist)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "password_reset_token" not in tables:
        op.create_table(
            "password_reset_token",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("token", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("used_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["user.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_password_reset_token_user_id"),
            "password_reset_token",
            ["user_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_password_reset_token_token"), "password_reset_token", ["token"], unique=True
        )


def downgrade() -> None:
    # Drop password_reset_token table (only if it exists)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "password_reset_token" in tables:
        # Check if indexes exist before dropping
        indexes = inspector.get_indexes("password_reset_token")
        index_names = [idx["name"] for idx in indexes]

        if "ix_password_reset_token_token" in index_names:
            op.drop_index(op.f("ix_password_reset_token_token"), table_name="password_reset_token")
        if "ix_password_reset_token_user_id" in index_names:
            op.drop_index(
                op.f("ix_password_reset_token_user_id"), table_name="password_reset_token"
            )
        op.drop_table("password_reset_token")
