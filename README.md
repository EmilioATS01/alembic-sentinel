# alembic-sentinel
[![CI](https://github.com/EmilioATS01/alembic-sentinel/actions/workflows/ci.yml/badge.svg)](https://github.com/EmilioATS01/alembic-sentinel/actions/workflows/ci.yml)

**Catch dangerous PostgreSQL migrations in Alembic before they reach production.**

Some schema changes look harmless in code review but lock a production table for minutes:
a plain `CREATE INDEX` blocks every write, adding a `NOT NULL` column without a default
fails on tables with data, changing a column type rewrites the whole table.
`alembic-sentinel` reads your Alembic migration files and flags those operations in CI,
with a clear explanation and the safe alternative.

```console
$ alembic-sentinel check migrations/versions
migrations/versions/0001_add_email_index.py:15 error AS001 Creating 'ix_users_email' on 'users'
without CONCURRENTLY blocks all writes to the table until the index is built.
  hint: Pass postgresql_concurrently=True and run it inside
  `with op.get_context().autocommit_block():` (CONCURRENTLY can't run inside a transaction).

1 problem(s) found.
```

> 🚧 **Status: early development (v0.2).** The five core rules (AS001–AS005) are implemented;
> size-aware mode, ignore comments and configuration are next. See the [roadmap](ROADMAP.md).

## Why another migration linter?

[Squawk](https://github.com/sbdchd/squawk) is an excellent linter for **SQL** migration files,
and this project is inspired by it. But many Python teams write migrations with
**Alembic**, in Python (`op.add_column(...)`), so there is no SQL file to lint unless you
render it first. `alembic-sentinel`:

- **Understands Alembic natively.** It parses migration files with Python's `ast` module.
  It never imports or runs them, so it's safe in CI and needs no database or dependencies.
- **Knows Alembic-specific pitfalls**, like running `CREATE INDEX CONCURRENTLY` outside an
  `autocommit_block()` (it fails, because Alembic wraps migrations in a transaction).
- **Will be size-aware** *(planned)*: optionally connect to your database to read table sizes
  and rank warnings by real risk. An index on a 50-row table is fine; on 20M rows it isn't.

## Install

Requires Python 3.10+.

```bash
pip install git+https://github.com/EmilioATS01/alembic-sentinel
```

## Usage

```bash
alembic-sentinel check migrations/versions        # lint a folder (recursive)
alembic-sentinel check path/to/0001_migration.py  # lint one file
alembic-sentinel check a.py b.py migrations/      # several paths at once
alembic-sentinel check --format json migrations/  # machine-readable output (-f json)
alembic-sentinel rules                            # list rules
alembic-sentinel --version
```

**Exit codes**

| Code | Meaning |
|------|---------|
| `0` | No errors (warnings may still be printed) |
| `1` | At least one `error`-severity violation |
| `2` | A file couldn't be parsed (invalid Python) |

Only `upgrade()` is checked, since that's what runs during a deploy. Files without an
`upgrade()` function and `__init__.py` files are skipped.

### JSON output

`--format json` prints a list of violations, handy for scripts or editor integrations:

```json
[
  {
    "rule_id": "AS001",
    "severity": "error",
    "message": "Creating 'ix_users_email' on 'users' without CONCURRENTLY blocks all writes to the table until the index is built.",
    "hint": "Pass postgresql_concurrently=True and run it inside `with op.get_context().autocommit_block():` (CONCURRENTLY can't run inside a transaction).",
    "path": "migrations/versions/0001_add_email_index.py",
    "line": 15
  }
]
```

An empty list (`[]`) means no problems.

### In CI (GitHub Actions)

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
- run: pip install git+https://github.com/EmilioATS01/alembic-sentinel
- run: alembic-sentinel check migrations/versions
```

The job fails (exit code `1`) as soon as a migration contains an `error`. A packaged
GitHub Action and a pre-commit hook are planned for v0.5.

## Rules

| ID | Severity | Rule | Status |
|----|----------|------|--------|
| AS001 | error | `create_index` without `postgresql_concurrently=True` | ✅ |
| AS002 | error | Concurrent index created/dropped outside `autocommit_block()` | ✅ |
| AS003 | error | `add_column` with `nullable=False` and no `server_default` | ✅ |
| AS004 | warning | `alter_column` changing `type_` (table rewrite) | ✅ |
| AS005 | warning | `drop_column` / column rename (breaks running app versions) | ✅ |

- **error**: will block or break production → CI fails.
- **warning**: risky depending on context (e.g. the old column type) → reported, CI passes.

What each rule detects, why it's dangerous and the safe alternative, with examples:
**[docs/rules.md](docs/rules.md)**.

## How it works

```
paths ──► linter.iter_migration_files ──► parser.parse_file ──► rules ──► CLI output
          (expands folders, *.py)          (ast, upgrade() only)  (Rule.check)  (text / json + exit code)
```

1. **Collect files.** Folders are walked recursively for `*.py` files (sorted, skipping
   `__init__.py`); file paths are used as-is.
2. **Parse statically.** Each file is parsed with `ast` (never imported). The parser finds the
   top-level `upgrade()` function and records every `op.<name>(...)` call as an `Operation`:
   its name, positional and keyword arguments, line number, and whether it sits inside
   `with op.get_context().autocommit_block():`. Helpers that aren't schema operations
   (`op.get_context`, `op.get_bind`, `op.f`, `op.inline_literal`) are ignored.
3. **Literal, call or unknown.** Argument values are evaluated with `ast.literal_eval`.
   Calls like `sa.Column("status", sa.String(20), nullable=False)` become a `Call` value
   with its own (recursively parsed) arguments, so rules can look inside columns and types.
   Anything else (a variable, an expression) becomes `UNKNOWN`, and rules never report a
   problem based on an `UNKNOWN` value, to avoid false positives.
4. **Run the rules.** Every operation is passed to every rule in `ALL_RULES`; a rule returns
   a `Violation` (rule id, severity, message, hint, path, line) or `None`.
5. **Report.** The CLI prints violations as colored text or JSON and sets the exit code.

### Project layout

```
src/alembic_sentinel/
├── cli.py            # Typer app: `check` and `rules` commands, output, exit codes
├── linter.py         # file discovery + runs every rule on every operation
├── parser.py         # AST parser: upgrade() → list[Operation]
├── models.py         # Operation, Call, Violation, MigrationFile, Severity, UNKNOWN
└── rules/
    ├── __init__.py                        # ALL_RULES registry
    ├── base.py                            # Rule base class + helpers
    ├── create_index_concurrently.py       # AS001
    ├── concurrently_outside_autocommit.py # AS002
    ├── add_column_not_null.py             # AS003
    ├── alter_column_type.py               # AS004
    └── drop_or_rename_column.py           # AS005
tests/
├── fixtures/         # sample safe / unsafe / warning-only migrations
├── test_parser.py
├── test_cli.py
└── test_rule_as001.py … test_rule_as005.py
docs/rules.md         # user-facing rule reference
```

## Known limitations

- Only operations written literally as `op.<name>(...)` inside `upgrade()` are seen. Calls
  made through helper functions, loops building names dynamically, or an alias of `op` are
  not analysed.
- Raw SQL in `op.execute("...")` is not inspected.
- AS003 only sees columns written inline (`op.add_column("t", sa.Column(...))`); a column
  built in a variable or helper function is skipped.
- The linter has no database access yet, so it can't tell a 50-row table from a 20M-row one
  (size-aware mode is planned for v0.3).
- There's no way to silence a specific finding yet; `# sentinel: ignore[AS001]` comments and
  a `[tool.alembic-sentinel]` config section are planned for v0.4.

## Development

```bash
git clone https://github.com/EmilioATS01/alembic-sentinel
cd alembic-sentinel
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
ruff check . && ruff format --check .
```

CI runs ruff and the test suite on Python 3.10–3.13 for every push to `main` and every PR.

### Adding a rule

1. Create a module in `src/alembic_sentinel/rules/` (e.g. `add_column_not_null.py`).
2. Subclass `Rule`, set `id`, `severity` and `summary`, and implement
   `check(op, path) -> Violation | None`. Use `op.arg(position, keyword)` to read arguments
   that may be positional or keyword, and return `None` whenever a value is `UNKNOWN`.
3. Register it in `ALL_RULES` (`rules/__init__.py`).
4. Add safe/unsafe fixtures in `tests/fixtures/` and a `tests/test_rule_asXXX.py`.
5. Document it in `docs/rules.md` and update the table above.

## License

MIT © Emilio Antonio Tolosa Soto
