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
