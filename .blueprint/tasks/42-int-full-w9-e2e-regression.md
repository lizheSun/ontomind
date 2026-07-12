# T42 · int-full-w9 integration + E2E regression

## Goal
Build `blueprint/int-full-w9-final` = int-full-w9 + T40 + T41. Run full regression suite.

## Files touched
- `frontend/tests/e2e/agent-looper.spec.ts` (NEW — 3 tests: list page loads, discover button, wizard opens)
- `.blueprint/qa/T42/playwright.txt`
- `.blueprint/qa/T42/merge-log.txt`

## Depends on
- T41

## Integration
```
git checkout -b blueprint/int-full-w9-final blueprint/int-full-w9
git merge --no-ff blueprint/40-agent-picker-component
git merge --no-ff blueprint/41-inject-agent-picker
```
Boot backend 8007 + frontend 5186, run Playwright.

## Verify
- 103 backend pytest
- 32+ frontend vitest
- 21+ Playwright (14 baseline + 3 agent-looper + 3 Wave 8 + 1 additional)

## Commit
`tests: Wave 9 E2E + int-full-w9-final regression`
