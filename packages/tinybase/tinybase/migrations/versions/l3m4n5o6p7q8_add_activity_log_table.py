"""add activity log table

Revision ID: l3m4n5o6p7q8
Revises: k2l3m4n5o6p7
Create Date: 2026-01-28 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "l3m4n5o6p7q8"
down_revision: Union[str, None] = "k2l3m4n5o6p7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create activity_log table
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "activity_log" not in tables:
        op.create_table(
            "activity_log",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("action", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
            sa.Column("resource_type", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
            sa.Column("resource_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
            sa.Column("user_id", sa.UUID(), nullable=True),
            sa.Column("meta_data", sa.JSON(), nullable=False),
            sa.Column("ip_address", sqlmodel.sql.sqltypes.AutoString(length=45), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        )
        op.create_index(op.f("ix_activity_log_action"), "activity_log", ["action"], unique=False)
        op.create_index(op.f("ix_activity_log_user_id"), "activity_log", ["user_id"], unique=False)
        op.create_index(
            op.f("ix_activity_log_created_at"),
            "activity_log",
            ["created_at"],
            unique=False,
        )


def downgrade() -> None:
    # Drop activity_log table
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "activity_log" in tables:
        # Check if indexes exist before dropping
        indexes = inspector.get_indexes("activity_log")
        index_names = [idx["name"] for idx in indexes]

        if "ix_activity_log_created_at" in index_names:
            op.drop_index(op.f("ix_activity_log_created_at"), table_name="activity_log")
        if "ix_activity_log_user_id" in index_names:
            op.drop_index(op.f("ix_activity_log_user_id"), table_name="activity_log")
        if "ix_activity_log_action" in index_names:
            op.drop_index(op.f("ix_activity_log_action"), table_name="activity_log")
        op.drop_table("activity_log")
