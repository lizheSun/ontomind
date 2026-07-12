# T21 — /data-platform/sources page

## Goal
Data sources list page: header, StatCard row (total sources / active / recent queries), DataTable of sources, "新建数据源" modal drawer with smart form validated per dialect, row actions (测试连接 / 查看 / 编辑 / 删除).

## Files touched
- `frontend/src/pages/data-platform/SourcesListPage.tsx`  (NEW)
- `frontend/src/pages/data-platform/components/SourceFormDrawer.tsx`  (NEW)
- `frontend/src/pages/data-platform/index.ts`  (barrel — NEW)

## Depends on
- T03, T11, T12, T19, T20

## Implementation notes
- PageHeader title `数据平台 / 数据源` subtitle `连接、探查、并对话你的数据资产`.
- Right slot: `<Button type="primary" icon={<PlusOutlined/>}>新建数据源</Button>`.
- Three StatCards from `/history` + `/sources`.
- DataTable columns: 名称 / 类型 / 数据库 / 状态 (Tag) / 拥有者 / 更新时间 / 操作.
- Row action `测试连接` triggers `POST /sources/{id}/test`, shows `Message.success` with `server_version + elapsed_ms`.
- Drawer form: name / source_type (Segmented) / dialect / host / port / username / password (Input.Password, empty on edit) / database / default_schema / description; validation per dialect.

## Acceptance
- Page renders with real backend; create → row appears; test connection succeeds on a reachable DB; delete removes row.

## Verify
```bash
cd frontend && bunx playwright test tests/e2e/dp-sources-list.spec.ts | tee ../.blueprint/qa/T21/pw.txt
```

## Commit
`ui: data platform sources list page + smart create/edit drawer`
