# Review — Task 11: ResultGrid + SchemaTree

## Verdict
APPROVE

## Reasoning
- **ResultGrid** uses `useVirtualizer` from `@tanstack/react-virtual` with proper scroll ref, `estimateSize`, `overscan: 8`, `getTotalSize()`, and absolute-positioned rows via `translateY(vRow.start)` — canonical TanStack pattern, not hand-rolled.
- **CSV export** is RFC 4180 compliant: BOM `\uFEFF` prefix, `/[",\n]/` triggers quoting, inner `"` doubled via `.replace(/"/g, '""')`, objects JSON-stringified, `null/undefined` → empty. Custom `onExportCsv` short-circuits the default.
- **Props** exactly match spec: `columns`, `rows`, `rowCount?`, `elapsedMs?`, `truncated?`, `onExportCsv?`, `height?` (default 480), `'data-testid'?`.
- **Sticky header** via `position: 'sticky'; top: 0; zIndex: 2` on `<thead>` with elevated background.
- **Cell tooltip** applied per-cell with full raw value (`Tooltip title={raw}`) — overflow ellipsis + hover reveal covered.
- **EmptyState** branch on `rows.length === 0` (before virtualizer render), plus export button disabled.
- **SchemaTree** uses AntD `Tree` with DB → table → column hierarchy, distinct icons per level (`DatabaseOutlined` / `TableOutlined` / `FieldNumberOutlined`), namespaced keys (`db::` / `tbl::` / `col::`).
- **Click-to-insert callbacks** wired via `onClick` on inner `Space` with `stopPropagation` so table/column click bubbling doesn't collide with Tree row selection; cursor toggles only when a callback exists.
- **Both components wrap in `GlassPanel`** (`padded={false}` to control inner scrollers).
- **Vitest**: all 3 tests pass. Virtualization proof asserts `<50` rendered `rg-row` nodes for a 500-row input — jsdom emits a small window, meeting the "not full DOM" bar. `elapsedMs` and `暂无查询结果` empty-state assertions also pass.
- **`.blueprint/qa/T11/vitest.txt`** ends with an explicit "tsc new errors (should be empty)" header and empty body → clean tsc.
- **No `package.json` / `package-lock.json` changes**; `@tanstack/react-virtual` and `antd` were already dependencies from T03/T08.
- **`index.ts` append-only**: the original 7 component exports + `SqlEditorProps` + `SchemaHint, SupportedDialect` types (lines 1–10) are intact; new exports added on lines 11–20.

## Required changes
None.

## Nice-to-haves (non-blocking)
- Tooltip wraps every cell — for very wide result sets this can be noisy. Consider gating on `overflow` via a `ref`/measured width in a follow-up polish pass.
- `columnWidths` is fixed at 180px per column; a future improvement could auto-size or accept a `columnWidths?: number[]` prop.
- Consider `role="grid"` / `role="row"` / `role="columnheader"` ARIA on the virtualized table for a11y — not spec'd, safe to defer.
- `raw` value for `null` collapses to empty string in tooltip while cell shows `NULL` badge; harmless, but you may want the tooltip to also read `NULL` for consistency.
