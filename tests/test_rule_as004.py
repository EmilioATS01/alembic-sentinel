from pathlib import Path

from alembic_sentinel.linter import lint_file
from alembic_sentinel.models import Severity
from alembic_sentinel.parser import parse_source
from alembic_sentinel.rules.alter_column_type import AlterColumnType

FIXTURES = Path(__file__).parent / "fixtures"
RULE = AlterColumnType()


def _check(body: str):
    op = parse_source(f"def upgrade():\n    {body}\n").operations[0]
    return RULE.check(op, Path("m.py"))


def test_warns_on_type_change():
    violations = lint_file(FIXTURES / "warning_alter_type_and_drop.py", [RULE])
    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "AS004"
    assert v.severity is Severity.WARNING
    assert "'id'" in v.message and "'events'" in v.message and "BigInteger" in v.message
    assert v.lineno == 15


def test_warns_even_when_type_is_a_variable():
    # The new type is unknown, but the fact that the type changes is not.
    assert _check('op.alter_column("t", "c", type_=NEW_TYPE)') is not None


def test_ignores_alter_column_without_type():
    assert _check('op.alter_column("t", "c", nullable=True)') is None
    assert _check('op.alter_column("t", "c", type_=None)') is None
