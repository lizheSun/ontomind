## Verdict
APPROVE

## Reasoning
- **All exports present** in `monaco-setup.ts`: `configureMonaco`, `monacoLanguageForDialect`, `registerSchemaCompletion`, `SchemaHint`, `SupportedDialect`, `ONTOMIND_DARK_THEME_ID`. ✓
- **ontomind-dark theme** colors match the T02 CSS tokens exactly: bg `#0a0f1f`, fg `#d1d9e6`, keyword `#a78bfa` (bold), string `#34d399`, number `#fbbf24`, comment `#506080` (italic). ✓
- **SqlEditor props** match spec: `value, onChange, dialect, schema?, onRun?, height?, readOnly?, 'data-testid'?`. Cmd/Ctrl+Enter handled via `monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter` (single binding covers both platforms). ✓
- **Schema completion** correctly branches on `<table>.` prefix (regex `/(\w+)\.$/` → columns of that table) vs default (all tables + curated SELECT keywords). Case-insensitive table match; disposes provider on unmount via `disposeRef`. ✓
- **monaco-sql-languages** imported inside `beforeMount` through `ensureSqlLanguages()` dynamic import, wrapped with `.catch(() => noop)` so failure degrades to plain-text highlighting. ✓
- **Smoke test** has 2 passing assertions, uses `data-testid`, and reads through the `monaco-mock` textarea from `test-setup.ts`. Vitest 2/2 passed per `.blueprint/qa/T08/build.txt`. ✓
- **Scope respected**: diff touches only `frontend/src/components/common/*` + `.blueprint/qa/T08`. No changes to `package.json`, `vite.config.ts`, or `test-setup.ts` (T02 territory). Fresh `index.ts` is correct under this branch's base scope (see task note — merge conflict with T03 is known, not a T08 defect). ✓
- **No new tsc errors** originate from `components/common/*`; the build.txt errors are all pre-existing `pages/*` + `stores/userStore.ts` noise, out of scope.

## Required changes
None.

## Nice-to-haves (non-blocking)
- Comment in `SqlEditor.tsx` says `ensureSqlLanguages` "只需一次" but it re-runs on every mount. Dynamic-import caching makes this a no-op in practice — worth a tiny comment tweak later, not now.
- `sqlite` dialect falls back to plain `'sql'` language id; if a downstream page ever expects sqlite-specific highlighting, revisit. Fine for T08 acceptance.
