# T20 — App.tsx routes + AppLayout menu

## Goal
Register new routes and menu entries; add index redirects.

## Files touched
- `frontend/src/App.tsx`  (routes block only, lines 79-104)
- `frontend/src/components/layout/AppLayout.tsx`  (menu items block only, lines 24-34)

## Depends on
- T02, T19

## Implementation notes
- Route additions (inside existing protected shell):
  - `/data-platform` → `<Navigate to="/data-platform/sources" replace />`
  - `/data-platform/sources` → `<SourcesListPage />`
  - `/data-platform/sources/:sid` → `<SourceDetailPage />`
  - `/knowledge-base` → `<Navigate to="/knowledge-base/data-assets" replace />`
  - `/knowledge-base/data-assets` → `<DataAssetsPage />`
  - `/knowledge-base/code-repos` → `<CodeReposPage />`
  - `/knowledge-base/documents` → `<DocumentsPage />`
  - `/knowledge-base/experiences` → `<ExperiencesPage />`
  - `/knowledge-base/search` → `<KbSearchPage />`
- Menu additions after `/perception`: `{ key: '/data-platform', icon: <DatabaseOutlined/>, label: '数据平台' }`, `{ key: '/knowledge-base', icon: <BookOutlined/>, label: '知识库', children: [4 sub-items] }`.
- Pages imported lazily via `React.lazy` + `Suspense` fallback = `Spin` to keep initial bundle tight (compatible with existing flat routes).

## Acceptance
- Navigating to `/data-platform` in dev redirects to `/data-platform/sources`.
- Menu shows two new top-level items.

## Verify
```bash
cd frontend && bun run dev &
sleep 5
bunx playwright test tests/e2e/nav.spec.ts --project=chromium | tee ../.blueprint/qa/T20/nav.txt
kill %1
```

## Commit
`ui: register perception routes + nav menu items`
