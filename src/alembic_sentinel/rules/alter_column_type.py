"""AS004 — avoid changing a column type in place.

Most type changes rewrite the whole table and rebuild its indexes under an
ACCESS EXCLUSIVE lock (blocks reads and writes). Some are metadata-only
(e.g. widening a VARCHAR), but the old type isn't visible in the migration,
so this is a warning.
"""

from __future__ import annotations

from pathlib import Path

from ..models import Call, Operation, Severity, Violation
from .base import Rule, quote


class AlterColumnType(Rule):
    id = "AS004"
    severity = Severity.WARNING
    summary = "Changing a column type can rewrite the whole table"

    def check(self, op: Operation, path: Path) -> Violation | None:
        if op.name != "alter_column" or op.kwargs.get("type_") is None:
            return None

        new_type = op.kwargs["type_"]
        type_label = f" to {new_type.name}" if isinstance(new_type, Call) else ""
        column_label = quote(op.arg(1, "column_name"), "a column")
        table_label = quote(op.arg(0, "table_name"), "the table")
        return self.violation(
            op,
            path,
            message=(
                f"Changing the type of {column_label} on {table_label}{type_label} usually "
                "rewrites the table under an ACCESS EXCLUSIVE lock, blocking reads and writes."
            ),
            hint=(
                "Safe only if the change is binary-compatible (e.g. widening VARCHAR, VARCHAR "
                "to TEXT). Otherwise add a new column, backfill it, switch the app, then drop "
                "the old one."
            ),
        )
