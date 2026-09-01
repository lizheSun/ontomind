# AGENTS.md

面向 OpenCode / 其它编码 Agent 的仓库速查。仅列**容易踩坑或非直觉**的项，其它请读代码。

> 🆕 **新 agent 冷启动请先读 [HANDOFF.md](./HANDOFF.md)**

## 项目一句话

OntoMind — AI Agent 工作平台 + DataOps/本体语义层。落地页 `/overview`。

主要能力：
1. **会话** — 原生聊天 `/chat`：交互层 + OpenCode / DSH 插件（**不是** AIDE iframe）
2. **看板** — 任务看板 `/board`：卡片绑定会话，列是工作流，运行状态单独过滤
3. **AIDE** — iframe 嵌入 opencode Web UI（`/infra/aide`），模块独立
4. **用户管理** — `/users`
5. **DataOps** — 数据仓库、智能数开、Wiki 知识库、元数据标注、本体建模
6. **AgentOps / Infra** — Agent/Skill 设计与容器发布；Infra「电脑」管理节点与容器

后端路由域（`/api/v1/`）：`auth` / `users` / `opencode` / `harness` / `kanban` / `compute` / `agent-factory` / `skill-platform` / `dataops` / `wiki` / `metadata` / `ontology`。  
ORM **51 张表**（权威清单见 `app/db/models/__init__.py`）。`pytest` 当前 **106 passed**。

> 🗑️ **2026-08-03 曾大清理**历史五层/专家团等模块；之后又增量恢复 Compute/Agent/DataOps/Wiki/Ontology。  
> 以**当前代码与本文件**为准，不要盲信旧 HANDOFF 里「只有 4 张表」的段落。

## 技术栈关键版本（易猜错）

- Backend: Python 3.12+, FastAPI 0.115, **SQLAlchemy 2.0** (DeclarativeBase), Pydantic **v2**, MySQL 8
- Frontend: React **19**, TypeScript **~6.0**, Vite **8**, **antd v6**, Zustand 5, React Router 7
- 主题：**Yao Agents CUI**（Outfit + `#3371fc` + 64px 图标轨 + 256px 上下文栏；参考本地 `http://127.0.0.1:5091/dashboard/assistants`）
- **前端 lint 用 `oxlint`，不是 eslint**
- **monaco-editor / @xterm / @xyflow/react / @opencode-ai/sdk** 已在依赖中（SmartDev / 终端 / 本体图）
- **opencode CLI ≥ 1.18**（AIDE）；开发需 `--cors http://localhost:5173`

## 常用命令

```bash
opencode serve --port 4096 --cors http://localhost:5173
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev

cd frontend && npm run build
cd frontend && npm run lint
cd backend && pytest
```

## 数据库

- 建表权威：`app/db/models/` + `main.py` 的 `create_all`（**无 alembic**）
- `schema.sql` 为 ORM 导出参考；改 Model 后按文件末尾命令再生
- 新增 Model：**必须**在 `models/__init__.py` import + `__all__`

## 三层架构硬约束

- `api/v1` → `services` → `repositories`（只 flush）→ `models`
- Service：**禁止** `with self.db.begin()`；用 `flush` + `commit`
- `app/services/base_service.py` 是历史遗留（含 begin），**不要参考**
- LLM：`LLMClient` + **GovOps → LLM 配置**（`platform_llm_settings`，优先于 `.env`）；未配置时 llm 模式抛 `LLM_NOT_CONFIGURED`，**rules 模式必须仍可用**
- 元数据扫描走 `information_schema`（才有 `COLUMN_COMMENT` / `TABLE_COMMENT`）
- 长任务：`job_runner.run_in_background` + 独立 Session，勿绑 FastAPI BackgroundTasks 生命周期

## AIDE

- `AideHost` 必须与 `<Outlet/>` 同级常驻，**禁止**放进路由（卸载会重建 iframe，慢 ~18.5x）

## 统一会话（/chat）

- 前端只打 `/api/v1/harness/*`，不直连 OpenCode SDK / DSH JSON-RPC
- 插件：`app/harness/plugins/`
  - **OpenCode**：优先本机 `opencode serve`（`/event` SSE → thinking / tools）；serve 没起才回退 `opencode run --format json`
  - **DSH**：源码 JSON-RPC（`tsx packages/examples/jsonrpc-demo`）或 `deepseek-harness-sdk`。**不是** `dsh --profile web`，也没有 `dsh --profile sdk`
- 加 runner：实现 `RunnerPlugin`（`probe` + `stream` → `StreamEvent`），在 `PluginRegistry.with_builtins` 注册
- **不要**把会话塞进 AIDE iframe；两套入口并存
- 组合器：切 Agent / 语音（识别结果**追加**）/ 工作区 / 上传（`inbox/`，无会话则先建）/ 优化提示（GovOps LLM；未配置友好报错）
- 附件只进插件 prompt，用户气泡仍显示原文 + file parts
- DSH 密钥走 GovOps → LLM 配置（`DEEPSEEK_API_KEY` / `BASE_URL`）
- DSH model **只能是** `deepseek-v4-flash` / `deepseek-v4-pro` / `deepseek-v4-flash-vision-exp`（默认 flash）。`deepseek-official` 是 provider 名，不能当 model。JSON-RPC 必须先等 `initialize` 返回再 `session/prompt`

## 任务看板（/board）

- 表：`kanban_boards` 1—N `kanban_columns` 1—N `kanban_tasks`；任务可选绑 `harness_sessions`
- **列位置 ≠ `run_status`**：拖拽只改 `column_id`/`position`；会话执行写 `pending|running|waiting|completed|failed`
- 点卡片 / 新任务在本页打开任务会话层（不跳 `/chat`）；第一条消息会写成卡片标题
- 前端只打 `/api/v1/kanban/*`

## 前端约定

- antd v6：`destroyOnHidden` / `mask.closable` / `Space orientation` / Spin 勿单独 tip
- 页面根节点优先 `className="page-enter"`；颜色用 `var(--*)`
- `AntApp.useApp()` 取 message/modal

## 参考文档

- `docs/ONTOLOGY_AIBI_DATA_AGENT.md` — 本体产品愿景
- `docs/prd/ontology.md` — 本次本体/标注实现说明
- `AGENT_LOG.md` / `HANDOFF.md` / `backend/STANDARDS.md`
