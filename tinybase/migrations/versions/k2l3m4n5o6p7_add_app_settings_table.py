"""add app settings table

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-01-23 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "k2l3m4n5o6p7"
down_revision: Union[str, None] = "j1k2l3m4n5o6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create app_settings table
    op.create_table(
        "app_settings",
        sa.Column("key", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("value", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("value_type", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )

    # Migrate data from instance_settings to app_settings
    # This is done via raw SQL to handle the data transformation
    connection = op.get_bind()

    # Check if instance_settings table exists and has data
    inspector = sa.inspect(connection)
    if "instance_settings" in inspector.get_table_names():
        result = connection.execute(
            sa.text("SELECT * FROM instance_settings WHERE id = 1")
        ).fetchone()

        if result:
            # Map instance_settings columns to app_settings keys
            # We'll use a dictionary to map column names to keys
            mappings = {
                "instance_name": ("core.instance_name", "str"),
                "server_timezone": ("core.server_timezone", "str"),
                "allow_public_registration": ("core.auth.allow_public_registration", "bool"),
                "auth_portal_enabled": ("core.auth.portal.enabled", "bool"),
                "auth_portal_logo_url": ("core.auth.portal.logo_url", "str"),
                "auth_portal_primary_color": ("core.auth.portal.primary_color", "str"),
                "auth_portal_background_image_url": ("core.auth.portal.background_image_url", "str"),
                "auth_portal_login_redirect_url": ("core.auth.portal.login_redirect_url", "str"),
                "auth_portal_register_redirect_url": ("core.auth.portal.register_redirect_url", "str"),
                "token_cleanup_interval": ("core.jobs.token_cleanup.interval", "int"),
                "metrics_collection_interval": ("core.jobs.metrics.interval", "int"),
                "scheduler_function_timeout_seconds": ("core.scheduler.function_timeout_seconds", "int"),
                "scheduler_max_schedules_per_tick": ("core.scheduler.max_schedules_per_tick", "int"),
                "scheduler_max_concurrent_executions": ("core.scheduler.max_concurrent_executions", "int"),
                "max_concurrent_functions_per_user": ("core.limits.max_concurrent_functions_per_user", "int"),
                "storage_enabled": ("core.storage.enabled", "bool"),
                "storage_url": ("core.storage.url", "str"),
                "storage_bucket": ("core.storage.bucket", "str"),
                "storage_access_key": ("core.storage.access_key", "str"),
                "storage_secret_key": ("core.storage.secret_key", "str"),
                "storage_region": ("core.storage.region", "str"),
                "admin_report_email_enabled": ("core.jobs.admin_report.enabled", "bool"),
                "admin_report_email_interval_days": ("core.jobs.admin_report.interval_days", "int"),
            }

            # Get column names from result
            columns = result.keys()

            # Insert migrated data
            for col_name in columns:
                if col_name in mappings and col_name not in ("id", "created_at", "updated_at", "last_admin_report_sent_at"):
                    key, value_type = mappings[col_name]
                    value = result[col_name]

                    # Convert value to string based on type
                    if value is None:
                        value_str = None
                    elif value_type == "bool":
                        value_str = "true" if value else "false"
                    elif value_type == "int":
                        value_str = str(value) if value is not None else None
                    else:
                        value_str = str(value) if value is not None else None

                    if value_str is not None:
                        connection.execute(
                            sa.text("""
                                INSERT INTO app_settings (key, value, value_type, created_at, updated_at)
                                VALUES (:key, :value, :value_type, datetime('now'), datetime('now'))
                            """),
                            {"key": key, "value": value_str, "value_type": value_type}
                        )

            connection.commit()


def downgrade() -> None:
    # Drop app_settings table
    op.drop_table("app_settings")
