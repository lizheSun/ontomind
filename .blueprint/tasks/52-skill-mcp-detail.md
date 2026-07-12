# T52 · 技能 + MCP 详情页

## Goal
新增 `SkillDetailPage` + `MCPDetailPage`：显示来源（opencode 自动发现 / 手动创建），支持编辑 / 同步 / 删除。Skill 显示 body_markdown 预览；MCP 显示 manifest JSON。

## Files touched
- `frontend/src/pages/resources/SkillDetail.tsx` (NEW)
- `frontend/src/pages/resources/MCPDetail.tsx` (NEW)
- `frontend/src/pages/resources/components/MarkdownPreview.tsx` (NEW — react-markdown wrapper)
- `frontend/src/pages/resources/components/JsonViewer.tsx` (NEW — 语法高亮 + 折叠)
- `frontend/src/pages/resources/components/SourceBadge.tsx` (NEW — "来自 opencode" / "手动创建")
- `frontend/src/services/resourceService.ts` (skill/mcp CRUD 补齐)
- `frontend/src/routes.tsx` (新增两条子路由 `/resources/skills/:id`, `/resources/mcps/:id`)
- `frontend/src/pages/resources/__tests__/SkillDetail.test.tsx`
- `frontend/src/pages/resources/__tests__/MCPDetail.test.tsx`
- `.blueprint/qa/T52/vitest.txt`

## Depends on
- T48, T49

## UX 规格
- Skill 详情：name / type / source_path / description / body preview（可切换编辑）；右侧：绑定的智能体列表
- MCP 详情：name / transport_type / command 或 url / env 摘要 / tools_manifest；右侧：绑定的智能体列表
- 「同步到 opencode」按钮：调用 T48 sync 端点
- 「删除」需二次确认

## Acceptance
- 两个页面 vitest 各 4+ 用例
- Markdown 预览支持代码块高亮
- JSON viewer 支持复制 / 展开
- 「同步」按钮显示 diff 后再确认

## Verify
```bash
cd frontend
npm run test -- resources/SkillDetail resources/MCPDetail
npm run typecheck
```

## Commit
`feat(resources): skill & mcp detail pages with source-aware editing`
