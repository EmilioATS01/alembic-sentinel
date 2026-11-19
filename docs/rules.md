# Rules

Each rule explains **what** it detects, **why** it's dangerous on a live PostgreSQL
database, and **how** to do it safely.

---

## AS001 — Create indexes concurrently

**Severity:** error

**Detects:** `op.create_index(...)` without `postgresql_concurrently=True`.

**Why it's dangerous:** a plain `CREATE INDEX` takes a `SHARE` lock on the table. Reads keep
working, but every `INSERT`, `UPDATE` and `DELETE` waits until the index is fully built.
On a large table that can take minutes: for users, the app is down.

**Unsafe**

```python
def upgrade():
    op.create_index("ix_users_email", "users", ["email"])
```

**Safe**

```python
def upgrade():
    with op.get_context().autocommit_block():
        op.create_index("ix_users_email", "users", ["email"], postgresql_concurrently=True)
```

`CREATE INDEX CONCURRENTLY` can't run inside a transaction, and Alembic wraps each migration
in one, so it must go inside `autocommit_block()` (see AS002).

**Not flagged:** when `postgresql_concurrently` comes from a variable, the linter can't know
its value and stays silent to avoid false positives.

---

## Planned

- **AS002** — `postgresql_concurrently=True` outside `autocommit_block()`.
- **AS003** — `add_column(..., nullable=False)` without `server_default`.
- **AS004** — `alter_column(..., type_=...)`: rewrites the table under an `ACCESS EXCLUSIVE` lock.
- **AS005** — `drop_column` and column renames: break the app version still running during deploy.
