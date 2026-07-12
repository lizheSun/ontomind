# T28 Visual QA + Regression — Review

Commit: `58d8720` on `blueprint/28-visual-qa-regression` (base `blueprint/int-full-w6`).

## Verdict
APPROVE

## Reasoning
- All 9 acceptance criteria met. Diff scope is clean: only `frontend/tests/visual/screenshots.spec.ts` and `.blueprint/qa/T28/**`. `git diff --stat ... -- backend frontend/src` returns empty — zero product-source changes.
- **15 tests present** — `screenshots.spec.ts` loops 5 pages × 3 viewports: `dp-sources`, `kb-data-assets`, `kb-search`, `perception-legacy`, `dashboard` × `375/768/1280`. ✅
- **JWT injection** — same shape as T27: `POST /api/v1/auth/login {admin,admin123}` → `page.addInitScript` writes `localStorage.access_token` before navigation. ✅
- **15 PNGs present** in `.blueprint/qa/T28/screenshots/` — `ls | wc -l` = 15, one per (page, viewport) tuple. ✅
- **pageerror assertion** — new pages are enforced clean (`expect(pageErrs, ...).toEqual([])`), legacy `perception-legacy` and `dashboard` (`/`) are excluded from the assertion via `if (!['perception-legacy', 'dashboard'].includes(p.slug))`. Console log confirms `pageerror: 0` on all 15 tests. ✅
- **console.error capture** — `console.log` records `console.error` count + first 5 samples for every test (152 lines total, one section per test). CORS preflight failures (5180 → 8005) show up as expected environment noise and are documented as Known Limitation #5 in `summary.md`. ✅
- **summary.md** — 129 lines: 28-row task inventory with per-task evidence paths, integration-branch topology table, verification totals (backend 95 tests / 89% coverage, frontend 29 vitest, 15 visual PNGs), 5 known limitations (SSE, charset default, default_schema clear, /perception coexistence, backend CORS not configured for arbitrary dev ports), signed-off statement at top and bottom. ✅
- **Temporary `playwright.visual.config.ts`** — not present in the worktree tree and not in the commit; the spec lives at `frontend/tests/visual/screenshots.spec.ts` and was run via an out-of-tree config (as expected, since the committed `playwright.config.ts:testDir` points at `./tests/e2e`). ✅
- **All 15/15 pass** — evidenced by full-populated `screenshots/` (15 PNGs, one write per successful test) and per-test `pageerror: 0` in `console.log`. ✅

## Required changes
_None._

## Nice-to-haves (non-blocking, per orchestrator)
- `summary.md`'s T27 row claims "11 specs, 8 files" — the T27 commit that landed after this one is actually **8 spec files / 14 tests**. Orchestrator flagged this as a follow-up patch outside this review.
- `console.error` counts (6–16 per test) are almost entirely CORS-preflight failures caused by running the FE on `:5180` against a BE on `:8005` without a matching allow-origin. Not a product defect; already documented as Known Limitation #5.
