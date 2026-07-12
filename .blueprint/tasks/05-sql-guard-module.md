# T05 — SQL guard module (TDD red-first)

## Goal
Implement `backend/app/core/sql_guard.py` — a pure function `validate_and_shape(sql: str, dialect: str, max_rows: int, allowed_tables: set[str] | None = None) -> ShapedSql` — that (a) rejects multi-statement input via `sqlparse.split()`; (b) requires `sqlparse.get_type() == "SELECT"`; (c) parses via `sqlglot.parse_one(sql, dialect)`; (d) walks the AST and REJECTS any node whose type is one of `Insert, Update, Delete, Merge, Create, Drop, Alter, TruncateTable, Command`; (e) enforces `LIMIT` (injects if absent, clamps if larger); (f) if `allowed_tables` given, all Table nodes must resolve to a name inside the set. Custom exception `SqlGuardError` with typed `reason` enum.

## Files touched
- `backend/app/core/sql_guard.py`  (NEW)
- `backend/app/core/errors.py`  (extend with `SqlGuardError` if not present)
- `backend/tests/security/test_sql_guard.py`  (NEW — 15+ cases red-first)

## Depends on
- T01 (sqlglot/sqlparse installed)

## Implementation notes
- TDD order: write tests first, run pytest → RED, then implement, run pytest → GREEN.
- Test cases (each is a `def test_*`):
  - reject `INSERT INTO users (id) VALUES (1)`
  - reject `UPDATE users SET a = 1`
  - reject `DELETE FROM users`
  - reject `DROP TABLE users`
  - reject `TRUNCATE TABLE users`
  - reject `CREATE TABLE t (a INT)`
  - reject `SELECT 1; SELECT 2` (multi-statement)
  - reject `SELECT 1; --` (multi-statement w/ comment)
  - reject a stacked query `SELECT * FROM users WHERE 1=1; DROP TABLE users`
  - reject WITH-clause containing INSERT (`WITH x AS (INSERT ...) SELECT ...` via CTE UPDATE)
  - reject `SELECT * FROM users` when `allowed_tables={"orders"}`
  - accept `SELECT * FROM users` when `allowed_tables={"users"}`
  - accept `SELECT id FROM users LIMIT 500` → LIMIT stays 500
  - accept `SELECT id FROM users` w/ `max_rows=100` → LIMIT injected = 100
  - accept `SELECT id FROM users LIMIT 5000` w/ `max_rows=1000` → LIMIT clamped to 1000
- `ShapedSql` returns `.sql` (rewritten string) and `.tables` (list of names touched).

## Acceptance
- `pytest backend/tests/security/test_sql_guard.py -q` — all tests green.
- Coverage: guard module ≥95%.

## Verify
```bash
cd backend && pytest tests/security/test_sql_guard.py -q --tb=short | tee ../.blueprint/qa/T05/pytest.txt
```

## Commit
`guard: SQL guard (sqlparse+sqlglot AST) w/ 15 TDD cases`
