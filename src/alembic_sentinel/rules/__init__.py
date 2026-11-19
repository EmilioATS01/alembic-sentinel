"""Rule registry. Every rule the linter runs must be listed in ALL_RULES."""

from __future__ import annotations

from .add_column_not_null import AddColumnNotNull
from .alter_column_type import AlterColumnType
from .base import Rule
from .concurrently_outside_autocommit import ConcurrentlyOutsideAutocommit
from .create_index_concurrently import CreateIndexConcurrently
from .drop_or_rename_column import DropOrRenameColumn

ALL_RULES: list[Rule] = [
    CreateIndexConcurrently(),
    ConcurrentlyOutsideAutocommit(),
    AddColumnNotNull(),
    AlterColumnType(),
    DropOrRenameColumn(),
]

__all__ = ["ALL_RULES", "Rule"]
