# T30 · Migrate metadata browse to /data-platform/metadata

## Goal
Verbatim-port the metadata browse + WebSocket stream annotate feature from legacy `frontend/src/pages/perception/index.tsx` (L68-91, L94-253, L480-565, L789-1029) into a new page `frontend/src/pages/data-platform/MetadataPage.tsx`. Backend is UNCHANGED — reuses `perceptionAPI.*` methods (already wired in `services/index.ts` L127-148).

## Files touched
- `frontend/src/pages/data-platform/MetadataPage.tsx` (NEW — ~400 LOC)
- `frontend/src/App.tsx` (add route `<Route path="data-platform/metadata" element={<MetadataPage />} />` next to existing sources routes)
- `frontend/src/pages/data-platform/SourcesListPage.tsx` (add a Tab-like sub-nav at top: [数据源] [元数据]; second link navigates to `/data-platform/metadata`)
- `.blueprint/qa/T30/tsc.txt`
- `.blueprint/qa/T30/vite-smoke.txt`

## Depends on
- None (all backend endpoints exist unchanged; frontend service already wraps them)

## Migration procedure (per recon bg_148f9901)

Strategy: **A — Verbatim copy** (recon-recommended, cheapest). No sub-component split.

1. Copy state block L68-91 from `pages/perception/index.tsx`
2. Copy handlers L94-253 (`handleOpenMeta`, `fetchMetaTables`, `handleSyncMeta`, `handleOpenTableDetail`, `handlePreview`, `handleProfile`, `handleAnnotate`, `handleStopAnnotate`, `fetchAgents`, `handleDbChange`)
3. Copy JSX:
   - Datasource picker at top (small — from perception page's DS list, reuse SourcesListPage's data via `useDataPlatformStore().sources`)
   - Metadata browse Card L480-565
   - Table detail Drawer L789-1029 including WebSocket stream panel
4. Rewrite imports: drop unused (data-source CRUD, smart-add related), keep `perceptionAPI` + `resourcesAPI.listAgents`
5. Change hook style but preserve behavior; type-annotate anything untyped
6. Wrap outer container in `<GlassPanel padded={false}>` (not required but improves aesthetic per Strategy A note)

## Sub-nav integration in SourcesListPage.tsx

Above existing PageHeader, add a small `<Space>` or `<Radio.Group>` at top:
```
[● 数据源] [ 元数据]     <-- 数据源 selected on SourcesListPage
[  数据源] [● 元数据]     <-- 元数据 selected on MetadataPage
```
Both link across via `useNavigate()`. Reuses same visual style as page-internal Tabs. Same sub-nav also renders at top of MetadataPage.

## Acceptance
- `/data-platform/metadata` renders (mounts without crash)
- Datasource picker shows sources from store
- Selecting a DS + clicking "提取元数据" triggers `perceptionAPI.syncMetadata` and populates the metadata table
- "详情" opens the drawer with columns + profile + preview + WebSocket stream chat panel
- Sub-nav at top of both SourcesListPage and MetadataPage renders with active state

## Verify
```
cd frontend
npx tsc --noEmit -p tsconfig.app.json 2>&1 | grep -E "MetadataPage|SourcesListPage" | tee /tmp/T30-tsc.txt
# Empty

# Vite smoke
npx vite --port 5182 --host 127.0.0.1 &
sleep 6
curl -sf -o /dev/null -w "meta %{http_code}\n" http://127.0.0.1:5182/data-platform/metadata
curl -sf -o /dev/null -w "sources %{http_code}\n" http://127.0.0.1:5182/data-platform/sources
kill %1
```

## Commit
`ui: migrate metadata browse + stream annotate to /data-platform/metadata`
