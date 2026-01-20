"""add function version tracking

Revision ID: j1k2l3m4n5o6
Revises: i0j1k2l3m4n5
Create Date: 2026-01-20 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "j1k2l3m4n5o6"
down_revision: Union[str, None] = "i0j1k2l3m4n5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create function_version table
    op.create_table(
        "function_version",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("function_name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("content_hash", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("deployed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("deployed_at", sa.DateTime(), nullable=False),
        sa.Column("notes", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.ForeignKeyConstraint(
            ["deployed_by_user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("function_version", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_function_version_content_hash"), ["content_hash"], unique=False)
        batch_op.create_index(batch_op.f("ix_function_version_deployed_at"), ["deployed_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_function_version_function_name"), ["function_name"], unique=False)

    # Add version_id column to function_call table
    with op.batch_alter_table("function_call", schema=None) as batch_op:
        batch_op.add_column(sa.Column("version_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key("fk_function_call_version_id", "function_version", ["version_id"], ["id"])


def downgrade() -> None:
    # Remove version_id column from function_call table
    with op.batch_alter_table("function_call", schema=None) as batch_op:
        batch_op.drop_constraint("fk_function_call_version_id", type_="foreignkey")
        batch_op.drop_column("version_id")

    # Drop function_version table
    with op.batch_alter_table("function_version", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_function_version_function_name"))
        batch_op.drop_index(batch_op.f("ix_function_version_deployed_at"))
        batch_op.drop_index(batch_op.f("ix_function_version_content_hash"))
    op.drop_table("function_version")
