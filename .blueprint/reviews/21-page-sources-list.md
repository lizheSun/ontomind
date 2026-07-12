# Task 21 Review — SourcesListPage + SourceFormDrawer

## Verdict
**APPROVE**

## Reasoning
- **SourcesListPage** hits every spec item: `PageHeader` with correct title/subtitle + `新建数据源` primary button on the right; three-column grid of `StatCard`s (总数 / 已激活 / 最近 7 天查询数); `DataTable` wired to `useDataPlatformStore` with `fetchSources` on mount + `deleteSource` on delete; columns match spec (name / TagPill type / database / colored `Tag` status / owner / `dayjs`-formatted `updatedAt` / actions); row actions cover 测试连接 (`dataPlatformService.testConnection` + `message.success/error` with elapsed ms), 详情 (`navigate(/data-platform/sources/:id)`), 编辑 (opens drawer with prefill), 删除 (`DangerConfirm` with the cascade-delete note in `content`). Empty state uses `DataTable`'s `emptyAction` slot with the 新建数据源 CTA.
- **SourceFormDrawer** meets all criteria: `Drawer width={520}`, dynamic title (`新建数据源` vs `编辑数据源: <name>`); `Segmented` picks MySQL / PostgreSQL / SQLite and drives both `source_type` and `dialect` in the payload; host/port/username hidden for SQLite (via `hidesHost`) and their values are explicitly nulled in the payload; port defaults 3306 / 5432 per dialect and clears for SQLite; `default_schema` only rendered/emitted for PostgreSQL; password is `required` on create and shows `留空保留原密码` with the field stripped from the update payload when blank; all required fields (name, source_type, dialect, database, charset, description, read_only_flag) are wired.
- **Barrel**: `index.ts` re-exports `SourcesListPage` + `SourceFormDrawer` and preserves the T20 default via `export { default } from './index.tsx'`. Vite/TS resolves `./pages/data-platform` to `index.ts` first, and the re-export forwards the redirect stub — App.tsx's `import DataPlatformIndex from './pages/data-platform'` still resolves to the `<Navigate to="/data-platform/sources" replace />` component, so `/data-platform` → `/data-platform/sources` still works.
- **Guardrails clean**: `.blueprint/qa/T21/tsc.txt` is 0 bytes (in-scope tsc clean); diff is scoped to the three declared files — App.tsx, AppLayout.tsx, other pages, `components/common/*`, and `package.json` are untouched; no emojis, only AntD icons (`PlusOutlined`, `ReloadOutlined`, `DatabaseOutlined`, `ThunderboltOutlined`, `ApiOutlined`); no new dependencies (`dayjs` and `axios` types already in tree).

## Required changes
None.

## Nice-to-haves (non-blocking)
- `charset` default is hard-coded to `utf8mb4` even for PostgreSQL / SQLite where that string is meaningless; a per-dialect default (or hiding the field for SQLite) would be cleaner.
- On edit, switching from PostgreSQL to another dialect doesn't explicitly null out `default_schema` in the patch — backend likely tolerates it, but an explicit `null` when `!showsSchema` would be more defensive.
- 最近 7 天查询数 `StatCard` is a hardcoded `0` — fine for T21 scope since query history aggregation lives in later tasks, but worth wiring once the store exposes it.
