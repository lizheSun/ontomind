# T26 — frontend vitest coverage

## Goal
Vitest for stateful primitives, services (mapper), stores, and one representative page (SourceDetailPage tab switching).

## Files touched
- `frontend/src/components/common/__tests__/SqlEditor.test.tsx`
- `frontend/src/components/common/__tests__/ResultGrid.test.tsx`
- `frontend/src/components/common/__tests__/SchemaTree.test.tsx`
- `frontend/src/components/common/__tests__/DataTable.test.tsx`
- `frontend/src/services/__tests__/dataPlatform.service.test.ts`
- `frontend/src/services/__tests__/knowledgeBase.service.test.ts`
- `frontend/src/stores/__tests__/dataPlatformStore.test.ts`
- `frontend/src/pages/data-platform/__tests__/SourceDetailPage.test.tsx`

## Depends on
- T21, T22, T23, T24

## Implementation notes
- Mock axios via `vi.mock('@/services/api')`.
- Assert: mapper output shape, store updates on schema fetch, tab switch renders correct tab.

## Acceptance
- `bun run test` all green; coverage ≥70% for `services/`, `stores/`, `components/common/`.

## Verify
```bash
cd frontend && bunx vitest run --coverage | tee ../.blueprint/qa/T26/vitest.txt
```

## Commit
`tests: frontend vitest (primitives + services + stores + detail page)`
