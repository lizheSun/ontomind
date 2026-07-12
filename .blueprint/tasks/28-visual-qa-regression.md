# T28 — visual QA + regression + final review

## Goal
Manual + automated visual QA against 3 viewport widths (375 / 768 / 1280); Lighthouse quick check; ensure legacy `/perception` still loads; produce `.blueprint/qa/summary.md` and final wave7 commit.

## Files touched
- `.blueprint/qa/summary.md`  (NEW — evidence index)
- `frontend/tests/visual/*.spec.ts`  (NEW — screenshot diff optional)

## Depends on
- T21, T22, T23, T24

## Implementation notes
- Playwright screenshots at 375 / 768 / 1280 for: `/data-platform/sources`, `/data-platform/sources/:sid` (each tab), `/knowledge-base/data-assets`, `/knowledge-base/search?q=测试`, `/perception` (legacy regression).
- Assert:
  - No console errors.
  - `<PageHeader>` present on every new page.
  - `<GlassPanel>` present ≥1 per page.
  - No AntD default color (`#1677ff`) leaking — should be replaced by `--accent`.
  - AntD `<Empty>` state renders on empty tables.
- Lighthouse (Chromium via Playwright) accessibility ≥90 for both surfaces.

## Acceptance
- `.blueprint/qa/summary.md` lists every prior task with its `verify` evidence path, and PASS/FAIL flag.
- Zero regressions on `/perception`.

## Verify
```bash
cd frontend && bunx playwright test tests/visual --reporter=list | tee ../.blueprint/qa/T28/visual.txt
cat .blueprint/qa/summary.md
```

## Commit
`chore: perception-layer wave7 verification (screenshots + summary)`
