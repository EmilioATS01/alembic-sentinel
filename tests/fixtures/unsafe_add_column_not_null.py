"""add orders.status as NOT NULL without a server default

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"


def upgrade() -> None:
    op.add_column("orders", sa.Column("status", sa.String(20), nullable=False, default="new"))


def downgrade() -> None:
    op.drop_column("orders", "status")
