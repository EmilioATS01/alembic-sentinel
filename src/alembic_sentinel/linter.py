"""Glue between files, the parser and the rules."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path

from .models import Violation
from .parser import parse_file
from .rules import ALL_RULES, Rule


def iter_migration_files(paths: Iterable[Path]) -> Iterator[Path]:
    """Expand directories into the .py files they contain (sorted, recursive)."""
    for path in paths:
        if path.is_dir():
            yield from sorted(p for p in path.rglob("*.py") if p.name != "__init__.py")
        else:
            yield path


def lint_file(path: Path, rules: Iterable[Rule] = ALL_RULES) -> list[Violation]:
    migration = parse_file(path)
    rules = list(rules)
    violations: list[Violation] = []
    for op in migration.operations:
        for rule in rules:
            violation = rule.check(op, migration.path)
            if violation is not None:
                violations.append(violation)
    return violations


def lint_paths(paths: Iterable[Path], rules: Iterable[Rule] = ALL_RULES) -> list[Violation]:
    rules = list(rules)
    violations: list[Violation] = []
    for file in iter_migration_files(paths):
        violations.extend(lint_file(file, rules))
    return violations
