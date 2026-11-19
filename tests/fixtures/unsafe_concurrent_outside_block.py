"""add index concurrently, but inside Alembic's transaction

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade() -> None:
    op.create_index("ix_orders_created_at", "orders", ["created_at"], postgresql_concurrently=True)


def downgrade() -> None:
    op.drop_index("ix_orders_created_at", table_name="orders")
