"""add orders.status the safe way

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
    )
    op.add_column("orders", sa.Column("note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "note")
    op.drop_column("orders", "status")
