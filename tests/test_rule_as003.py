from pathlib import Path

from alembic_sentinel.linter import lint_file
from alembic_sentinel.models import Severity
from alembic_sentinel.parser import parse_source
from alembic_sentinel.rules.add_column_not_null import AddColumnNotNull

FIXTURES = Path(__file__).parent / "fixtures"
RULE = AddColumnNotNull()


def _check(column: str):
    op = parse_source(f'def upgrade():\n    op.add_column("t", {column})\n').operations[0]
    return RULE.check(op, Path("m.py"))


def test_flags_not_null_without_server_default():
    violations = lint_file(FIXTURES / "unsafe_add_column_not_null.py", [RULE])
    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "AS003"
    assert v.severity is Severity.ERROR
    assert "'status'" in v.message and "'orders'" in v.message
    assert v.lineno == 15


def test_accepts_server_default_and_nullable_columns():
    assert lint_file(FIXTURES / "safe_add_column_not_null.py", [RULE]) == []


def test_python_default_does_not_count():
    assert _check('sa.Column("c", sa.Integer(), nullable=False, default=0)') is not None


def test_explicit_server_default_none_is_flagged():
    assert _check('sa.Column("c", sa.Integer(), nullable=False, server_default=None)') is not None


def test_accepts_sql_expression_server_default():
    column = 'sa.Column("c", sa.DateTime(), nullable=False, server_default=sa.func.now())'
    assert _check(column) is None


def test_nullable_omitted_is_nullable():
    assert _check('sa.Column("c", sa.Integer())') is None


def test_primary_key_is_not_null():
    assert _check('sa.Column("c", sa.Integer(), primary_key=True)') is not None


def test_identity_and_computed_columns_fill_themselves():
    assert _check('sa.Column("c", sa.BigInteger(), sa.Identity(), nullable=False)') is None
    assert _check('sa.Column("c", sa.Integer(), sa.Computed("a + b"), nullable=False)') is None


def test_works_with_bare_column_import():
    assert _check('Column("c", Integer, nullable=False)') is not None


def test_does_not_guess():
    assert _check('sa.Column("c", sa.Integer(), nullable=NULLABLE)') is None
    assert _check('sa.Column("c", sa.Integer(), nullable=False, server_default=DEFAULT)') is None
    assert _check("make_column()") is None
    assert _check("COLUMN") is None
