# T08 — SqlEditor primitive (Monaco wrapper)

## Goal
Create `frontend/src/components/common/SqlEditor.tsx` — a themed Monaco wrapper with SQL autocompletion via `monaco-sql-languages`, dialect prop, schema-aware completion, height prop, controlled value/onChange, Ctrl+Enter → onRun.

## Files touched
- `frontend/src/components/common/SqlEditor.tsx`  (NEW)
- `frontend/src/components/common/monaco-setup.ts`  (NEW — one-time worker config)
- `frontend/vite.config.ts`  (add monaco worker plugin config)

## Depends on
- T02, T03

## Implementation notes
- Use `@monaco-editor/react` `<Editor>` + `beforeMount` to register `monaco-sql-languages` for `mysql`/`postgresql`/`sqlite`.
- Theme: define `ontomind-dark` matching CSS vars (`--code-bg`, `--code-fg`, `--accent-purple` for keywords).
- Props: `value`, `onChange`, `dialect`, `schema?: {tables: {name, columns: string[]}[]}`, `onRun?`, `height?`.
- Register completion provider that surfaces schema tables/columns when schema prop provided.
- Ctrl+Enter (Cmd+Enter on mac) fires onRun.
- No emojis; keep monochrome.

## Acceptance
- Component renders in a vitest test using `@testing-library/react` (`render(<SqlEditor value="SELECT 1" onChange={()=>{}} dialect="mysql" />)`) without throwing.
- Type-checks: `bun run build` passes.

## Verify
```bash
cd frontend && bun run build 2>&1 | tail -10 | tee ../.blueprint/qa/T08/build.txt
bunx vitest run src/components/common/__tests__/SqlEditor.smoke.test.tsx | tee -a ../.blueprint/qa/T08/build.txt
```

## Commit
`ui: SqlEditor primitive (Monaco + monaco-sql-languages, Ctrl+Enter, schema autocomplete)`
