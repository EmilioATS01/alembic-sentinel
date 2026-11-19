"""widen events.id and drop users.full_name (warnings only)

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"


def upgrade() -> None:
    op.alter_column("events", "id", type_=sa.BigInteger())
    op.drop_column("users", "full_name")


def downgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(), nullable=True))
    op.alter_column("events", "id", type_=sa.Integer())
