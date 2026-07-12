# Review: T26 frontend vitest

## Verdict
APPROVE

## Reasoning
- All 6 required new suites present: `SchemaTree.test.tsx`, `knowledgeBase.service.test.ts`, `dataPlatformStore.test.ts`, `knowledgeBaseStore.test.ts`, `SourceDetailPage.test.tsx`, `KbSearchPage.test.tsx`.
- `vitest.txt` reports **10 files / 29 tests passing** (11 pre-existing DataTable/SqlEditor/ResultGrid/dataPlatform.service + 18 new). Coverage report renders cleanly.
- `ResizeObserver` polyfill added inline in `beforeAll` of every suite that mounts AntD Tree/Tabs/Input.Search (SchemaTree, KbSearchPage, SourceDetailPage) — test-setup.ts is untouched, matching the spec's "T26 out-of-scope for test-setup" constraint.
- Service tests exercise all required behaviors: snake_case→camelCase mapping (library `name_zh`→`nameZh`, `sort_order`→`sortOrder`; grouped search `library_code`→`libraryCode`), non-SUCCESS envelope throws with server message, `uploadDocument` produces a `FormData` POST to `/knowledge-base/documents`.
- Store tests: `fetchSources` hydrates + clears loading, `fetchSchema(1)` called twice → service invoked once (caching per source_id verified), `deleteSource(1)` removes source and clears `currentSourceId` when it matches the deleted id.
- Page tests use `MemoryRouter`; `KbSearchPage` verifies URL-driven state via `initialEntries=[/knowledge-base/search?q=%E8%AE%A2%E5%8D%95]` waiting for search result title. `SourceDetailPage` verifies header name + 4 tab labels (SQL 编辑器 / AI 对话 / 执行历史 / 保存的查询) after mocked load.
- Diff scoped strictly to `frontend/src/**/__tests__/*` + `.blueprint/qa/T26/vitest.txt` — no changes to existing tests, services, stores, or components. `frontend/package.json` untouched (empty diff), no new deps.

## Required changes (if any)
None.

## Nice-to-haves (non-blocking)
- `AntD Space direction is deprecated` and `Tabs destroyInactiveTabPane` warnings hit repeatedly in test stderr — cosmetic AntD 5.x migration nits belonging to page code, not this task.
- Long-term: consider moving the inline `ResizeObserver` polyfill into `test-setup.ts` once its ownership window opens — three near-identical copies exist now.
