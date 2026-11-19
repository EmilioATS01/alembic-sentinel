"""AS003 — add NOT NULL columns with a `server_default`.

Existing rows get NULL for a new column, so `ADD COLUMN ... NOT NULL` without a
database-side default fails on any table that already has data. SQLAlchemy's
`default=` doesn't help: it's applied by Python on future inserts, not by PostgreSQL.
"""

from __future__ import annotations

from pathlib import Path

from ..models import Call, Operation, Severity, Violation
from .base import Rule, quote

# Positional column arguments that make PostgreSQL fill existing rows by itself.
_SELF_FILLING = frozenset({"Identity", "Computed"})


class AddColumnNotNull(Rule):
    id = "AS003"
    severity = Severity.ERROR
    summary = "NOT NULL columns must be added with a server_default"

    def check(self, op: Operation, path: Path) -> Violation | None:
        if op.name != "add_column":
            return None
        column = op.arg(1, "column")
        if not isinstance(column, Call) or column.name != "Column":
            return None  # built elsewhere (variable, helper): can't tell

        if not _is_not_null(column):
            return None
        if column.kwargs.get("server_default") is not None:
            return None  # any server_default fills existing rows (or is a value we can't see)
        if any(isinstance(a, Call) and a.name in _SELF_FILLING for a in column.args):
            return None

        column_label = quote(column.arg(0, "name"), "a column")
        table_label = quote(op.arg(0, "table_name"), "the table")
        return self.violation(
            op,
            path,
            message=(
                f"Adding NOT NULL {column_label} to {table_label} without a server_default "
                "fails if the table already has rows (they would get NULL)."
            ),
            hint=(
                "Add a constant server_default=..., or add the column as nullable, backfill "
                "it, then set NOT NULL in a later migration. `default=` does not help: it's "
                "applied by Python, not by the database."
            ),
        )


def _is_not_null(column: Call) -> bool:
    """True only when the column is certainly NOT NULL."""
    nullable = column.kwargs.get("nullable")
    if "nullable" in column.kwargs:
        return nullable is False
    # SQLAlchemy's default: nullable unless it's part of the primary key.
    return column.kwargs.get("primary_key") is True
