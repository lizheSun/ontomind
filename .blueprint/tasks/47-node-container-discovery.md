# T47 · 计算节点 + 智能体容器自动发现增强

## Goal
扩展 `POST /api/v1/resources/register-local` 端点，新增 `discover_agent_containers()` 逻辑：扫描本地 opencode / openclaw / harness 进程，自动创建 `agent_containers` 行并建立 `node_containers` 关联。发现流程串联 T46 的 opencode 配置发现。

## Files touched
- `backend/app/services/compute_node_service.py` (扩展 register_local)
- `backend/app/services/agent_container_discovery_service.py` (NEW)
- `backend/app/schemas/compute_node.py` (返回结构新增 containers/skills/mcps)
- `backend/app/api/v1/resources.py` (register-local 端点整合发现流程)
- `backend/app/utils/process_scan.py` (NEW — psutil 扫描本地进程)
- `backend/tests/data_platform/test_container_discovery.py` (NEW)
- `.blueprint/qa/T47/pytest.txt`

## Depends on
- T44, T46

## 功能规格
1. 采集本机硬件：hostname / platform / cpu_cores / mem / disk / ip
2. 扫描 `psutil.process_iter`，匹配 opencode / openclaw / harness 关键字，读取 `pid / cwd / cmdline / exe`
3. 探测容器版本（`opencode --version` 等）
4. 自动调用 T46 的 opencode 发现服务把 MCP / Skill 入库
5. 建立 `node_containers` / `container_skills` / `container_mcps` 关联（binding_type=inherit）
6. 返回统计：`{node, containers[], skills_synced, mcps_synced, elapsed_ms}`

## Acceptance
- register-local 端点端到端跑通，返回节点 + 容器 + 技能 + MCP 计数
- 至少 8 个 test（无进程 / 单进程 / 多进程 / 版本探测失败 / 幂等重跑等）
- 心跳更新 `last_heartbeat` 字段

## Verify
```bash
cd backend
pytest tests/data_platform/test_container_discovery.py -v
curl -X POST http://localhost:8000/api/v1/resources/register-local -H "Authorization: Bearer $TOKEN" | jq
```

## Commit
`feat(resources): compute node + agent container auto-discovery`
