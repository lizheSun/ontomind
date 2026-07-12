# T11 — ResultGrid + SchemaTree primitives

## Goal
Create `ResultGrid.tsx` (TanStack table + virtual, sticky header, cell truncation with tooltip, CSV export button using `pandas`-equivalent client-side blob) and `SchemaTree.tsx` (AntD Tree with database → table → column nodes fed from `/schema` endpoint, click-to-insert into SqlEditor).

## Files touched
- `frontend/src/components/common/ResultGrid.tsx`  (NEW)
- `frontend/src/components/common/SchemaTree.tsx`  (NEW)
- `frontend/src/components/common/index.ts`  (append exports)

## Depends on
- T02, T03, T08

## Implementation notes
- ResultGrid props: `columns: string[]`, `rows: unknown[][]`, `rowCount`, `elapsedMs`, `onExportCsv?`.
- Use `useVirtualizer` with row height 32; render only visible rows.
- Toolbar row: `<Space>` with row count, elapsed ms chip, export CSV button (client-side CSV via Blob + URL.createObjectURL).
- SchemaTree props: `data: {databases: {name, tables: {name, columns: {name, type}[]}[]}[]}`, `onColumnClick?(col)`, `onTableClick?(table)`.
- Both wrap contents in `<GlassPanel>`.

## Acceptance
- `bun run build` passes.
- Vitest smoke: render ResultGrid with 500 rows; assert only ~15 rows in DOM at once (virtualization proof).

## Verify
```bash
cd frontend && bunx vitest run src/components/common/__tests__/ResultGrid.test.tsx | tee ../.blueprint/qa/T11/vitest.txt
```

## Commit
`ui: ResultGrid (TanStack virtual) + SchemaTree (AntD Tree)`
