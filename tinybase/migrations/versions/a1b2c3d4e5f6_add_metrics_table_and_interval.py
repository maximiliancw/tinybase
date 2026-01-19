"""add metrics table and collection interval

Revision ID: a1b2c3d4e5f6
Revises: 5b77edb363ab
Create Date: 2025-01-15 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "5b77edb363ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add metrics_collection_interval to instance_settings (only if table and column don't exist)
    # SQLite doesn't support IF NOT EXISTS for ALTER TABLE, so we check first
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    # Only try to add column if the table exists
    if "instance_settings" in tables:
        columns = [col["name"] for col in inspector.get_columns("instance_settings")]
        if "metrics_collection_interval" not in columns:
            op.add_column(
                "instance_settings",
                sa.Column(
                    "metrics_collection_interval", sa.Integer(), nullable=True, server_default="360"
                ),
            )

    # Create metrics table (only if it doesn't exist)
    tables = inspector.get_table_names()
    if "metrics" not in tables:
        op.create_table(
            "metrics",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("metric_type", sa.String(length=50), nullable=False),
            sa.Column("data", sa.JSON(), nullable=False),
            sa.Column("collected_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_metrics_metric_type"), "metrics", ["metric_type"], unique=False)
        op.create_index(op.f("ix_metrics_collected_at"), "metrics", ["collected_at"], unique=False)


def downgrade() -> None:
    # Drop metrics table (only if it exists)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "metrics" in tables:
        # Check if indexes exist before dropping
        indexes = inspector.get_indexes("metrics")
        index_names = [idx["name"] for idx in indexes]

        if "ix_metrics_collected_at" in index_names:
            op.drop_index(op.f("ix_metrics_collected_at"), table_name="metrics")
        if "ix_metrics_metric_type" in index_names:
            op.drop_index(op.f("ix_metrics_metric_type"), table_name="metrics")
        op.drop_table("metrics")

    # Remove metrics_collection_interval from instance_settings (only if table and column exist)
    if "instance_settings" in tables:
        columns = [col["name"] for col in inspector.get_columns("instance_settings")]
        if "metrics_collection_interval" in columns:
            op.drop_column("instance_settings", "metrics_collection_interval")
