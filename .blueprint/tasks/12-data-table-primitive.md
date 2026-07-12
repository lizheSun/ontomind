# T12 — DataTable primitive

## Goal
Thin wrapper over AntD `<Table>` with default pagination, loading skeleton, empty state via `EmptyState`, RowKey enforcement, sticky header inside a GlassPanel; used by every CRUD list page in Wave 6.

## Files touched
- `frontend/src/components/common/DataTable.tsx`  (NEW)
- `frontend/src/components/common/index.ts`  (append)

## Depends on
- T02, T03

## Implementation notes
- Props extend AntD Table props; enforce `rowKey` required.
- Wrap in GlassPanel.
- When `dataSource.length === 0 && !loading`, render `<EmptyState>`.

## Acceptance
- `bun run build` passes.
- Vitest smoke covers empty state branch.

## Verify
```bash
cd frontend && bunx vitest run src/components/common/__tests__/DataTable.test.tsx | tee ../.blueprint/qa/T12/vitest.txt
```

## Commit
`ui: DataTable primitive (AntD Table + EmptyState + GlassPanel)`
