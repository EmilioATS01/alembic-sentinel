"""AS001 — create indexes concurrently.

A plain `CREATE INDEX` takes a SHARE lock on the table: reads keep working, but
every INSERT, UPDATE and DELETE is blocked until the index finishes building.
On a large table that can take minutes, which is effectively downtime.
`CREATE INDEX CONCURRENTLY` builds the index without blocking writes.
"""

from __future__ import annotations

from pathlib import Path

from ..models import UNKNOWN, Operation, Severity, Violation
from .base import Rule


class CreateIndexConcurrently(Rule):
    id = "AS001"
    severity = Severity.ERROR
    summary = "Indexes must be created with postgresql_concurrently=True"

    def check(self, op: Operation, path: Path) -> Violation | None:
        if op.name != "create_index":
            return None

        concurrently = op.kwargs.get("postgresql_concurrently", False)
        if concurrently is True or concurrently is UNKNOWN:
            # UNKNOWN: the value comes from a variable; don't guess (no false positives).
            return None

        index_name = op.arg(0, "index_name", UNKNOWN)
        table = op.arg(1, "table_name", UNKNOWN)
        index_label = f"'{index_name}'" if index_name is not UNKNOWN else "an index"
        table_label = f"'{table}'" if table is not UNKNOWN else "the table"

        return self.violation(
            op,
            path,
            message=(
                f"Creating {index_label} on {table_label} without CONCURRENTLY blocks "
                "all writes to the table until the index is built."
            ),
            hint=(
                "Pass postgresql_concurrently=True and run it inside "
                "`with op.get_context().autocommit_block():` "
                "(CONCURRENTLY can't run inside a transaction)."
            ),
        )
