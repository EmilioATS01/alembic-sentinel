from pathlib import Path

from alembic_sentinel.linter import lint_file
from alembic_sentinel.models import Severity
from alembic_sentinel.parser import parse_source
from alembic_sentinel.rules.drop_or_rename_column import DropOrRenameColumn

FIXTURES = Path(__file__).parent / "fixtures"
RULE = DropOrRenameColumn()


def _check(body: str):
    op = parse_source(f"def upgrade():\n    {body}\n").operations[0]
    return RULE.check(op, Path("m.py"))


def test_warns_on_drop_column_in_upgrade_only():
    # The fixture's downgrade() also touches columns; only upgrade() is linted.
    violations = lint_file(FIXTURES / "warning_alter_type_and_drop.py", [RULE])
    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "AS005"
    assert v.severity is Severity.WARNING
    assert "'full_name'" in v.message and "'users'" in v.message
    assert v.lineno == 16


def test_warns_on_rename():
    v = _check('op.alter_column("users", "email", new_column_name="email_address")')
    assert v is not None
    assert "'email'" in v.message and "'email_address'" in v.message


def test_ignores_other_alter_column():
    assert _check('op.alter_column("users", "email", nullable=False)') is None
