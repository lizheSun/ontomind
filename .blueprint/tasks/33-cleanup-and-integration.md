# T33 · Legacy /perception cleanup + int-full-w8 + E2E regression

## Goal
- Deprecate legacy `pages/perception/index.tsx` data-source CRUD + smart-add halves (only metadata browse remains, but that's already migrated to MetadataPage in T30). Legacy file can stay on disk but the route `/perception` now points to PerceptionShell (T29).
- Add redirect: `/perception-legacy` → `/perception` (in case anyone bookmarked)
- Build `blueprint/int-full-w8` integration branch = int-full-w6 + T29 + T30 + T31 + T32
- Run Playwright regression E2E on the merged branch

## Files touched
- `frontend/src/App.tsx` (add `<Route path="perception-legacy" element={<Navigate to="/perception" replace />} />`)
- `frontend/tests/e2e/perception-shell.spec.ts` (NEW — 3 tests: shell renders, cards click, /perception-legacy redirects)
- `frontend/tests/e2e/dp-metadata.spec.ts` (NEW — 2 tests: MetadataPage loads, sub-nav switches)
- `frontend/tests/e2e/dp-smart-add.spec.ts` (NEW — 2 tests: modal opens, parse triggers drawer)
- `.blueprint/qa/T33/playwright.txt`
- `.blueprint/qa/T33/int-w8-log.txt` (integration build log)

## Depends on
- T29, T30, T31, T32 all committed

## Integration steps
1. `git checkout main` (or int-full-w6)
2. `git checkout -b blueprint/int-full-w8 blueprint/int-full-w6`
3. `git merge --no-ff blueprint/29-perception-shell-menu-cleanup`
4. `git merge --no-ff blueprint/30-metadata-migration` (expect App.tsx conflict — both add routes)
5. `git merge --no-ff blueprint/31-parse-config-endpoint` (backend disjoint — clean)
6. `git merge --no-ff blueprint/32-smart-add-ui` (extends dataPlatform.service — clean)
7. Boot backend + frontend, run Playwright regression suite

## Acceptance
- Wave-1-7 tests still pass (63 pytest, 29 vitest, 14 E2E baseline)
- Wave-8 adds 7+ E2E tests, all pass
- Total: ~90 backend pytest + ~30 frontend vitest + ~21 E2E — all green

## Commit
`tests: Wave 8 E2E (perception shell + metadata migration + smart-add)`
