"""Rule registry. Every rule the linter runs must be listed in ALL_RULES."""

from __future__ import annotations

from .base import Rule
from .create_index_concurrently import CreateIndexConcurrently

ALL_RULES: list[Rule] = [
    CreateIndexConcurrently(),
    # TODO(week 2): AS002 concurrently outside autocommit_block
    # TODO(week 2): AS003 add_column NOT NULL without server_default
    # TODO(week 2): AS004 alter_column changing type_
    # TODO(week 2): AS005 drop_column / renaming a column
]

__all__ = ["ALL_RULES", "Rule"]
