from pathlib import Path

from alembic_sentinel.linter import lint_file
from alembic_sentinel.models import Severity
from alembic_sentinel.parser import parse_source
from alembic_sentinel.rules.concurrently_outside_autocommit import ConcurrentlyOutsideAutocommit

FIXTURES = Path(__file__).parent / "fixtures"
RULE = ConcurrentlyOutsideAutocommit()


def _check(body: str):
    op = parse_source(f"def upgrade():\n    {body}\n").operations[0]
    return RULE.check(op, Path("m.py"))


def test_flags_concurrent_index_outside_block():
    violations = lint_file(FIXTURES / "unsafe_concurrent_outside_block.py", [RULE])
    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "AS002"
    assert v.severity is Severity.ERROR
    assert "ix_orders_created_at" in v.message
    assert v.lineno == 14


def test_accepts_concurrent_index_inside_block():
    assert lint_file(FIXTURES / "safe_create_index.py", [RULE]) == []


def test_flags_concurrent_drop_index_outside_block():
    v = _check('op.drop_index("ix", table_name="t", postgresql_concurrently=True)')
    assert v is not None and "DROP INDEX CONCURRENTLY" in v.message


def test_ignores_non_concurrent_index():
    # Not concurrent at all: that's AS001's job, not AS002's.
    assert _check('op.create_index("ix", "t", ["c"])') is None


def test_does_not_guess_when_value_is_a_variable():
    assert _check('op.create_index("ix", "t", ["c"], postgresql_concurrently=FLAG)') is None
