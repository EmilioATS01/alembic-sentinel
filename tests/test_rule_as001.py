from pathlib import Path

from alembic_sentinel.linter import lint_file
from alembic_sentinel.models import Severity
from alembic_sentinel.parser import parse_source
from alembic_sentinel.rules.create_index_concurrently import CreateIndexConcurrently

FIXTURES = Path(__file__).parent / "fixtures"
RULE = CreateIndexConcurrently()


def _check(source: str):
    op = parse_source(source).operations[0]
    return RULE.check(op, Path("m.py"))


def test_flags_index_without_concurrently():
    violations = lint_file(FIXTURES / "unsafe_create_index.py", [RULE])
    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "AS001"
    assert v.severity is Severity.ERROR
    assert "ix_users_email" in v.message and "users" in v.message
    assert v.lineno == 15


def test_accepts_concurrent_index():
    assert lint_file(FIXTURES / "safe_create_index.py", [RULE]) == []


def test_flags_explicit_false():
    source = (
        'def upgrade():\n    op.create_index("ix", "t", ["c"], postgresql_concurrently=False)\n'
    )
    assert _check(source) is not None


def test_does_not_guess_when_value_is_a_variable():
    source = 'def upgrade():\n    op.create_index("ix", "t", ["c"], postgresql_concurrently=FLAG)\n'
    assert _check(source) is None


def test_ignores_other_operations():
    source = 'def upgrade():\n    op.drop_index("ix", table_name="t")\n'
    assert _check(source) is None
