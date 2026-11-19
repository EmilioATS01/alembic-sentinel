"""Core data structures shared by the parser, the rules and the CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Severity(str, Enum):
    """How serious a violation is. `error` makes the CLI exit with code 1."""

    WARNING = "warning"
    ERROR = "error"


class _Unknown:
    """Marker for argument values that are not literals (variables, function calls...).

    Rules must treat UNKNOWN as "can't tell" and avoid false positives on it.
    """

    _instance: _Unknown | None = None

    def __new__(cls) -> _Unknown:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNKNOWN"


UNKNOWN: Any = _Unknown()


@dataclass(frozen=True)
class Call:
    """A function call used as an argument value, e.g. `sa.Column("email", nullable=False)`.

    Its own arguments are parsed the same way as an operation's: literals when possible,
    nested `Call`s for calls, otherwise UNKNOWN.
    """

    qualname: str
    """Dotted name as written, e.g. "sa.Column" or "Column"."""

    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        """Last part of the dotted name: "Column" for `sa.Column(...)`."""
        return self.qualname.rsplit(".", 1)[-1]

    def arg(self, position: int, keyword: str, default: Any = None) -> Any:
        """Return an argument that may be passed positionally or by keyword."""
        if keyword in self.kwargs:
            return self.kwargs[keyword]
        if len(self.args) > position:
            return self.args[position]
        return default


@dataclass(frozen=True)
class Operation:
    """A single `op.<name>(...)` call found inside a migration's `upgrade()` function."""

    name: str
    """Operation name, e.g. "create_index", "add_column"."""

    args: tuple[Any, ...]
    """Positional arguments: Python literals, `Call`s (e.g. `sa.Column(...)`), or UNKNOWN."""

    kwargs: dict[str, Any]
    """Keyword arguments: Python literals, `Call`s, or UNKNOWN."""

    lineno: int
    """1-based line number of the call in the source file."""

    in_autocommit_block: bool = False
    """True if the call is inside `with op.get_context().autocommit_block():`."""

    def arg(self, position: int, keyword: str, default: Any = None) -> Any:
        """Return an argument that may be passed positionally or by keyword."""
        if keyword in self.kwargs:
            return self.kwargs[keyword]
        if len(self.args) > position:
            return self.args[position]
        return default


@dataclass(frozen=True)
class Violation:
    """A problem a rule found in a migration."""

    rule_id: str
    severity: Severity
    message: str
    hint: str
    path: Path
    lineno: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "hint": self.hint,
            "path": str(self.path),
            "line": self.lineno,
        }


@dataclass
class MigrationFile:
    """A parsed migration file: its path and the operations of its `upgrade()`."""

    path: Path
    operations: list[Operation] = field(default_factory=list)
