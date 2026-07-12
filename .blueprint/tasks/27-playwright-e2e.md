# T27 — Playwright E2E scenarios

## Goal
Full end-to-end user journeys against a live dev backend + frontend.

## Files touched
- `frontend/tests/e2e/nav.spec.ts`  (already stubbed T20)
- `frontend/tests/e2e/dp-sources-list.spec.ts`  (already stubbed T21)
- `frontend/tests/e2e/dp-source-detail.spec.ts`  (already stubbed T22)
- `frontend/tests/e2e/dp-sql-guard.spec.ts`  (NEW — asserts DROP TABLE returns error toast, not execution)
- `frontend/tests/e2e/dp-chat-stream.spec.ts`  (NEW — asserts SSE tokens streamed)
- `frontend/tests/e2e/kb-sublibs.spec.ts`  (already stubbed T23)
- `frontend/tests/e2e/kb-search.spec.ts`  (already stubbed T24)
- `frontend/tests/e2e/kb-upload-download.spec.ts`  (NEW)
- `frontend/tests/e2e/perception-regression.spec.ts`  (NEW — legacy page still opens)
- `frontend/tests/e2e/fixtures.ts`  (NEW — login helper mints JWT via API)

## Depends on
- T25, T26

## Implementation notes
- `playwright.config.ts` `webServer` boots backend on 8000 + frontend on 5173.
- Fixture creates a test user + auth token, injects into localStorage.
- Screenshot per scenario saved to `.blueprint/qa/T27/screenshots/`.

## Acceptance
- `bunx playwright test` — 9 specs green.
- Screenshots exist for all specs.

## Verify
```bash
cd frontend && bunx playwright test --reporter=list | tee ../.blueprint/qa/T27/playwright.txt
```

## Commit
`tests: Playwright E2E (9 scenarios + regression)`
