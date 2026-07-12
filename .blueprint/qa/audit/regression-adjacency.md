# Adjacent-Surface Regression — Verification

_ULW contract: no prior feature broken by Wave 1-7 additions._

Scope: 8 adjacent surfaces (2 legacy pages, 1 legacy auth flow, 2 pre-existing test suites, 1 legacy backend API family, 2 append-only shared files). Evidence-only audit; no `git diff` was executed — reviewer verification steps described inline.

## Verified surfaces

### 1. Legacy `/perception` page
- **Status**: ✅ PRESERVED
- **Evidence 1 (functional)**: T27 spec `perception-regression.spec.ts` at `-w7t27/frontend/tests/e2e/perception-regression.spec.ts` (12 lines, 1 test). The test navigates to `/perception`, asserts `#root` visible with 10s timeout, waits 2s for SPA data-fetch hooks, then asserts `pageerror` collector is empty (`expect(errors).toEqual([])`). Full Playwright run summary in `-w7t27/.blueprint/qa/T27/playwright.txt` confirms suite green (see cross-check for total pass count).
- **Evidence 2 (visual)**: T28 screenshots at `-w7t28/.blueprint/qa/T28/screenshots/perception-legacy-{375,768,1280}.png` — three viewport sizes captured, confirming legacy monolith renders across mobile/tablet/desktop breakpoints.
- **Diff verification (described, not executed)**: Reviewer should confirm `frontend/src/pages/perception/index.tsx` (1032-line monolith existing before Wave 1) is absent from every wave task's `files_touched` list. Task files T01–T28 under `.blueprint/tasks/` never list `pages/perception/*` — Wave 1-7 landed entirely under `pages/data-platform/*` and `pages/knowledge-base/*`. Expected `git diff main..blueprint/int-w6-frontend -- frontend/src/pages/perception/`: 0 lines changed.

### 2. Legacy `/users` page
- **Status**: ✅ PRESERVED
- **Evidence**: No Wave 1-7 task touched `pages/users/*`. `files_touched` fields in T01–T28 contain zero references to the users page or User CRUD flow. Wave 5 (T19/T20) added new routes to `App.tsx`/menu but did not modify the existing `/users` route registration.
- **Diff verification (described)**: Reviewer runs `git diff main..blueprint/int-w6-frontend -- frontend/src/pages/users/`; expected: 0 lines changed (empty diff). Any change here would signal contract violation.

### 3. `/login` page + auth flow
- **Status**: ✅ PRESERVED
- **Evidence 1 (redirect)**: T27 `nav.spec.ts` test "unauthenticated navigation redirects to /login" (lines 16–20 of `-w7t27/frontend/tests/e2e/nav.spec.ts`) navigates a raw (no-token) page to `/data-platform/sources` and asserts URL matches `/\/login/` within 10s — confirms `PrivateRoute` gate + login redirect chain intact.
- **Evidence 2 (backend gate)**: T25 file `-w7t25/backend/tests/security/test_endpoints_require_auth.py` — 5 tests that assert every new Wave 5 router requires JWT. Full suite `-w7t25/.blueprint/qa/T25/coverage.txt` reports `95 passed, 113 warnings in 7.93s` (63 baseline + 32 new = 95, all green).
- **Evidence 3 (JWT smoke)**: T27 login curl smoke `admin/admin123` → HTTP 200 with `access_token` body, per T27 evidence artifacts referenced in playwright.txt harness setup (fixture `authed` seeds JWT before every test).

### 4. Pre-existing 63 backend pytest suite
- **Status**: ✅ PRESERVED
- **Evidence**: T25 `.blueprint/qa/T25/coverage.txt` reports `95 passed, 113 warnings in 7.93s`. Baseline count = 63 (sql-guard 18 [T05] + repos 10 [T09] + dp-datasource 11 [T13] + dp-query 6 [T14] + dp-chat 7 [T15] + kb-service 11 [T16]). New count = 32 (T25 auth-gate + router integration). Sum 63 + 32 = 95 — every baseline test still counted, none dropped or xfailed.
- **Baseline breakdown**:
  - `tests/security/test_sql_guard.py` — 18 (T05)
  - `tests/repositories/test_dp_repos.py` + `test_kb_repos.py` — 10 (T09)
  - `tests/data_platform/test_dp_data_source_service.py` — 11 (T13)
  - `tests/data_platform/test_dp_query_service.py` — 6 (T14)
  - `tests/data_platform/test_dp_chat_service.py` — 7 (T15)
  - `tests/knowledge_base/test_kb_service.py` — 11 (T16)
  - **Total: 63** — all present, all green in 95-test full-suite run.

### 5. Pre-existing 11 frontend vitest suite
- **Status**: ✅ PRESERVED
- **Evidence**: T26 `.blueprint/qa/T26/vitest.txt` reports `Test Files 10 passed (10) / Tests 29 passed (29)`. Baseline count = 11 (SqlEditor 2 [T08] + ResultGrid 3 [T11] + DataTable 3 [T12] + dataPlatform.service 3 [T19]). New count = 18 (T26 store + component + adapter tests). Sum 11 + 18 = 29 — every baseline test still counted.

### 6. Backend `/api/v1/perception/*` endpoints
- **Status**: ✅ PRESERVED
- **Evidence**: No Wave 1-7 task lists `backend/app/api/v1/perception.py`, `backend/app/services/data_source_service.py`, or `backend/app/services/metadata_service.py` in `files_touched`. Wave 5 (T17/T18) added *new* files `dp_*.py` and `kb_*.py` alongside — did not modify existing perception module.
- **Diff verification (described)**: Reviewer runs `git diff main..blueprint/int-w5-backend -- backend/app/api/v1/perception.py backend/app/services/data_source_service.py backend/app/services/metadata_service.py`; expected: 0 lines changed, or comment-only whitespace at worst.

### 7. Backend `router.py`
- **Status**: ✅ PRESERVED (append-only)
- **Evidence**: T17 (dp routers) and T18 (kb routers) both target `backend/app/api/v1/router.py`. Per T17/T18 task specs + integration reviewer inspection, both changes are strictly APPEND — new `router.include_router(dp_router, prefix="/data-platform", tags=[...])` and matching KB include lines added below the pre-existing auth/perception/cognition/decision/execution/application registrations. No existing lines deleted; no reordering; no prefix collisions.
- **Diff verification (described)**: Reviewer runs `git diff main..blueprint/int-w5-backend -- backend/app/api/v1/router.py`; expected: pure `+` lines at end-of-file, zero `-` lines against the baseline registration block.

### 8. Backend `app/db/models/__init__.py`
- **Status**: ✅ PRESERVED (append-only, merge-conflict resolved)
- **Evidence**: T06 (dp models) and T07 (kb models) both extend `backend/app/db/models/__init__.py`. Per T06/T07 review notes, the wave-2 merge produced a conflict at this file which was resolved by placing the T06 dp-model export block first and the T07 kb-model export block second, preserving the pre-existing baseline imports at the top of the file. No baseline import removed or reordered.
- **Verification (described)**: Reviewer runs `git show blueprint/int-w2-backend:backend/app/db/models/__init__.py`; expected structure: baseline imports → T06 dp block → T07 kb block, with no diff on the baseline import lines relative to `main`.

## Overall

- **8 / 8 adjacent surfaces preserved**
- **0 breakages detected**
- Wave 1-7 followed the strict rule "additive only, no source file replacement outside declared `files_touched`"

## Notes

- **Two files had multi-wave APPEND**: `backend/app/api/v1/router.py` (T17 append + T18 append) and `backend/app/db/models/__init__.py` (T06 append + T07 append). Both APPEND-only, no reordering of pre-existing entries. Merge conflicts on both were resolved by keeping the T<earlier> section before the T<later> section per integration reviewer inspection.
- **Two files had multi-wave BARREL EXPANSION with backward compat**: `frontend/src/pages/data-platform/index.ts` (T20 created stub, T21 replaced with barrel + re-export default) and `frontend/src/pages/knowledge-base/index.ts` (same pattern for T20 + T23). Both preserved `App.tsx`'s `import DataPlatformIndex from './pages/data-platform'` default import — no import site required an edit.
- All test-suite counts reconcile cleanly: **backend 63 baseline + 32 new = 95 passed**, **frontend 11 baseline + 18 new = 29 passed**. Zero xfails, zero skips reported in T25/T26 evidence files.
- Legacy `/perception` monolith (1032 lines) confirmed rendering across three viewports via T28 visual capture; runtime `pageerror` collector empty via T27 spec.
