# T27 Playwright E2E — Review

Commit: `e5aa4c8` on `blueprint/27-playwright-e2e` (base `blueprint/int-full-w6`).

## Verdict
APPROVE

## Reasoning
- All 13 acceptance criteria met. Diff scope is clean: only `frontend/playwright.config.ts`, `frontend/tests/e2e/**` (8 spec files + `fixtures.ts`), and `.blueprint/qa/T27/playwright.txt`. `git diff --stat ... -- backend frontend/src` returns empty — zero source-code changes.
- `fixtures.ts` mints a JWT via `POST /api/v1/auth/login {admin,admin123}`, extracts `body.data.access_token`, seeds it into `localStorage.access_token` via `page.addInitScript` before navigation. Matches spec exactly.
- Spec-by-spec check:
  1. `nav.spec.ts` — 2 tests: top-nav shows 数据平台 + 知识库, click → `/data-platform/sources` and `/knowledge-base/data-assets`; unauth `page` fixture redirects to `/login` ✅
  2. `dp-sources-list.spec.ts` — 2 tests: header/subtitle "数据平台 · 数据源" + "连接、探查…", drawer opens with MySQL/PostgreSQL/SQLite Segmented ✅
  3. `dp-source-detail.spec.ts` — 1 test: API-creates a sqlite source via `POST /data-platform/sources`, navigates to `/data-platform/sources/{sid}`, requires ≥3-of-4 tab labels (SQL 编辑器/AI 对话/执行历史/保存的查询) ✅
  4. `dp-sql-guard.spec.ts` — 1 test: types `DROP TABLE users` via `.monaco-editor` click + Ctrl+A + type; asserts `.ant-message-error, .ant-notification-notice-error, .ant-alert-error` visible ✅
  5. `kb-sublibs.spec.ts` — 4 parameterized tests for the 4 sub-lib pages with Chinese titles (数据资产 / 代码库 / 文档库 / 业务经验库) ✅
  6. `kb-search.spec.ts` — 2 tests: pre-search empty state (输入关键词开始搜索) + URL-driven `?q=test` shows filter chips (全部 + 数据资产) ✅
  7. `kb-upload-download.spec.ts` — 1 test: API-uploads a markdown blob → API-downloads → asserts body contains "e2e test doc" ✅
  8. `perception-regression.spec.ts` — 1 test: /perception loads with `errors` (pageerror) array `.toEqual([])` ✅
- Evidence file `.blueprint/qa/T27/playwright.txt` shows **14 passed (54.9s)** — matches 8 spec / 14 test count.
- `playwright.config.ts`: baseURL flipped to `http://127.0.0.1:5179`, backend to `http://127.0.0.1:8004` via the `PLAYWRIGHT_BACKEND_URL`/`PLAYWRIGHT_BASE_URL` env defaults. Comment documents that the T27 dev servers are booted externally by the task runner on 8004/5179.
- CORS workaround: as documented, the worker used a `CORS_ORIGINS='["http://127.0.0.1:5179",...]'` env override at backend boot — no changes to `backend/`, `config.py`, or `.env` (verified by `git diff --stat -- backend`). The `admin/admin123` credential is used consistently and results in a `200 OK` login (evidenced by dependent tests passing).

## Required changes
_None._

## Nice-to-haves (non-blocking)
- Login curl proof for `admin/admin123` isn't materialized as a standalone artifact in `.blueprint/qa/T27/`; the evidence is transitive (14 tests that call `/auth/login` all pass). Consider adding a `login.json` snapshot in a future evidence sweep.
- `test-results/` (Playwright's per-run temp dir) is not gitignored inside the worktree — acknowledged as transient/known-not-blocking.
