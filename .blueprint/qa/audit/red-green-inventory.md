# RED→GREEN Inventory — Test-Producing Tasks

_ULW TDD contract: every behavior change requires a failing test written FIRST, then GREEN via smallest change._

## Summary

- **Strict RED→GREEN capture inside the evidence file itself**: T05 → **1**
- **Worker-reported RED-first discipline (RED not saved in evidence file, but tests exercise negative branches)**: T25, T26 → **2**
- **GREEN-only capture (no historical RED artefact)**: T09, T13, T14, T15, T16 → **5**
- **Gap**: 7 / 8 test-producing tasks lack a persisted RED artefact; only T05's `pytest.txt` embeds both phases in one file.

_(the gap is accepted and documented in `gaps.md`: all tests DO exist, DO pass GREEN, and DO exercise their intended negative branches — but the RED-first artefact was skipped for services and captured only in narrative for T25/T26.)_

## Per-task inventory

### T05 — sql-guard-module

**Test file**: `backend/tests/security/test_sql_guard.py` (18 cases, TDD RED-first per spec)
**Evidence bundle**: `(w2t05) .blueprint/qa/T05/pytest.txt` — 40 lines

**RED phase** (before implementation):
- Command: `pytest tests/security/test_sql_guard.py -q --tb=short`
- Header in evidence file: `=== RED phase (module unimplemented) ===`
- Expected failure mode: `ModuleNotFoundError: No module named 'app.core.sql_guard'`
- Evidence quote (lines 15–17):
  - `tests/security/test_sql_guard.py:10: in <module>`
  - `    from app.core.sql_guard import validate_and_shape, SqlGuardError`
  - `E   ModuleNotFoundError: No module named 'app.core.sql_guard'`
- Terminal summary: `ERROR tests/security/test_sql_guard.py` / `Interrupted: 1 error during collection` / `1 error in 0.04s`

**GREEN phase** (after implementation):
- Command: same
- Evidence quote: `..................                                                       [100%]` / `18 passed in 0.05s`

**Test discipline check**:
- ✅ Tests were NOT weakened to force GREEN. Review `05-sql-guard-module.md` confirms diff-stat is limited to the 5 declared files (sql_guard.py, test_sql_guard.py, two `__init__.py`, pytest.txt).
- ✅ 18 tests exercise all AST-walk branches: multi-statement split, non-SELECT top type (INSERT/UPDATE/DELETE/DROP/TRUNCATE/CREATE/ALTER), CTE with DML, allowed_tables whitelist reject + accept, LIMIT preserve/inject/clamp, UNION+LIMIT, JOIN table extraction.
- ⚠️ Coverage tooling (`pytest-cov`) not installed in the shared venv at T05 time; 18/18 contract cases documented in evidence file as coverage proxy. `pytest-cov==7.1.0` later added by T25 — see T25 report where `sql_guard.py` measures 78 % line coverage.

---

### T09 — dp-kb-repositories

**Test file**: `backend/tests/data_platform/test_repositories.py` and `backend/tests/knowledge_base/test_repositories.py` (10 cases across 2 files per spec)
**Evidence bundle**: `(w3t09) .blueprint/qa/T09/pytest.txt` — 6 lines

**RED phase**: ⚠️ **RED not documented**. The evidence file contains only the GREEN run. No `ImportError` / `ModuleNotFoundError` header, no `=== RED phase ===` marker.

**GREEN phase**:
- Command: `pytest tests/data_platform/test_repositories.py tests/knowledge_base/test_repositories.py -q`
- Evidence quote: `..........                                                               [100%]` / `10 passed in 0.09s`

**Test discipline check**:
- ✅ Tests DO exist and pass; they DO exercise negative branches (owner-scoping, 404, filter combos).
- ⚠️ No historical proof that these 10 tests failed BEFORE the repository implementation existed — RED-first artefact was skipped in favour of test-and-impl-together.
- ✅ No test skips, no test deletions, no weakened asserts observed in review `09-dp-kb-repositories.md`.

---

### T13 — dp-datasource-service

**Test file**: `backend/tests/data_platform/test_dp_data_source_service.py` (11 cases per spec)
**Evidence bundle**: `(w4t13) .blueprint/qa/T13/pytest.txt` — 6 lines

**RED phase**: ⚠️ **RED not documented**. Evidence file is GREEN-only.

**GREEN phase**:
- Command: `pytest tests/data_platform/test_dp_data_source_service.py -q`
- Evidence quote: `...........                                                              [100%]` / `11 passed in 0.31s`

**Test discipline check**:
- ✅ Tests exercise Fernet encryption enabled/disabled, non-owner 403, connection test success/failure, schema describe, CRUD happy path.
- ⚠️ No captured proof of RED-first for these 11 cases; test-with-impl commit path was used.
- ✅ No skips/deletions/weakenings.

---

### T14 — dp-query-service

**Test file**: `backend/tests/data_platform/test_dp_query_service.py` (6 cases per spec)
**Evidence bundle**: `(w4t14) .blueprint/qa/T14/pytest.txt` — 6 lines

**RED phase**: ⚠️ **RED not documented**. Evidence file is GREEN-only.

**GREEN phase**:
- Command: `pytest tests/data_platform/test_dp_query_service.py -q`
- Evidence quote: `......                                                                   [100%]` / `6 passed in 0.46s`

**Retry note** (legitimate blocker recovery, not a discipline violation):
- **First attempt BLOCKED**: T13 hadn't yet committed `DataSourceService`, so T14's tests couldn't import `dp_data_source_service`. Orchestration race.
- **Second attempt succeeded** once T13 was on `main`. Same test cases, same command — no assertions weakened, only the upstream import resolved.

**Test discipline check**:
- ✅ Tests exercise SQL guard rejection path (DROP), LIMIT clamp, execute + stream + history.
- ⚠️ No captured RED artefact for the 6 cases.
- ✅ No skips/deletions/weakenings.

---

### T15 — dp-chat-service

**Test file**: `backend/tests/data_platform/test_dp_chat_service.py` (7 cases per spec)
**Evidence bundle**: `(w4t15) .blueprint/qa/T15/pytest.txt` — 6 lines

**RED phase**: ⚠️ **RED not documented**. Evidence file is GREEN-only.

**GREEN phase**:
- Command: `pytest tests/data_platform/test_dp_chat_service.py -q`
- Evidence quote: `.......                                                                  [100%]` / `7 passed in 0.41s`

**Retry note** (same class as T14):
- **First attempt BLOCKED**: T13 hadn't committed. Legitimate orchestration race, not a test-discipline failure.
- **Second attempt succeeded** on the T13-committed base.

**Test discipline check**:
- ✅ Tests exercise session CRUD, message append, DROP-reject via SQL guard, LLM path monkeypatched.
- ⚠️ No captured RED artefact.
- ✅ No skips/deletions/weakenings.

---

### T16 — kb-service

**Test file**: `backend/tests/knowledge_base/test_kb_service.py` (11 cases per spec)
**Evidence bundle**: `(w4t16) .blueprint/qa/T16/pytest.txt` — 6 lines

**RED phase**: ⚠️ **RED not documented**. Evidence file is GREEN-only.

**GREEN phase**:
- Command: `pytest tests/knowledge_base/test_kb_service.py -q`
- Evidence quote: `...........                                                              [100%]` / `11 passed in 0.23s`

**Test discipline check**:
- ✅ Tests exercise libraries=4 guarantee, data_asset/code_repo/experience CRUD, document upload/download with UPLOAD_DIR override, grouped search 4 buckets, non-owner ACL, tags listing.
- ⚠️ No captured RED artefact for the 11 cases.
- ✅ No skips/deletions/weakenings.

---

### T25 — backend-pytest-coverage

**Test files** (all new integration/gate suites):
- `backend/tests/data_platform/test_dp_routers_integration.py` — 16 cases (DP router e2e)
- `backend/tests/knowledge_base/test_kb_routers_integration.py` — 11 cases (KB router e2e)
- `backend/tests/security/test_auth_gate.py` — 5 cases (401 gate)
- Total new: **32**. Combined with prior suites the run reports **95 passed**.
- Root `conftest.py` also added (StaticPool in-memory sqlite + MEDIUMTEXT/FULLTEXT shim + Fernet autouse).

**Evidence bundle**: `(w7t25) .blueprint/qa/T25/coverage.txt` — 51 lines, includes coverage table.

**RED phase**: ⚠️ **RED artefact NOT preserved in the evidence file** — coverage.txt is a GREEN-only run.
- Worker report and review `25-backend-pytest-coverage.md` describe RED-first discipline for the 3 new suites, but the failing run was overwritten by the passing coverage run.
- Classified: **worker-reported RED-first, no captured artefact**.

**GREEN phase**:
- Command: `pytest -q --cov=app/api/v1/data_platform --cov=app/api/v1/knowledge_base --cov=app/services --cov=app/core/sql_guard --cov=app/core/crypto`
- Evidence quote: `95 passed, 113 warnings in 7.93s`
- Coverage table (from evidence file):
  - `app/api/v1/data_platform/**` — 98–100 % per file
  - `app/api/v1/knowledge_base/**` — 84–100 % per file (docs 84 %, code_repos 91 %, experiences 94 %, others 100 %)
  - `app/services/dp_chat_service.py` — 90 %
  - `app/services/dp_data_source_service.py` — 90 %
  - `app/services/dp_query_service.py` — 85 %
  - `app/services/kb_service.py` — 87 %
  - `app/core/sql_guard.py` — 78 %
  - `app/core/crypto.py` — 71 %
  - **TOTAL: 1149 stmts, 127 miss, 89 % Cover**  (target ≥ 80 %)

**Test discipline check**:
- ✅ Every DP/KB endpoint asserted for owner-scoping, 404, and 401. Auth-gate suite dynamically enumerates ≥ 20 routes and asserts 401 for every non-HEAD/OPTIONS method.
- ✅ LLM path fully mocked via `monkeypatch.setattr(LLMConfigService, "chat_completion", _fake)` — zero real network calls.
- ✅ Diff scoped to `backend/tests/**` + `backend/requirements.txt` (added `pytest-cov==7.1.0`) + evidence file. No prod code changed to force GREEN.
- ✅ No skips, no `xfail`, no test deletions.
- ⚠️ 89 % is a run-time snapshot; RED-first proof for the 32 new cases is not in the evidence bundle.

---

### T26 — frontend-vitest

**Test files** (all new suites):
- `frontend/src/components/common/__tests__/SchemaTree.test.tsx` — 4 cases
- `frontend/src/services/__tests__/knowledgeBase.service.test.ts` — 4 cases
- `frontend/src/stores/__tests__/dataPlatformStore.test.ts` — 3 cases
- `frontend/src/stores/__tests__/knowledgeBaseStore.test.ts` — 2 cases
- `frontend/src/pages/data-platform/__tests__/SourceDetailPage.test.tsx` — 2 cases
- `frontend/src/pages/knowledge-base/__tests__/KbSearchPage.test.tsx` — 3 cases
- Total new: **18**. Combined with pre-existing suites the run reports **10 files / 29 tests passing**.

**Evidence bundle**: `(w7t26) .blueprint/qa/T26/vitest.txt` — 121 lines, includes v8 coverage table.

**RED phase**: ⚠️ **RED artefact NOT preserved in the evidence file** — vitest.txt is a GREEN-only run.
- Worker report and review `26-frontend-vitest.md` document RED-first discipline: the 6 new suites imported components/stores that did not previously satisfy the tested contracts (URL-driven state in `KbSearchPage`, per-source schema caching in `dataPlatformStore`, snake→camel mapping in service).
- Classified: **worker-reported RED-first, no captured artefact**.

**GREEN phase**:
- Command: `bun run test:cov` (vitest + v8 coverage)
- Evidence quote:
  - ` Test Files  10 passed (10)`
  - `      Tests  29 passed (29)`
  - `   Duration  2.13s`
- Coverage highlights from evidence file:
  - `SchemaTree.tsx` — 93.1 % lines
  - `DataTable.tsx` — 97.56 % lines
  - `dataPlatformStore.ts` — 82.35 %
  - `knowledgeBaseStore.ts` — 78.26 %
  - `dataPlatform.service.ts` — 28.5 % (only mapper paths under test — expected per spec)
  - `knowledgeBase.service.ts` — 47.39 %
  - Overall: `All files | 45.24 | 71.31 | 31.42 | 45.24` — repo-wide coverage number is a v8 artefact including untouched services; per-target coverage on the new suites meets spec.

**Test discipline check**:
- ✅ `ResizeObserver` polyfill added inline per-suite (SchemaTree, KbSearchPage, SourceDetailPage). `test-setup.ts` untouched, per spec's "T26 out-of-scope for test-setup" constraint.
- ✅ Diff scoped strictly to `frontend/src/**/__tests__/*` + evidence file. `frontend/package.json` untouched, no new deps.
- ✅ No skips, no `.only`, no `.skip`, no test deletions.
- ✅ AntD Space + Tabs deprecation warnings surface at run time but are page-code cosmetic, not test-discipline issues.
- ⚠️ RED-first proof for the 18 new cases is not in the evidence bundle.

---

## Findings

1. **Strict RED-first artefact only captured for T05**. `.blueprint/qa/T05/pytest.txt` explicitly labels a `=== RED phase (module unimplemented) ===` block with `ModuleNotFoundError` before the GREEN run. This is the only test-producing task where the evidence file itself contains both phases.
2. **T25 and T26 workers report RED-first discipline in prose** (review files describe the failing behaviors the new suites were written to lock in), but the failing pytest/vitest run was overwritten by the passing coverage run. RED artefact loss is a persisted-evidence gap, not a proven discipline failure.
3. **T09, T13, T14, T15, T16 services** were driven test-and-impl-together. Tests DO exercise the intended negative branches (Fernet disabled, SQL guard DROP-reject, non-owner ACL, 4-bucket search bucket presence, etc.) but there is no historical run showing them failing before the code existed.
4. **No tests were weakened, deleted, skipped, or `xfail`-ed** to force GREEN across any of the 8 tasks. Reviews `05`, `09`, `13`, `15`, `16`, `25`, `26` all explicitly confirm scope discipline and diff-stat purity.
5. **T14 and T15 first-attempt failures were orchestration races** (T13 hadn't landed `DataSourceService` on `main`), not TDD failures. Second attempts on the T13-committed base passed cleanly with the same assertions.
6. **Coverage bar met**: T25 lands **89 % total** on DP/KB service+router modules (≥ 80 % contract). T26's v8 report is repo-wide-diluted but per-target modules (`SchemaTree.tsx` 93 %, `DataTable.tsx` 98 %, both stores > 78 %) all meet spec.
7. **Recommendation for future runs**: workers should preserve a first-run failing pytest/vitest output (`tee -a <task>-red.txt`) BEFORE running the GREEN suite. The single-file overwrite pattern used by T25/T26 loses TDD provenance.
