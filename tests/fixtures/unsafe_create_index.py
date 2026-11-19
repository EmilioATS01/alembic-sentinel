"""add index on users.email

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa  # noqa: F401
from alembic import op

revision = "0001"
down_revision = None


def upgrade() -> None:
    op.create_index("ix_users_email", "users", ["email"])


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
