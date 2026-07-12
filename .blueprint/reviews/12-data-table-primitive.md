# Task 12 — DataTable primitive review

## Verdict
APPROVE

## Reasoning
- **Generic + required rowKey**: `DataTable<T extends object>` uses `Omit<TableProps<T>, 'rowKey'>` and re-adds `rowKey: TableProps<T>['rowKey']` as required — enforced at type level. ✅
- **EmptyState fallback**: `showCustomEmpty = data.length === 0 && !loading` short-circuits to `<EmptyState>` with `title ?? '暂无数据'` and passes through `description`/`action`. Matches EmptyState's actual API. ✅
- **GlassPanel wrap**: `panelWrapped = true` default; wraps with `padded={false}` + `overflow: hidden`; `panelWrapped=false` returns bare body. GlassPanel `padded` prop exists. ✅
- **Pagination defaults**: `size:'small'`, `showSizeChanger:true`, `pageSizeOptions:[10,20,50,100]`, `defaultPageSize:20`. `pagination === false` respected verbatim; object overrides spread AFTER defaults (correct override order). ✅
- **Sticky + scroll**: `sticky` always set; `scroll={rest.scroll ?? { x: 'max-content' }}` allows caller override. ✅ (Small nit below.)
- **Tests pass**: `.blueprint/qa/T12/vitest.txt` shows 3/3 tests green; the jsdom `getComputedStyle` stderr from rc-table is a warning, not a failure. Tsc block is empty (no new errors). ✅
- **ResizeObserver stub**: Scoped inside `beforeAll` in the test file only — no touch of `test-setup.ts`. Idempotent guard (`if (!('ResizeObserver' in globalThis))`). ✅
- **React 19 JSX import**: `import type { JSX, ReactNode } from 'react'` — correct for React 19 where `JSX` is exported from `react`, not the global namespace. ✅
- **Untouched files**: diff --stat against `package.json`, `App.tsx`, `test-setup.ts` returns empty. ✅
- **index.ts**: All 10 pre-existing lines preserved verbatim (7 primitives + SqlEditor value + SqlEditorProps + SchemaHint/SupportedDialect types); only appends `DataTable` value + `DataTableProps` type. ✅

## Required changes
None.

## Nice-to-haves (non-blocking)
- The `rest.scroll` default trick relies on `scroll` not being explicitly stripped by `...rest` — works because `scroll` isn't destructured, but a more defensive pattern would be to destructure `scroll` explicitly. Not worth blocking on.
- The jsdom `getComputedStyle` warning from `@rc-component/util/getScrollBarSize` is noisy but harmless; a future test-utility PR could stub it. Out of scope for this task.
