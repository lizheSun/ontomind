# T29 · Perception shell + menu cleanup

## Goal
Turn `/perception` from the legacy 1032-LOC data-source page into a **shell landing page** with 2 large cards (数据平台 / 知识库). Remove the 2 top-level menu items I added in Wave 5 (数据平台 / 知识库) — restore top nav to original 9 entries.

## Files touched
- `frontend/src/pages/perception/PerceptionShell.tsx` (NEW — the 2-card landing page)
- `frontend/src/App.tsx` (change: `<Route path="perception" element={<PerceptionShell />} />` — but leave old `<PerceptionIndex />` import intact for `/perception/legacy` fallback if wanted; concrete decision: replace `<PerceptionIndex />` with `<PerceptionShell />` at the `/perception` route line)
- `frontend/src/components/layout/AppLayout.tsx` (delete 2 lines in `topMenuItems`: `/data-platform` and `/knowledge-base` — restore 9-item nav)
- `.blueprint/qa/T29/tsc.txt` (evidence)

## Depends on
- None (self-contained, no worktree dep)

## Design contract for PerceptionShell.tsx

- `<PageHeader title="感知层" subtitle="信息入口 · 连接一切数据源与知识资产" />`
- Row layout: 2 `<GlassPanel hover>` cards side by side, each `flex: 1`, 300px min-height
- Card 1 (数据平台):
  - Icon `<DatabaseOutlined />` at top, 48px, colored `--accent`
  - Title "数据平台" (h2, 24px, primary color)
  - Subtitle "数据源管理 · SQL 探查 · AI 对话 SQL · 元数据浏览"
  - Bullet list (small): 数据源 CRUD / SQL Editor + Chat / 元数据 + 智能标注
  - CTA button `<Button type="primary" size="large">进入 →</Button>` calls `navigate('/data-platform/sources')`
- Card 2 (知识库):
  - Icon `<BookOutlined />` at top, 48px, colored `--accent-purple`
  - Title "知识库"
  - Subtitle "数据资产 · 代码库 · 文档库 · 业务经验"
  - Bullet list: 4 sub-libs + 跨库搜索
  - CTA `navigate('/knowledge-base/data-assets')`

Uses `PageHeader` + `GlassPanel` primitives from `frontend/src/components/common`. Chinese labels. No emojis. Monochrome AntD icons.

## Acceptance
- `/perception` renders new shell (2 cards visible, ChineseCJK, no crash)
- Clicking each card navigates to the right sub-module
- Top nav shows exactly 9 items (dashboard/perception/cognition/decision/execution/application/projects/resources/users)

## Verify
```
cd frontend
npx tsc --noEmit -p tsconfig.app.json 2>&1 | grep -E "pages/perception/PerceptionShell|AppLayout" | tee /tmp/T29-tsc.txt
# Should be empty
```
Save to `.blueprint/qa/T29/tsc.txt`.

Boot vite on 5181, curl `/` → 200, curl `/perception` → 200.

## Commit
`ui: perception shell (2 cards) + top nav cleanup`
