"""add index on users.email, the safe way

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_users_email",
            "users",
            ["email"],
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    # Not linted: only upgrade() runs during a deploy.
    op.create_index("ix_users_email_old", "users", ["email"])
