# T45 · 前后端命名体系更新

## Goal
重命名所有 DTO / 路由 / 组件 / 存储中的 `Instance → ComputeNode`, `AgentLooper → Agent`, `mcp_configs → mcps`。更新前端类型定义。**不创建新功能，只改名。**

## Files touched
- `backend/app/schemas/compute_node.py` (RENAMED from instance.py)
- `backend/app/schemas/agent.py` (RENAMED from agent_looper.py, 合并 agent.py)
- `backend/app/schemas/skill.py` (更新字段)
- `backend/app/schemas/mcp.py` (RENAMED from mcp_config.py)
- `backend/app/services/compute_node_service.py` (RENAMED from instance_service.py)
- `backend/app/services/agent_service.py` (RENAMED from agent_looper_service.py)
- `backend/app/api/v1/resources.py` (路由改名 `/instances → /compute-nodes`, `/agent-loopers → /agents`, `/mcp-configs → /mcps`；注意：使用 HTTP 308 而不是 301，以保留请求方法。)
- `frontend/src/types/resource.ts` (更新所有 TypeScript 类型)
- `frontend/src/services/resourceService.ts` (更新所有 API 调用)
- `frontend/src/stores/resourceStore.ts` (更新字段名)
- `frontend/src/pages/resources/*.tsx` (临时占位，保证不 crash)
- `backend/tests/data_platform/test_naming_migration.py` (NEW)
- `.blueprint/qa/T45/pytest.txt`

## Depends on
- T44

## Acceptance
- 全仓库 grep `Instance` / `AgentLooper` / `mcp_configs` 只剩历史注释
- 旧路由保留 3 个月的重定向（301 → 新路由）
- 前后端类型对齐，`npm run typecheck` 通过
- 现有 pytest 全部通过（改名不改行为）

## Verify
```bash
cd backend && pytest tests/data_platform/test_naming_migration.py -v
cd frontend && npm run typecheck
grep -R "AgentLooper" backend/app frontend/src | grep -v "# legacy" | wc -l   # → 0
```

## Commit
`refactor(naming): Instance→ComputeNode, AgentLooper→Agent, mcp_configs→mcps`
