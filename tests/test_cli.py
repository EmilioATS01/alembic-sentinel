import json
from pathlib import Path

from typer.testing import CliRunner

from alembic_sentinel.cli import app

FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner()


def test_check_exits_1_on_errors():
    result = runner.invoke(app, ["check", str(FIXTURES / "unsafe_create_index.py")])
    assert result.exit_code == 1
    assert "AS001" in result.output


def test_check_exits_0_when_clean():
    result = runner.invoke(app, ["check", str(FIXTURES / "safe_create_index.py")])
    assert result.exit_code == 0
    assert "No problems found" in result.output


def test_check_accepts_directories():
    result = runner.invoke(app, ["check", str(FIXTURES)])
    assert result.exit_code == 1
    assert "1 problem(s) found" in result.output


def test_json_output():
    result = runner.invoke(
        app, ["check", "--format", "json", str(FIXTURES / "unsafe_create_index.py")]
    )
    data = json.loads(result.output)
    assert data[0]["rule_id"] == "AS001"
    assert data[0]["line"] == 15


def test_rules_command_lists_rules():
    result = runner.invoke(app, ["rules"])
    assert result.exit_code == 0
    assert "AS001" in result.output
