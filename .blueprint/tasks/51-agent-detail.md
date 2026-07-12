# T51 · 智能体详情页（升级版 Agent Looper 详情）

## Goal
升级原 Agent Looper 详情页：保留原有 3 个 tab（配置 / 版本历史 / 测试），新增「关联的 Skill」「关联的 MCP」「Job 历史」共 6 个 tab。Skill / MCP 可在此页面绑定与解除。

## Files touched
- `frontend/src/pages/resources/AgentDetail.tsx` (REPLACE — 从旧的 AgentLooperDetail 升级)
- `frontend/src/pages/resources/components/AgentSkillsTab.tsx` (NEW)
- `frontend/src/pages/resources/components/AgentMCPsTab.tsx` (NEW)
- `frontend/src/pages/resources/components/AgentJobHistoryTab.tsx` (NEW)
- `frontend/src/pages/resources/components/BindingSelector.tsx` (NEW — inherit/include/exclude)
- `frontend/src/services/agentService.ts` (新增 bind/unbind 接口调用)
- `backend/app/api/v1/agents.py` (新增 bind/unbind Skill/MCP 端点)
- `backend/app/services/agent_service.py` (bind_skill / unbind_skill / bind_mcp / unbind_mcp)
- `backend/tests/data_platform/test_agent_binding.py`
- `frontend/src/pages/resources/__tests__/AgentDetail.test.tsx`
- `.blueprint/qa/T51/pytest.txt`

## Depends on
- T44, T45, T49

## Acceptance
- 3 个新 tab 渲染正确
- 绑定操作实时刷新
- inherit → explicit_include → explicit_exclude 三态可切换
- pytest 覆盖绑定/解绑/去重/幂等场景

## Verify
```bash
cd backend && pytest tests/data_platform/test_agent_binding.py -v
cd frontend && npm run test -- resources/AgentDetail
```

## Commit
`feat(resources): agent detail with skills/mcps/jobs tabs and binding`
