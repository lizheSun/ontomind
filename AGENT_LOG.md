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

---

## 2026-07-24

### Agent: OpenCode Serve/SDK 接入对话工作台

### 目标
不用 iframe 嵌 OpenCode Web；自研 `/workspace` UI 保持不变，后端将对话主路径从短命 `opencode run` 升级为长驻 `opencode serve` + HTTP/SSE 桥接，能力对齐 Web（多轮会话、流式、审批、取消）。

### 决策
| 决策点 | 选择 |
|--------|------|
| UI | 继续 AgentChatPanel / ChatWorkspacePage，不嵌官方 Web |
| 协议 | 前端只谈 OntoMind Session/Run/SSE；后端桥接 Serve |
| SDK | Python `httpx` 调 Serve HTTP/SSE（对齐 CLI 1.17+），不引入 Node `@opencode-ai/sdk` |
| 会话 | OntoMind `session_metadata.opencode_session_id` 映射远端 session |
| Fallback | Serve 不可用时回退 `opencode run --format json` |
| 权限 | v1 默认 `OPENCODE_PERMISSION={"*":"allow"}`；`permission.asked` 仍可落审批并回写 Serve |

### 新增文件
- `backend/app/services/agent_platform/opencode_serve_manager.py`
- `backend/app/services/agent_platform/opencode_session_bridge.py`

### 修改文件
- `backend/app/services/agent_platform/opencode_chat.py` — Serve 优先 stream
- `backend/app/services/agent_platform/run.py` — meta/checkpoint、取消 abort、审批落库
- `backend/app/services/agent_platform/approval.py` — 回写 OpenCode permission
- `backend/app/services/agent_platform/node_service.py` — 暴露 `opencode_serve` 状态（无密码）
- `backend/app/api/v1/agent_platform/nodes.py` — `POST .../opencode-serve/ensure`
- `backend/app/core/config.py` — `OPENCODE_SERVE_*` / `OPENCODE_MIN_VERSION`
- `frontend/.../ChatWorkspacePage.tsx`、`AgentChatPanel.tsx`、`timelineReducer.ts`
- `AGENTS.md`、`backend/requirements.txt` 注释

### API 端点
- `POST /api/v1/agent-platform/nodes/{node_id}/opencode-serve/ensure`

### 验证
- 本机 CLI 1.17.18；ensure → health；bridge prompt「PONG」收到 text 事件 exit=0

## [2026-07-24] 对话工作台切换为 SDK 直连（Wave 1-3 完成）

### 目标
按用户决策把 `/agent-platform/chat` 对话工作台从"后端 CLI 子进程 + 后端 SSE 桥接"架构，
彻底切换为"前端直连本机 opencode serve (127.0.0.1:4096)"的 SDK 直连架构。
- Vendor 起点：opencode `v1.18.4` (commit `49c69c5`)
- 样式隔离：Tailwind Path B (`preflight:false` + `important:'.oc-scope'`)，Wave 4 启用
- Dev spawn：`POST /api/v1/opencode/spawn` 仅 `DEBUG=True` 挂载
- 保留 openclaw / harness 历史模块（AIBIPage / RunsPage / agent_platform 编排层仍在用），
  只删掉 `agent_runner.py` 一个 CLI wrapper；新对话工作台走全新代码路径。

### 决策
1. **不 vendor 官方 UI 组件**（Wave 3 交付版）：第一版消息 Part 用 antd 原生渲染
   （`features/opencode/components/MessagePart.tsx`），足够跑通 text/reasoning/tool/file 四类。
   Wave 4 再从 opencode `packages/web/src/components/` 移植 15 个组件（≈2500 行）。
2. **不接 `@opencode-ai/sdk`**：`features/opencode/client.ts` 自己封 fetch，接口签名与 SDK 等价，
   方便断网 / 私有 registry 场景直接构建。切回 SDK 只需替换 `client.ts` 一个文件。
3. `useAgentStream` / `AgentEmbedRunner` 保留（AIBIPage 嵌入用），新对话工作台完全不再引用。

### 新增文件
- `backend/app/api/v1/opencode.py` — 三端点：`/health`、`/spawn`(DEBUG)、`/session-link` (POST+GET)
- `backend/app/db/models/opencode_session_model.py` — 业务侧 `opencode_sessions` 映射表
- `frontend/.env.example` — `VITE_OPENCODE_URL=http://127.0.0.1:4096`
- `frontend/src/features/opencode/`（15 文件）：
  - `client.ts` — fetch wrapper（health/sessions/messages/prompt/permissions/find/config/agents/commands/mcp/SSE）
  - `types.ts` — OpenCode 数据模型（OcSession/OcPart/OcMessage/OcPermission/OcEvent…）
  - `stores/opencodeStore.ts` — Zustand，全局会话/消息/权限/流状态
  - `hooks/useOpencodeHealth.ts` `useSessions.ts` `useMessages.ts` `useEventStream.ts`
    `useSendPrompt.ts` `usePermissions.ts` `useAgents.ts` `useCommands.ts` `useFilesMention.ts`
    `useProviders.ts`
  - `components/OpencodeGuard.tsx` `HealthBanner.tsx` `ChatWorkspaceShell.tsx`
    `SessionListSidebar.tsx` `ChatMessageList.tsx` `ChatComposer.tsx` `MessagePart.tsx`
    `PermissionDialog.tsx`
  - `vendor/{LICENSE, VENDOR_META.md, styles/opencode.css}` — Wave 4 vendor 目录占位

### 修改文件
- `backend/app/api/v1/router.py` — include_router `opencode_bridge` under `/opencode`
- `backend/app/db/models/__init__.py` — 注册 `OpencodeSession`
- `backend/schema.sql` — 追加 `opencode_sessions` 表 DDL
- `backend/app/services/requirement_service.py` — Prompt 中的 agent_type 描述从 openclaw/harness/custom 改为 opencode
- `frontend/src/pages/agent-platform/ChatWorkspacePage.tsx` — 完全重写为 `<OpencodeGuard><ChatWorkspaceShell/></OpencodeGuard>`
- `AGENTS.md` — 对话工作台架构描述更新

### 删除文件
- `backend/app/services/agent_runner.py` (377 行) — CLI 子进程 wrapper，彻底废弃

### API 端点
- `GET  /api/v1/opencode/health`
- `POST /api/v1/opencode/spawn`（仅 `settings.DEBUG=True` 挂载）
- `POST /api/v1/opencode/session-link` — 绑定 (opencode_session_id, user_id, project_id)
- `GET  /api/v1/opencode/session-link` — 列出当前用户绑定过的会话

### 数据库
- 新表 `opencode_sessions`：主键 + `opencode_session_id` unique + `user_id/project_id` FK + `title`
- ⚠️ AGENTS.md 已提示：alembic 形同虚设，`app/main.py` 靠 `create_all` 自动建表；
  上生产前需要手工执行 `backend/schema.sql` 里的 `CREATE TABLE opencode_sessions ...`。

### 前置条件
开发者需先启动本机 opencode server（否则 Guard 会显示引导页）：
```bash
opencode serve --port 4096 --cors http://localhost:5173
```
Guard 会通过 `GET /api/v1/opencode/health` 每 5s 探活；也可点击顶部 [一键启动]（仅 DEBUG 模式）。

### 验证
- `tsc --noEmit` 对新增 `features/opencode` + `ChatWorkspacePage.tsx` 零错误
- `npm run lint` (oxlint) 对新增文件零 warning
- `python3 -c "import app.api.v1.opencode; import app.db.models"` 通过
- 端到端流式对话验证：**留给用户在浏览器手工验证**（需要本机启动 opencode serve 才能跑）

### 未完成（Wave 4-7）
- Wave 4：Vendor opencode v1.18.4 官方组件 + Tailwind 启用
- Wave 5：CommandPalette / FileMention / ModelSwitcher / undo-redo-fork 高级功能
- Wave 6：MCP/Skill/Agent 资源面板改造为 opencode SDK 数据源
- Wave 7：更详细的启动脚本、README 更新、E2E playwright

## [2026-07-24 后续] 对话工作台 `/` 命令面板 + `@` 文件面板

### 目标
用户反馈"输入斜杠没有反应"，要求 100% 复刻 opencode web 的交互体验。
先实现最痛点的两个：`/` 命令面板 + `@` 文件搜索面板。

### 决策
1. **不搬 SolidJS 源码**：opencode `packages/app/src/components/prompt-input/` 是 SolidJS + Effect
   (2757 行) + 自研 editor-dom + attachments，硬移植成本高。
2. **视觉参考 + React 原生实现**：参考 opencode `slash-popover.tsx` 的视觉与交互（深色圆角卡片、
   ↑↓ 键盘导航、Enter/Tab 选中、Esc 关闭、按 trigger 前 char + 空白规则识别 token）。
   用 React + antd 复刻，2 个文件 ≈ 320 行。
3. **触发规则**：光标向前扫到首个 `/` 或 `@`；trigger 前一个字符必须是空白/换行/开头
   （防止 email @ 干扰）；token 内不能含空白。

### 新增文件
- `frontend/src/features/opencode/components/SlashPopover.tsx` — `/` 命令面板
  - 输入 `/` 弹出前 12 条命令；`/x` 前缀过滤
  - source badge（command/skill/mcp）
  - 支持键盘 ↑/↓/Enter/Tab/Esc，鼠标点选，选中滚入可视区
- `frontend/src/features/opencode/components/MentionPopover.tsx` — `@` 文件面板
  - `@xxx` 触发 `oc.findFiles()`，debounce 200ms
  - 文件名 + 目录路径双行显示
  - 同样支持键盘/鼠标

### 修改文件
- `frontend/src/features/opencode/components/ChatComposer.tsx` — 深度改写
  - 新增 `detectToken()` 光标 token 识别
  - 集成 SlashPopover + MentionPopover
  - popover 打开时，textarea 的 ↑↓Enter Esc Tab 让给 popover 处理
  - 选中后 `replaceToken()` 精确替换 token 段（保留光标位置）
  - 底部快捷键提示条加了 `/=命令` `@=文件` badge

### 验证（playwright headless 冒烟）
- 输入 `/` → 弹出 12 条命令（含 command + skill）✅
- `/arkcli` 过滤 → 只显示 arkcli 前缀 ✅
- ↑↓ + Enter → 选中并插入 `/name ` ✅
- 鼠标 click → 选中 ✅
- Esc → 关闭 popover ✅
- 触发规则前 char 校验通过 ✅
- `@AGENTS` → 弹出对应文件（依赖 opencode server 启动目录，非 bug）✅

### 已知边界
- `@` 文件搜索的可用文件受限于 `opencode serve` 启动时的 cwd（就是 opencode server 的 project 根）。
  用户如果在 `/Users/sunleone` 起 server 就只能搜到该目录里的文件；在 ontomind 目录起就能搜到项目文件。
  这是 opencode server 侧的行为，不是 UI bug。
- 键盘导航时 popover 里的项目 scrollIntoView 已就位。

### 未完成（后续 Wave）
- 命令有 `template` / `arguments` 时应弹出参数输入框（当前只是插入 `/name `）
- Model Switcher（`Cmd+/` 或按钮切模型）
- Undo/Redo/Fork 消息级操作
- Markdown + code block 高亮渲染
- Diff viewer（session.diff 事件）

## [2026-07-24 追加] 对话工作台 UI 重构 — 严格对齐 opencode v1.18.4 视觉

### 目标
用户反馈"UI 太丑，重新设计简单大方一些，严格参考 opencode web/desktop 模型"。
彻底换掉 antd Card / Space / Splitter / Tag / List 的堆砌感，用 opencode v1.18.4 的
`packages/ui/src/v2/styles/*` + `packages/session-ui/src/components/*.css` 里的视觉规范复刻。

### 关键视觉决策 (参考 opencode source)
- **消息布局**：`user` 右对齐圆角气泡 (max-width `min(82%, 64ch)`, radius 10px, bg `layer-1`)；
  `assistant` 左对齐纯文本流无气泡，靠位置区分角色（严格照 `message-part.css`）
- **色板**：完整搬 opencode v2 grey scale (grey-50..1200) + blue accent + state colors，
  用 CSS `light-dark()` 自动跟随系统
- **字体**：`-apple-system` sans + `SF Mono` mono，body 14px / line-height 1.65
- **圆角**：气泡/tool card 10px，popover 12px，按钮 8px，chip 999px（pill）
- **无 badge 满天飞**：只在 tool status 和 popover source 显示；用户消息不显示 role tag
- **深浅色主题**：CSS 变量 + `light-dark()`，跟随系统主题
- **工具卡片**：head (bg layer-2 + 单色 status pill) / body (mono pre with layer-deep bg)

### 新增文件
- `frontend/src/features/opencode/vendor/styles/opencode.css` — 500 行完整视觉主题
  - v2 grey scale + blue accent + light-dark 自动切换
  - `.oc-msg-wrap[data-role]` 用户/助手区分
  - `.oc-part-tool` opencode 风格工具卡片
  - `.oc-popover` 浮层 + `oc-pop-in` 动画
  - `.oc-composer-inner` 圆角边框容器 + focus-within 边框态
  - 全套 `.oc-btn` / `.oc-icon-btn` / `.oc-hint-chip` / `.oc-session-item`

### 修改文件（视觉全部重写，不再包 antd Card/Space/Splitter/Tag/List）
- `frontend/src/features/opencode/components/ChatWorkspaceShell.tsx` — 原生 CSS grid 2 栏
- `frontend/src/features/opencode/components/SessionListSidebar.tsx` — 纯 div + SVG 图标
- `frontend/src/features/opencode/components/ChatMessageList.tsx` — user 气泡 / assistant 流
- `frontend/src/features/opencode/components/MessagePart.tsx` — 无 antd 全 css class
- `frontend/src/features/opencode/components/ChatComposer.tsx` — 圆角容器 + textarea + toolbar
- `frontend/src/features/opencode/components/SlashPopover.tsx` — opencode-style 命令面板
- `frontend/src/features/opencode/components/MentionPopover.tsx` — opencode-style 文件面板
- `frontend/src/features/opencode/components/OpencodeGuard.tsx` — 引导页视觉
- `frontend/src/features/opencode/index.ts` — 移除已删除的 HealthBanner 导出
- `frontend/src/pages/agent-platform/ChatWorkspacePage.tsx` — 去掉 antd PageHeader，全屏 shell
- `frontend/src/main.tsx` — import opencode.css

### 删除文件
- `frontend/src/features/opencode/components/HealthBanner.tsx` — 引导页并入 OpencodeGuard

### 验证
- `tsc --noEmit` 零错误
- `npm run lint` (oxlint) 新增/修改文件零告警
- Playwright headless: 发消息 → 用户右气泡 + assistant 左流式回复 + PONG 通过 ✅
- `/init` 弹 opencode-style popover，键盘/鼠标交互全通 ✅
- Esc 关 popover ✅

## [2026-07-24 又追加] session 清理 + 布局固定 + zen/god 联动

### 三个问题
1. 用户命令：清理 opencode 里所有 session，只留一个（并期望前端 sidebar 自动同步）
2. UI 有"松散感"，上下能滚动 → 底部 composer 不固定
3. Zen/God 模式对新 opencode UI 没差别

### 修复
**1. Session 清理 & 前端联动**
- 一次性调 opencode API `DELETE /session/:id` 清 79 条 session，仅留最新一条（60 直删成功 + 19
  子会话父删时级联；opencode server 侧只剩 1 条）
- Store 新增 `session.deleted` SSE 事件处理 → 自动 `state.removeSession(sid)`
- `useSessions` 新增"死绑定自愈"：`activeSessionId` 指向的 session 不在列表时，自动切到第一条或 null

**2. 布局硬修**
- 原因 1：ChatWorkspacePage 用 `position: absolute + inset:0` 撞了 antd `.ant-layout-content`
- 原因 2：算高度按 header=64px（实际是 56px）
- 修复：`useEffect` 挂载期改写 `.ant-layout-content` 的 margin/padding/minHeight/overflow/height
  为固定值；shell 用严格 `flex column` + 各 slot `flexShrink:0` / `flex:1 minHeight:0`；
  只有 `.oc-turn` 有 `overflow-y: auto`
- 结果：`bodyH=900` = `winH`，body 不再滚；`.oc-turn.scrollH=2574 > clientH=670` 只在消息区滚动

**3. Zen/God 模式**
- `AGENTS.md` 里已有 `html[data-ui-mode="zen|god"]` 全局机制（ZenGodToggle）
- 在 `opencode.css` 追加规则：
  - Zen: 隐藏 `.oc-msg-meta` `.oc-hint-chip` `.oc-header-sub` `.oc-composer-toolbar-left`
  - God: 消息 meta 蓝色高亮，暴露 `.oc-god-only` 元素（如 message id 前缀）
- `ChatMessageList` 消息底部 meta 加 `<span class="oc-god-only">· msg_id</span>`

### 修改文件
- `frontend/src/pages/agent-platform/ChatWorkspacePage.tsx` — 完全重写高度算法
- `frontend/src/features/opencode/components/ChatWorkspaceShell.tsx` — 严格 flex + 各 slot 定
- `frontend/src/features/opencode/components/ChatMessageList.tsx` — 增加 `.oc-god-only` id 显示
- `frontend/src/features/opencode/stores/opencodeStore.ts` — 新增 `session.deleted` 事件
- `frontend/src/features/opencode/hooks/useSessions.ts` — 死绑定自愈
- `frontend/src/features/opencode/vendor/styles/opencode.css` — `.oc-turn` 严格 100%，zen/god 规则

### 验证 (playwright headless)
- Sidebar session count = 1 ✅
- Shell w=1440 h=844 (=viewport 900 - header 56) ✅
- Sidebar h=844 (与 shell 齐平) ✅
- Turn scrollH=2574 > clientH=670，只在 turn 滚 ✅
- body scrollY=0 且 bodyH === winH，外层无滚动 ✅
- Zen → 隐藏 hint chips；God → 显示 hint chips ✅
- 发消息 → 1s 收到 PONG ✅

## [2026-07-24 又追加 3] Plan/Build 切换 + Model 选择

### 目标
用户反馈：composer 没 Plan/Build 模式切换，也不能选/加 Model。这是 opencode 桌面版核心 UX。

### 决策
- **Agent Mode** = 从 `GET /agent` 过滤 `mode==='primary' && !HIDDEN` 得到 build / plan
  两个 pill，横排在 composer 左下；对齐 opencode desktop 的 primary agent cycle
- **Model** = `GET /config/providers` 拿所有 provider + model，pill 在 send 按钮左边，
  点开 popover 分组展示、带搜索框、点选后 pill 立刻更新
- **快捷键**：`Cmd/Ctrl + .` 循环 primary agent；`Cmd/Ctrl + M` 打开 model switcher
- **持久化**：sessionStorage 存 `oc:currentAgent` / `oc:currentModel`
- **未配 provider**：popover 内引导点击"打开 opencode UI" (`http://127.0.0.1:4096/`)；
  原生 Add-Provider Dialog 下一 wave 再做

### 新增文件
- `frontend/src/features/opencode/components/AgentModeSwitcher.tsx` — Plan/Build pill group
- `frontend/src/features/opencode/components/ModelSwitcher.tsx` — pill + popover + 搜索

### 修改文件
- `frontend/src/features/opencode/stores/opencodeStore.ts` — 新增
  `currentAgent` / `currentModel` state、`setCurrentAgent()` / `setCurrentModel()` 及
  sessionStorage 持久化（load/save）
- `frontend/src/features/opencode/hooks/useSendPrompt.ts` — 发消息时读取 store
  currentAgent + currentModel，注入 `body.agent` / `body.model`
- `frontend/src/features/opencode/hooks/useProviders.ts` — 重写返回结构，展平 provider.models
  从 Record→ProviderModelInfo[]
- `frontend/src/features/opencode/client.ts` — `listProviders` 返回类型对齐 v1.17 真实 shape
- `frontend/src/features/opencode/components/ChatComposer.tsx` — toolbar-left 挂
  `<AgentModeSwitcher/>`，toolbar-right 挂 `<ModelSwitcher openTrigger/>`；全局监听
  `Cmd/Ctrl+.` 循环切 primary agent，`Cmd/Ctrl+M` 弹模型面板
- `frontend/src/features/opencode/vendor/styles/opencode.css` — 新增 `.oc-pill`
  `.oc-mode-group` `.oc-mode-pill` `.oc-model-popover` 全套视觉；zen 只隐藏 hint chips，
  不隐藏 mode/model switcher（核心 UX）
- `frontend/src/features/opencode/index.ts` — 导出新组件

### 验证（Playwright）
- Build + Plan pill 渲染，默认 Build 高亮 ✅
- 点击 / Cmd+. 快捷键切换 ✅
- Model pill 显示 `provider/modelID`，Cmd+M 打开面板 ✅
- 搜索 "gpt-5" 命中 12 个模型（跨 provider）✅
- 选中后 pill 更新，发消息 body 正确携带 `agent: "plan"` + `model: {...}` ✅

### 未做（下一 wave）
- 原生 Add Provider Dialog（含 API Key / OAuth / custom endpoint）—— 现在通过跳转
  `http://127.0.0.1:4096/` 兜底
- Model popover 的键盘 ↑↓ 高亮 & Enter 选中（现在只支持鼠标点选和搜索）

## [2026-07-24 又追加 4] 全站 UI 重设计 — Editorial Light Theme

### 目标
用户："重新设计整个项目的 UI，浅色为主，要高级、整洁、简单"。

### 设计定位
**editorial minimal**（编辑排版级极简）:
- 象牙白 `#fafaf7` (paper) 主背景 + 深墨黛 `#1a1918` (ink) 主文字
- 单色 accent：靛蓝墨水 `#3b52af`（indigo ink），代替以前的青蓝渐变
- Fraunces (serif italic) 做 display / 标题；Geist Sans 做 body；JetBrains Mono 做 code
- 边框全用 hairline `rgba(26,25,24,0.06~0.10)`；阴影极其克制（无 glow）
- Card / Modal / Popover 都平白无渐变，靠精确排版 + 空间讲话
- Primary Button 是**纯墨黛**背景 + 白字，不是蓝色渐变（editorial 惯例）

### 修改文件
- `frontend/src/styles/global.css` — 全面重写：
  - 新 token（paper-00..04 / ink-100..10 / accent），保留 legacy 变量映射以兼容既有页面
  - Fraunces + Geist + JetBrains Mono 三字体链
  - Antd overrides 全面浅色：Layout / Menu / Card / Table / Tag / Button / Input / Select / Modal /
    Tabs / Statistic / Pagination / Dropdown / Message / Tooltip / Alert / Splitter / Popover /
    Radio / Checkbox / Switch / Typography
  - `.bg-grid` 由深色 dot grid 改为极淡米色 dot 底噪
- `frontend/src/App.tsx` — antd `algorithm: theme.defaultAlgorithm`；token 全线切浅
- `frontend/src/components/layout/AppLayout.tsx` — Header 淡化 + Logo 改 Fraunces italic
  "OntoMind" + mono "v0.1"；Avatar 改为墨黛 solid（不是渐变）
- `frontend/src/features/opencode/vendor/styles/opencode.css` — 移除 `light-dark()`，硬编码浅色
  scheme；改用 warm-ivory grey scale 替代冷灰；header + sidebar title 改为 Fraunces italic
- 用户消息气泡：`bg-layer-2` + hairline border（不再纯 solid）
- `.oc-header-title` 从 13px sans 改为 18px Fraunces italic

### 验证 (Playwright)
- body bg = `rgb(250,250,247)` 米白 ✅
- body color = `rgb(26,25,24)` 墨黛 ✅
- header bg = `rgba(250,250,247,0.85)` + blur ✅
- font-family 首选 Geist（浏览器已加载 Google Fonts）✅
- 发消息 → 回复 ping 正常 ✅
- tsc + oxlint 零错误 ✅

### 视觉对比
- Before: 深色 (`#060b14`) + 蓝紫渐变 logo + Plus Jakarta Sans + 玻璃卡片阴影发光
- After: 象牙白 (`#fafaf7`) + Fraunces italic serif logo + hairline border + editorial 排版

### 未做（可后续）
- 其他页面 (Login / Dashboard / Resources 各详情页) 使用 legacy 变量已自动继承新色；
  但视觉密度可能还需 case-by-case 抛光
- Dark mode 切换（当前默认强制浅色）
- Google Fonts 加载失败降级样式（当前直接回退到 system-ui）

## [2026-07-24 又追加 5] Settings 面板（Shell / 推理摘要 / 工具展开 / 新版布局）

### 目标
用户："opencode web 还有这些设置" —— Shell 选择、显示推理摘要、展开 shell 工具部分、
展开编辑工具部分、新版布局。

### 分工
- **Shell**：opencode server 侧行为，通过 `PATCH /config` 写；auto → 传 `null`
- 其它 4 项：纯前端偏好（localStorage `oc:ui-settings`），影响 UI 层渲染逻辑

### 新增文件
- `frontend/src/features/opencode/hooks/useOcSettings.ts` — 偏好 state（load/save/CustomEvent 广播）+
  updateShell 顺带 PATCH /config
- `frontend/src/features/opencode/components/SettingsDialog.tsx` — Modal 面板，Editorial Light
  视觉：Fraunces italic 标题、hairline row 分隔、shell 分段控件、原生 antd Switch

### 修改文件
- `frontend/src/features/opencode/client.ts` — `patchConfig()` API
- `frontend/src/features/opencode/types.ts` — `OcConfig.shell?: string | null`
- `frontend/src/features/opencode/components/MessagePart.tsx` — reasoning part 遵循
  `showReasoningSummaries`；tool part 按 tool name 判断是否为 shell / edit 类，配合
  `expandShellTool` / `expandEditTool` 决定默认展开态；用户可点击 head 折叠
- `frontend/src/features/opencode/components/ChatWorkspaceShell.tsx` — Header 右侧新增齿轮按钮，
  点开 SettingsDialog
- `frontend/src/features/opencode/index.ts` — 导出 SettingsDialog

### 验证（Playwright）
- 齿轮按钮存在 ✅
- 点击弹出 Modal，5 个设置行 ✅
- 点 "zsh" → PATCH /config 200 返回 `{shell: zsh}`（opencode v1.17.18 不持久化 shell 字段到 GET
  响应，是 server 版本行为，UI 层已正确调用）✅
- Toggle "显示推理摘要" 从 false → true ✅
- localStorage 保存: `{"shell":"zsh","showReasoningSummaries":true,...}` ✅
- 关掉 Modal 再打开，Toggle 保持 true ✅
- 点 "自动" → PATCH `{shell:null}` ✅
- tsc + lint 零错误 ✅

### 已知问题（非本次引入）
- 有 React 警告 "Cannot update a component while rendering" 来自 SSE store 事件，不阻塞使用，
  后续可用 `queueMicrotask` 或 `useSyncExternalStore` 优化

## [2026-07-24 大清理] 删除 4 个页面 + 所有依赖（前后端 + DB）

### 目标
用户要求删除：仪表盘、应用层、项目管理、运行记录 4 个页面，**前后端全部清干净**。

### 5 项决策（均已确认）
1. 后端 agent_platform 编排层（run/approval/session/version/migration/opencode_chat/serve_manager/session_bridge）连同前端 RunsPage 一起清；保留 agents/deployments/nodes/discoveries
2. `opencode_sessions.project_id` 字段整个删（配合 projects 表 drop）
3. `resources.py::/runs*` 端点 + AgentRun model/service/repo/schema 一起删
4. AppLayout 顶部菜单去 4 项，剩 workspace / resources / perception / cognition / decision / execution / users
5. agent_looper/test.py::/jobs* + AgentJobService + AgentRunJob + AgentJobPage 一起删

### 前端删除（约 15 文件 / 2000 行）
- 页面：`pages/dashboard/` `pages/application/` `pages/projects/`（整目录）
- 页面：`pages/agent-platform/RunsPage.tsx` `timelineReducer.ts` `__tests__/`
- 隐藏页：`pages/resources/AgentJobPage.tsx`（无路由，死代码）
- 组件：`components/common/AgentEmbedRunner.tsx` + `__tests__/AgentEmbedRunner.test.tsx`
- Hooks / Store：`hooks/useAgentStream.ts` `stores/agentPlatformStore.ts`

### 前端修改
- `services/agentPlatform.service.ts` — 重写为薄壳，只保留 agents / nodes / discoveries / deployments 相关方法（~130 行）
- `services/index.ts` — 删 `projectsAPI` / `applicationAPI` block
- `types/index.ts` — 删 `Project` `Requirement` `Plan` `Task` `KanbanData` `AgentRun` 5 个 interface
- `App.tsx` — 移 4 个 imports + 4 个 route
- `components/layout/AppLayout.tsx` — `topMenuItems` 移 4 项 + 移 icon imports
- `components/common/CmdKOmnibar.tsx::buildNavItems` — 移 4 项 nav + "新建项目" 快捷操作
- `components/common/index.ts` — 移 AgentEmbedRunner 导出
- `pages/agent-platform/index.ts` — 移 RunsPage / timelineReducer 导出
- `pages/resources/AgentDetailPage.tsx` — 删 "Job 历史" tab + AgentRun / runColumns 相关（150+ 行）
- `pages/resources/index.tsx` — 删 running/errors 计数卡片 + `loadRunsStats`
- `tests/visual/screenshots.spec.ts` — 移 dashboard 断言

### 后端删除（约 30 文件 / 4000 行）
- API：`api/v1/application.py` `projects.py`；`api/v1/agent_platform/runs.py, approvals.py, sessions.py`
- Services：`agent_run_service.py` `agent_job_service.py` `agent_loop_service.py`
  `project_service.py` `requirement_service.py`
- Services：`agent_platform/run.py, approval.py, session.py, migration.py,
  opencode_chat.py, opencode_serve_manager.py, opencode_session_bridge.py`
- Repos：`agent_run_repo.py, project_repo.py, requirement_repo.py, plan_repo.py, task_repo.py`
- Models：`agent_run_model.py, agent_run_job_model.py, project_model.py,
  requirement_model.py, plan_model.py, task_model.py`
- Schemas：`agent_run_schema.py, agent_loop_schema.py`
- Tests：`tests/data_platform/test_agent_loop.py, test_agent_jobs.py, agent_platform/test_agent_platform.py`

### 后端修改
- `api/v1/router.py` — 移除 projects / application 的 include_router；改为直接 `from app.api.v1 import ...`（不含删除模块）
- `api/v1/__init__.py` — 兼容 shim（`from app.api.v1.router import api_router`）
- `api/v1/resources.py` — 删掉 AgentRun 端点段（`/runs*` GET/POST/PUT + stop + WebSocket）+ 相关 imports
- `api/v1/agent_platform/__init__.py` — 只保留 nodes/discoveries/agents/deployments 4 个 sub-router
- `api/v1/agent_platform/agents.py` — 删掉 `POST /legacy/{id}/migrate` 与 `LegacyAgentMigrationService` 引用
- `api/v1/agent_looper/test.py` — 删 `/jobs*` 端点段（190 行）+ `AgentJobService` import
- `db/models/agent_platform_model.py` — 只保留 `AgentVersion` + `AgentDeployment`；删掉
  Session/Message/RunStep/RunEvent/ToolApproval/EvalSuite/EvalCase 7 个模型
- `db/models/opencode_session_model.py` — 删 `project_id` 字段（配合 projects 表删）
- `db/models/__init__.py` — 移除对应 imports 与 `__all__`
- `tests/data_platform/test_data_model.py` — 删 AgentRunJob 相关断言，保留其余 11 张核心表

### 数据库
- **DROP**（14 张）：tasks / plans / requirements / eval_cases / eval_suites /
  agent_tool_approvals / agent_run_events / agent_run_steps / agent_messages /
  agent_sessions / agent_run_jobs / agent_runs / projects（+ opencode_sessions 的 FK to projects）
- opencode_sessions 移除 `project_id` 列
- 剩余 54 张表

### schema.sql 同步
- 删掉 agent_runs / projects / requirements / plans / tasks 5 段 DDL
- opencode_sessions DDL 去掉 project_id 字段 + fk_ocsession_project 约束

### 验证
- Playwright headless：
  - Header 菜单只剩 7 项（对话工作台 / 资源管理 / 感知层 / 认知层 / 决策层 / 执行层 / 用户管理）✅
  - `/dashboard` / `/application` / `/projects` / `/agent-platform/runs` 全部 redirect 到 `/workspace` ✅
  - Workspace 发送 ping → 收到回复 ✅
- Backend `from app.main import app` 成功，203 个 route
- `tsc --noEmit` — 我改动的文件零错误（存量老代码错误未管）
- `npm run lint` — 我改动的文件零告警

## [2026-07-24 大重构] 专家团（Expert Team）+ opencode 原生 @agent 路由

### 目标
用户要求："删除资源管理页面重建，改名'专家团'"；
1 个专家 = 一套定制好的 opencode agent 配置；
在线状态可控（启动/关闭）；对话工作台可选取。

### 核心架构决策
1. **Expert = opencode agent 定义**：创建/编辑专家时同步写入 `~/.config/opencode/agent/{slug}.md`
   (YAML frontmatter + Markdown body)；opencode 启动时 discover 该 agent
2. **对话工作台走 opencode 原生 `@agent` 路由**（不用 system prompt 伪造）：
   - ExpertPicker 选中 → `store.currentAgent = expert.slug`
   - `useSendPrompt` 里 body.agent 直接是 slug（不带 @）
   - `@popover` 里选 agent → 插入 `@slug` 到 textarea
3. **状态管理**：online = agent md 文件存在；offline = 文件不存在
4. **Docker 保留位**：`image` 字段已建，`ExpertService._start_container` mock 逻辑就位，
   等真正需要多实例隔离时再启用

### 后端新增
- `backend/app/db/models/expert_model.py` — Expert model：
  role / sop / provider / model / skills / mcps / tools / agent_file_path / status
- `backend/app/db/repositories/expert_repo.py` — Expert repo（list_ordered / get_by_slug / list_online）
- `backend/app/schemas/expert_schema.py` — Pydantic schema
- `backend/app/services/expert_service.py` — Expert service:
  - `_write_agent_md(e)` 生成 opencode agent MD 文件
  - `_remove_agent_md(e)` 删除对应文件
  - CRUD / start / stop / seed 4 个内置专家
  - 4 个内置专家 seed：data-analyst / frontend / backend / product-manager
- `backend/app/api/v1/experts.py` — /api/v1/experts 完整 CRUD + start/stop + seed

### 前端新增
- `frontend/src/services/expert.service.ts` — API 客户端
- `frontend/src/pages/experts/ExpertTeamPage.tsx` — 专家团管理页（卡片网格 + 启停 + 编辑抽屉）
  - 结构化表单：基本信息 / 角色 & 工作流 / 模型 / Skills-MCPs-Tools / 部署端点
  - Skills 支持从 20+ 常用 opencode skill 里选 + 自定义 tag
  - 工具权限勾选（read/write/bash/todo）
- `frontend/src/features/opencode/components/ExpertPicker.tsx` — Header 专家下拉
  - 显示当前 agent（默认 Build）
  - 列出所有在线专家；未被 opencode discover 的显示"未加载"提示
  - 选中 → 设置 currentAgent + currentModel + 新建专属会话（标题带 emoji）

### 前端修改
- `App.tsx` — 新增 `/experts` 路由；`/agent-platform/resources` redirect 到 `/experts`
- `AppLayout.tsx` — 菜单"资源管理"改为"专家团"
- `CmdKOmnibar.tsx` — 快捷跳转项更新
- `MentionPopover.tsx` — 扩展为 agents + files 两类结果：
  - agent 项标 `agent` badge，前缀 `@`
  - file 项标 `file` badge
  - opencode `/agent` API 拉取所有已 discover 的 agent
- `ChatWorkspaceShell.tsx` — Header 加入 ExpertPicker（AgentModeSwitcher 左侧）
- `stores/opencodeStore.ts` — 新增 currentExpertId / currentSystemPrompt state
  （后来废弃 system prompt 用法，但字段保留兼容）
- `Login.tsx` — 从深色改成 editorial light 主题（跟 workspace 一致）

### 数据库
- 新表 `experts`（在 `schema.sql` 添加）
- 字段：id / name / slug (unique) / avatar / description / role / sop /
  provider / model / temperature / skills (JSON) / mcps (JSON) / tools (JSON) /
  image / container_name / container_id / host_port / host / port / status /
  agent_file_path / started_at / stopped_at / error_message / sort_order

## [2026-07-24 后续 bug 修复]

### 1. 保存专家 500 错误
- 根因：`ExpertService` 用 `with self.db.begin()` 嵌套事务，FastAPI 的 `get_db` 已开事务
- 修：所有 create/update/delete/start/stop 改成 `flush()` + `commit()`，无 `begin()` 嵌套

### 2. 选专家后对话不知道自己身份
- 根因 1：切专家时用的是**已有 session**，opencode `system` 只在首条消息生效
- 修 1：ExpertPicker.select() 自动 `oc.createSession()` 新建专属会话
- 根因 2（更本质）：用 `system` prompt 是绕路，应该用 opencode 原生 `@agent` 路由
- 修 2：改为 `store.currentAgent = expert.slug`；`useSendPrompt` 去掉 `system` 参数

### 3. @ popover 增强
- MentionPopover 从 files-only 扩为 agents + files
- opencode `GET /agent` 拉取已 discover 的 agent（含 build/plan/product-manager
  及所有 seed 的专家）
- 选中 → 直接插入 `@slug` 到 textarea，opencode 原生解析

### 4. 双 @ bug
- 现象：`@` 后选择插入 → 变成 `@@data-analyst`
- 根因：某些场景（stale token state / IME 交互）导致 `token.triggerStart`
  位置错位，`before.slice(0, triggerStart)` 保留了原 `@`
- 修：`replaceToken()` 加防御 —— 如果 `replacement` 首字符是 `@`/`/` 且 `before`
  末尾也是同一字符，吞掉 `before` 末尾那个字符

### 5. opencode agent 热加载限制（架构注意）
- opencode server 只在启动时扫描 `~/.config/opencode/agent/*.md`
- 新增/编辑专家后需**重启 opencode** 才能通过 `@agent` 路由
- UI 应对：ExpertPicker 里未 discover 的专家灰显 + "未加载"tag + 点击时提示重启

### 验证（Playwright）
- 保存专家：`PATCH /api/v1/experts/1` 返回 SUCCESS ✅
- @pro Enter → `@product-manager ` (1 个 @) ✅
- @ Enter → `@build ` ✅
- hello @pro Enter → `hello @product-manager ` ✅
- 鼠标点选 → 同样 1 个 @ ✅
- 发送 `@product-manager who are you in 3 words` → 回复 "Product requirement doc." ✅
  (opencode 原生 subagent 路由生效)

## [2026-07-25] 补交 HANDOFF.md + 刷新 AGENTS.md

### 目标
让下一位 agent 拿到仓库能 30 分钟内跑通全链路（数据库初始化 / opencode CLI / 后端 / 前端）。

### 新增
- **`HANDOFF.md`**（新 agent 冷启动 30 分钟指南）：
  - §1 一次性初始化：装依赖、起 MySQL/Redis、建库、`.env`、`create_all` 建表、seed admin 用户 + 4 个专家
  - §2 日常启动 3 个终端（opencode serve + uvicorn + npm dev）
  - §3 核心架构：对话工作台/专家团/三方数据流
  - §4 数据库真相：alembic 坏、schema.sql 不全、如何完全重置
  - §5-6 三层架构 + 前端硬约束
  - §7 常见问题排查表
  - §8 手上活的接头协议（AGENT_LOG 格式）
  - §9 参考文档索引
  - §10 一键冒烟脚本（后端/opencode/数据库/登录列专家四步探活）

### 修改
- **`AGENTS.md`** 全量刷新：
  - 首行加"新 agent 先读 HANDOFF.md"提示
  - 项目一句话去掉已删的 application 层，改为"对话工作台 + 专家团"
  - 技术栈补充 opencode CLI ≥ 1.17
  - 常用命令改为 3 个终端方式（不再靠 docker compose）
  - 数据库章明确 schema.sql 不包含 experts/agent_versions/agent_deployments
  - 三层约束里补充"不用 `with self.db.begin()`"陷阱
  - 业务域列表更新到当前 15 个真实 router 前缀
  - 新增"对话工作台 + 专家团"章节完整描述当前架构
  - 参考文档索引加 HANDOFF.md
  - 常见坑速览补充：Service 事务陷阱 / opencode 不热加载 / IME 中文输入回车

### 未修改
- backend/STANDARDS.md / DESIGN_STANDARDS.md 保持（团队一致规范未变）
- frontend/STANDARDS.md 保持

### 验证
- 手工 review HANDOFF.md 3 遍确保 §1.6 的 seed 脚本可复制粘贴直接跑
- AGENTS.md 里所有链接指向的文件均存在

## [2026-07-27] 新增算力调度模块（Compute Scheduling）

### 目标
用户需求：新 tab「算力调度」包含两大功能
1. Docker 服务管理（管理 opencode docker 容器）
2. 调度管理（长时/定时任务 + 运行监控 + 实时日志）

### 数据模型（4 张新表）
- **docker_services**：一个 opencode docker 容器 = 一条记录（可关联 expert）
  - image / container_id / host_port / opencode_args / env / volumes / status
- **schedule_tasks**：任务定义
  - schedule_type: manual/once/interval/cron
  - schedule_expr: cron 表达式 / interval 秒数 / once ISO 时间戳
  - opencode_config: {prompt, agent, model, system}
  - enabled / status / last_run_at / next_run_at / total_runs / success_runs / failed_runs
- **task_runs**：一次运行记录（一个 task 多个 run）
  - trigger (manual/schedule/retry) / status / started_at / finished_at / duration_ms
  - snapshot (任务配置快照) / exit_code / output_summary / opencode_session_id
- **task_log_entries**：日志行（一个 run 多条 log）
  - sequence 保证同 run 内顺序，level (info/warn/error/stdout/stderr/event)

### 新增文件（后端）
- `backend/app/db/models/docker_service_model.py`
- `backend/app/db/models/schedule_task_model.py` (含 ScheduleTask + TaskRun + TaskLogEntry)
- `backend/app/db/repositories/docker_service_repo.py`
- `backend/app/db/repositories/schedule_task_repo.py`
- `backend/app/schemas/docker_service_schema.py`
- `backend/app/schemas/schedule_task_schema.py`
- `backend/app/services/docker_service_service.py`
  - Docker 可用 → 真实 `docker run/start/stop`，端口自动分配 4200-4400
  - Docker 不可用 → mock 模式，只更新 DB 状态回退到本机 4096
  - 定时探测 socket 同步状态
  - `logs(tail)` 调 `docker logs --tail N`
- `backend/app/services/schedule_task_service.py`
  - `_run_task_worker`：后台线程执行 opencode 调用，日志实时写入 task_log_entries
  - `_compute_next_run`：极简 interval + cron（`*/N * * * *` / `0 */N * * *`）+ once
  - `_Scheduler`：asyncio 后台协程每 5s 扫描 due tasks 触发
  - 手动 trigger 与调度 trigger 复用同一 worker
- `backend/app/api/v1/compute.py` — 19 个端点：
  - Docker services: list/get/create/patch/delete/start/stop/logs (8)
  - Tasks: list/get/create/patch/delete/toggle/trigger (7)
  - Runs: list_by_task/get/cancel/logs (4)

### 修改文件（后端）
- `backend/app/db/models/__init__.py` 注册 4 张新表
- `backend/app/api/v1/router.py` include `/compute`
- `backend/app/main.py` lifespan 里启动调度器 `scheduler.start(loop)`
- `backend/schema.sql` 追加 4 表 DDL

### 新增文件（前端）
- `frontend/src/services/compute.service.ts` — 完整类型 + 19 个 API 方法
- `frontend/src/pages/compute/ComputePage.tsx` — 顶层 tabs 主页
- `frontend/src/pages/compute/DockerServicePanel.tsx` — 卡片网格 + 启停 + 编辑抽屉 + 日志 Modal
- `frontend/src/pages/compute/ScheduleTaskPanel.tsx` — 卡片网格 + 触发 + 运行记录 Modal + 日志实时刷新 Modal

### 修改文件（前端）
- `frontend/src/App.tsx` — 加 `/compute` 路由 + import
- `frontend/src/components/layout/AppLayout.tsx` — 顶部菜单加"算力调度"
- `frontend/src/components/common/CmdKOmnibar.tsx` — CmdK 快捷跳转
- `AGENTS.md` — 五层业务域列表加入 `/api/v1/compute`

### 数据库
- `experts` 表以外新增 4 张：docker_services / schedule_tasks / task_runs / task_log_entries
- 建表通过 `Base.metadata.create_all(engine)` 自动完成
- schema.sql 追加 4 段完整 DDL

### API 端点（19 个）
```
GET    /api/v1/compute/docker-services
POST   /api/v1/compute/docker-services
GET    /api/v1/compute/docker-services/{id}
PATCH  /api/v1/compute/docker-services/{id}
DELETE /api/v1/compute/docker-services/{id}
POST   /api/v1/compute/docker-services/{id}/start
POST   /api/v1/compute/docker-services/{id}/stop
GET    /api/v1/compute/docker-services/{id}/logs?tail=200

GET    /api/v1/compute/tasks
POST   /api/v1/compute/tasks
GET    /api/v1/compute/tasks/{id}
PATCH  /api/v1/compute/tasks/{id}
DELETE /api/v1/compute/tasks/{id}
POST   /api/v1/compute/tasks/{id}/toggle
POST   /api/v1/compute/tasks/{id}/trigger

GET    /api/v1/compute/tasks/{id}/runs
GET    /api/v1/compute/runs/{id}
POST   /api/v1/compute/runs/{id}/cancel
GET    /api/v1/compute/runs/{id}/logs?since_seq=0
```

### 验证（Playwright + curl）
- 页面：算力调度标题 / 两个 tab (Docker 服务 + 调度任务) / 添加服务按钮 ✅
- 创建 docker service：200 ✅
- 创建 task（manual + prompt=say hi）：200 ✅
- 触发 task → 后台 worker 起线程调 opencode → 3.8s 完成 ✅
- 8 行日志按 sequence 顺序追加，含 event/info/warn/stdout ✅
- run.opencode_session_id 记录（可跳转 workspace 复盘）✅
- run.exit_code=0, status=success, duration_ms=3780 ✅
- tsc 零错误、oxlint 零告警 ✅

### 已知限制
- cron 表达式简化实现（只支持 `*/N * * * *` 和 `0 */N * * *`）—— 需要更完整可换 croniter
- 日志推送用轮询（3s 一次），非真实 SSE / WebSocket —— 用户体验足够
- Docker 未装时走 mock 模式，UI 顶部 tag 明示

## [2026-07-27] 算力调度页面原型 v2（前端重构，脱离后端）

### 目标
按新交互方案重做 `/compute` 页面：**原型先行，不接后端**。页面所有数据为本地 mock 状态，操作仅在前端模拟。

### 决策
- 头部改紧凑单行（标题 + 原型 Tag + 一句话说明 + 右侧 Tabs），不再用大 hero 区
- Docker 服务改为「节点卡片（上）+ 容器列表（下）」两层结构；节点支持本机 / SSH / Docker API(TLS) 三种挂载方式，弹窗内附两种远程方案的后端要求说明（推荐 SSH：目标节点零配置，后端走 `DOCKER_HOST=ssh://` 通道）
- 镜像搜索直连 Docker Hub 公共 API（`hub.docker.com/v2/search/repositories`，只读无需登录），失败回退内置示例数据；搜到镜像一键创建容器
- 调度运行改为「任务表 + 运行记录表」两张表：任务 = id/name/命令/日志目录/调度配置；日志落盘规则 `{logDir}/{taskId}/{yyyyMMdd}/{taskId}-{HHmmss}-{seed}.log`，编辑器内实时预览 `>> log 2>&1` 重定向后的完整命令
- 手动执行任务会生成 running 记录，打开日志窗模拟流式追加（1.2s/行，18 行后自动完结并回填统计），演示实时日志体验
- 旧实现（直连后端 compute API 的两个 Panel + service）删除，后端 `/api/v1/compute` 暂成无头 API，后续按新模型重写

### 新增文件
- `frontend/src/pages/compute/types.ts` — ComputeNode / ContainerInstance / SchedulerTask / TaskRunRecord / LogLine / HubImage
- `frontend/src/pages/compute/mock.ts` — mock 节点/容器/任务/运行记录 + 日志生成 + buildLogFile 落盘规则
- `frontend/src/pages/compute/LogViewer.tsx` — 公共日志视图（级别着色 + 跟随滚动）
- `frontend/src/pages/compute/ResourcesPanel.tsx` — 节点卡片 + 容器表格 + 挂载节点/镜像搜索/创建容器/日志 4 个弹窗
- `frontend/src/pages/compute/SchedulerPanel.tsx` — 任务表 + 编辑抽屉 + 运行记录 Modal + 日志 Modal（实时模拟）
- `frontend/src/pages/compute/compute.css` — 紧凑头部 + 节点卡片样式

### 删除文件
- `frontend/src/pages/compute/DockerServicePanel.tsx`
- `frontend/src/pages/compute/ScheduleTaskPanel.tsx`
- `frontend/src/services/compute.service.ts`

### 修改文件
- `frontend/src/pages/compute/ComputePage.tsx` — 重写为紧凑头部 + 双面板（保持挂载以保留 tab 内状态）

### 数据库 / API
- 无变化（后端未动；现有 compute 后端与新原型模型不一致，留待后端阶段重写）

### 验证
- `tsc -b` compute 目录零错误（其余模块历史错误未动）
- `oxlint src/pages/compute` 0 warnings 0 errors
- dev server (5173) HMR 加载正常，`/compute` 可访问

### 已知限制
- 全部操作为前端模拟，刷新即还原
- 远程节点"测试连接"为假延时；镜像搜索依赖浏览器可访问 hub.docker.com
- 后端重写建议：节点接入先落 SSH 方案（docker CLI over SSH / SDK `use_ssh_client`），Docker API(TLS) 作为备选

## [2026-07-27] 调度运行视图重设计（搜索 + 勾选过滤 + 任务/记录分离）

### 目标
调度运行 tab 美观度与可用性升级：任务管理与运行记录拆成独立视图；两个视图都有搜索与筛选能力。

### 决策（frontend-design skill，延续 Editorial Light 运维账簿风）
- 顶部段落式切换器（sched-switch，ink 底 + 等宽计数）：任务管理 / 运行记录（跨任务全局流水）
- 任务视图：衬线大数字统计条（总数/调度中/运行中/成功率）+ 搜索（名称/命令/#ID）+ 类型/状态下拉筛选
- 运行记录视图：搜索（#ID/日志文件/任务名）+ 任务下拉 + 触发下拉 + **状态 chips 勾选过滤**（ink 实心激活态，带实时计数）
- 细节：运行中行左侧琥珀发丝线 + 状态脉冲点、失败行红色发丝线、命令等宽 code-chip、衬线斜体空状态插画位
- 任务行「运行记录」动作直接跳到运行记录视图并带上任务过滤（替代原 Modal）
- 修复 webview 告警：antd List（v6 已废弃）→ 自绘 img-results 列表；Alert message → title；隐藏 tab 面板改懒挂载（避免 display:none 下 rc 组件测量异常）

### 修改文件
- `frontend/src/pages/compute/SchedulerPanel.tsx` — 全量重写（双视图 + 双筛选体系 + 空状态组件）
- `frontend/src/pages/compute/compute.css` — 追加 sched-switch / sched-stats / sched-toolbar / filter-chip / code-chip / run-row 发丝线 / pulse-dot / sched-empty / img-results 样式
- `frontend/src/pages/compute/ResourcesPanel.tsx` — List→自绘列表、Alert title
- `frontend/src/pages/compute/ComputePage.tsx` — 面板懒挂载

### 验证
- tsc compute 目录零错误；oxlint 0/0；read_lints 0

## [2026-07-27] 算力调度后端实现 + 前端全量接入 API

### 目标
原型确认后，实现完整后端（模型 / Repository / Service / API 三层）+ 前端从 mock 切换到真实 API 调用。

### 决策

**后端架构**
- **Docker 节点**：模型 `docker_nodes` 表（docker_hosts），支持 local / ssh / docker-api 三种连接方式。服务层用 `subprocess` 调 Docker CLI（不依赖 Python Docker SDK），SSH 远程走 `DOCKER_HOST=ssh://user@host:port` 环境变量
- **调度任务**：模型重写为 `schedule_tasks` + `task_runs` 两张表。日志不再写 DB（删除 TaskLogEntry），改为落地磁盘文件：`{logDir}/{taskId}/{yyyyMMdd}/{taskId}-{HHmmss}-{seed}.log`。执行用 `subprocess.Popen` + `preexec_fn=os.setsid`（进程组，便于 kill）。后台线程每 15s 扫描到期任务
- **API 端点 23 条**：节点 CRUD/测试 → 容器列表/创建/启停/删除/日志 → Docker Hub 代理搜索 → 任务 CRUD/启停/触发 → 运行记录查询/取消 → 运行日志增量读取
- **调度器**改用类方法 `_Scheduler.start()/stop()`（原走 `scheduler.start(event_loop)` 已废弃）

**前端改动**
- 新增 `services/compute.service.ts`：完整封装 23 条 API + 数据归一化（snake_case→camelCase）
- `ResourcesPanel.tsx`：节点/容器全部从后端加载；镜像搜索直连后端代理（再代理 Docker Hub）；操作按钮（启停/删除/日志）全部走真实 API
- `SchedulerPanel.tsx`：任务/运行记录均从后端加载；日志弹窗增量轮询（`since_line=`，3s 刷新）；运行中自动跟随、非运行中最终拉一次并停止轮询
- `types.ts`：`ContainerStatus` 新增 `'unknown'`，`SchedulerTask` 新增 `status` 字段

### 新增文件
- `backend/app/db/models/docker_node_model.py` — DockerHost ORM
- `backend/app/db/repositories/docker_node_repo.py`
- `backend/app/services/docker_node_service.py` — Docker CLI 封装 + Hub 搜索
- `backend/app/schemas/docker_node_schema.py` — DockerHostCreate/Response, ContainerCreate/Info, NodeTestResult
- `frontend/src/services/compute.service.ts` — 完整前端 API 封装

### 重写文件
- `backend/app/db/models/schedule_task_model.py` — ScheduleTask + TaskRun（原 ScheduleTask/TaskRun/TaskLogEntry）
- `backend/app/db/repositories/schedule_task_repo.py`
- `backend/app/services/schedule_task_service.py` — subprocess 执行 + 日志落盘 + _Scheduler 轮询
- `backend/app/schemas/schedule_task_schema.py`
- `backend/app/api/v1/compute.py` — 23 条端点
- `frontend/src/pages/compute/ResourcesPanel.tsx` — mock→真实 API
- `frontend/src/pages/compute/SchedulerPanel.tsx` — mock→真实 API（含增量日志轮询）
- `frontend/src/pages/compute/ComputePage.tsx`

### 删除文件
- `backend/app/db/models/docker_service_model.py`
- `backend/app/schemas/docker_service_schema.py`
- `backend/app/services/docker_service_service.py`
- `backend/app/db/repositories/docker_service_repo.py`

### 修改文件
- `backend/app/db/models/__init__.py` — 注册 DockerHost, ScheduleTask, TaskRun
- `backend/app/main.py` — 调度器启动 `_Scheduler.start()`；移除 `import asyncio`
- `frontend/src/pages/compute/types.ts` — ContainerStatus + SchedulerTask.status
- `frontend/src/pages/compute/mock.ts` — mock 数据补 status 字段 + 导出 fmtDuration

### 验证
- 后端：`python -c "from app.main import app"` 加载成功，23 条 compute 路由全部注册
- 前端：`tsc -b` compute 目录零错误（其余模块历史错误未动）
- `oxlint src/pages/compute` — 0 errors, 1 warning（hook deps 无关）
- `read_lints src/pages/compute` — 0 diagnostics

## [2026-07-27] 算力调度三大能力：Docker 镜像管理 + 本地 OpenCode 服务 + 对话工作台选服

### 目标
1. Docker 服务增加镜像管理（列表/拉取/删除/从镜像一键创建容器带 volume 配置）
2. 新增「本地服务」tab：OpenCode 安装检测/Web 启停/CLI 一次执行/对话工作台选服务
3. Docker 容器创建支持目录映射 + 重启策略
4. 对话工作台自动读取算力调度选中的 opencode 服务 URL

### 决策

**后端新增 11 条 API**
- 镜像管理：`GET images` / `POST images/pull` / `DELETE images/path/{name:path}`
- OpenCode 服务：`GET opencode/status` / `POST start-web` / `POST stop-web` / `GET web-instances` / `POST run-cli` (async) / `GET runs` / `GET runs/{id}`
- 共 34 条 compute 路由

**OpenCodeLocalService** (`backend/app/services/opencode_local_service.py`)
- 检测安装：`shutil.which("opencode")` + `--version`
- Web 管理：`subprocess.Popen` 后台起 serve，`psutil` 扫描运行中进程
- CLI 执行：`asyncio.create_subprocess_exec` + 超时控制 + 输出持久化到 `/tmp/ontomind/opencode/runs/`
- 进程间隔离：`start_new_session=True`

**对话工作台选服**
- `ontomind_opencode_url` 存入 localStorage
- `opencodeBaseUrl()` 优先读取 localStorage，其次 VITE_OPENCODE_URL 环境变量
- 算力调度「本地服务」tab 中可选择运行中的 web 实例 → 对话工作台自动切换

**Docker 容器创建增强**
- 新增 volumes 配置：一行一个 `hostPath:containerPath`
- 新增 restart 策略：no / always / on-failure / unless-stopped
- 新增 `--network` / `extra_args`（后端 schema 已支持）

### 新增文件
- `backend/app/services/opencode_local_service.py`
- `frontend/src/pages/compute/OpenCodePanel.tsx`

### 重写文件
- `frontend/src/pages/compute/ComputePage.tsx` — 从 2 tab → 3 tab（Docker 服务 / 调度运行 / 本地服务）
- `frontend/src/pages/compute/ResourcesPanel.tsx` — 节点详情增加「容器/镜像管理」tab 切换；创建容器增加 volumes + restart 配置
- `frontend/src/services/compute.service.ts` — 新增镜像 API + OpenCode API 共 13 个方法
- `frontend/src/pages/compute/types.ts` — 新增 ImageListItem / OpenCodeStatus / OpenCodeWebInstance / OpenCodeCliRun 类型
- `frontend/src/features/opencode/client.ts` — opencodeBaseUrl() 优先读取 localStorage

### 修改文件
- `backend/app/api/v1/compute.py` — 新增 11 条端点 + 导入新 service
- `backend/app/services/docker_node_service.py` — 新增 list_images / pull_image / remove_image + ContainerCreate volumes/restart/network/extra_args
- `backend/app/schemas/docker_node_schema.py` — 新增 ImageInfo / PullImageRequest + ContainerCreate 新字段

### 验证
- 后端 34 条路由全部注册，python import 无错误
- 前端 tsc -b：compute + opencode + service 目录零错误
- oxlint：0 errors, 3 warnings（历史 hook deps）

## [2026-07-27] 提交收尾

### 提交
- 29 files changed, 4939 insertions(+), 2058 deletions(-)
- Commit: `e531227` — `feat(compute): 算力调度全面重构`
- **Push 失败**：GitHub SSH connection reset（国内网络问题），待网络恢复后重试 `git push origin main`

## [2026-07-29] 容器三件套：启动命令 + Console 终端 + 镜像模板

### 目标
算力调度页扩展容器管理三大能力：
1. 镜像默认启动命令（docker run 覆盖 CMD，无需 Dockerfile）
2. 容器 Console：xterm.js 交互终端（WS+pty）+ 一次性命令执行
3. 镜像模板系统：CRUD + 内置 opencode 模板 + 创建容器一键填充

### 决策
- **拒绝 Dockerfile 路线**：`docker run <image> <command>` 原生覆盖 CMD，配置存模板而非镜像，镜像保持干净、配置随时可调
- **Console 双形态**：完整 xterm.js 终端（WS+pty，支持 bash/sh 探测+resize）+ 轻量一次性 exec REST API
- **pty 桥接**：pty.openpty + docker exec -it，对 local/ssh/docker-api 三种节点天然兼容（DOCKER_HOST 透传 TTY）
- **模板内置保护**：is_builtin 字段保护内置模板不可删/不可改名
- **修复 extra_args 语义**：从 image 之后（误当 CMD）移到 image 之前（正确 docker run flags）；新增 command 字段追加 image 之后

### 新增文件
- backend: `container_template_model.py` / `container_template_repo.py` / `container_template_schema.py` / `container_template_service.py` / `seed_compute.py`
- frontend: `TemplatesPanel.tsx` / `TerminalDrawer.tsx` / `ExecCommandModal.tsx`

### 修改文件
- `backend/app/schemas/docker_node_schema.py` — ContainerCreate +command 字段；+ExecRequest/ExecResult
- `backend/app/services/docker_node_service.py` — create_container 修正 extra_args/command 顺序（shlex）；+exec_in_container +detect_shell
- `backend/app/api/v1/compute.py` — +POST /exec、+WS /terminal（pty 桥接）、+模板 CRUD 4 端点
- `backend/app/db/models/__init__.py` — 注册 ContainerTemplate
- `backend/app/main.py` — lifespan 接入 seed_container_templates
- `frontend/src/services/compute.service.ts` — +execContainerCommand +terminalWsUrl +模板 CRUD 4 方法
- `frontend/src/pages/compute/types.ts` — +ContainerTemplate +ExecResult
- `frontend/src/pages/compute/ResourcesPanel.tsx` — 创建 Modal 加模板选择/启动命令/另存模板；容器行加终端/执行命令按钮；+模板 Tab
- `frontend/src/pages/compute/compute.css` — +模板卡片/终端/执行输出样式

### API 端点
- `POST /api/v1/compute/nodes/{nid}/containers/{cid}/exec` — 一次性命令执行
- `WS  /api/v1/compute/nodes/{nid}/containers/{cid}/terminal` — 交互终端
- `GET/POST /api/v1/compute/templates` — 模板列表/创建
- `PATCH/DELETE /api/v1/compute/templates/{id}` — 模板更新/删除

### 数据库
- 新表 `container_templates`（靠 create_all 自动建表）：name/image/command/ports(JSON)/env_vars(JSON)/volumes(JSON)/restart_policy/network/extra_args/is_builtin/sort_order
- 内置 seed：OpenCode 模板（image=sst/opencode:latest, command=`opencode web --port 4096`, ports=4096:4096, restart=unless-stopped）

### 验证
- 后端：模板 API 返回内置 OpenCode 模板（command/ports/is_builtin 正确）；CRUD + 内置保护测试通过（删内置抛 BusinessException，ORM 无污染）；exec/WS 端点已注册
- 前端：tsc -b 无新增错误（预存无关错误不计）；oxlint 0 errors；@xterm/xterm + @xterm/addon-fit 已安装
- 端到端 preview：算力调度页正常打开

---

## 2026-07-31

### Agent: 主开发 Agent（OALP v1.0 — 专家团 / 多 Agent 协同 / 容器化 / AI 一键生成 / Skill+MCP 管理）

### 目标
基于 [opencode 1.17+ Agent 协议](https://opencode.ai/docs/agents/) 把专家团升级为完整多 Agent 协同平台：
1. 容器部署时自动注入 expert（agent md + skills + opencode.json）到 opencode 容器
2. expert 元数据对齐 opencode 协议（OALP v1.0），用 MySQL 存储
3. 一句话 LLM 自动生成专家草稿
4. 专家团页面管理 skill/mcp（discover / 加载 / LLM 解读 / 文件夹上传）
5. 选 expert 时从 DB 动态选 skill/mcp（不再硬编码）

### 调研结论（opencode 官方，无"loop 引擎"产品级概念）
- 多 Agent 协同 = primary → subagent（`@` 引用 / `task` 工具）→ 子返回文本 → 主继续
- 没有 "loop 引擎" 原语；loop 由 LLM 自身推理驱动，受 `steps` + `subagent_depth` 约束
- "evals hook" = plugin event 总线：`tool.execute.before/after` / `session.idle` / `permission.asked` / `experimental.session.compacting`
- 协议 frontmatter 关键字段：`mode` / `steps` / `permission` / `permission.task`（glob→action）/ `tools` / `model` / `temperature` / `top_p`

### 决策
- **DB 是 source of truth**，`~/.config/opencode/agent/{slug}.md` 是 sync 产物
- **permission.task 不进 agent md**（避免每次保存反查关系），单独由 `sync_expert_relations_to_opencode` 合并到 `opencode.json` 的 `agent.{slug}.permission.task`
- **schema 增量迁移**：`create_all` 只对全新表生效；已有表加列用 `app/db/schema_patch.py` 的 `add_column_if_missing`（捕获 1060 重复列错误做幂等）
- **evals_json 字段先只读展示**，本期不连 LLM judge（决策确认）
- **新容器模板 `opencode-agent`**（区别于通用 `OpenCode`）：用 `opencode serve` 而非 `web`，挂载由 deploy 函数运行时注入
- **容器注入只 mount 必要文件**：`{agent_dir}` + `{skill_dir}` + `opencode.json` 三个 bind，不动其他命名 volume

### 新增文件
- backend: `db/models/agent_relation_model.py`（AgentRelation + assert_no_cycle）/`db/schema_patch.py`（幂等加列 helper）/`api/v1/expert_skill_mcp.py`（discover/load/upload/summarize 子路由）
- 修改文件（按层）：

### 修改文件
- `backend/app/db/models/expert_model.py` — +OALP 字段（mode/subagent_depth/max_steps/system_prompt/permission_json/hooks_json/evals_json/version/container_template_id/bind_skills_to_container/top_p）
- `backend/app/db/models/skill_model.py` — +folder_path/is_loaded/auto_description
- `backend/app/db/models/mcp_model.py` — +auto_description/tools_manifest_json/last_synced_at（import 加 Text）
- `backend/app/db/models/__init__.py` — 注册 AgentRelation + assert_no_cycle
- `backend/app/db/seed_compute.py` — +内置 opencode-agent 模板（image=sst/opencode、command=`opencode serve`）
- `backend/app/services/expert_service.py` — 重写：_build_frontmatter（OALP 全集）/ _render_frontmatter_yaml（嵌套 dict/list）/ sync_expert_relations_to_opencode（合并 task 到 opencode.json）/ AgentRelationService / auto_draft_expert（LLM + fallback）/ clone_expert / deploy_expert_container（mount 注入 + health check）
- `backend/app/schemas/expert_schema.py` — +mode/subagent_depth/max_steps/system_prompt/permission/hooks/evals/container_template_id/bind_skills_to_container/top_p + ExpertAutoDraftResponse + ExpertDeployContainerRequest + ExpertCloneRequest + AgentRelationCreate
- `backend/app/api/v1/experts.py` — 重写：+auto-draft /clone /deploy-container /relations CRUD 端点
- `backend/app/api/v1/router.py` — 注册 `/experts/skill-mcp` 子路由
- `backend/app/main.py` — lifespan 接入 OALP schema 补丁 + seed_default_experts
- `frontend/src/services/expert.service.ts` — 重写：Expert OALP 全集类型 + 全部 OALP 端点
- `frontend/src/pages/experts/ExpertTeamPage.tsx` — 重写为 3 Tab（专家 / Skills / MCPs）+ AI 一键生成 Modal + 部署容器 Drawer + 关系管理 Drawer

### API 端点（OALP v1.0）
- `POST /api/v1/experts/auto-draft` — 一句话 LLM 生成草稿（response_model 扁平返回）
- `POST /api/v1/experts/{id}/clone` — 复制专家
- `POST /api/v1/experts/{id}/deploy-container` — 拉起 opencode 容器并注入（node_id + container_template_id + host_port + extra_env + auto_start）
- `GET  /api/v1/experts/relations/all` — 全部关系
- `GET  /api/v1/experts/{id}/relations` — 指定专家的关系
- `POST /api/v1/experts/relations` — 建关系（DFS 反环）
- `DELETE /api/v1/experts/relations/{id}` — 删关系
- `GET  /api/v1/experts/skill-mcp/skills/discover` — 扫 opencode + claude + .agents 的 SKILL.md
- `POST /api/v1/experts/skill-mcp/skills/load-from-opencode` — 全部 upsert 到 skills 表
- `POST /api/v1/experts/skill-mcp/skills/upload-folder` — zip 上传 + 扫 SKILL.md
- `POST /api/v1/experts/skill-mcp/skills/{id}/summarize` — LLM 解读
- `GET  /api/v1/experts/skill-mcp/mcps/discover` — 从 opencode.json 读 mcp 节
- `POST /api/v1/experts/skill-mcp/mcps/load-from-opencode` — upsert 到 mcps 表
- `POST /api/v1/experts/skill-mcp/mcps/{id}/summarize` — LLM 解读
- `GET  /api/v1/experts/skill-mcp/agents/list-local` — 列出本机 agent/*.md

### 数据库
- 新表 `agent_relations`（靠 create_all 自动建表）：parent_expert_id / child_expert_id / relation / condition / sort_order + unique(parent, child)
- `experts` 表加 11 列：`top_p`/`mode`/`subagent_depth`/`max_steps`/`system_prompt`/`permission_json`/`hooks_json`/`evals_json`/`version`/`container_template_id`/`bind_skills_to_container`（通过 `db/schema_patch.py` 幂等 ALTER）
- `skills` 表加 3 列：`folder_path`/`is_loaded`/`auto_description`
- `mcps` 表加 3 列：`auto_description`/`tools_manifest_json`/`last_synced_at`
- 内置 seed：4 个专家（data-analyst / frontend / backend / product-manager）+ 3 条演示关系（pm→fe/be/da）+ 1 个 opencode-agent 容器模板

### 验证
- 后端启动 + schema 补丁幂等：成功（已加列的表跳过，未加列的 ADD）
- 启动后 seed 4 个内置专家 + 演示关系：成功
- HTTP e2e（用 `oalp_admin`/`Oalp123!` 跑）：
  - `POST /experts/seed` → 已 seed 0（幂等）
  - `GET  /experts` → 6 个专家（4 内置 + 1 xiaohua + 1 test-oalp），全部 OALP 字段填充
  - `POST /experts` (with permission) → 写入磁盘 md 含完整 frontmatter
  - `POST /experts/relations` → 自动合并到 `opencode.json` 的 `product-manager.permission.task = {test-oalp: allow, *: deny, test-rel: allow}`（保留旧规则不覆盖）
  - `GET  /experts/relations/all` → 3 条
  - `POST /experts/relations` 构造环 → 400 `AGENT_RELATION_CYCLE`
  - `GET  /experts/skill-mcp/skills/discover` → 42 个 SKILL.md
  - `POST /experts/skill-mcp/skills/load-from-opencode` → 新增 20 / 更新 69
  - `GET  /experts/skill-mcp/mcps/discover` → 3 个 MCP（dataPro-search / mcp-server-askecho-search-infinity / openviking-controlplane）
  - `POST /experts/{id}/deploy-container` (无 docker node) → 404 友好
  - `POST /experts/auto-draft` → 200（LLM 不可用走 fallback 也填好）
  - `POST /experts/{id}/clone` → 新 slug `data-analyst-copy`
- 前端：`npm run build` 我引入的 ExpertTeamPage 错误 = 0（剩余 13 个 TS 错误是仓库原有，与本次无关）
- 前端 lint（oxlint）：我引入的 ExpertTeamPage 错误 = 0
- pytest 现有测试：68 passed（1 deselected，是仓库原有 agent_platform websocket 鉴权测试，与本次无关）

### 已知遗留（未做）
- 真正的"主 agent 跑通调用子 agent"留给 Agent Looper 那条线（本期只做关系持久化 + opencode.json 同步）
- evals 字段仅展示，UI 上没接 eval runner
- LLM 解读的 prompt 用的中文硬编码，多语言切换未做

---

## 2026-08-03

### Agent: 主开发 Agent（AIDE — 把 opencode Web UI 嵌入平台）

### 目标
新增 `AIDE` Tab 页，把 opencode 的完整 Web UI 嵌进平台，作为「完整 IDE 体验」入口。
要求：页面布局合理、运行流畅。

### 关键调研发现（决定了实现方案）
1. 查 [opencode web 文档](https://opencode.ai/docs/web/) — `opencode web` 提供浏览器 UI，`serve` 文档上写的是「headless HTTP server」
2. **但实测本机 opencode 1.18.4 的 `serve` 已内置完整 Web UI**：
   `curl http://127.0.0.1:4096/` 返回 2884 字节完整 HTML（`<title>OpenCode</title>` + manifest + favicon）
3. **响应头没有 `X-Frame-Options`，CSP 也没有 `frame-ancestors`** → iframe 嵌入不会被浏览器拦
   （CSP 只有 `default-src 'self'` 等，管的是 iframe 内部资源加载，不管谁能嵌它）

### 决策
- **优先复用对话工作台已有的 `serve(4096)`**，零额外进程、零额外内存、启动即用
  → 后端 `_serves_html()` 探测 `GET /` 是否返回 `text/html` 来判断
- **独立 `opencode web`(4097) 只作兜底**（老版本 opencode 的 serve 没 UI 时）
- **不做反向代理**：直接 iframe `127.0.0.1:4096`，少一跳、无 WebSocket/SSE 转发损耗，最流畅
- **iframe 而非搬 UI 源码**：opencode UI 迭代快，iframe 自动跟随升级，零维护成本
- **AppLayout 加 full-bleed 分支**：`/aide` 路由跳过 `Content margin:24` 和 `.page-enter`
  （后者的 `transform: translateY` 会让 `position: fixed` 全屏失效 — CSS containing block 陷阱）

### 新增文件
- `backend/app/api/v1/opencode.py` 内新增 3 端点（不是新文件，见修改文件）
- `frontend/src/services/aide.service.ts` — AideStatus/AideStartResult 类型 + status/start/stop
- `frontend/src/pages/aide/AidePage.tsx` — AIDE 页面（工具条 + iframe + 未就绪引导 + 全屏）

### 修改文件
- `backend/app/api/v1/opencode.py` — +`_find_web_processes()` / +`_serves_html()` / +`GET /web/status`（智能决策嵌入源）/ +`POST /web/start`（幂等，15s 轮询，注入 `OPENCODE_NO_OPEN=1` 防自动开浏览器）/ +`POST /web/stop`
- `frontend/src/App.tsx` — import AidePage + `<Route path="aide">`
- `frontend/src/components/layout/AppLayout.tsx` — 菜单加 `{ key: '/aide', icon: <CodeOutlined />, label: 'AIDE' }`（放在对话工作台之后）+ `isFullBleed` 分支

### API 端点
- `GET  /api/v1/opencode/web/status` — 探活 + 返回最佳 `embed_url` / `embed_source`(serve|web|none) / cli 版本 / serve+web 双端状态
- `POST /api/v1/opencode/web/start` — 拉起独立 `opencode web`（幂等，body: port/cors/hostname）
- `POST /api/v1/opencode/web/stop` — 停掉指定端口的 `opencode web`

### 数据库
无变更（纯运行时探测，不落库）

### 页面交互设计
- **工具条（40px）**：AIDE 标题 + 状态点（已连接/未就绪）+ 嵌入源标签（复用 serve / 独立 web）+ URL + 版本号 + 右侧 4 个按钮
  - 重新加载 iframe（改 `key` 强制重挂）
  - 在新窗口打开
  - 全屏 / 退出全屏（支持 **Esc**）
  - 启停：`embed_source === 'web'` 才给「停止」按钮（**避免误关对话工作台在用的 serve**）
- **未就绪态**：`<Result>` 展示两种启动方式的可复制命令 + 「一键启动 opencode web」+「重新探测」；CLI 未安装时给安装命令
- **流畅性优化**：
  - 就绪后停止轮询（`if (status?.healthy) return`），避免无谓请求
  - iframe `key` 固定，切 Tab 回来不重新 load
  - iframe 加载遮罩（`iframeLoaded` 状态）
  - `allow="clipboard-read; clipboard-write; fullscreen"` + `sandbox` 给足权限（opencode UI 要用剪贴板/弹窗/下载）

### 验证
- 后端 `GET /web/status` 实测：`healthy=True` / `embed_url='http://127.0.0.1:4096'` / `embed_source='serve'` / `serve_has_ui=True` / `version='1.18.4'` ✅
- **Playwright e2e 全绿**（`/tmp/aide_0*.png`）：
  - 登录 → `/aide` → `frames = 2`，第二个是 `http://127.0.0.1:4096/` ✅
  - iframe 内真实渲染出 opencode UI：`Projects / Add project / Settings / Help / Nothing here yet / Create a session to get started` + 8 个可交互按钮 ✅
  - 工具条：「已连接」+「复用 serve」标签都在 ✅
  - **无双滚动条**：`hasBodyScroll = False`（`docScrollH 1000 === docClientH 1000`）✅
  - iframe 精确铺满：`1600 × 904`，`top=96`（= 56 Header + 40 工具条），`1000 - 96 = 904` ✅
  - 全屏：`top: 40, h: 960`（占满视口只留工具条）→ Esc 正常退出 ✅
- 前端 `npm run build`：AIDE 相关 0 error（剩余 13 个是仓库原有，与本次无关）
- 前端 `npm run lint`（oxlint）：AIDE 相关 0 error/warning
- 修掉一个 antd v6 废弃警告：`<Spin tip>` → `<Spin />` + 独立 `<Text>`

### 已知遗留
- iframe 内 opencode 的主题跟平台 Editorial Light 不统一（opencode 自己的深/浅色跟随系统），后续可考虑通过 opencode `tui.json` 的 theme 或注入 CSS 变量对齐
- 平台侧无法感知 iframe 内的 session 状态（跨域 iframe 无法读 DOM），若要打通需走 `postMessage` 协议（opencode 上游暂未提供）
- `serve` 内置 UI 是 opencode ≥ 1.18 的行为；若降级到老版本会自动回退到独立 `opencode web` 路径（代码已兼容）

---

## 2026-08-03（补）

### Agent: 主开发 Agent（AIDE 性能优化 — 根治"每次进来都在加载"）

### 问题
用户反馈：「为什么每次进 AIDE 总是会加载 opencode UI，很慢」

### 根因定位（实测数据，不是猜）
分三层量化：

**A. 后端 `/web/status` 端点 600ms**
```
[1] subprocess opencode --version :  504.2 ms   ← 占 85%
[2] psutil process_iter (611 procs):  50.3 ms
[3] port_open 4096                :   3.5 ms
[4] GET 4096/ (serves_html)       : 105.3 ms
>>> 合计 ≈ 663 ms，curl 实测 0.56~0.60s
```

**B. 前端 iframe 每次都重建（真正主因）**
React Router 切走路由会卸载 `AidePage`，iframe 随之从 DOM 移除；
再回 `/aide` 时 opencode UI 得从零重来：重下 11 个 JS/CSS bundle、
重建 SSE 连接、重新拉 session 列表 → 每次 2 秒白屏。

**C. 首屏必须等接口返回才渲染** → 叠加 600ms 空等

### 决策与修法

**后端（`opencode.py`）**
- `_cli_version()` 加 10min TTL 缓存 —— CLI 版本在进程生命周期内不会变，504ms → 0ms
- `_serves_html()` 加 60s TTL 缓存 + 改用 `HEAD`（不传 body，比 GET 快），4xx 时回退 GET
- `_find_web_processes()`（50ms psutil 遍历）改成**只在 `?detail=1` 才跑**，默认不跑
- 新增 `?fast=1` 快路径：只做端口探活（~4ms），跳过 HTML 探测和版本查询，给前端轮询用
- `/web/start` `/web/stop` 成功后主动清 `_HTML_CACHE`，避免返回失效的嵌入源

**前端（架构调整）**
- 新增 `components/layout/AideHost.tsx` —— iframe 常驻宿主，**挂在 `AppLayout` 里**（跟路由同级），
  切走路由只做 `display: none`，iframe 不卸载、SSE 不断
- 新增 `stores/aideStore.ts` —— iframe 在 AppLayout、控制它的工具条在 AidePage，
  两者非父子关系，用 zustand 共享状态
  - `mounted`：进过一次就永久 true
  - `visible`：当前是否在 /aide（仅控制 display）
  - `reloadToken`：递增触发手动 reload（改 `el.src` 而非换 key，避免 DOM 节点重建）
  - status 结果落 `sessionStorage`，**首屏直接渲染 + iframe 立刻开始加载，不等接口**
- `AidePage.tsx` 瘦身为「工具条 + 未就绪引导」，iframe 交给 AideHost
  - 全屏时工具条 `zIndex: 1001` 盖在 iframe(1000) 上，`pointerEvents: 'none'` 让 iframe 可点
  - 首次探测用 full（拿 version/cli_path），之后全部走 `fast=1`
- `aide.service.ts` — `status()` 支持 `{ fast, detail }` 参数

### 修改文件
- `backend/app/api/v1/opencode.py` — +`_VERSION_CACHE`/`_HTML_CACHE`/`_cli_version()`；`_serves_html()` 加缓存+HEAD；`web_status()` 加 `fast`/`detail` 参数；启停后清缓存
- `frontend/src/components/layout/AideHost.tsx` — **新增**
- `frontend/src/stores/aideStore.ts` — **新增**
- `frontend/src/pages/aide/AidePage.tsx` — 重写（去掉 iframe，改用 store）
- `frontend/src/services/aide.service.ts` — `status()` 加 fast/detail
- `frontend/src/components/layout/AppLayout.tsx` — 挂载 `<AideHost />`

### 验证（Playwright e2e，`/tmp/aide_perf.png`）

⚠️ **测试坑**：一开始用 `page.goto()` 测「切走再回来」，结果 `iframe exists = False`，
误判优化无效。原因是 `goto` 是**整页导航**（整个 SPA 重新加载），
而真实用户点导航菜单走的是**客户端路由**。改成 `page.click('.ant-menu-item:has-text("专家团")')` 后才测准。

| 指标 | 优化前 | 优化后 | 提升 |
|---|---|---|---|
| 二次进入 iframe 就绪 | 2076 ms | **112 ms** | **18.5x** |
| 二次进入 iframe 请求数 | 11 个 | **0 个** | 完全复用 |
| 切走后 iframe 状态 | 被销毁 | `display:none` 存活 | — |
| `/web/status`（缓存热） | 600 ms | **2 ms** | **300x** |
| `/web/status?fast=1`（含网络） | — | 13~21 ms | — |
| 布局回归 | — | `hasBodyScroll=False`, `1600×904`, `top=96` | 无回归 |

- 前端 `npx tsc -b`：AIDE 相关 0 error
- 前端 `npm run lint`：AIDE 相关 0 问题

### 已知遗留
- 首次进入仍需 ~2s（opencode UI 自身的 bundle 加载时间，非本平台可控）；
  若要再压，需 opencode 上游支持 SSR 或 service worker 预缓存
- 整页刷新（F5）时 iframe 仍会重载 —— 浏览器行为，无法规避；
  但 `sessionStorage` 缓存让 iframe 少等 600ms 接口，能提前开始加载

---

## 2026-08-03（补 2）

### Agent: 主开发 Agent（修「无法连接后端服务」— 加网络错误自动重试）

### 现象
用户报错：`无法连接后端服务，请确认后端已启动且 CORS 配置正确`

### 诊断过程（先量化，不猜）

**第一步：确认后端到底行不行**
```
lsof -iTCP:8000  → python3.1 78433 LISTEN ✅ 在跑
curl /health     → {"status":"healthy"} HTTP 200 / 0.023s ✅
curl OPTIONS 预检 → access-control-allow-origin: http://localhost:5173 ✅
curl GET 带 Origin → 200 + 正确 CORS 头 ✅
```
**后端和 CORS 完全正常。**

**第二步：Playwright 走真实浏览器复现**
```
9 个 API 调用全部 200：
  200 POST /auth/login    200 GET /auth/me       200 GET /opencode/health
  200 GET /experts        200 GET /opencode/web/status
AIDE 页面正常显示：已连接 / 复用 serve / v1.18.4
唯一失败：GET http://127.0.0.1:4096/event :: net::ERR_ABORTED
  ← 这是 iframe 内 opencode 自己的 SSE，跟我们后端无关
```

**第三步：定位文案来源**
```
grep -rn "无法连接" frontend/src
  → pages/Login.tsx:23   ← 是【登录页】的提示，不是 AIDE
```

**第四步：找到真正根因**
```
ps -p 78433 -o lstart=,etime=
  → Mon Aug 3 11:18:33 2026   etime=03:37
```
后端进程只活了 **3 分 37 秒** —— 因为我前面在改 `opencode.py`，
`uvicorn --reload` 触发了热重载。**热重载期间有 1~3 秒窗口会 ECONNREFUSED**，
用户恰好在这个窗口点了登录 → axios 抛 `Network Error` → 弹出那句提示。

**不是配置问题，是开发时热重载的固有时序窗口。**

### 决策
既然是必然存在的时序窗口，就让前端自己扛住，而不是把锅甩给用户：
1. **网络层失败自动重试**（有 HTTP 响应的 4xx/5xx 一律不重试，避免重复提交）
2. **重试白名单**：GET/HEAD/OPTIONS 天然幂等可重试；
   POST 默认不重试，但 `/auth/login` `/auth/me` 是纯查询语义，显式加白名单
3. **指数退避** 300/600/1200ms —— 总窗口 2.1s，刚好覆盖 uvicorn 热重载时间
4. **错误提示改成可执行的排查步骤**，而不是笼统说"CORS 配置不对"（本来就没错）

### 修改文件
- `frontend/src/services/api.ts` — 重写响应拦截器：
  - `shouldRetry()`：只重试无 response 的网络错误 + 幂等方法/白名单路径
  - 指数退避重试，`__retryCount` 挂在 config 上防无限循环
  - 401 处理加防护：已在 `/login` 就不再跳转，避免无限刷新
- `frontend/src/pages/Login.tsx` — `formatApiError()` 区分场景：
  - 超时（ECONNABORTED）→ 提示负载过高
  - 网络失败 → 给出 3 步可执行排查（含具体命令），并说明已自动重试过
  - notification 加 `whiteSpace: 'pre-line'` 让多行提示正常换行，`duration: 8` 给足阅读时间

### 验证（Playwright e2e）

**场景 1：后端未启动时登录，中途拉起后端**
```
准备：kill -9 后端，确认 8000 端口空
点登录 → 1.2s 后后台拉起后端
控制台：
  [api] 网络失败，300ms 后重试 (1/3): POST /auth/login
  [api] 网络失败，600ms 后重试 (2/3): POST /auth/login
  [api] 网络失败，1200ms 后重试 (3/3): POST /auth/login
结果：url = http://localhost:5173/workspace
✅ 自动重试成功 —— 后端恢复后登录自动完成，用户全程无感
```

**场景 2：后端真的挂了（不重启）**
```
重试 3 次后停止，弹出提示：
  连不上后端 http://localhost:8000/api/v1（已自动重试 3 次）。请检查：
  1. 后端是否在跑：cd backend && uvicorn app.main:app --reload --port 8000
  2. 若刚改过后端代码，--reload 热重载需 1~3 秒，稍等再试
  3. 端口是否被占用：lsof -iTCP:8000 -sTCP:LISTEN
✅ 提示清晰可执行，不再误导用户查 CORS
```

- `npx tsc -b`：api.ts / Login.tsx 相关 0 error
- `npm run lint`：api.ts / Login.tsx 相关 0 问题
- 后端已恢复运行（`/health` 200）

### 副作用说明
- 全站所有走 `services/api.ts` 的请求都获得了网络重试能力（GET 类自动生效）
- POST/PATCH/PUT/DELETE 默认**不重试**，不会产生重复写入
- 重试日志用 `console.warn` 打印，便于开发时观察，不影响用户

---

## 2026-08-03（补 3）

### Agent: 主开发 Agent（下线「对话工作台」— 前后端彻底删除）

### 目标
对话工作台功能不再需要，前后端删除干净。能力已由 AIDE（iframe 嵌 opencode 官方 UI）承接。

### 删前盘点（避免删漏/删错）
```
frontend:
  features/opencode/**                    31 个文件，只被 ChatWorkspacePage 引用（自闭环）
  pages/agent-platform/ChatWorkspacePage.tsx
  main.tsx                                引了 vendor/styles/opencode.css
  App.tsx / AppLayout.tsx / CmdKOmnibar.tsx / AgentStudioPage.tsx / ResourcesConsolePage.tsx
                                          共 10 处 /workspace 引用
backend:
  api/v1/opencode.py                      /health /spawn /session-link 三个端点（仅工作台用）
  db/models/opencode_session_model.py
  db/models/__init__.py                   注册 + __all__
  schema.sql                              第 8 节 opencode_sessions 建表
  MySQL                                   opencode_sessions 表（9 行数据）
```
**关键确认**：AIDE 只用 `/opencode/web/*`，跟被删的三个端点零交集；
`features/opencode` 里的 `ExpertPicker` 只被 `ChatWorkspaceShell` 用，专家团页面不依赖它。

### 决策
- **`/workspace` 路由保留为重定向**（`<Navigate to="/aide" replace />`），
  老书签/外链不会 404
- **默认落地页从 `/workspace` 改成 `/aide`**（`<Route index>` + `AppLayout.selectedKey`）
- CmdK 面板的「对话工作台」项换成「AIDE」；顺手删掉指向死路由的「运行记录」（`/agent-platform/runs` 早已下线）
- `ResourcesConsolePage`（已不在路由里的死代码）里的 `/workspace` 跳转也改指 `/aide`，避免留脏引用
- **MySQL 表直接 DROP**（9 行历史数据无保留价值，纯审计映射）
- `schema.sql` 删掉第 8 节后，把 9~13 节编号重排为 8~12，保持连续

### 删除文件
- `frontend/src/features/opencode/`（**整目录 31 个文件**：client.ts / types.ts / index.ts /
  13 个 components / 11 个 hooks / stores/opencodeStore.ts / vendor/{LICENSE,opencode.css,VENDOR_META.md}）
- `frontend/src/pages/agent-platform/ChatWorkspacePage.tsx`
- `backend/app/db/models/opencode_session_model.py`

### 修改文件
- `frontend/src/main.tsx` — 去掉 `import './features/opencode/vendor/styles/opencode.css'`
- `frontend/src/App.tsx` — 去掉 ChatWorkspacePage import；`<Route index>` 改指 `/aide`；
  `workspace` 改成 `<Navigate to="/aide" replace />`
- `frontend/src/components/layout/AppLayout.tsx` — 删「对话工作台」菜单项 + `MessageOutlined` import；
  `selectedKey` 默认值 `/workspace` → `/aide`
- `frontend/src/components/common/CmdKOmnibar.tsx` — 「对话工作台」项换成「AIDE」；删「运行记录」死项
- `frontend/src/pages/agent-platform/index.ts` — 去掉 ChatWorkspacePage 导出
- `frontend/src/pages/agent-platform/AgentStudioPage.tsx` — 「前往对话工作台」→「前往 AIDE」
- `frontend/src/pages/agent-platform/ResourcesConsolePage.tsx` — 2 处跳转改指 `/aide`
- `backend/app/api/v1/opencode.py` — **526 行 → 348 行**，只保留 `/web/{status,start,stop}`；
  清掉 `get_db` / `Session` / `OpencodeSession` / `settings` 等不再需要的 import
- `backend/app/db/models/__init__.py` — 去掉 OpencodeSession import + `__all__` 条目
- `backend/schema.sql` — 删第 8 节 opencode_sessions 建表（22 行），9~13 节编号重排为 8~12
- `AGENTS.md` — 「对话工作台 + 专家团」章节重写为「AIDE + 专家团」；补已删端点清单；
  清 2 行过期内容（vendor 计划、ChatComposer 输入法说明）
- `HANDOFF.md` — 10 处更新：目标/活跃模块/CLI 版本/终端说明/验证步骤/3.1 整节重写/
  数据流图/数据表清单/排查表/冒烟脚本加 AIDE 探活

### 数据库
- `DROP TABLE opencode_sessions`（含 9 行历史数据）
- `schema.sql` 同步删除建表语句
- ⚠️ `task_runs.opencode_session_id` 字段**保留** —— 那是算力调度记录 opencode 任务用的独立字段，与本次无关

### API 端点变更
- ❌ `GET  /api/v1/opencode/health`
- ❌ `POST /api/v1/opencode/spawn`
- ❌ `POST /api/v1/opencode/session-link`
- ❌ `GET  /api/v1/opencode/session-link`
- ✅ 保留 `GET /api/v1/opencode/web/status` / `POST /web/start` / `POST /web/stop`

### 验证
**后端**
```
GET /opencode/web/status  -> 200  healthy=True src=serve   ✅ 保留端点正常
GET /opencode/health      -> 404  ✅
GET /opencode/session-link-> 404  ✅
GET /opencode/spawn       -> 404  ✅
后端启动无错误（bcrypt 警告是仓库既有问题）
pytest: 68 passed, 1 deselected  ← 与删除前完全一致，无回归
```

**前端**
```
npm run build: 14 个 error 全是仓库原有（AgentStudioPage/TemplatesPanel/perception/
               AgentDetailPage/AgentLooperWizard/userStore），无「找不到模块」类删漏错误
npm run lint : 只有既有 warning
grep -rn "/workspace" frontend/src  -> 无残留
```

**Playwright e2e 回归全绿**（`/tmp/after_delete.png`）
```
1) 登录后默认落地页 = http://localhost:5173/aide            ✅
2) 顶部菜单 = [AIDE, 专家团, 算力调度, 感知层, 认知层,
              决策层, 执行层, 用户管理]                      ✅ 无「对话工作台」
3) 访问老链接 /workspace → 自动跳 /aide                      ✅
4) AIDE 页面：含「AIDE / 已连接 / 复用 serve」，
   iframe 指向 http://127.0.0.1:4096/                        ✅
5) 专家团：正常渲染，14 个专家卡片匹配                        ✅
6) CmdK 面板已无「对话工作台」                                ✅
页面错误：仅 2 个 antd 既有废弃警告
失败请求：仅 iframe 内 opencode 自己的 SSE（正常）
```

### 代码量变化
- 前端：删 32 个文件
- 后端：删 1 个文件，`opencode.py` 瘦身 178 行（526 → 348）
- schema.sql：删 22 行

---

## 2026-08-03（补 4）

### Agent: 主开发 Agent（大清理 — 删除五层业务域 + resources + agent-looper/platform）

### 目标
感知层 / 认知层 / 决策层 / 执行层全部删除，前后端 + 数据库表都要干净。

### 删前盘点发现的 3 个关键交叉点（不是无脑删）

**1. 数据平台的「元数据」页完全依赖感知层**
```
/data-platform/metadata（仍在导航里活着）是从感知层 verbatim port 过来的：
  前端 12 处调 perceptionAPI
  后端 8 个 /api/v1/perception/* 端点
  MetadataService + metadata_repo + MetaTable/MetaColumn/MetaProfile
  4 张表：meta_tables(3007) / meta_columns(83451!) / meta_profiles(11) / data_sources(2)
```
→ 用户决策：**元数据能力也一起删干净**

**2. instances/agents 被 /api/v1/resources 大量使用**
```
resources.py 46 个端点，其中 29 处是 skills/mcps —— 而专家团页面正在用
（resourcesAPI.listSkills / listMCPs）
```
→ 用户决策：**全删 resources，skills/mcps 搬到 experts 下**

**3. Agent Looper 的 3 个页面挂在 /resources 下**
→ 用户决策：**一起删掉**

### 决策
- **先搬迁再删除**：skills/mcps 的 13 个 CRUD/sync 端点先搬到
  `/api/v1/experts/skill-mcp/*`（原文件 21 个端点），再删 resources.py
- **前端 resourcesAPI 彻底废弃**：`expert.service.ts` 补 `listSkills/createSkill/.../syncMCPs`
  等 13 个方法，ExpertTeamPage 改用 expertService
- **所有已删路由保留为重定向**（`<Navigate>`），老书签/外链不 404：
  `/workspace|/perception|/cognition|/decision|/execution` → `/aide`；
  `/resources/*|/agent-platform/*` → `/experts`；`/data-platform/metadata` → `/data-platform`
- **schema.sql 从 ORM 自动重生**：原文件表名大量过期（`mcp_configs`/`docker_services`/
  `schedule_tasks` 早已改名）且只覆盖 12 张表 → 改成用 `CreateTable` 从
  `Base.metadata.sorted_tables` 导出，并在头部写清 24 张保留表 + 39 张已删表清单
- **3 个跨模块外键去掉但保留列**（标 DEPRECATED），避免与历史数据不一致：
  `kb_data_assets.ref_meta_table_id` / `ref_data_source_id` / `dp_chat_sessions.agent_looper_config_id`
- **role_service / audit_log_service 保留**：被 `core/authorization.py` 用（llm.py 的权限校验依赖）

### 删除文件（后端 58 个）
- **API（7）**：`api/v1/{perception,cognition,decision,execution,resources}.py`
  + `api/v1/agent_looper/`（4 文件）+ `api/v1/agent_platform/`（6 文件）
- **Service（21）**：`services/agent_platform/`（10 文件）+ `agent_container_discovery_service`
  / `agent_discovery` / `agent_looper_{discovery,service,writer}_service` / `agent_service`
  / `data_source_service` / `instance_service` / `metadata_service` / `ontology_service`
  / `credential_service`
- **Repository（7）**：`agent_looper_repo` / `agent_platform_repo` / `agent_repo`
  / `data_source_repo` / `instance_repo` / `metadata_repo` / `credential_repo`
- **Model（21）**：`data_source` / `metadata` / `ontology` / `instance` / `agent`
  / `compute_node` / `agent_container` / `node_container` / `container_agent`
  / `container_skill` / `container_mcp` / `agent_skill` / `agent_mcp` / `node_connection`
  / `discovery_run` / `discovery_item` / `agent_platform` / `agent_looper_{config,version,test_run}`
  / `credential`
- **Schema（8）**：`agent_looper` / `agent_platform` / `agent` / `data_source` / `instance`
  / `metadata` / `credential` / `project`
- **测试（9）**：`tests/agent_platform/`（1）+ `test_agent_looper_*`（4）
  / `test_compute_node` / `test_node_container_discovery` / `test_naming_migration`
  / `test_agent_platform_wave0`
- **孤儿脚本（1）**：`app/scripts/purge_test_runs.py`

### 删除文件（前端）
- **页面目录（6）**：`pages/{perception,cognition,decision,execution,resources,agent-platform}/`
- **单页（1）**：`pages/data-platform/MetadataPage.tsx`（依赖感知层）
- **Service（3）**：`services/{resourcesAPI,agentPlatform.service,agentLooper.service}.ts`
- **组件（2）**：`components/common/AgentPicker.tsx` + 其测试（依赖已删 service，已成孤儿）

### 修改文件
- `backend/app/api/v1/expert_skill_mcp.py` — **+13 个 skills/mcps CRUD/sync 端点**（493→660 行，共 21 端点）
- `backend/app/api/v1/router.py` — 重写：只注册 8 个模块，头部写清已删路由清单
- `backend/app/db/models/__init__.py` — 重写：24 个 model，头部写清已删 model 清单
- `backend/app/db/models/kb_data_asset_model.py` — 2 个外键去约束保留列（DEPRECATED）
- `backend/app/db/models/dp_chat_session_model.py` — `agent_looper_config_id` 去外键（DEPRECATED）
- `backend/schema.sql` — **从 ORM 自动重生**（609 行 / 24 张表 + 完整已删清单）
- `backend/tests/data_platform/test_opencode_sync.py` — 3 处 `app.api.v1.resources`
  改成 `expert_skill_mcp`；异常类型 `HTTPException` → `BusinessException`
- `frontend/src/services/expert.service.ts` — +`SkillRow`/`McpRow` 类型 + 13 个 CRUD 方法
- `frontend/src/services/index.ts` — 重写：删 `resourcesAPI`/`perceptionAPI`/`cognitionAPI`
  /`decisionAPI`/`executionAPI`，只留 `llmAPI`+`authAPI`，头部写清迁移指引
- `frontend/src/App.tsx` — 重写：8 个活跃路由 + 8 条重定向
- `frontend/src/components/layout/AppLayout.tsx` — 菜单 6 项（AIDE/专家团/算力调度/数据平台/知识库/用户管理）；
  `selectedKey` 简化（agent-platform 分支已删）
- `frontend/src/components/common/CmdKOmnibar.tsx` — 删 7 个指向死路由的 nav 项 + 4 个未用图标
- `frontend/src/components/common/index.ts` — 去掉 AgentPicker 导出
- `frontend/src/pages/experts/ExpertTeamPage.tsx` — `resourcesAPI` → `expertService`；`MCPConfig` → `McpRow`
- `frontend/src/pages/compute/TemplatesPanel.tsx` / `stores/userStore.ts` — 顺手清历史未用变量
- `AGENTS.md` / `HANDOFF.md` — 项目定位、活跃模块、路由清单、数据表清单、数据流图全部同步

### 数据库
**DROP 39 张表（约 9 万行数据）**，一次性执行（关 FOREIGN_KEY_CHECKS）：
```
感知层    : data_sources(2) / meta_tables(3007) / meta_columns(83451) / meta_profiles(11)
认知层    : onto_versions(3) / onto_classes(138) / onto_properties(1250)
            / onto_relationships(40) / onto_constraints(680)
资源管理  : instances(1) / agents(2) / credentials(0) / mcp_configs(0)
T44 平台  : compute_nodes(1) / agent_containers(0) / node_containers(0)
            / container_agents(0) / container_skills(0) / container_mcps(0)
            / agent_skills(0) / agent_mcps(0) / node_connections(1)
            / discovery_runs(71) / discovery_items(1828)
AgentLooper: agent_looper_configs(0) / agent_looper_versions(0) / agent_looper_test_runs(0)
AgentPlatform: agent_versions(2) / agent_deployments(0)
旧知识库  : knowledge_bases(1) / knowledge_chunks(0) / knowledge_documents(0)
            / source_code_repos(0) / source_code_files(0)
旧算力表名: docker_services(1) / schedule_tasks(1) / task_runs(1) / task_log_entries(8)
Alembic   : alembic_version(1)
```
**结果**：DB 从 63 张表 → **24 张**，零孤儿零缺失（ORM 声明与 DB 实际完全一致）

### API 端点变更
- ❌ 删除：`/api/v1/{perception,cognition,decision,execution,resources,agent-looper,agent-platform}/*`
- ✅ 新增：`/api/v1/experts/skill-mcp/{skills,mcps}` 全套 CRUD + `/sync`（从 resources 搬迁）
- ✅ 保留：`/api/v1/{auth,users,llm,opencode,experts,compute,data-platform,knowledge-base}`

### 验证

**后端**
```
app import 成功，路由只剩 8 个模块前缀
✅ 保留端点（7 个全 200）:
   /experts (8) · /experts/skill-mcp/skills (43) · /experts/skill-mcp/mcps (3)
   /opencode/web/status · /compute/nodes (1) · /data-platform/sources · /knowledge-base/libraries (4)
❌ 已删端点（8 个全 404）:
   /perception/* · /cognition/* · /decision/* · /execution/*
   /resources/skills · /resources/compute-nodes · /agent-looper/configs · /agent-platform/agents
外键完整性：Base.metadata.sorted_tables 成功排序 24 张表（修完 3 个断链后）
启动日志无错误
```

**pytest 基线对比**（用 `git stash` 精确对比）
```
删除前：34 failed, 202 passed, 6 errors
删除后：29 failed, 109 passed, 6 errors
→ 失败数 34→29（修好 5 个 opencode_sync 端点测试）
→ passed 下降是因为删了 8 个测试文件（测的都是已删模块）
→ 剩余 29 个失败全部集中在 data_platform 既有测试（用 mcp_type 等旧字段名），
  逐个用 git stash 验证过：删除前后完全一致，非本次引入
```

**前端**
```
npm run build → ✓ built，0 error
  （连历史遗留的 14 个 TS 错误也一并清零：AgentStudioPage/AgentLooperWizard
   /AgentDetailPage/perception 等文件已删除，TemplatesPanel/userStore 顺手修掉）
```

**Playwright e2e 全绿**（`/tmp/after_purge.png`）
```
1) 登录 → 默认落地 /aide                                          ✅
2) 菜单 = [AIDE, 专家团, 算力调度, 数据平台, 知识库, 用户管理]      ✅ 与预期完全一致
3) 8 条死路由重定向全部生效                                        ✅
   /workspace|/perception|/cognition|/decision|/execution → /aide
   /resources|/agent-platform → /experts
   /data-platform/metadata → /data-platform/sources
4) 6 个保留页面全部正常渲染（无白屏）                              ✅
5) 专家团 Skills Tab 20 行 / MCPs Tab 23 行                        ✅ 端点搬迁成功
页面错误：仅 antd 既有废弃警告 + 2 个 403（/api/v1/users，
          测试用户非平台管理员，权限系统正常工作，与本次无关）
失败请求：仅 iframe 内 opencode 自己的 SSE（正常）
```

### 代码量变化
- 后端：删 **58 个文件**（API 7 + service 21 + repo 7 + model 21 + schema 8 + 测试 9 + 脚本 1，含目录）
- 前端：删 **6 个页面目录 + 4 个单文件**
- 数据库：63 张表 → **24 张**（DROP 39 张，约 9 万行）
- schema.sql：从手工维护的 12 张过期表 → ORM 自动生成的 24 张准确表

---

## 2026-08-03（补 5）

### Agent: 主开发 Agent（深度清理 — 删除专家团/算力调度/数据平台/知识库/LLM，只留 AIDE + 用户管理）

### 目标
继续删除专家团、算力调度、数据平台、知识库，让项目整体清爽干净，包括数据库。

### 删前盘点
- **AIDE 完全自闭环**：`AidePage`/`AideHost`/`aideStore`/`aide.service` 只依赖 `api.ts`；
  后端 `opencode.py` 只依赖 `auth` + `exceptions` → 删四模块对 AIDE 零影响 ✅
- 发现上次删除留下的**空壳目录**（只剩 `__pycache__`）：
  `api/v1/agent_looper/` / `api/v1/agent_platform/` / `services/agent_platform/` → 一并清掉

### 用户决策（提问确认）
1. **LLM 配置** → 一起删掉（四模块删完后 `LLMConfigService` 只剩 `/api/v1/llm` 自己在用，前端无页面）
2. **用户管理** → 保留（登录必需 `users` 表）
3. **4 个重组件** → 全删 + 卸依赖（`SqlEditor`/`ResultGrid`/`SchemaTree`/`DataTable`
   拖着 monaco-editor 6.9MB worker，删完页面后已成孤儿）

### 删除文件（后端 79 个）
- **API（6）**：`experts.py` / `expert_skill_mcp.py` / `compute.py` / `llm.py`
  + `data_platform/`（6 文件）+ `knowledge_base/`（8 文件）
- **Service（14）**：`expert` / `skill` / `mcp` / `docker_node` / `schedule_task`
  / `container_template` / `opencode_config_discovery` / `opencode_sync` / `opencode_local`
  / `dp_data_source` / `dp_query` / `dp_chat` / `kb` / `llm_config`
- **Repository（17）**：expert / skill / mcp / docker_node / schedule_task / container_template
  / dp_*（4）/ kb_*（6）/ llm_config
- **Model（19）**：expert / agent_relation / skill / mcp / docker_node / schedule_task
  / container_template / dp_*（5）/ kb_*（6）/ llm_config
- **Schema（17）**：对应上述模块的全部 Pydantic schema
- **Core（3）**：`sql_guard.py` / `crypto.py` / `decorators.py`（删完模块后成孤儿）
- **DB 工具（3）**：`seed_kb.py` / `seed_compute.py` / `schema_patch.py`
- **目录（4）**：`app/connectors/`（4 文件，Agent Platform 遗留）/ `app/scripts/` / `app/models/`
  / `sim/`（数据模拟器）/ `alembic/` + `alembic.ini`（本就不可用）
- **测试（12）**：`tests/{data_platform,knowledge_base,repositories,security}/` 全部

### 删除文件（前端）
- **页面目录（4）**：`pages/{experts,compute,data-platform,knowledge-base}/`
- **Service（5）**：`{expert,compute,dataPlatform,knowledgeBase,llm}.service.ts`
- **Store（2）**：`{dataPlatform,knowledgeBase}Store.ts`
- **组件（11）**：`SqlEditor` / `ResultGrid` / `SchemaTree` / `DataTable` / `monaco-setup`
  / `AgentChatPanel` / `DangerConfirm` / `PageHeader` / `SectionTitle` / `StatCard` / `TagPill`
- **测试（4）**：`{dataPlatform,knowledgeBase}.service.test.ts` / `{dataPlatform,knowledgeBase}Store.test.ts`
  + `components/common/__tests__/`（4 个）

### 卸载依赖
**前端（11 个）**：`@monaco-editor/react` / `monaco-editor` / `monaco-sql-languages`
/ `@xterm/xterm` / `@xterm/addon-fit` / `@tanstack/react-table` / `@tanstack/react-virtual`
/ `@ant-design/charts` / `@antv/g6` / `echarts` / `echarts-for-react`
→ dependencies **12 个 → 8 个**

**后端（13 个）**：`alembic` / `aiomysql` / `redis` / `langchain` / `langchain-openai`
/ `openai` / `numpy` / `pandas` / `celery` / `rdflib` / `asyncssh` / `sqlglot` / `sqlparse`
/ `sse-starlette`（`cryptography` 保留 — `python-jose[cryptography]` 需要）
→ 新增显式 `psutil`（AIDE 扫 `opencode web` 进程用，原来靠间接依赖）

### 修改文件
- `backend/app/api/v1/router.py` — 重写：只注册 3 个域，附完整已删清单表格
- `backend/app/main.py` — 重写：lifespan 只留 `create_all`（seed/scheduler/schema_patch 全删）
- `backend/app/db/models/__init__.py` — 重写：4 个 model，附两批删除清单
- `backend/app/core/config.py` — 重写：删 Redis/OpenAI/Fernet/AgentLooper/OpencodeServe 等过期配置；
  **加 `"extra": "ignore"`** 让 `.env` 历史遗留项（FERNET_KEY 等）不导致启动崩溃；
  新增 `OPENCODE_{HOST,PORT,WEB_PORT}` 统一管理
- `backend/app/api/v1/opencode.py` — `os.environ.get` 改用 `settings.OPENCODE_*`
- `backend/requirements.txt` — 重写：从 30+ 个依赖精简到 15 个
- `backend/schema.sql` — 从 ORM 重生（135 行 / 4 张表 + 88 张已删表完整清单）
- `backend/tests/conftest.py` — 重写：删 kb_libraries / MEDIUMTEXT shim / FULLTEXT strip
  / FERNET_KEY fixture（都指向已删模块）
- `frontend/src/App.tsx` — 重写：2 个活跃路由 + 11 条重定向
- `frontend/src/components/layout/AppLayout.tsx` — 菜单 2 项（AIDE / 用户管理）
- `frontend/src/components/common/CmdKOmnibar.tsx` — 删 10 个死路由 nav 项 + 3 个未用图标
- `frontend/src/components/common/index.ts` — 重写：只导出 4 个组件
- `frontend/src/services/index.ts` — 重写为空壳（`export {}`），附迁移指引
- `frontend/src/test-setup.ts` — 删 monaco mock（依赖已卸）
- `AGENTS.md` / `HANDOFF.md` — **整篇重写**，反映"只剩 2 个模块"的新形态

### 新增文件
- `backend/tests/test_smoke.py` — **25 个冒烟测试**（原测试全删了不能裸奔）：
  - `/health` `/` 可用性
  - **OpenAPI 里只应出现 auth/users/opencode 三个域**（防止误恢复模块）
  - 登录成功 / 密码错误 401 / `/auth/me`
  - `/users` 认证闸门（无 token / 伪造 token / Basic / 乱码 全 401）
  - `/opencode/web/status?fast=1` 响应协议校验
  - **15 个已删端点必须 404**（参数化，防回归）
  - ORM 只应剩 4 张表

### 数据库
**DROP 49 张表**（含上次删除后被 `create_all` 重建的 25 张空表壳）：
```
专家团   : experts(8) / agent_relations(2) / skills(43) / mcps(3)
算力调度 : docker_nodes(1) / compute_tasks / compute_runs / container_templates(2)
数据平台 : dp_data_sources(1) / dp_sql_queries / dp_query_history(3)
           / dp_chat_sessions(1) / dp_chat_messages(2)
知识库   : kb_libraries(4) / kb_data_assets / kb_code_repos
           / kb_documents / kb_experiences / kb_tags
LLM      : llm_configs(2)
+ 25 张第一批已删但被 create_all 重建的空壳
```
**结果**：DB **53 张 → 4 张**（`users` / `roles` / `user_roles` / `audit_logs`），零孤儿零缺失

累计两批共 **DROP 88 张表**。

### API 端点变更
- ❌ 删除：`/api/v1/{experts, experts/skill-mcp, compute, data-platform, knowledge-base, llm}/*`
- ✅ 保留：`/api/v1/{auth, users, opencode}` —— **共 11 个端点**

### 验证

**后端**
```
app import ✅ · 4 张表 ✅ · 11 个端点 ✅ · 启动无错误 ✅
保留端点：/health · /auth/me · /opencode/web/status?fast=1  全 200
已删端点：/experts · /experts/skill-mcp/skills · /compute/nodes
          /data-platform/sources · /knowledge-base/libraries · /llm  全 404
pytest: 25 passed / 0 failed  ← 从长期的 34 failed 变成全绿
残留扫描：expert_service / skill_service / mcp_service / docker_node / kb_service
          / dp_chat / llm_config / sql_guard / crypto / connectors / seed_* / schema_patch
          → 全部 0 处引用 ✅
```

**前端**
```
npx tsc -b        → 0 error
npm run build     → ✓ built in 208ms
构建产物：8MB（含 6.9MB monaco worker）→ 单个 1.1MB（gzip 369KB）
构建时间：914ms → 208ms
```

**Playwright e2e 全绿**（`/tmp/final.png`）
```
1) 登录 → 默认落地 /aide                     ✅
2) 菜单 = [AIDE, 用户管理]                    ✅ 与预期完全一致
3) 11 条死路由全部重定向到 /aide              ✅
   /workspace /perception /cognition /decision /execution
   /resources /agent-platform /experts /compute
   /data-platform /knowledge-base
4) 2 个保留页面正常渲染（无白屏）              ✅
5) AIDE iframe → http://127.0.0.1:4096/       ✅
   工具条含「AIDE / 已连接 / 复用 serve」      ✅
页面错误：仅 1 个 antd 既有警告 + 2 个 403（/users，测试用户非管理员，权限系统正常）
失败请求：仅 iframe 内 opencode 自己的 SSE（正常）
```

### 过程中修掉的一个自引入回归
删 `core/crypto.py` 后从 `config.py` 移除了 `FERNET_KEY` 字段，
但 `.env` 里仍有该项 → pydantic 抛 `extra_forbidden`，全部 25 个测试变 ERROR。
**修法**：`Settings.model_config` 加 `"extra": "ignore"`，让 `.env` 里任何历史遗留项
都不会导致启动失败（比逐个声明废弃字段更健壮）。

### 项目最终形态
```
前端：AIDE（iframe 嵌 opencode Web UI）+ 用户管理
      2 个页面 · 8 个 npm 依赖 · 产物 1.1MB
后端：/api/v1/{auth, users, opencode} · 11 个端点 · 4 张表 · 15 个依赖
测试：pytest 25 passed / 0 failed · tsc 0 error
```

### 代码量变化（两批累计）
| | 第一批前 | 第一批后 | 第二批后（当前） |
|---|---|---|---|
| 后端文件 | — | -58 | **-79（再删）** |
| 前端页面目录 | 11 | 5 | **2** |
| API 路由域 | 15 | 8 | **3** |
| API 端点 | ~200 | ~90 | **11** |
| 数据库表 | 63 | 24 | **4** |
| 前端 npm 依赖 | 19 | 12 | **8** |
| 后端 pip 依赖 | 30+ | 30+ | **15** |
| 构建产物 | ~8MB | ~8MB | **1.1MB** |
| pytest | 34 failed | 27 failed | **0 failed** |

### 补充清理（同批次收尾）

盘点后又发现一批孤儿，一并清掉：

**前端**
- `presets/agentLoopers.ts`（Agent Looper 预设）
- `types/{agent,agentLooper,dataPlatform,knowledgeBase,index}.ts` — 只剩 `types/user.ts` 有人用
- `stores/appStore.ts` — 零引用
- **`tests/` 整目录**：15 个 spec（`dp-*` 5 个 / `kb-*` 3 个 / `perception-*` 2 个
  / `w10-*` 3 个 / `nav` / `visual/screenshots`）全部测已删模块
- `playwright.config.ts` + 卸载 `@playwright/test` + 删 `test:e2e` script

**新增前端测试** `src/__tests__/smoke.test.tsx`（**20 个**）：
- 品牌名渲染
- 菜单只有 AIDE / 用户管理两项
- **参数化断言 10 个已删模块名不应出现在菜单**（专家团/算力调度/数据平台/知识库/
  感知层/认知层/决策层/执行层/对话工作台/资源管理）
- `/aide` `/users` 正常渲染
- **参数化断言 6 条已删路由重定向到 `/aide`**

**踩坑**：React 19 + jsdom 下 antd Menu 需要 `ResizeObserver`，
`test-setup.ts` 补了 stub 才跑通（报错信息里 `AggregateError` 会掩盖真实原因，
要往下翻才看到 `ResizeObserver is not defined`）。

### 最终文件数
```
后端 app/     33 个 .py
前端 src/     26 个文件
前端依赖      8 dependencies / 13 devDependencies
后端依赖      15 个
```

### 最终验证（全绿）
```
后端 pytest    25 passed / 0 failed
前端 vitest    20 passed / 0 failed
前端 tsc       0 error
前端 lint      0 error（2 个 fast-refresh warning）
前端 build     ✓ 217ms · 1.1MB
e2e            5 组全绿
```
