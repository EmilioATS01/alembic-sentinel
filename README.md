# alembic-sentinel

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

> 🚧 **Status: early development (v0.1).** One rule is implemented; more are on the way.
> See the [roadmap](ROADMAP.md).

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

```bash
pip install git+https://github.com/EmilioATS01/alembic-sentinel
```

## Usage

```bash
alembic-sentinel check migrations/versions        # lint a folder (recursive)
alembic-sentinel check path/to/0001_migration.py  # lint one file
alembic-sentinel check --format json migrations/  # machine-readable output
alembic-sentinel rules                            # list rules
```

Exit codes: `0` no errors · `1` at least one error · `2` a file couldn't be parsed.

Only `upgrade()` is checked, since that's what runs during a deploy.

## Rules

| ID | Severity | Rule | Status |
|----|----------|------|--------|
| AS001 | error | `create_index` without `postgresql_concurrently=True` | ✅ |
| AS002 | error | Concurrent index created outside `autocommit_block()` | planned |
| AS003 | error | `add_column` with `nullable=False` and no `server_default` | planned |
| AS004 | warning | `alter_column` changing `type_` (table rewrite) | planned |
| AS005 | warning | `drop_column` / column rename (breaks running app versions) | planned |

Details and safe alternatives: [docs/rules.md](docs/rules.md).

## Development

```bash
git clone https://github.com/EmilioATS01/alembic-sentinel
cd alembic-sentinel
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
ruff check . && ruff format --check .
```

## License

MIT © Emilio Antonio Tolosa Soto
