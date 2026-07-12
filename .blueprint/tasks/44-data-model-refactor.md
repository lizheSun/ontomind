# T44 · 数据模型重构

## Goal
创建 5 张核心表 + 7 张关联表的新数据模型，替换现有的 instances/agents/agent_looper_configs/mcp_configs/skills 表。

## Files touched
- `backend/app/db/models/compute_node_model.py` (NEW)
- `backend/app/db/models/agent_container_model.py` (NEW)
- `backend/app/db/models/agent_model.py` (REPLACE — 合并 agent + agent_looper_config 模型)
- `backend/app/db/models/skill_model.py` (REPLACE — 扩展支持 opencode SKILL.md)
- `backend/app/db/models/mcp_model.py` (REPLACE — 扩展支持 opencode mcp 格式)
- `backend/app/db/models/node_container_model.py` (NEW)
- `backend/app/db/models/container_agent_model.py` (NEW)
- `backend/app/db/models/container_skill_model.py` (NEW)
- `backend/app/db/models/container_mcp_model.py` (NEW)
- `backend/app/db/models/agent_skill_model.py` (NEW)
- `backend/app/db/models/agent_mcp_model.py` (NEW)
- `backend/app/db/models/agent_run_job_model.py` (NEW)
- `backend/app/db/models/__init__.py` (更新)
- `backend/app/core/config.py` (添加 OPENCODE_CONFIG_PATH 等配置)
- `backend/tests/data_platform/test_data_model.py` (NEW)
- `.blueprint/qa/T44/pytest.txt`

## Depends on
- None

## 数据模型设计

### compute_nodes（计算节点）
继承原 instances 表字段 + 扩展：`hostname, platform, cpu_cores, memory_mb, disk_gb, os_version, ip, status (online|offline|maintenance), last_heartbeat, agent_count, container_count, skill_count, mcp_count, labels (JSON)`

### agent_containers（智能体容器）
NEW: `name, container_type (opencode|openclaw|harness|custom), version, port, host, health_url, status (running|stopped|error), process_name, pid, cli_path, env (JSON), skills_auto_inherit (bool default true), mcps_auto_inherit (bool default true), last_heartbeat`

### agents（智能体）
合并原 agent_looper_configs + agents 表：`name, type (custom_looper|opencode_native|mcp_agent|imported), container_id (FK), description, model, temperature, loop_strategy, system_prompt, tool_permissions (JSON), custom_tools (JSON), memory_window, guardrails (JSON), resource_bindings (JSON), credential_ref (JSON), is_active, is_published, version (int), published_path`

### skills（技能模块）
扩展原 skills 表：`name, type (opencode_prompt|docker|mcp|script|api), source_path (opencode SKILL.md 路径), body_markdown (SKILL.md body), version, requires_bins (JSON), description, parameters_schema (JSON), output_schema (JSON), env_vars (JSON), tags (JSON), is_installed, is_active`

### mcps（工具连接）
扩展原 mcp_configs 表：`name, transport_type (local|remote|sse|stdio|http), command (JSON array), url, args (JSON), env_vars (JSON), headers (JSON), auto_discovery_url, auto_discovery_enabled, tools_manifest (JSON), source (manual|opencode_config|auto_discover), is_active`

### 关联表
全部使用 `model_id / container_id / agent_id` + `binding_type (inherit|explicit_include|explicit_exclude)` 字段，支持继承/排除模式。

## Acceptance
- 12 张新表创建成功（mysql SHOW TABLES）
- 22 个模型类 importable
- 现有数据迁移脚本（从旧表迁移到新表）
- 旧表保留兼容视图（6 个月后删除）

## Verify
```bash
cd backend
python -c "from app.db.models import *; print('ok')"
mysql -uroot -e "USE ontomind; SHOW TABLES;" | grep -cE "compute_nodes|agent_containers|agents|skills|mcps|node_container|container_agent|container_skill|container_mcp|agent_skill|agent_mcp|agent_run_jobs"
# → 12
```

## Commit
`refactor: data model rewrite (12 tables: compute_nodes → agent_run_jobs)`
