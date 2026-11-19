"""AS005 — don't drop or rename columns the running app still uses.

During a deploy the previous app version keeps running. SQLAlchemy selects every
mapped column, so once a column is gone or renamed, every query on that model
from the old code fails. A warning, because it's safe if the code already stopped
using the column in an earlier release.
"""

from __future__ import annotations

from pathlib import Path

from ..models import Operation, Severity, Violation
from .base import Rule, quote


class DropOrRenameColumn(Rule):
    id = "AS005"
    severity = Severity.WARNING
    summary = "Dropping or renaming a column breaks app versions still running"

    def check(self, op: Operation, path: Path) -> Violation | None:
        table_label = quote(op.arg(0, "table_name"), "the table")

        if op.name == "drop_column":
            column_label = quote(op.arg(1, "column_name"), "a column")
            return self.violation(
                op,
                path,
                message=(
                    f"Dropping {column_label} from {table_label} breaks any running app "
                    "version that still reads it (SQLAlchemy selects every mapped column)."
                ),
                hint=(
                    "First remove the column from the code and the SQLAlchemy model and "
                    "deploy; drop it in a later release."
                ),
            )

        if op.name == "alter_column" and op.kwargs.get("new_column_name") is not None:
            column_label = quote(op.arg(1, "column_name"), "a column")
            new_label = quote(op.kwargs["new_column_name"], "a new name")
            return self.violation(
                op,
                path,
                message=(
                    f"Renaming {column_label} to {new_label} on {table_label} breaks any "
                    "running app version that still uses the old name."
                ),
                hint=(
                    "Add the new column, write to both and backfill, switch reads, then drop "
                    "the old one later. Or keep the DB name and rename only the Python "
                    'attribute: Column("old_name", ...).'
                ),
            )

        return None
