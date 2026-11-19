"""Static parser for Alembic migration files.

We never import or execute the migration: we read it with Python's `ast` module.
That makes the linter safe to run in CI and independent of the user's database
and dependencies.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from .models import UNKNOWN, MigrationFile, Operation

# `op.<name>` helpers that are not schema operations: never report them as operations.
_NON_OPERATIONS = frozenset({"get_context", "get_bind", "f", "inline_literal"})


class MigrationParseError(Exception):
    """Raised when a file can't be parsed as Python."""


def parse_file(path: Path) -> MigrationFile:
    """Parse a migration file and return the operations of its `upgrade()` function."""
    source = path.read_text(encoding="utf-8")
    return parse_source(source, path)


def parse_source(source: str, path: Path | None = None) -> MigrationFile:
    """Parse migration source code. Useful in tests."""
    path = path or Path("<string>")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise MigrationParseError(f"{path}: invalid Python syntax ({exc.msg})") from exc

    migration = MigrationFile(path=path)
    upgrade = _find_function(tree, "upgrade")
    if upgrade is None:
        return migration  # not a migration file (or an empty one): nothing to lint

    visitor = _OperationVisitor()
    for statement in upgrade.body:
        visitor.visit(statement)
    migration.operations = visitor.operations
    return migration


def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


class _OperationVisitor(ast.NodeVisitor):
    """Collects `op.<name>(...)` calls and tracks whether we're in an autocommit block."""

    def __init__(self) -> None:
        self.operations: list[Operation] = []
        self._autocommit_depth = 0

    def visit_With(self, node: ast.With) -> None:
        is_autocommit = any(_is_autocommit_block(item.context_expr) for item in node.items)
        if is_autocommit:
            self._autocommit_depth += 1
        # Visit the context expressions too, in case they contain op calls.
        for item in node.items:
            self.visit(item.context_expr)
        for statement in node.body:
            self.visit(statement)
        if is_autocommit:
            self._autocommit_depth -= 1

    def visit_Call(self, node: ast.Call) -> None:
        name = _op_call_name(node)
        if name is not None:
            self.operations.append(
                Operation(
                    name=name,
                    args=tuple(_literal(arg) for arg in node.args),
                    kwargs={kw.arg: _literal(kw.value) for kw in node.keywords if kw.arg},
                    lineno=node.lineno,
                    in_autocommit_block=self._autocommit_depth > 0,
                )
            )
        self.generic_visit(node)


def _op_call_name(node: ast.Call) -> str | None:
    """Return "create_index" for `op.create_index(...)`, otherwise None."""
    func = node.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        if func.value.id == "op" and func.attr not in _NON_OPERATIONS:
            return func.attr
    return None


def _is_autocommit_block(expr: ast.expr) -> bool:
    """Match `op.get_context().autocommit_block()` (and any `<x>.autocommit_block()`)."""
    return (
        isinstance(expr, ast.Call)
        and isinstance(expr.func, ast.Attribute)
        and expr.func.attr == "autocommit_block"
    )


def _literal(node: ast.expr) -> Any:
    """Return the Python value of a literal node, or UNKNOWN if it isn't a literal."""
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return UNKNOWN
