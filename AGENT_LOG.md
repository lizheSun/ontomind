# Agent 操作记录

> **用途**: 多 Agent 协同开发时，记录每次操作的目的、内容和影响范围，方便其他 Agent 快速理解上下文。

---

## 2025-07-07

### Agent: 主开发 Agent（感知层元数据提取系统 — 存储 + 浏览 + LLM/Agent 标注 + 流式交互）

### 目标
1. 对挂载的数据源进行元数据提取（表结构、字段信息、注释）
2. 元数据按表维度存储到 MySQL，设计可用于本体提取的结构
3. 实时连接数据源浏览数据
4. 支持大模型/Agent 自动注释（无注释的字段自动生成）
5. 标注交互参照 Cursor/CodeBuddy 风格 — 右侧对话面板 + 流式执行

### 设计决策

| 决策点 | 选择 |
|--------|------|
| 存储方式 | 表维度存储（meta_tables + meta_columns 两张表） |
| 元数据提取 | 通过 information_schema.TABLES + .COLUMNS + .KEY_COLUMN_USAGE |
| 同步策略 | 支持指定库 / 一键同步所有用户库（跳过系统库） |
| 查询优化 | 批量查 COLUMNS 再按表分组，避免 N+1 |
| 数据浏览 | 实时连接数据源 SELECT * LIMIT N OFFSET M |
| 标注方式 | 平台 LLM 或指定 Agent（CLI 模式），可自定义 prompt |
| 标注交互 | WebSocket 流式，右侧对话面板（参照 Cursor/CodeBuddy） |
| 本体映射 | entity_candidate + is_entity_identifier + is_relationship_key + related_table |

### 新增文件

| 文件 | 说明 |
|------|------|
| `backend/app/db/models/metadata_model.py` | MetaTable + MetaColumn ORM 模型 |
| `backend/app/db/repositories/metadata_repo.py` | MetaTableRepository（upsert）+ MetaColumnRepository |
| `backend/app/services/metadata_service.py` | 元数据提取/浏览/标注/本体候选 服务 |
| `backend/app/schemas/metadata_schema.py` | 元数据 Pydantic Schema |

### 修改文件

| 文件 | 变更 |
|------|------|
| `backend/app/db/models/__init__.py` | 注册 MetaTable, MetaColumn |
| `backend/app/api/v1/perception.py` | 新增 10 个端点（sync/databases/tables/detail/preview/annotate + WebSocket 流式标注） |
| `frontend/src/services/index.ts` | 新增 10 个 API 方法 + WebSocket URL |
| `frontend/src/pages/perception/index.tsx` | 元数据浏览区 + 表详情双栏 Drawer（左:元数据 右:标注对话面板） |

### 数据库表设计

#### meta_tables — 表级元数据

| 字段 | 说明 |
|------|------|
| datasource_id | 关联数据源 |
| database_name + table_name | 库表定位（联合唯一） |
| table_type | table / view |
| table_comment / table_comment_llm | 原始注释 + LLM 生成注释 |
| business_description / purpose / domain | 业务描述/用途(dim/fact/ods/...)/业务域 |
| entity_candidate | 本体候选实体标记 |
| row_count / column_count / storage_size_mb / engine | 技术元数据 |

#### meta_columns — 字段级元数据

| 字段 | 说明 |
|------|------|
| column_name / data_type / data_type_full | 字段名和类型 |
| is_primary_key / is_unique / is_indexed / is_nullable | 约束信息 |
| column_comment / column_comment_llm | 原始注释 + LLM 注释 |
| semantic_type | 语义类型(id/name/amount/time/status/...) |
| is_entity_identifier / is_relationship_key | 本体映射辅助 |
| related_table / related_column | 外键关联（用于提取关系） |

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/datasources/{id}/sync` | 提取元数据（支持 sync_all） |
| GET | `/datasources/{id}/databases` | 列出所有库 |
| GET | `/datasources/{id}/tables` | 表元数据列表 |
| GET | `/meta/tables/{id}` | 表详情（含字段） |
| PUT | `/meta/tables/{id}` | 编辑表业务元数据 |
| PUT | `/meta/columns/{id}` | 编辑字段业务元数据 |
| POST | `/meta/tables/{id}/preview` | 实时数据预览 |
| POST | `/meta/tables/{id}/annotate` | LLM/Agent 自动注释（HTTP） |
| **WS** | `/meta/tables/{id}/annotate/stream` | 流式标注（WebSocket） |
| GET | `/datasources/{id}/ontology-candidates` | 本体候选 |

### 标注交互（Cursor/CodeBuddy 风格）

后端 WebSocket `/meta/tables/{id}/annotate/stream`:
- asyncio subprocess 逐行读取 Agent CLI stdout
- 实时推送事件: status/context/prompt/thinking/text/tool_use/tool_result/error/applied/done
- 支持 Agent CLI 流式（OpenClaw --json / OpenCode --format json）
- 也支持平台 LLM
- 自动解析 JSON 结果并应用注释到数据库

前端表详情 Drawer（1200px 双栏）:
- 左侧（flex 1）: 表元数据 + 字段列表 + 数据预览
- 右侧（460px）: 智能标注对话面板
  - Agent 选择器（平台 LLM / OpenClaw / OpenCode）
  - 事件流区域（实时显示执行过程，带图标颜色区分）
  - 自定义 prompt 输入框 + 发送/停止按钮

### 验证
- ✅ TypeScript 编译零错误
- ✅ 后端路由全部注册
- ✅ WebSocket 流式标注可用
- ✅ 元数据提取支持同步所有库
- ✅ 外键关系自动提取

---

## 2025-07-02

### Agent: 主开发 Agent（资源管理增强 — 本地服务器一键注册 + Agent 自动发现 + CLI 流式交互）

### 目标
1. 修复计算节点显示 offline 问题
2. 实现一键添加本地服务器为计算节点
3. 自动发现计算节点上运行的 Agent（OpenClaw/OpenCode）
4. 支持与 Agent 实时流式交互测试（WebSocket）

### Bug 修复

| 问题 | 根因 | 修复 |
|------|------|------|
| 计算节点显示 offline | `status` 默认值是 `offline`，心跳接口只写 `last_heartbeat` 不写 `status` | `update_heartbeat()` 同时设置 `status=online`；`register-local` 注册后立即设为 `online` |
| Ant Design v5 废弃警告 | `bodyStyle`/`valueStyle`/`width`/`direction` 等 prop 被废弃 | 全量替换为 `styles.body`/`styles.content`/`styles.wrapper`/`orientation` |
| Agent 测试「无响应内容」 | OpenClaw/OpenCode 是 CLI 工具不是 HTTP 服务，之前用 HTTP 请求打 dev server 端口 | 改为 CLI 模式，用 `shutil.which` 检测命令路径 |
| OpenCode 输出解析失败 | 输出带 ANSI 转义码 + JSONL 事件流，旧代码直接 `json.loads` 整体失败 | 逐行解析 JSONL + ANSI 清理 |
| OpenClaw 需要 --agent 参数 | `agent` 命令必须指定 `--agent <name>` | 自动执行 `agents list` 获取第一个可用 agent 名称 |
| WebSocket 连接失败 | 后端缺少 `websockets` 库 | `pip install websockets` |
| 发送后不自动停止 loading | 后端 `while True` 循环发完 `done` 后没 `break`；前端 `onclose` 只在无内容时才 `setChatSending(false)` | 后端加 `break`；前端 `onclose` 无条件重置 |
| Space.Compact DOM 错误 | antd Drawer 内 `getBoundingClientRect` on null | 改为普通 flex div |

### 新增文件

| 文件 | 说明 |
|------|------|
| `backend/app/services/agent_discovery.py` | Agent 发现与可用性检测服务（CLI 检测 + 进程扫描 + 端口扫描 + HTTP 健康检查） |

### 修改文件

| 文件 | 变更要点 |
|------|---------|
| `backend/app/api/v1/resources.py` | 新增 `register-local`、`scan-agents`、`agents/{id}/chat`（POST）、`agents/{id}/chat/stream`（WebSocket）4 个端点 |
| `backend/app/db/repositories/instance_repo.py` | `update_heartbeat` 同时更新 `status=online` |
| `frontend/src/pages/resources/index.tsx` | 计算节点卡片新增「添加本地服务器」按钮 + Agent 发现区域 + Agent 卡片新增 💬 测试按钮 + WebSocket 流式聊天 Drawer |
| `frontend/src/services/index.ts` | 新增 `registerLocalInstance`、`scanAgents`、`chatWithAgent`、`chatWithAgentStream` |
| `frontend/src/types/index.ts` | 新增 `DiscoveredAgent`、`AgentScanResult` 类型 |

### 设计决策

| 决策点 | 选择 |
|--------|------|
| Agent 发现策略 | CLI 命令检测（`shutil.which`）> 进程扫描（`pgrep`）> 端口扫描 + HTTP 健康检查 |
| Agent 交互模式 | 自动判断：entrypoint 以 `http` 开头 → HTTP 模式，否则 → CLI 模式 |
| CLI 命令模板 | 参照 multica 项目封装方式，每种 agent_type 有专属 `cli_chat_args` |
| 流式交互 | WebSocket + `asyncio.create_subprocess_exec` 逐行读取 stdout，实时推送事件 |
| agent_name 存储 | OpenClaw 的 `--agent` 参数值存入 `env_template` 字段 |

### Agent 发现配置（参照 multica）

| Agent | CLI 命令 | 交互参数 | 环境变量 |
|-------|---------|---------|---------|
| OpenClaw | `openclaw` | `agent --agent {agent_name} -m "{msg}" --json` | — |
| OpenCode | `opencode` | `run --format json "{msg}"` | `OPENCODE_PERMISSION={"*":"allow"}` |
| Harness | `harness` | `"{msg}"` | — |

### WebSocket 事件类型

| 事件 | 图标 | 说明 |
|------|------|------|
| `status` | ⏳ | 执行状态 |
| `thinking` | 💭 | 思考过程 |
| `text` | 💬 | 文本回复 |
| `tool_use` | 🔧 | 工具调用 |
| `tool_result` | 📋 | 工具结果 |
| `error` | ⚠️ | 错误信息 |
| `log` | ┃ | 原始日志 |
| `meta` | ℹ️ | 模型信息 |
| `done` | — | 完成（exit_code + stderr） |

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/resources/instances/register-local` | 一键添加本地服务器 |
| POST | `/resources/instances/{id}/scan-agents` | 扫描 Agent + 自动注册 |
| POST | `/resources/agents/{id}/chat` | Agent 交互（HTTP，兼容旧版） |
| **WS** | `/resources/agents/{id}/chat/stream` | Agent 交互（WebSocket 流式） |

### 本机检测结果
- OpenClaw → `/opt/homebrew/bin/openclaw` (v2026.3.13) — CLI 模式，agent_name=testagent
- OpenCode → `/Users/sunleone/.opencode/bin/opencode` (v1.14.39) — CLI 模式
- 当前状态：两个 Agent 的 API key/订阅均过期（OpenCode: Coding Plan expired，OpenClaw: API rate limit）

### 验证
- ✅ TypeScript 编译零错误
- ✅ 后端所有路由注册正常
- ✅ WebSocket 流式交互可用（thinking/text/error/log 实时推送）
- ✅ 前端事件流渲染正常（带图标+颜色区分）
- ✅ 发送/停止 loading 状态正确

---

## 2025-07-01

### Agent: 主开发 Agent（下午 — 需求项目管理完整实现）

### 目标
实现 Agent 驱动的需求项目管理（Project / Requirement / Plan / Task + Kanban），打通「需求提交 → Agent评审打分 → Agent拆解为Task → 看板跟踪」全链路。

### 设计决策

| 决策 | 方案 |
|------|------|
| 需求模板 | 标题 / 类型(feature|bug|improvement|perf) / 优先级(P0-P3) / 描述 / 验收标准 / 影响范围 |
| Agent 评审 | LLM 三维打分：需求清晰度 + 技术可行性 + 业务价值 → 综合评分 ≥5 通过 |
| 任务拆解 | LLM 自动拆分为 3-8 个 Task，含标题/描述/优先级/工时/建议Agent类型 |
| 敏捷看板 | 4 列（待开始/进行中/评审中/已完成），HTML5 原生拖拽移动 |
| 项目层级 | Project → Plan (Sprint/Release/Milestone) → Task |

### 新增文件（后端）

| 文件 | 说明 |
|------|------|
| `backend/app/db/models/project_model.py` | Project ORM（name/key/icon/color/status） |
| `backend/app/db/models/requirement_model.py` | Requirement ORM（模板字段 + Agent 评分字段） |
| `backend/app/db/models/plan_model.py` | Plan ORM（sprint/release/milestone + 日期范围） |
| `backend/app/db/models/task_model.py` | Task ORM（status/assignee_agent/工时/position） |
| `backend/app/db/repositories/project_repo.py` | ProjectRepository |
| `backend/app/db/repositories/requirement_repo.py` | RequirementRepository |
| `backend/app/db/repositories/plan_repo.py` | PlanRepository |
| `backend/app/db/repositories/task_repo.py` | TaskRepository（含 get_kanban / batch_create） |
| `backend/app/schemas/project_schema.py` | 全部 Pydantic Schema（含 TaskMove 看板移动） |
| `backend/app/services/project_service.py` | ProjectService CRUD |
| `backend/app/services/requirement_service.py` | RequirementService + analyze() LLM评审 + decompose() LLM拆解 |
| `backend/app/api/v1/projects.py` | 完整 REST API（20 个端点 + /kanban 看板查询） |

### 新增文件（前端）

| 文件 | 说明 |
|------|------|
| `frontend/src/pages/projects/index.tsx` | 完整页面：项目选择器 + 需求池(卡片列表) + 敏捷看板(拖拽4列) + 计划列表 + Agent工作流引导 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `backend/app/db/models/__init__.py` | 注册 4 个新模型 |
| `backend/app/api/v1/router.py` | 挂载 projects 路由 |
| `backend/schema.sql` | 新增 4 张表 DDL（projects/requirements/plans/tasks） |
| `frontend/src/App.tsx` | 注册 /projects 路由 |
| `frontend/src/components/layout/AppLayout.tsx` | 导航新增「项目管理」 |
| `frontend/src/types/index.ts` | 新增 5 个类型（Project/Requirement/Plan/Task/KanbanData） |
| `frontend/src/services/index.ts` | 新增 projectsAPI 完整封装（20+ 方法） |

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST/PUT/DELETE | `/projects` | 项目 CRUD |
| GET/POST | `/projects/{id}/requirements` | 需求列表/创建 |
| PUT/DELETE | `/projects/{id}/requirements/{rid}` | 需求更新/删除 |
| POST | `/projects/{id}/requirements/{rid}/analyze` | 🤖 Agent 评审打分 |
| POST | `/projects/{id}/requirements/{rid}/decompose` | 🤖 Agent 拆解为 Task |
| GET/POST/PUT/DELETE | `/projects/{id}/plans` | 计划 CRUD |
| GET/POST/PUT/DELETE | `/projects/{id}/tasks` | 任务 CRUD |
| PUT | `/projects/{id}/tasks/{tid}/move` | 看板拖拽移动 |
| GET | `/projects/{id}/kanban` | 看板数据 |

### 验证
- ✅ TypeScript 编译零错误
- ✅ 全部 API 端点返回正常
- ✅ 项目 CRUD + 需求 CRUD + 计划 CRUD 全链路验证
- ✅ 后端自动建表生效（12 张表完整）

---

### Agent: 主开发 Agent（上午 — 资源管理中心完整实现）

### 目标
实现资源管理的 5 个核心实体（Instance / Agent / Skill / MCP / AgentRun）+ WebSocket 实时日志，支撑 Agent 编排配置能力。

### 设计决策
| 决策点 | 选择 |
|--------|------|
| 节点管理协议 | SSH + Docker API（不做 k8s） |
| Agent 运行方式 | 混合支持：docker / python / node / binary |
| Skill 归属 | 全局共享，Agent 管理页一键安装 |
| MCP 自动发现 | 任意 HTTP API + LLM 推断参数 |
| 实时日志 | WebSocket 流式推送 |

### 新增文件（后端）

| 文件 | 层 | 说明 |
|------|------|------|
| `backend/app/db/models/instance_model.py` | 数据层 | Instance ORM（instance_type / protocol / credential / labels / status） |
| `backend/app/db/models/agent_model.py` | 数据层 | Agent ORM（agent_type / runtime / docker_image / skill_ids） |
| `backend/app/db/models/skill_model.py` | 数据层 | Skill ORM（skill_type / install_cmd / is_installed / tags） |
| `backend/app/db/models/mcp_model.py` | 数据层 | MCPConfig ORM（mcp_type / auto_discovery / tools_manifest） |
| `backend/app/db/models/agent_run_model.py` | 数据层 | AgentRun ORM（status / container_id / pid / log_offset） |
| `backend/app/db/repositories/instance_repo.py` | 数据层 | InstanceRepository（update_heartbeat） |
| `backend/app/db/repositories/agent_repo.py` | 数据层 | AgentRepository（get_by_type） |
| `backend/app/db/repositories/skill_repo.py` | 数据层 | SkillRepository（get_installed / get_by_tags） |
| `backend/app/db/repositories/mcp_repo.py` | 数据层 | MCPRepository |
| `backend/app/db/repositories/agent_run_repo.py` | 数据层 | AgentRunRepository（get_running / get_by_agent / get_by_instance） |
| `backend/app/schemas/instance_schema.py` | Schema | Instance CRUD Pydantic 校验 |
| `backend/app/schemas/agent_schema.py` | Schema | Agent CRUD + AgentUpdate |
| `backend/app/schemas/skill_schema.py` | Schema | Skill CRUD + SkillInstallRequest |
| `backend/app/schemas/mcp_schema.py` | Schema | MCP CRUD + MCPAutoDiscoverRequest（api_url / method / LLM 推断参数） |
| `backend/app/schemas/agent_run_schema.py` | Schema | AgentRun CRUD + LogEntry |
| `backend/app/services/instance_service.py` | 服务层 | InstanceService 完整 CRUD |
| `backend/app/services/agent_service.py` | 服务层 | AgentService 完整 CRUD |
| `backend/app/services/skill_service.py` | 服务层 | SkillService + install() 一键安装 |
| `backend/app/services/mcp_service.py` | 服务层 | MCPService + auto_discover() LLM 推断 |
| `backend/app/services/agent_run_service.py` | 服务层 | AgentRunService + stream_logs() WebSocket 日志流 |
| `backend/app/api/v1/resources.py` | 接口层 | 完整 API：Instance/Agent/Skill/MCP/AgentRun 全部 CRUD + WebSocket 日志 + MCP 自动发现 |

### 新增文件（前端）

| 文件 | 说明 |
|------|------|
| `frontend/src/pages/resources/index.tsx` | 全面重写：6 个 Tab（LLM 配置 + 计算节点 + 智能体 + 技能 + MCP 工具 + 运行监控），含 WebSocket 日志抽屉、MCP 自动发现弹窗、Skill 一键安装按钮 |
| `docs/RESOURCE_MANAGEMENT_DESIGN.md` | 资源管理模块设计文档（实体关系、字段设计） |

### 修改文件

| 文件 | 变更 |
|------|------|
| `backend/app/db/models/__init__.py` | 注册 5 个新模型 |
| `backend/app/api/v1/router.py` | 挂载 resources 路由 `/resources` |
| `backend/app/main.py` | 添加启动时自动建表 `Base.metadata.create_all()` |
| `backend/schema.sql` | 新增 5 张表 DDL（instances / agents / skills / mcp_configs / agent_runs） |
| `frontend/src/types/index.ts` | 新增 5 个实体类型定义 |
| `frontend/src/services/index.ts` | 新增 resourcesAPI 完整调用封装 |

### API 端点汇总（全部测试通过）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST/PUT/DELETE | `/resources/instances` | 计算节点 CRUD |
| POST | `/resources/instances/{id}/heartbeat` | 心跳刷新 |
| GET/POST/PUT/DELETE | `/resources/agents` | Smart Agent CRUD |
| GET/POST/PUT/DELETE | `/resources/skills` | Skill CRUD |
| POST | `/resources/skills/{id}/install` | 一键安装 Skill |
| GET/POST/PUT/DELETE | `/resources/mcps` | MCP 工具 CRUD |
| POST | `/resources/mcps/auto-discover` | LLM 自动发现 MCP |
| GET/POST/PUT | `/resources/runs` | AgentRun 管理 |
| POST | `/resources/runs/{id}/stop` | 停止运行 |
| **WS** | `/resources/runs/{id}/logs` | WebSocket 实时日志 |

### 验证
- ✅ TypeScript 编译零错误
- ✅ 5 个端点全部返回 `{"code":"SUCCESS"}`
- ✅ 创建/查询/删除 Instance、Agent 全链路验证通过
- ✅ 后端自动建表生效（8 张表完整）

---

## 2025-06-30

### Agent: 主开发 Agent（晚间 — 感知层智能添加 & Bug 修复）

### 目标
修复前端白屏和智能添加失败问题，打通感知层完整链路（LLM 解析 → 保存 → 测试连接）。

### Bug 修复

| 问题 | 根因 | 修复 |
|------|------|------|
| 前端白屏 | `perception/index.tsx` 使用不存在的图标 `TestOutlined`（`@ant-design/icons` 无此导出） | 替换为 `ExperimentOutlined` |
| 智能添加返回 500 | Qwen 推理模型返回 `content: null`，实际内容在 `reasoning` 字段 | `_call_openai()` 增加 fallback：`content` → `reasoning` → `reasoning_content` |
| LLM 解析 token 不足 | `max_tokens=1024` 不够推理模型思考 | 增加为 `4096`（parse-config / auto-configure），诊断类增加为 `512` |
| 保存数据源事务冲突 | `DataSourceService` 多处 `with self.db.begin()` 嵌套导致冲突 | 改为手动 `self.db.commit()` |
| LLM 返回字段名不标准 | Qwen 返回 `"type": "doris"` 而非 `"source_type": "doris"`，导致类型设为 unknown | 新增 `_normalize_parsed()` 辅助函数，`_FIELD_ALIASES` 映射 15+ 别名 |

### 新增文件

| 文件 | 说明 |
|------|------|
| `backend/app/db/models/data_source_model.py` | DataSource ORM 模型 |
| `backend/app/db/repositories/data_source_repo.py` | DataSourceRepository 数据层 |
| `backend/app/schemas/data_source_schema.py` | DataSource Pydantic Schema |
| `backend/app/services/data_source_service.py` | DataSourceService 服务层（含 create/update/delete/update_status/test_connection） |

### 修改文件

| 文件 | 变更要点 |
|------|---------|
| `backend/app/api/v1/perception.py` | 新增智能添加 3 个端点（parse-config / auto-configure / test-connection-for-source）、LLM 调用集成、`_normalize_parsed` 字段别名映射 |
| `backend/app/services/llm_config_service.py` | `_call_openai()` 增加 reasoning 字段 fallback；统一 `_call` 方法 |
| `backend/app/api/v1/llm.py` | 新增 `/active/info` 端点获取当前活跃 LLM 配置快照 |
| `backend/app/db/models/llm_config_model.py` | 补充字段 |
| `backend/app/schemas/llm_config_schema.py` | 补充 Schema 字段 |
| `backend/app/db/models/__init__.py` | 注册 DataSource 模型 |
| `frontend/src/pages/perception/index.tsx` | 重写：完整 CRUD 表格 + 智能添加对话框 + 连接测试 |
| `frontend/src/services/index.ts` | 新增 `DataSource` 类型和 API |
| `frontend/src/types/index.ts` | 新增 DataSource 类型定义 |
| `frontend/src/services/llm.service.ts` | 补充 API 方法 |
| `frontend/src/pages/resources/index.tsx` | 适配新类型 |

### 验证
- ✅ 智能添加全链路：LLM 解析配置 → 保存数据库 → 连接测试成功
- ✅ 解析返回正确字段：`source_type: doris` 带全部连接参数
- ✅ 前端无白屏，页面正常渲染
- ✅ TypeScript 编译零错误

---

### Agent: 主开发 Agent（下午 — UI/UE 框架重构）

### 目标
将前端整体替换为**硅谷风格**设计系统，涵盖暗色主题、玻璃拟态、渐变光晕、点阵背景、精致排版。

### 设计决策
| 维度 | 选择 |
|------|------|
| 主题 | Ant Design `darkAlgorithm` + 自定义覆写 |
| 字体 | Plus Jakarta Sans（Google Fonts）+ JetBrains Mono |
| 主色 | 蓝 `#3b82f6` → 紫 `#8b5cf6` → 青 `#06b6d4` 三色渐变 |
| 背景 | `#060b14` 根背景，`32px` 间距点阵纹理 |
| 玻璃效果 | `backdrop-filter: blur(12-20px)` + 半透明渐变 |
| 动效 | `cubic-bezier(0.16, 1, 0.3, 1)` 弹性曲线 |

### 新增文件
| 文件 | 说明 |
|------|------|
| `frontend/src/styles/global.css` | 全局设计系统：CSS 变量（60+ Token）、动画关键帧（6 组）、点阵背景、玻璃拟态工具类、antd 组件 20+ 覆写 |

### 重写文件
| 文件 | 变更要点 |
|------|---------|
| `frontend/index.html` | 标题、lang、theme-color meta |
| `frontend/src/main.tsx` | 导入 global.css |
| `frontend/src/App.tsx` | `darkAlgorithm`、覆写全部 token、添加 `App` 包裹 |
| `frontend/src/components/layout/AppLayout.tsx` | 分组菜单（五层架构 group）、毛玻璃侧边栏、粘性顶栏、Logo 渐变图标、页面入场 `.page-enter` 错开动画 |
| `frontend/src/pages/Login.tsx` | 全屏暗色背景、双色模糊光球、玻璃拟态卡片、入场淡入 |
| `frontend/src/pages/dashboard/index.tsx` | 渐变色统计卡片、彩色图标容器、五层状态彩色指示灯 |
| `frontend/src/pages/perception/index.tsx` | Tag 颜色系统重构、Card 标题带图标 |
| `frontend/src/pages/cognition/index.tsx` | 图谱占位区渐变背景、语义搜索、实体/关系表格统一 Tag 风格 |
| `frontend/src/pages/decision/index.tsx` | 决策层 3 统计卡片、策略状态色彩映射表 |
| `frontend/src/pages/execution/index.tsx` | 监控指标彩色数字、目标系统在线 Tag、执行状态映射 |
| `frontend/src/pages/application/index.tsx` | AIbi 输入区渐变底层、数据集/仪表盘卡片 |
| `frontend/src/pages/users/index.tsx` | 用户表格外容器玻璃态、角色/状态彩色 Tag |

### Bug 修复
- 修复 `cognition/index.tsx` 缺少 `NodeIndexOutlined` 导入导致白屏
- 修复 `AppLayout.tsx` 误用 `useUserStore` 获取 sidebar 状态（改为 `useAppStore`）

### 验证
- TypeScript 编译零错误
- 20 个文件变更，+1646 / -267 行

---

### Agent: 主开发 Agent（上午 — 全链路打通）

### 目标
打通前后端全链路，实现用户注册/登录/删除完整功能，并使用本地 MySQL 数据库。

### 后端修复
| 文件 | 修复内容 |
|------|----------|
| `backend/app/core/exceptions.py` | 新增 `UnauthorizedException`（auth_service 之前引用但未定义） |
| `backend/app/api/v1/router.py` | 挂载 users 路由（之前遗漏） |
| `backend/app/api/v1/users.py` | 移除 router 内的 `prefix="/users"`（避免与 include_router 的 prefix 重复）；移除重复的 login 端点；路由重新排序避免 GET "" 与 GET "/{user_id}" 冲突 |
| `backend/app/api/v1/auth.py` | `/me` 端点从硬编码改为从 JWT Authorization Header 提取 user_id；`get_current_user_id` 依赖注入; register 改用 UserCreate Pydantic 校验 |
| `backend/app/services/auth_service.py` | 补充缺失的 `NotFoundException` 导入 |
| `backend/app/main.py` | 注册全局异常处理器 `add_exception_handlers(app)` |
| `backend/.env` | 新建：配置 DB_USER=root（无密码），匹配本地 MySQL |

### 数据库
- 创建 MySQL 数据库 `ontomind`（utf8mb4）
- SQLAlchemy `Base.metadata.create_all()` 初始化 `users` 表
- 注意：bcrypt 需用 4.x 版本（5.x 与 passlib 不兼容）

### 前端修复
| 文件 | 修复内容 |
|------|----------|
| `frontend/src/App.tsx` | 重写：移除循环引用，正确配置 react-router-dom Routes（公开 /login + 受保护路由 + 404 兜底） |
| `frontend/src/pages/Login.tsx` | 重写：真实对接 /auth/login 和 /auth/register API，支持登录+注册双 Tab |
| `frontend/src/services/user.service.ts` | login 改为 /auth/login，新增 getCurrentUser(/auth/me)；添加 snake_case→camelCase 映射 |
| `frontend/src/stores/userStore.ts` | fetchCurrentUser 调用 /auth/me |
| `frontend/src/components/layout/AppLayout.tsx` | 新增退出登录功能、当前用户显示、用户管理菜单项 |

### 新增文件
| 文件 | 说明 |
|------|------|
| `frontend/src/pages/users/index.tsx` | 用户管理页面（表格展示 + 新建 + 删除） |

### 验证结果
- ✅ 用户注册 POST /auth/register
- ✅ 用户登录 POST /auth/login → 返回 JWT Token
- ✅ 获取当前用户 GET /auth/me（JWT 认证）
- ✅ 用户列表 GET /users
- ✅ 用户删除 DELETE /users/{id}
- ✅ 后端运行在 :8000，前端运行在 :5173
- ✅ MySQL `ontomind` 数据库，root 无密码

### 已知问题
- 前端用户管理页面（/users）需手动登录后访问，登录/注册在 Login 页面的双 Tab 中

---

## 2025-06-29

### Agent: 主开发 Agent

### 目标
为 OntoMind 项目建立全栈开发规范和设计范式，实现后端三层架构（接口层/服务层/数据层）分层重构。

### 新增文件

#### 规范文档
| 文件 | 说明 |
|------|------|
| `backend/STANDARDS.md` | 后端开发规范：分层架构、事务控制、命名规范、错误处理、依赖注入 |
| `backend/DESIGN_STANDARDS.md` | API 设计标准（RESTful 规范、错误码）和数据库设计标准（表命名、字段命名、索引策略） |
| `backend/REFACTORING_GUIDE.md` | 现有代码重构指南，指导如何将旧代码迁移到三层架构 |
| `frontend/STANDARDS.md` | 前端开发规范：代码组织、TypeScript 类型、API 服务层、Zustand 状态管理 |

#### 后端基础架构
| 文件 | 说明 |
|------|------|
| `backend/app/db/models/base.py` | BaseModel - 所有 ORM 模型基类（含 id, created_at, updated_at） |
| `backend/app/db/repositories/base_repo.py` | BaseRepository - 数据层基类，封装通用 CRUD 方法 |
| `backend/app/services/base_service.py` | BaseService - 服务层基类，统一管理 db session 注入 |
| `backend/app/core/exceptions.py` | BusinessException - 统一业务异常类（含错误码 + HTTP 状态码） |
| `backend/app/core/decorators.py` | @transactional - 事务装饰器，自动管理 commit/rollback |

#### 安全工具（新增 + 重构）
| 文件 | 说明 |
|------|------|
| `backend/app/core/security.py` | 密码哈希（bcrypt）、JWT Token 生成/解码/验证 |

#### 用户模块示例（完整三层架构模板）
| 文件 | 层 | 说明 |
|------|------|------|
| `backend/app/db/models/user_model.py` | 数据层 | User ORM 模型 |
| `backend/app/db/repositories/user_repo.py` | 数据层 | UserRepository，含特有查询方法 |
| `backend/app/schemas/user_schema.py` | Schema | Pydantic 请求/响应校验模型 |
| `backend/app/services/user_service.py` | 服务层 | UserService，含事务控制、密码加密等业务逻辑 |
| `backend/app/api/v1/users.py` | 接口层 | User CRUD API 端点 |

#### 认证模块重构
| 文件 | 说明 |
|------|------|
| `backend/app/services/auth_service.py` | 新增 AuthService，处理登录/注册/获取当前用户逻辑 |
| `backend/app/api/v1/auth.py` | 重构：从占位代码改为调用 AuthService，统一响应格式 |

#### 前端示例
| 文件 | 说明 |
|------|------|
| `frontend/src/types/user.ts` | User 相关 TypeScript 类型定义 |
| `frontend/src/services/user.service.ts` | 用户 API 服务层封装 |
| `frontend/src/stores/userStore.ts` | Zustand Store，用户状态管理 |

### 修改文件
- `backend/app/api/v1/auth.py` - 重构为三层架构，注入 AuthService
- `backend/app/core/security.py` - 重构：新增 get_password_hash/get_current_user_id_from_token，返回类型改为 Dict

### 架构决策
1. **事务边界在服务层控制**：使用 `with self.db.begin()` 或 `@transactional` 装饰器
2. **接口层只做参数校验和响应格式化**：不包含任何业务逻辑
3. **数据层不处理业务逻辑**：只封装数据库查询操作
4. **统一异常体系**：所有业务异常抛出 `BusinessException`，由全局 handler 统一处理
5. **用户模块作为完整模板**：后续所有模块（perception/cognition 等）均参照此模式开发

### 后续待办
- [ ] 重构 `perception.py`、`cognition.py` 等其他 API 文件为三层架构
- [ ] 完善 JWT 认证中间件（当前 `/me` 端点临时硬编码 user_id=1）
- [ ] 创建 perceptions/cognitions 等模块的 Repository 和 Service

---

## 2026-07-12

### Agent: 主开发 Agent（OntoMind Agent 资源平台 + OpenCode 流式 SSE）

### 目标
1. 落地 Agent 资源管理 / Studio / 对话工作台，对接本机 OpenCode
2. 会话执行过程（thinking / tools / steps / 文本）改为 **实时 SSE 流式**，不再与最终回复整包阻塞返回
3. 写清跨机交接文档，便于另一台电脑 pull 后续作

### 设计决策

| 决策点 | 选择 |
|--------|------|
| 资源真源 | 平台 `agents` 表；OpenCode 为运行时/发现面 |
| 层级 | 计算节点 → OpenCode 容器 → Agent/Skill/MCP |
| 编辑发布 | 仅资源管理 + Studio；对话工作台只聊天 |
| 执行通道 | `opencode run --format json`，按行解析 JSONL |
| 实时推送 | SSE（`GET /runs/{id}/events` 长连接）；非 WebSocket |
| 发消息 | 立即返回 `run_id`，BackgroundTasks 后台流式写事件 |
| 测试 | `force_stub=true` 同步 stub，不调 CLI |

### 功能清单
- 资源控制台：本机注册、inventory、三栏 UI、发布/去对话
- Agent Studio：草稿/发布、绑本机 OpenCode runtime
- 对话工作台：Session + Run + SSE 时间线
- Run 控制：start/cancel/pause/resume/retry + 乐观锁 `state_version`

### 新增主要路径
- `backend/app/api/v1/agent_platform/`
- `backend/app/services/agent_platform/`（含 `opencode_chat.py` 流式）
- `backend/app/db/models/agent_platform_model.py` 及 credentials/audit/discovery 模型
- `backend/alembic/versions/2026071202_*.py`、`2026071204_*.py`
- `frontend/src/pages/agent-platform/`、`hooks/useAgentStream.ts`、`stores/agentPlatformStore.ts`
- `docs/agent-platform/HANDOFF-2026-07-12.md`（**跨机必读**）

### 数据库
- **库**：一般不新建 schema/database，仍用同一 MySQL 库做 **CREATE TABLE + ALTER**
- **新表**：`credentials`、`audit_logs`、`agent_versions`、`agent_deployments`、`agent_sessions`、`agent_messages`、`agent_run_steps`、`agent_run_events`（SSE 真源）、`agent_tool_approvals`、`eval_suites`、`eval_cases`、`node_connections`、`discovery_runs`、`discovery_items`
- **改表**：`agents`（owner/current_version）、`agent_runs`（status→VARCHAR + session/strategy/input/output/state_version…）、`compute_nodes`（address/environment/heartbeat…）
- **字段级明细**：见 [`docs/agent-platform/HANDOFF-2026-07-12.md`](docs/agent-platform/HANDOFF-2026-07-12.md) §3

### 验证
- `pytest tests/agent_platform/` → 10 passed
- 联调：发消息应立刻返回，SSE 推送 step/thinking/message.delta

### 跨机续作入口
详见 [`docs/agent-platform/HANDOFF-2026-07-12.md`](docs/agent-platform/HANDOFF-2026-07-12.md)
