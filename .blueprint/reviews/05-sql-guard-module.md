# Task 05 Review — SQL Guard Module

## Verdict
APPROVE

## Reasoning
- **TDD RED evidence**: `.blueprint/qa/T05/pytest.txt` shows `ModuleNotFoundError: No module named 'app.core.sql_guard'` at collection time (line 16), then `18 passed in 0.05s` (line 28). ✅
- **Test count/coverage**: 18 tests, mapping cleanly to spec — 7 DML/DDL rejects (insert/update/delete/drop/truncate/create/alter) ≥ 6, 3 multi-statement (multi / trailing-`--` / stacked-DDL), 1 CTE-DML (Postgres `WITH x AS (INSERT ...) SELECT`), 2 whitelist (reject + accept), 3 LIMIT (preserve 500≤1000, inject → 100, clamp 5000→1000), plus `UNION ALL` and JOIN table-extraction cases. ✅
- **AST walk**: `_FORBIDDEN_NODES` uses `exp.Insert / Update / Delete / Merge / Create / Drop / Alter / TruncateTable / Command` (sql_guard.py:56–68) — no string matching. `root.walk()` isinstance check on tuple[0]. `_ALLOWED_TOP` gates top-level to `Select / Union / With / Subquery`. ✅
- **Multi-statement**: `sqlparse.split()` filtered against empty/`;`-only fragments (line 97) — the trailing `--` case in `test_reject_multi_statement_with_trailing_comment` proves this works. ✅
- **LIMIT logic**: `_apply_limit_on_select` — inject when `args.get("limit") is None`, preserve when `int(lit.name) <= cap`, clamp otherwise. `Union` variant also handled. Non-literal LIMIT expression falls through to `cap` (defensive). ✅
- **Local `SqlGuardError`**: defined at sql_guard.py:35 as `ValueError` subclass with `.reason`. `git diff main..blueprint/05-sql-guard-module --stat` confirms `exceptions.py` NOT touched. ✅
- **Scope discipline**: diff-stat shows only the 5 declared files (sql_guard.py, test_sql_guard.py, two `__init__.py`, pytest.txt). No model/service/router files touched. ✅
- **Test integrity**: `match=` regexes are broad enough (`"非 SELECT|forbidden"`, `"多语句|multi|single"`, `"白名单|whitelist|allowed"`) to survive minor message edits without being weakened — the 2 admitted iterations tuned Chinese error strings in sql_guard.py, not the tests. ✅

## Required changes
(none)

## Nice-to-haves (non-blocking)
- The `exp.Command` catch-all for GRANT/REVOKE/SET/CALL etc. is not directly asserted by a dedicated test; a future case like `SET GLOBAL x = 1` would confirm the branch. Not blocking — top-level `non_select` check already rejects these.
- `pytest-cov` is unavailable in the shared venv; the 18-case contract testing is a proxy for coverage, as noted in the spec's acceptance clause.
