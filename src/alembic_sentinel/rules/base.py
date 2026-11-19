"""Base class every rule extends.

To add a rule:
1. Create a new module in this package (e.g. `add_column_not_null.py`).
2. Subclass `Rule`, set `id`, `severity`, `summary`, and implement `check`.
3. Register it in `rules/__init__.py` (ALL_RULES).
4. Add fixtures + tests in `tests/`, and document it in `docs/rules.md`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..models import Operation, Severity, Violation


class Rule(ABC):
    id: str
    severity: Severity
    summary: str

    @abstractmethod
    def check(self, op: Operation, path: Path) -> Violation | None:
        """Return a Violation if `op` breaks this rule, otherwise None."""

    def violation(self, op: Operation, path: Path, message: str, hint: str) -> Violation:
        return Violation(
            rule_id=self.id,
            severity=self.severity,
            message=message,
            hint=hint,
            path=path,
            lineno=op.lineno,
        )
