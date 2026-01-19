"""change auth portal default to false

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2025-12-14 16:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "g7h8i9j0k1l2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite doesn't support ALTER COLUMN to change defaults, so we need to recreate the table
    # Change the server default for auth_portal_enabled from True (1) to False (0)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if "instance_settings" not in tables:
        return  # Table doesn't exist, skip migration
    
    columns = [col["name"] for col in inspector.get_columns("instance_settings")]

    if "auth_portal_enabled" in columns:
        # Check if we're using SQLite (which requires table recreation)
        if conn.dialect.name == "sqlite":
            # SQLite: Recreate table with new default
            # Check if temp table exists from previous failed migration and drop it
            existing_tables = inspector.get_table_names()

            if "instance_settings_new" in existing_tables:
                op.drop_table("instance_settings_new")

            # 1. Create new table with updated default
            # Get all columns from existing table to ensure we include everything
            existing_columns = {
                col["name"]: col for col in inspector.get_columns("instance_settings")
            }

            # Build column list
            table_columns = [
                sa.Column("id", sa.Integer(), primary_key=True),
                sa.Column(
                    "instance_name",
                    sa.String(length=100),
                    nullable=False,
                    server_default="TinyBase",
                ),
                sa.Column(
                    "allow_public_registration", sa.Boolean(), nullable=False, server_default="1"
                ),
                sa.Column(
                    "server_timezone", sa.String(length=50), nullable=False, server_default="UTC"
                ),
                sa.Column(
                    "token_cleanup_interval", sa.Integer(), nullable=False, server_default="60"
                ),
                sa.Column(
                    "metrics_collection_interval",
                    sa.Integer(),
                    nullable=False,
                    server_default="360",
                ),
                sa.Column("scheduler_function_timeout_seconds", sa.Integer(), nullable=True),
                sa.Column("scheduler_max_schedules_per_tick", sa.Integer(), nullable=True),
                sa.Column("scheduler_max_concurrent_executions", sa.Integer(), nullable=True),
                sa.Column("storage_enabled", sa.Boolean(), nullable=False, server_default="0"),
                sa.Column("storage_endpoint", sa.String(length=500), nullable=True),
                sa.Column("storage_bucket", sa.String(length=100), nullable=True),
                sa.Column("storage_access_key", sa.String(length=200), nullable=True),
                sa.Column("storage_secret_key", sa.String(length=200), nullable=True),
                sa.Column("storage_region", sa.String(length=50), nullable=True),
                sa.Column("updated_at", sa.DateTime(), nullable=False),
                sa.Column(
                    "auth_portal_enabled", sa.Boolean(), nullable=True, server_default="0"
                ),  # Changed from "1" to "0"
                sa.Column("auth_portal_logo_url", sa.String(length=500), nullable=True),
                sa.Column("auth_portal_primary_color", sa.String(length=50), nullable=True),
            ]

            # Include old background_color column if it exists (for compatibility)
            if "auth_portal_background_color" in existing_columns:
                table_columns.append(
                    sa.Column("auth_portal_background_color", sa.String(length=50), nullable=True)
                )

            table_columns.extend(
                [
                    sa.Column(
                        "auth_portal_background_image_url", sa.String(length=500), nullable=True
                    ),
                    sa.Column(
                        "auth_portal_login_redirect_url", sa.String(length=500), nullable=True
                    ),
                    sa.Column(
                        "auth_portal_register_redirect_url", sa.String(length=500), nullable=True
                    ),
                ]
            )

            op.create_table("instance_settings_new", *table_columns)

            # 2. Copy data from old table to new table
            # Get column names from both tables to ensure proper mapping
            old_columns = [col["name"] for col in inspector.get_columns("instance_settings")]
            new_columns = [col["name"] for col in inspector.get_columns("instance_settings_new")]
            new_columns_info = {
                col["name"]: col for col in inspector.get_columns("instance_settings_new")
            }

            # Build explicit column list for INSERT to handle NULL values and column order
            # Use COALESCE to handle NULL values for NOT NULL columns
            select_parts = []
            for new_col in new_columns:
                col_info = new_columns_info[new_col]
                is_not_null = not col_info.get("nullable", True)

                if new_col in old_columns:
                    # Column exists in both - use COALESCE if NOT NULL to handle NULLs
                    if is_not_null:
                        # For NOT NULL columns, use COALESCE with appropriate default
                        if new_col == "storage_enabled":
                            select_parts.append(f"COALESCE(instance_settings.{new_col}, 0)")
                        elif new_col == "auth_portal_enabled":
                            select_parts.append(f"COALESCE(instance_settings.{new_col}, 0)")
                        elif new_col == "instance_name":
                            select_parts.append(
                                f"COALESCE(instance_settings.{new_col}, 'TinyBase')"
                            )
                        elif new_col == "allow_public_registration":
                            select_parts.append(f"COALESCE(instance_settings.{new_col}, 1)")
                        elif new_col == "server_timezone":
                            select_parts.append(f"COALESCE(instance_settings.{new_col}, 'UTC')")
                        elif new_col == "token_cleanup_interval":
                            select_parts.append(f"COALESCE(instance_settings.{new_col}, 60)")
                        elif new_col == "metrics_collection_interval":
                            select_parts.append(f"COALESCE(instance_settings.{new_col}, 360)")
                        else:
                            select_parts.append(f"instance_settings.{new_col}")
                    else:
                        select_parts.append(f"instance_settings.{new_col}")
                else:
                    # New column doesn't exist in old table - use default
                    if is_not_null:
                        if new_col == "storage_enabled":
                            select_parts.append("0")
                        elif new_col == "auth_portal_enabled":
                            select_parts.append("0")
                        else:
                            select_parts.append("NULL")
                    else:
                        select_parts.append("NULL")

            insert_sql = f"""
                INSERT INTO instance_settings_new ({", ".join(new_columns)})
                SELECT {", ".join(select_parts)} FROM instance_settings
            """

            conn.execute(text(insert_sql))
            conn.commit()

            # 3. Drop old table
            op.drop_table("instance_settings")

            # 4. Rename new table to original name
            op.rename_table("instance_settings_new", "instance_settings")
        else:
            # For other databases (PostgreSQL, MySQL, etc.), use ALTER COLUMN
            op.alter_column(
                "instance_settings",
                "auth_portal_enabled",
                server_default=sa.text("0"),
            )


def downgrade() -> None:
    # Revert the server default back to True (1)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("instance_settings")]

    if "auth_portal_enabled" in columns:
        if conn.dialect.name == "sqlite":
            # SQLite: Recreate table with old default
            # Check if temp table exists from previous failed migration and drop it
            existing_tables = inspector.get_table_names()
            if "instance_settings_new" in existing_tables:
                op.drop_table("instance_settings_new")

            existing_columns = {
                col["name"]: col for col in inspector.get_columns("instance_settings")
            }

            # Build column list
            table_columns = [
                sa.Column("id", sa.Integer(), primary_key=True),
                sa.Column(
                    "instance_name",
                    sa.String(length=100),
                    nullable=False,
                    server_default="TinyBase",
                ),
                sa.Column(
                    "allow_public_registration", sa.Boolean(), nullable=False, server_default="1"
                ),
                sa.Column(
                    "server_timezone", sa.String(length=50), nullable=False, server_default="UTC"
                ),
                sa.Column(
                    "token_cleanup_interval", sa.Integer(), nullable=False, server_default="60"
                ),
                sa.Column(
                    "metrics_collection_interval",
                    sa.Integer(),
                    nullable=False,
                    server_default="360",
                ),
                sa.Column("scheduler_function_timeout_seconds", sa.Integer(), nullable=True),
                sa.Column("scheduler_max_schedules_per_tick", sa.Integer(), nullable=True),
                sa.Column("scheduler_max_concurrent_executions", sa.Integer(), nullable=True),
                sa.Column("storage_enabled", sa.Boolean(), nullable=False, server_default="0"),
                sa.Column("storage_endpoint", sa.String(length=500), nullable=True),
                sa.Column("storage_bucket", sa.String(length=100), nullable=True),
                sa.Column("storage_access_key", sa.String(length=200), nullable=True),
                sa.Column("storage_secret_key", sa.String(length=200), nullable=True),
                sa.Column("storage_region", sa.String(length=50), nullable=True),
                sa.Column("updated_at", sa.DateTime(), nullable=False),
                sa.Column(
                    "auth_portal_enabled", sa.Boolean(), nullable=True, server_default="1"
                ),  # Revert to "1"
                sa.Column("auth_portal_logo_url", sa.String(length=500), nullable=True),
                sa.Column("auth_portal_primary_color", sa.String(length=50), nullable=True),
            ]

            # Include old background_color column if it exists (for compatibility)
            if "auth_portal_background_color" in existing_columns:
                table_columns.append(
                    sa.Column("auth_portal_background_color", sa.String(length=50), nullable=True)
                )

            table_columns.extend(
                [
                    sa.Column(
                        "auth_portal_background_image_url", sa.String(length=500), nullable=True
                    ),
                    sa.Column(
                        "auth_portal_login_redirect_url", sa.String(length=500), nullable=True
                    ),
                    sa.Column(
                        "auth_portal_register_redirect_url", sa.String(length=500), nullable=True
                    ),
                ]
            )

            op.create_table("instance_settings_new", *table_columns)

            # Get column names from both tables to ensure proper mapping
            old_columns = [col["name"] for col in inspector.get_columns("instance_settings")]
            new_columns = [col["name"] for col in inspector.get_columns("instance_settings_new")]
            new_columns_info = {
                col["name"]: col for col in inspector.get_columns("instance_settings_new")
            }

            # Build explicit column list for INSERT to handle NULL values and column order
            select_parts = []
            for new_col in new_columns:
                col_info = new_columns_info[new_col]
                is_not_null = not col_info.get("nullable", True)

                if new_col in old_columns:
                    # Column exists in both - use COALESCE if NOT NULL to handle NULLs
                    if is_not_null:
                        if new_col == "storage_enabled":
                            select_parts.append(f"COALESCE(instance_settings.{new_col}, 0)")
                        elif new_col == "auth_portal_enabled":
                            select_parts.append(
                                f"COALESCE(instance_settings.{new_col}, 1)"
                            )  # Revert to old default
                        elif new_col == "instance_name":
                            select_parts.append(
                                f"COALESCE(instance_settings.{new_col}, 'TinyBase')"
                            )
                        elif new_col == "allow_public_registration":
                            select_parts.append(f"COALESCE(instance_settings.{new_col}, 1)")
                        elif new_col == "server_timezone":
                            select_parts.append(f"COALESCE(instance_settings.{new_col}, 'UTC')")
                        elif new_col == "token_cleanup_interval":
                            select_parts.append(f"COALESCE(instance_settings.{new_col}, 60)")
                        elif new_col == "metrics_collection_interval":
                            select_parts.append(f"COALESCE(instance_settings.{new_col}, 360)")
                        else:
                            select_parts.append(f"instance_settings.{new_col}")
                    else:
                        select_parts.append(f"instance_settings.{new_col}")
                else:
                    # New column doesn't exist in old table - use default
                    if is_not_null:
                        if new_col == "storage_enabled":
                            select_parts.append("0")
                        elif new_col == "auth_portal_enabled":
                            select_parts.append("1")  # Revert to old default in downgrade
                        else:
                            select_parts.append("NULL")
                    else:
                        select_parts.append("NULL")

            insert_sql = f"""
                INSERT INTO instance_settings_new ({", ".join(new_columns)})
                SELECT {", ".join(select_parts)} FROM instance_settings
            """

            conn.execute(text(insert_sql))
            conn.commit()

            op.drop_table("instance_settings")
            op.rename_table("instance_settings_new", "instance_settings")
        else:
            # For other databases, use ALTER COLUMN
            op.alter_column(
                "instance_settings",
                "auth_portal_enabled",
                server_default=sa.text("1"),
            )
