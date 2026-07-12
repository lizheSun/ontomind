# T24 — /knowledge-base/search page

## Goal
Global aggregated search across 4 sub-libs; grouped result cards with library filter chips; deep-link `/knowledge-base/search?q=…`.

## Files touched
- `frontend/src/pages/knowledge-base/KbSearchPage.tsx`  (NEW)
- `frontend/src/pages/knowledge-base/components/SearchResultCard.tsx`  (NEW)

## Depends on
- T03, T12, T19, T20

## Implementation notes
- On mount / query change → call `GET /knowledge-base/search?q=...`.
- Group headers: 数据资产 / 代码库 / 文档库 / 业务经验库.
- Click result → navigate to owning sub-lib page (pre-filter or scroll to row).
- Highlight matched substring in title/snippet.

## Acceptance
- Search "test" returns grouped results; click card navigates to owning page.

## Verify
```bash
cd frontend && bunx playwright test tests/e2e/kb-search.spec.ts | tee ../.blueprint/qa/T24/pw.txt
```

## Commit
`ui: knowledge-base global aggregated search page`
