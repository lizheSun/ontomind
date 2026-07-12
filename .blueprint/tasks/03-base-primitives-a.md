# T03 — base primitives (batch A)

## Goal
Create the seven simple frontend primitives: `PageHeader`, `GlassPanel`, `StatCard`, `EmptyState`, `SectionTitle`, `TagPill`, `DangerConfirm`.

## Files touched
- `frontend/src/components/common/PageHeader.tsx`  (NEW)
- `frontend/src/components/common/GlassPanel.tsx`  (NEW)
- `frontend/src/components/common/StatCard.tsx`  (NEW)
- `frontend/src/components/common/EmptyState.tsx`  (NEW)
- `frontend/src/components/common/SectionTitle.tsx`  (NEW)
- `frontend/src/components/common/TagPill.tsx`  (NEW)
- `frontend/src/components/common/DangerConfirm.tsx`  (NEW)
- `frontend/src/components/common/index.ts`  (NEW barrel)

## Depends on
- T02 (tokens)

## Implementation notes
- All components strictly typed props via `interface`.
- `PageHeader`: title (h1 32px SC bold), subtitle (14px --text-secondary), right slot `React.ReactNode`; sticky within page area.
- `GlassPanel`: renders div with `background: rgba(255,255,255,0.03); border: 1px solid var(--dp-panel-border); backdrop-filter: blur(20px); border-radius: var(--radius-lg); padding: 24px;` — accepts `padded?`, `bordered?`, `className`.
- `StatCard`: icon + label + value + trend delta chip.
- `EmptyState`: uses AntD `<Empty>` with custom illustration slot + CTA.
- `SectionTitle`: h3 with gradient underline pseudo-element.
- `TagPill`: color prop mapped to `--kb-tag-*` vars.
- `DangerConfirm`: wrapper around `Modal.confirm` (danger + Chinese labels 确认删除 / 取消).

## Acceptance
- Each file exports one component; barrel re-exports all seven.
- `bun run build` passes tsc.

## Verify
```bash
cd frontend && bun run build 2>&1 | tail -20
ls src/components/common/*.tsx | wc -l   # → 7
```
Save to `.blueprint/qa/T03/output.txt`.

## Commit
`ui: add batch-A primitives (PageHeader/GlassPanel/StatCard/Empty/SectionTitle/TagPill/DangerConfirm)`
