# T19 — frontend services + Zustand stores

## Goal
Add typed axios services and Zustand stores for both surfaces.

## Files touched
- `frontend/src/services/dataPlatform.service.ts`  (NEW)
- `frontend/src/services/knowledgeBase.service.ts`  (NEW)
- `frontend/src/stores/dataPlatformStore.ts`  (NEW)
- `frontend/src/stores/knowledgeBaseStore.ts`  (NEW)
- `frontend/src/types/dataPlatform.ts`  (NEW)
- `frontend/src/types/knowledgeBase.ts`  (NEW)

## Depends on
- T02

## Implementation notes
- Services follow `frontend/src/services/user.service.ts` pattern: typed envelope + snake_case→camelCase mapper.
- Expose async methods 1:1 mirroring backend endpoints.
- SSE: `openExecuteStream(sourceId, sql, maxRows)` returns `EventSource` — page-level handler owns lifecycle.
- Stores: `dataPlatformStore` holds `currentSourceId`, `schemaCache: Record<id, Schema>`, `activeTab`; `knowledgeBaseStore` holds `currentLibraryCode`, `searchQuery`.

## Acceptance
- `bun run build` passes.
- Vitest smoke asserts mapper converts `owner_user_id` → `ownerUserId`.

## Verify
```bash
cd frontend && bunx vitest run src/services/__tests__/dataPlatform.service.test.ts | tee ../.blueprint/qa/T19/vitest.txt
```

## Commit
`ui: dataPlatform/knowledgeBase services + Zustand stores + types`
