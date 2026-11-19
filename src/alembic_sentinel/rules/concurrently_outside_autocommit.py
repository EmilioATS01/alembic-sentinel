"""AS002 — run concurrent index operations inside `autocommit_block()`.

Alembic wraps each migration in a transaction, and PostgreSQL refuses to run
`CREATE INDEX CONCURRENTLY` / `DROP INDEX CONCURRENTLY` inside one. Without
`with op.get_context().autocommit_block():` the migration fails mid-deploy.
"""

from __future__ import annotations

from pathlib import Path

from ..models import Operation, Severity, Violation
from .base import Rule, quote

_SQL = {"create_index": "CREATE INDEX CONCURRENTLY", "drop_index": "DROP INDEX CONCURRENTLY"}


class ConcurrentlyOutsideAutocommit(Rule):
    id = "AS002"
    severity = Severity.ERROR
    summary = "Concurrent index operations must run inside autocommit_block()"

    def check(self, op: Operation, path: Path) -> Violation | None:
        if op.name not in _SQL or op.in_autocommit_block:
            return None
        if op.kwargs.get("postgresql_concurrently") is not True:
            return None  # not concurrent (AS001's job), or a value we can't evaluate

        index_label = quote(op.arg(0, "index_name"), "an index")
        return self.violation(
            op,
            path,
            message=(
                f"{_SQL[op.name]} on {index_label} can't run inside a transaction, and Alembic "
                "runs every migration in one: this migration will fail."
            ),
            hint=(
                "Wrap it in `with op.get_context().autocommit_block():`, ideally in a "
                "migration of its own (the block commits everything that ran before it)."
            ),
        )
