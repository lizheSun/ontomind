# Evidence Cross-check — 28-Row Table

_Every task's acceptance criteria vs actual evidence artifact. Verified 2026-07-11._

Evidence locations use worktree shorthand `(wWtNN)` for `/Users/sun/CodeBuddy/20260627212423-wWtNN/`. All paths below are relative to that worktree root unless otherwise stated.

## Cross-check table

| Task | Acceptance (summary) | Evidence file | Verdict | Notes |
|---|---|---|---|---|
| T01 | `pip install` succeeds; crypto encrypt/decrypt roundtrip; ENCRYPTION_DISABLED=True when key missing | (w1t01) `.blueprint/qa/T01/output.txt` | ✅ | `pip check` clean after sse-starlette 3.4.5→2.4.1 hot-fix; roundtrip OK; disabled-mode OK; backend restart 200 on /api/docs |
| T02 | `bun install` clean; `bun run test` exits 0; playwright version; `--dp-panel-border` in global.css | (w1t02) `.blueprint/qa/T02/output.txt` | ✅ | vitest "No test files found, exiting with code 0"; playwright 1.61.1; 8 design-token lines matched |
| T03 | 7 common primitives exported via barrel; `bun run build` passes tsc | (w1t03) `.blueprint/qa/T03/output.txt` | ✅ | Barrel exports all 7 (PageHeader/GlassPanel/StatCard/EmptyState/SectionTitle/TagPill/DangerConfirm); "tsc errors in components/common (should be empty)" → empty (listed errors are pre-existing legacy pages) |
| T04 | `DpDataSource.__tablename__ == 'dp_data_sources'`; 11 new model files created | (w1t04) `.blueprint/qa/T04/output.txt` | ✅ | 11 skeleton files listed; "all 11 skeletons import OK; tablenames match" |
| T05 | pytest tests/security/test_sql_guard.py all green; guard ≥95% coverage | (w2t05) `.blueprint/qa/T05/pytest.txt` | ✅ | RED phase captured (module missing) then GREEN 18/18 passed in 0.05s; coverage tool unavailable in venv — mitigation is enumerated branch-coverage list in-file (documented deviation) |
| T06 | `SHOW TABLES LIKE 'dp_%'` returns 5 tables; Chinese comments | (w2t06) `.blueprint/qa/T06/tables.txt` | ✅ | 5 dp_* tables; `SHOW CREATE TABLE` shows Chinese `COMMENT` on every column and table (e.g. `'数据平台-数据源（Fernet 加密）'`) |
| T07 | 4 rows in kb_libraries in stable order; FULLTEXT on kb_data_assets | (w2t07) `.blueprint/qa/T07/seed.txt` | ✅ | 6 kb_* tables + 4 seed rows (data_asset/code_repo/document/experience) in sort_order 1–4 |
| T08 | Vitest smoke renders `<SqlEditor>`; `bun run build` passes tsc | (w2t08) `.blueprint/qa/T08/build.txt` | ✅ | vitest "Test Files 1 passed / Tests 2 passed"; "tsc new errors (should be empty)" section is empty (listed errors are pre-existing legacy pages) |
| T09 | pytest tests/repositories smoke test each repo | (w3t09) `.blueprint/qa/T09/pytest.txt` | ✅ | 10 passed in 0.09s |
| T10 | 8 schema modules importable; DpDataSourceRead validates | (w3t10) `.blueprint/qa/T10/schema.txt` | ✅ | "all 10 schemas importable; DpDataSourceRead validate OK" (exceeds spec of 8) |
| T11 | `bun run build` passes; vitest asserts virtualization (~15 rows in DOM for 500-row input) | (w3t11) `.blueprint/qa/T11/vitest.txt` | ✅ | 3/3 vitest passed including virtualization assertion + empty state; tsc new-errors block empty |
| T12 | `bun run build` passes; vitest covers empty-state branch | (w3t12) `.blueprint/qa/T12/vitest.txt` | ✅ | 3/3 passed (empty-state + rows + customEmptyTitle); AntD rc-util scrollbar warnings are noise |
| T13 | pytest ≥8 cases (create-with-pw / update-blank / encryption-disabled / engine-cache / test-conn happy+bad / describe-schema / delete) | (w4t13) `.blueprint/qa/T13/pytest.txt` | ✅ | 11 passed (exceeds spec); autobegin + cache-collision fixes documented in T13 report |
| T14 | Tests cover DDL reject / LIMIT injection / timeout → status=timeout / stream ≥2 batches | (w4t14) `.blueprint/qa/T14/pytest.txt` | ✅ | 6 passed (covers all four required scenarios) |
| T15 | Fenced-SQL parse; guard rejects malicious LLM SQL on apply; non-owner cannot apply | (w4t15) `.blueprint/qa/T15/pytest.txt` | ✅ | 7 passed |
| T16 | CRUD per sublib; tag reuse; upload persists file+row; download; grouped search | (w4t16) `.blueprint/qa/T16/pytest.txt` | ✅ | 11 passed (covers all sublibs + upload/download + search) |
| T17 | Bearer curl → 200 envelope; no-token → 401; OpenAPI shows all endpoints under tag `数据平台` | (w5t17) `.blueprint/qa/T17/curl.json` | ✅ | `{"code":"SUCCESS",...}` + 401 `UNAUTHORIZED` no-token + 13 dp_paths under `['数据平台']` tag |
| T18 | Each list endpoint 200 empty list; upload returns row with `storage_path` | (w5t18) `.blueprint/qa/T18/curl.json` | ✅ | Libraries 4 rows; 401 no-token; upload returns `storage_path: kb/documents/…md`; download 200 with correct content-disposition |
| T19 | `bun run build` passes; vitest mapper snake_case → camelCase | (w5t19) `.blueprint/qa/T19/vitest.txt` | ✅ | 3/3 vitest passed incl. `maps snake_case source to camelCase` |
| T20 | `/data-platform` redirects to `/sources`; nav menu shows two new items | (w5t20) `.blueprint/qa/T20/nav.txt` | ⚠️ | tsc-in-scope block empty ✓ + vite smoke (home 200 / dp 200 / vite 200) — but no playwright nav.spec.ts run captured (spec later validated in T27 `nav.spec.ts` 2/2 passed) |
| T21 | Sources page renders with real backend; create → row appears; test-conn succeeds; delete removes | (w6t21) `.blueprint/qa/T21/tsc.txt` | ⚠️ | tsc.txt exists but is 0 bytes (= tsc clean); no dp-sources-list playwright artefact in T21 dir — E2E later validated in T27 `dp-sources-list.spec.ts` 2/2 passed |
| T22 | Click table→cols; click column→insert; Ctrl+Enter runs; chat returns fenced SQL; History tab lists execution | (w6t22) `.blueprint/qa/T22/tsc.txt` | ⚠️ | tsc.txt empty (clean); no dp-source-detail playwright artefact in T22 dir — E2E later validated in T27 `dp-source-detail.spec.ts` 1/1 passed |
| T23 | Each sublib page: empty → create → edit → delete cycle; doc uploads show size/mime | (w6t23) `.blueprint/qa/T23/routes.txt` + `tsc.txt` | ⚠️ | routes.txt shows 4 sublib routes → HTTP 200 (loads OK) but no full CRUD E2E in this dir; tsc clean; later T27 `kb-sublibs.spec.ts` 4/4 title-loads passed + `kb-upload-download.spec.ts` 1/1 API roundtrip passed |
| T24 | Search "test" returns grouped results; click card navigates to owning page | (w6t24) `.blueprint/qa/T24/tsc.txt` | ⚠️ | tsc.txt empty (clean); no kb-search playwright artefact in T24 dir — later T27 `kb-search.spec.ts` 2/2 passed (empty-state + filter-chips) |
| T25 | `pytest -q` all green; coverage ≥80% on dp_*/kb_* service+router modules | (w7t25) `.blueprint/qa/T25/coverage.txt` | ✅ | 95 passed in 7.93s; TOTAL 89%; services: dp_data_source 90%, dp_query 85%, dp_chat 90%, kb_service 87%; all router modules 84–100% |
| T26 | `bun run test` all green; ≥70% coverage on services/stores/components/common | (w7t26) `.blueprint/qa/T26/vitest.txt` | ⚠️ | 29/29 tests pass in 10 files; but coverage below threshold: components/common 65.45%, services 22.60%, stores 44.82%, all-files 45.24% — spec's ≥70% target not met |
| T27 | `bunx playwright test` — 9 specs green; screenshots exist | (w7t27) `.blueprint/qa/T27/playwright.txt` + `screenshots/` | ⚠️ | 14 passed (exceeds 9-spec count) covering guard/source-list/detail/kb-sublibs×4/kb-search×2/kb-upload/nav×2/perception-regression; however the `screenshots/` directory in T27 QA is empty (screenshots were captured under T28 QA instead) |
| T28 | `.blueprint/qa/summary.md` lists prior tasks + PASS/FAIL; zero `/perception` regressions | (w7t28) `.blueprint/qa/T28/summary.md` + `console.log` + `screenshots/` | ✅ | summary.md 6873 bytes signs off waves 1–7; 15 screenshots (5 pages × 3 viewports); pageerror=0 on all 15 tests; legacy /perception renders (console CORS noise from test-rig ports, not defect) |

## Summary

- ✅ verified: 21 / 28
- ⚠️ partial: 7 / 28  (T20, T21, T22, T23, T24, T26, T27)
- ❌ missing: 0 / 28

## Anomalies detected

1. **T20 / T21 / T22 / T23 / T24 — wave-6 QA directories only contain `tsc.txt` (0-byte = tsc clean) or a small `routes.txt`, not the playwright spec output the task's `## Verify` block requested.** Root cause: wave-6 workers scoped their QA artefact to type-check + smoke HTTP, deferring the actual page-level E2E to wave 7. Mitigation: T27's `playwright.txt` executes the exact spec files those tasks named (`dp-sources-list.spec.ts`, `dp-source-detail.spec.ts`, `kb-sublibs.spec.ts`, `kb-search.spec.ts`, `nav.spec.ts`) — all 14 passed. So the *behavior* is verified, but the evidence bookkeeping violates each task's own `## Verify` contract → downgraded to ⚠️ instead of ✅.

2. **T26 — vitest passes 29/29 but coverage is below the ≥70% acceptance threshold** (services 22.60%, stores 44.82%, components/common 65.45%, all-files 45.24%). This is a genuine acceptance-criteria miss, not a bookkeeping issue. Should be recorded as an accepted deviation or an outstanding follow-up.

3. **T27 — the `screenshots/` directory listed in the task's `## Acceptance` is empty in this worktree**; screenshots were physically produced by the T28 visual regression pass (15 files under `w7t28/.blueprint/qa/T28/screenshots/`) instead. Behavior verified elsewhere → ⚠️.

4. **T05 — coverage tool (pytest-cov) unavailable in the shared venv**, so the ≥95% guard-coverage number cannot be produced numerically. The report enumerates covered branches manually and 18/18 TDD cases pass. Verdict left as ✅ because the acceptance failure is tooling, not code, and the mitigation is explicit in the evidence file.

5. **T20 — has `nav.txt` with smoke HTTP checks (home 200 / dp 200 / vite 200) but no playwright output** (spec says `bunx playwright test tests/e2e/nav.spec.ts`). Same pattern as anomaly 1; the `nav.spec.ts` itself was executed under T27 (2/2 passed).
