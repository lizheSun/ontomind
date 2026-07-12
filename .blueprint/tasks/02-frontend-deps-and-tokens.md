# T02 — frontend deps + design tokens

## Goal
Add TanStack table/virtual, Monaco + SQL languages, vitest, Playwright; extend design tokens in `global.css` and antd theme in `App.tsx` with data-platform / KB accent vars.

## Files touched
- `frontend/package.json`
- `frontend/src/styles/global.css`
- `frontend/src/App.tsx` (ConfigProvider theme block only)
- `frontend/vitest.config.ts` (NEW)
- `frontend/playwright.config.ts` (NEW)

## Depends on
- None

## Implementation notes
- pin: `@tanstack/react-table@8.21.3`, `@tanstack/react-virtual@3.14.5`, `@monaco-editor/react@4.7.0`, `monaco-editor@0.55.1`, `monaco-sql-languages@1.1.0`; devDeps: `vitest`, `@playwright/test`, `jsdom`, `@testing-library/react`, `@testing-library/user-event`.
- New tokens: `--dp-panel-border`, `--dp-panel-glow`, `--kb-tag-blue`, `--kb-tag-purple`, `--kb-tag-cyan`, `--kb-tag-amber`, `--code-bg`, `--code-fg`.
- vitest config: jsdom + setup file mocking monaco.
- Playwright config: baseURL `http://localhost:5173`, `webServer` boots vite + backend.

## Acceptance
- `bun install` clean.
- `bun run test` (empty suite) exits 0.
- `bunx playwright --version` prints version.
- `global.css` grep for `--dp-panel-border` returns 1 line.

## Verify
```bash
cd frontend && bun install && bun run test --run
bunx playwright --version
grep -n "--dp-panel-border" src/styles/global.css
```
Save to `.blueprint/qa/T02/output.txt`.

## Commit
`deps: add tanstack/monaco/vitest/playwright + perception design tokens`
