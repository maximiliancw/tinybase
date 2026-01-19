"""migrate_to_jwt

Revision ID: i0j1k2l3m4n5
Revises: ff0030cada65
Create Date: 2026-01-19 20:00:00.000000

This migration consolidates AuthToken and ApplicationToken into a single table
with JWT support. All existing tokens will be invalidated (truncated).
"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'i0j1k2l3m4n5'
down_revision: Union[str, None] = 'ff0030cada65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Migrate to JWT-based authentication.

    WARNING: This migration truncates all existing tokens. All users will need to log in again.

    Note: SQLModel already created the auth_token table with JWT fields, so this migration
    only needs to handle data cleanup and the application_token consolidation.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # TRUNCATE auth_token table (invalidate all existing sessions)
    op.execute('DELETE FROM auth_token')

    # TRUNCATE and drop application_token table if it exists (consolidated into auth_token)
    if 'application_token' in tables:
        op.execute('DELETE FROM application_token')
        op.drop_table('application_token')

    # Add max_concurrent_functions_per_user to instance_settings if it doesn't exist
    if 'instance_settings' in tables:
        columns = [col["name"] for col in inspector.get_columns("instance_settings")]
        if 'max_concurrent_functions_per_user' not in columns:
            with op.batch_alter_table('instance_settings', schema=None) as batch_op:
                batch_op.add_column(sa.Column('max_concurrent_functions_per_user', sa.Integer(), nullable=True))


def downgrade() -> None:
    """
    Downgrade from JWT to opaque tokens.

    WARNING: This is a destructive operation. All JWT tokens will be lost.

    Note: Since SQLModel controls the schema, downgrade just recreates application_token
    and cleans up data. The auth_token schema cannot be downgraded as it's managed by SQLModel.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Remove max_concurrent_functions_per_user from instance_settings if it exists
    if 'instance_settings' in tables:
        columns = [col["name"] for col in inspector.get_columns("instance_settings")]
        if 'max_concurrent_functions_per_user' in columns:
            with op.batch_alter_table('instance_settings', schema=None) as batch_op:
                batch_op.drop_column('max_concurrent_functions_per_user')

    # Recreate application_token table
    if 'application_token' not in tables:
        op.create_table('application_token',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
            sa.Column('token', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
            sa.Column('description', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('last_used_at', sa.DateTime(), nullable=True),
            sa.Column('expires_at', sa.DateTime(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_application_token_token', 'application_token', ['token'], unique=True)

    # TRUNCATE auth_token (cannot convert JWT back to opaque tokens)
    op.execute('DELETE FROM auth_token')
