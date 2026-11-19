# Roadmap

- [x] **v0.1 — Foundations:** AST parser for Alembic `upgrade()`, CLI (`check`, `rules`),
      text/JSON output, CI, rule AS001.
- [ ] **v0.2 — Core rules:** AS002–AS005, each with fixtures, tests and docs.
- [ ] **v0.3 — Size-aware mode:** `--database-url` reads table sizes (`pg_class.reltuples`)
      and ranks findings by real risk.
- [ ] **v0.4 — Team-ready:** config file (`[tool.alembic-sentinel]` in `pyproject.toml`),
      `# sentinel: ignore[AS001]` comments, GitHub PR annotations output.
- [ ] **v0.5 — Distribution:** PyPI release, GitHub Action on the Marketplace, pre-commit hook.
