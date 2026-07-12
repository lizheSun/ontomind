# T23 — 4 KB sub-library pages

## Goal
Four CRUD pages sharing a `KbLibraryLayout` component: 数据资产 / 代码库 / 文档库 / 业务经验库.

## Files touched
- `frontend/src/pages/knowledge-base/KbLibraryLayout.tsx`  (NEW — shared shell)
- `frontend/src/pages/knowledge-base/DataAssetsPage.tsx`  (NEW)
- `frontend/src/pages/knowledge-base/CodeReposPage.tsx`  (NEW)
- `frontend/src/pages/knowledge-base/DocumentsPage.tsx`  (NEW — includes Upload widget)
- `frontend/src/pages/knowledge-base/ExperiencesPage.tsx`  (NEW)
- `frontend/src/pages/knowledge-base/components/EntryFormDrawer.tsx`  (NEW — polymorphic)

## Depends on
- T03, T12, T19, T20

## Implementation notes
- Shared layout: PageHeader (library icon + name + description from `kb_libraries`), TagPill row for filters, `<Input.Search placeholder="在本库搜索">` triggers `?q=...` on the sublib endpoint.
- Cards or table (default table, view toggle 列表/卡片).
- DocumentsPage adds an AntD `<Upload>` inside the drawer, calls `/documents/upload`.
- Form fields per sub-lib per schema; markdown editor for `description_md` / `content_md` (use AntD `Input.TextArea` for MVP; annotate future work).
- Cross-lib nav: sidebar sub-menu (from T20 menu children).

## Acceptance
- Each page loads with empty state; create entry → row appears; edit → row updates; delete → row disappears.
- Document upload rows show file size and mime.

## Verify
```bash
cd frontend && bunx playwright test tests/e2e/kb-sublibs.spec.ts | tee ../.blueprint/qa/T23/pw.txt
```

## Commit
`ui: knowledge-base 4 sub-library pages (assets/repos/docs/experiences) + upload`
