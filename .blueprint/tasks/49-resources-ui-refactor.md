# T49 · 资源页全新 UI

## Goal
重构 `frontend/src/pages/resources/index.tsx`：五层导航（计算节点 / 容器 / 智能体 / Skill / MCP）+ 顶部统计大盘（7 个数字）+ 自动发现入口按钮。每一层是独立的可折叠面板。

## Files touched
- `frontend/src/pages/resources/index.tsx` (REPLACE)
- `frontend/src/pages/resources/components/StatsDashboard.tsx` (NEW)
- `frontend/src/pages/resources/components/ComputeNodePanel.tsx` (NEW)
- `frontend/src/pages/resources/components/AgentContainerPanel.tsx` (NEW)
- `frontend/src/pages/resources/components/AgentPanel.tsx` (NEW)
- `frontend/src/pages/resources/components/SkillPanel.tsx` (NEW)
- `frontend/src/pages/resources/components/MCPPanel.tsx` (NEW)
- `frontend/src/pages/resources/components/DiscoverButton.tsx` (NEW)
- `frontend/src/stores/resourceStore.ts` (增加 5 类数据 slice)
- `frontend/src/pages/resources/__tests__/index.test.tsx`
- `frontend/src/pages/resources/index.less` (NEW)
- `.blueprint/qa/T49/vitest.txt`

## Depends on
- T45, T47

## UX 规格
1. 顶部 StatsDashboard：`节点 / 容器 / 智能体 / Skill / MCP / 运行中 Job / 今日调用` 7 个指标卡
2. 主体：5 个可折叠面板，默认全部展开
3. 每个面板：左侧图标 + 名称 + 状态徽章 + 右侧操作 (查看/编辑/删除)
4. 全局「一键发现」按钮：调用 T46+T47 端点，进度条实时显示进展
5. 空态：显示中文引导 + "从 opencode 发现" CTA

## Acceptance
- vitest 覆盖 6 个组件的基础渲染 + 交互
- 首屏 3s 内加载完成（含数据）
- 折叠状态记忆到 localStorage
- 一键发现按钮触发后有 toast/进度反馈

## Verify
```bash
cd frontend
npm run test -- resources/index
npm run typecheck
npm run build
```

## Commit
`feat(resources): five-layer resource page with stats dashboard`
