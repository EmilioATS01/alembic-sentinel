from pathlib import Path

import pytest

from alembic_sentinel.models import UNKNOWN
from alembic_sentinel.parser import MigrationParseError, parse_file, parse_source

FIXTURES = Path(__file__).parent / "fixtures"


def test_parses_only_upgrade_operations():
    migration = parse_file(FIXTURES / "safe_create_index.py")
    assert [op.name for op in migration.operations] == ["create_index"]


def test_extracts_positional_and_keyword_arguments():
    migration = parse_file(FIXTURES / "safe_create_index.py")
    op = migration.operations[0]
    assert op.arg(0, "index_name") == "ix_users_email"
    assert op.arg(1, "table_name") == "users"
    assert op.kwargs["postgresql_concurrently"] is True


def test_tracks_autocommit_block():
    assert parse_file(FIXTURES / "safe_create_index.py").operations[0].in_autocommit_block
    assert not parse_file(FIXTURES / "unsafe_create_index.py").operations[0].in_autocommit_block


def test_non_literal_values_are_unknown():
    source = """
def upgrade():
    op.create_index(NAME, "users", ["email"], postgresql_concurrently=FLAG)
"""
    op = parse_source(source).operations[0]
    assert op.args[0] is UNKNOWN
    assert op.kwargs["postgresql_concurrently"] is UNKNOWN


def test_file_without_upgrade_has_no_operations():
    assert parse_source("x = 1\n").operations == []


def test_invalid_python_raises_parse_error():
    with pytest.raises(MigrationParseError):
        parse_source("def upgrade(:\n")


def test_context_helpers_are_not_operations():
    source = """
def upgrade():
    with op.get_context().autocommit_block():
        op.execute("SELECT 1")
"""
    ops = parse_source(source).operations
    assert [op.name for op in ops] == ["execute"]
    assert ops[0].in_autocommit_block
