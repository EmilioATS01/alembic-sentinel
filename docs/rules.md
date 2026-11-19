# Rules

Each rule explains **what** it detects, **why** it's dangerous on a live PostgreSQL
database, and **how** to do it safely.

| ID | Severity | Rule | Status |
|----|----------|------|--------|
| [AS001](#as001--create-indexes-concurrently) | error | `create_index` without `postgresql_concurrently=True` | ✅ implemented |
| [AS002](#as002--run-concurrent-index-operations-inside-autocommit_block) | error | Concurrent index operation outside `autocommit_block()` | ✅ implemented |
| [AS003](#as003--add-not-null-columns-with-a-server_default) | error | `add_column` with `nullable=False` and no `server_default` | ✅ implemented |
| [AS004](#as004--avoid-changing-a-column-type-in-place) | warning | `alter_column` changing `type_` | ✅ implemented |
| [AS005](#as005--dont-drop-or-rename-columns-the-running-app-still-uses) | warning | `drop_column` / renaming a column | ✅ implemented |

## How rules are applied

- **Only `upgrade()` is checked.** It's what runs during a deploy; `downgrade()` is ignored.
- **Severity.** `error` means "this will block or break production": the CLI exits with code
  `1`. `warning` means "this is risky depending on context": it's reported, but the exit code
  stays `0`.
- **No guessing.** Migrations are read statically (never imported or executed). Literal
  values (`"users"`, `False`) are read as-is, and calls such as `sa.Column(...)` are parsed
  into their name and arguments. When a value comes from a variable or something the linter
  can't evaluate, it's treated as *unknown*, and rules never report a violation based on an
  unknown value: a missed warning is better than a false alarm that teaches people to ignore
  the tool. (AS004 is the one nuance: `type_=SOME_VARIABLE` still means the type changes.)
- **`autocommit_block()` is tracked.** Every operation knows whether it sits inside
  `with op.get_context().autocommit_block():`, which is what AS001/AS002 rely on.

> **General advice for every rule:** set a `lock_timeout` at the start of your migrations
> (`op.execute("SET lock_timeout = '5s'")`). Even a "fast" `ALTER TABLE` has to wait for the
> `ACCESS EXCLUSIVE` lock, and while it waits, every other query on the table queues behind
> it. With a timeout, the migration fails and can be retried instead of causing an outage.

---

## AS001 — Create indexes concurrently

**Severity:** error · **Status:** ✅ implemented

**Detects:** `op.create_index(...)` without `postgresql_concurrently=True`
(missing, or explicitly `False`).

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

**Known limitation:** an index on a table created *in the same migration* is harmless (the
table is empty), but AS001 still reports it. Per-line ignores are planned for v0.4.

---

## AS002 — Run concurrent index operations inside `autocommit_block()`

**Severity:** error · **Status:** ✅ implemented

**Detects:** `op.create_index(...)` or `op.drop_index(...)` with
`postgresql_concurrently=True` that is **not** inside
`with op.get_context().autocommit_block():`.

**Why it's dangerous:** Alembic runs each migration inside a transaction, and PostgreSQL
refuses to run `CREATE INDEX CONCURRENTLY` / `DROP INDEX CONCURRENTLY` in one:

```
ERROR: CREATE INDEX CONCURRENTLY cannot run inside a transaction block
```

The migration fails in the middle of the deploy. This is an Alembic-specific trap: the code
looks correct (you *did* ask for `CONCURRENTLY`), it often passes against SQLite in tests,
and only breaks on the real PostgreSQL database.

**Unsafe**

```python
def upgrade():
    op.create_index("ix_users_email", "users", ["email"], postgresql_concurrently=True)
```

**Safe**

```python
def upgrade():
    with op.get_context().autocommit_block():
        op.create_index("ix_users_email", "users", ["email"], postgresql_concurrently=True)
```

**Good to know:**

- `autocommit_block()` **commits** whatever the migration did before it. If the migration
  fails after that point, the earlier operations are not rolled back. Prefer putting
  concurrent index operations in their own migration.
- If a concurrent build fails (e.g. a duplicate value for a unique index), PostgreSQL leaves
  an `INVALID` index behind. Drop it and retry; don't just re-run.

**Not flagged:** when `postgresql_concurrently` comes from a variable.

---

## AS003 — Add `NOT NULL` columns with a `server_default`

**Severity:** error · **Status:** ✅ implemented

**Detects:** `op.add_column(table, sa.Column(..., nullable=False))` where the column has no
`server_default`.

**Why it's dangerous:** existing rows have no value for the new column, so PostgreSQL fills
them with `NULL`, which violates `NOT NULL`. On any table that already has data, the
migration fails:

```
ERROR: column "status" of relation "orders" contains null values
```

It works in development (empty tables) and fails in production. Note that SQLAlchemy's
`default=` does **not** help: it's applied by Python on future inserts, not by the database
to existing rows. Only `server_default` is.

**Unsafe**

```python
def upgrade():
    op.add_column("orders", sa.Column("status", sa.String(20), nullable=False))
```

**Safe — option 1: constant `server_default`** (simplest)

```python
def upgrade():
    op.add_column(
        "orders",
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
    )
```

Since PostgreSQL 11, adding a column with a *constant* default is a metadata-only change:
instant, no table rewrite. A *volatile* default (`random()`, `gen_random_uuid()`,
`clock_timestamp()`) still rewrites the whole table.

**Safe — option 2: add nullable, backfill, then enforce** (when there's no sensible default)

```python
# Migration 1: add the column as nullable (instant).
def upgrade():
    op.add_column("orders", sa.Column("status", sa.String(20), nullable=True))


# Backfill existing rows in batches (a script or data migration), not one huge UPDATE.


# Migration 2: enforce NOT NULL without a long lock.
def upgrade():
    op.execute(
        "ALTER TABLE orders ADD CONSTRAINT orders_status_not_null "
        "CHECK (status IS NOT NULL) NOT VALID"
    )
    op.execute("ALTER TABLE orders VALIDATE CONSTRAINT orders_status_not_null")
    op.alter_column("orders", "status", nullable=False)
    op.drop_constraint("orders_status_not_null", "orders", type_="check")
```

A bare `SET NOT NULL` scans the whole table while holding an `ACCESS EXCLUSIVE` lock.
With a validated `CHECK (... IS NOT NULL)` constraint in place, PostgreSQL 12+ skips that
scan, and `VALIDATE CONSTRAINT` only takes a lock that doesn't block reads or writes.

**Not flagged:** `nullable=True` or omitted (columns are nullable by default), any
`server_default` (including `sa.text(...)`), and columns whose `nullable` value comes from a
variable.

---

## AS004 — Avoid changing a column type in place

**Severity:** warning · **Status:** ✅ implemented

**Detects:** `op.alter_column(..., type_=...)`.

**Why it's dangerous:** most type changes make PostgreSQL rewrite the entire table and
rebuild all of its indexes while holding an `ACCESS EXCLUSIVE` lock, which blocks **reads and
writes**. On a big table that's minutes of downtime. It can also break the application
version still running during the deploy, which expects the old type.

It's a *warning* because some changes are safe and the linter can't see the old type:

| Change | Rewrite? |
|--------|----------|
| `VARCHAR(n)` → `VARCHAR(m)` with `m > n`, or → `TEXT` | no (metadata only) |
| `NUMERIC(p, s)` → larger precision, same scale | no |
| `INTEGER` → `BIGINT`, `VARCHAR` → `INTEGER`, `TEXT` → `JSONB`, ... | **yes** |
| Shrinking a length (`VARCHAR(100)` → `VARCHAR(50)`) | no rewrite, but scans the whole table under `ACCESS EXCLUSIVE` |

**Unsafe**

```python
def upgrade():
    op.alter_column("events", "id", type_=sa.BigInteger())
```

**Safe** (expand / contract)

1. Add a new column with the new type (`op.add_column`, nullable).
2. Make the application write to both columns.
3. Backfill the new column in batches.
4. Switch reads to the new column.
5. In a later migration, drop the old column (and rename if needed; see AS005).

If you've checked the change is binary-compatible (first rows of the table above), the
warning can be accepted as-is.

---

## AS005 — Don't drop or rename columns the running app still uses

**Severity:** warning · **Status:** ✅ implemented

**Detects:**

- `op.drop_column(table, column)`
- `op.alter_column(table, column, new_column_name=...)` (column rename)

**Why it's dangerous:** during a deploy, the old version of the application keeps running
while (and after) the migration runs. The moment the column is gone or renamed, every query
from the old code that touches it fails:

```
ERROR: column "full_name" does not exist
```

With SQLAlchemy this is worse than it looks: the ORM selects **every mapped column**, so
*any* query on that model breaks, not only the ones that use the column. The operation itself
is fast, but the errors last until the last old instance is gone. Rolling back is also hard:
a dropped column's data is lost.

**Unsafe**

```python
def upgrade():
    op.drop_column("users", "full_name")
    op.alter_column("users", "email", new_column_name="email_address")
```

**Safe — dropping** (two deploys)

1. Remove every use of the column from the code, **including the SQLAlchemy model**, and
   deploy. The column is still in the database but nothing reads it.
2. In a later release, add the migration with `op.drop_column(...)`.

**Safe — renaming** (expand / contract)

1. Add the new column (`op.add_column`).
2. Write to both columns; backfill the new one.
3. Switch reads to the new column and deploy.
4. Stop writing the old one, then drop it in a later migration.

Alternatively, keep the database name and change only the Python attribute name
(`email_address = Column("email", String)`), which needs no migration at all.

**Why only a warning:** if the column was already removed from the code in a previous
release, the drop is safe. The linter can't know that, so it asks you to confirm.
