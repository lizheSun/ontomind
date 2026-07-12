# T50 · 计算节点 + 容器详情页

## Goal
新增 `ComputeNodeDetailPage` + `AgentContainerDetailPage`。节点页展示主机信息与关联容器；容器页展示类型/版本/端口/进程/关联智能体/Skill/MCP。

## Files touched
- `frontend/src/pages/resources/ComputeNodeDetail.tsx` (NEW)
- `frontend/src/pages/resources/AgentContainerDetail.tsx` (NEW)
- `frontend/src/pages/resources/components/NodeInfoCard.tsx` (NEW)
- `frontend/src/pages/resources/components/ContainerInfoCard.tsx` (NEW)
- `frontend/src/pages/resources/components/RelatedList.tsx` (NEW — 复用列表组件)
- `frontend/src/services/resourceService.ts` (新增 detail 接口调用)
- `frontend/src/routes.tsx` (新增两条子路由 `/resources/nodes/:id`, `/resources/containers/:id`)
- `frontend/src/pages/resources/__tests__/ComputeNodeDetail.test.tsx`
- `frontend/src/pages/resources/__tests__/AgentContainerDetail.test.tsx`
- `.blueprint/qa/T50/vitest.txt`

## Depends on
- T49

## UX 规格
- 节点详情：主机名 / OS / CPU / 内存 / 磁盘 / IP / 状态 / 心跳时间；下方 tab：容器列表 / Skill 汇总 / MCP 汇总
- 容器详情：类型 / 版本 / 端口 / 状态 / 进程 / CLI 路径 / env 摘要；下方 tab：智能体 / Skill / MCP
- 顶部面包屑：`资源 / 计算节点 / <name>`
- 返回按钮回到 `/resources`

## Acceptance
- 两个页面各自 4+ vitest 用例
- 空态、加载态、错误态齐全
- 支持在 tab 中直接跳转到子资源详情

## Verify
```bash
cd frontend
npm run test -- resources/ComputeNodeDetail resources/AgentContainerDetail
npm run typecheck
```

## Commit
`feat(resources): compute node & agent container detail pages`
