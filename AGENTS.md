# AGENTS.md

面向 OpenCode / 其它编码 Agent 的仓库速查。仅列**容易踩坑或非直觉**的项，其它请读代码。

> 🆕 **新 agent 冷启动请先读 [HANDOFF.md](./HANDOFF.md)**

## 项目一句话

OntoMind — AI Agent 工作平台。当前只有 **2 个模块**：

1. **AIDE** — iframe 嵌入 opencode 官方 Web UI（默认落地页 `/aide`）
2. **用户管理** — 用户 / 角色 / 权限 / 审计（`/users`）

后端 3 个路由域（`/api/v1/{auth, users, opencode}`，共 11 个端点）+ **4 张数据表**。

> 🗑️ **2026-08-03 分两批大清理**，删掉了几乎所有历史业务模块，
> 连带 **DROP 88 张数据库表**。详见 [AGENT_LOG.md](./AGENT_LOG.md) 与下方「已删除清单」。

## 技术栈关键版本（易猜错）

- Backend: Python 3.12+, FastAPI 0.115, **SQLAlchemy 2.0** (DeclarativeBase), Pydantic **v2**, MySQL 8
- Frontend: React **19**, TypeScript **~6.0**, Vite **8**, **antd v6**（不是 v5，Form/Drawer/Modal API 有差别）, Zustand 5, React Router 7
- **前端 lint 用 `oxlint`，不是 eslint**；不要新增 eslint 配置
- 后端 requirements 声明了 `black` + `ruff`，但仓库**没有 pyproject.toml / ruff.toml**
- **opencode CLI ≥ 1.18**（AIDE 的运行时依赖；1.18 起 `serve` 内置 Web UI，可直接 iframe）

## 常用命令

```bash
# 起 3 个终端
opencode serve --port 4096 --cors http://localhost:5173   # 终端 1：opencode（AIDE 依赖）
cd backend && uvicorn app.main:app --reload --port 8000   # 终端 2：后端（API docs: /api/docs）
cd frontend && npm run dev                                # 终端 3：Vite → http://localhost:5173

cd frontend && npm run build      # tsc -b && vite build（当前 0 error）
cd frontend && npm run lint       # oxlint
cd backend && pytest              # 当前 25 passed / 0 failed
```

## 数据库

- **只有 4 张表**：`users` / `roles` / `user_roles` / `audit_logs`
- `app/main.py` 启动时执行 `Base.metadata.create_all(bind=engine)` — 靠这个自动建表
- `backend/schema.sql` 由 **ORM 自动导出**（文件末尾有再生成命令），是参考文档；
  **建表权威是 `app/db/models/` 下的 Model**
- ⚠️ **alembic 已删除**（`alembic/` + `alembic.ini` 于 2026-08-03 移除）：
  它长期不可用（`env.py` import 路径错、`versions/` 空），且当前只有 4 张表不需要迁移工具
- **新增 ORM Model 必须**：
  1. 建 `app/db/models/<name>_model.py`
  2. 到 `app/db/models/__init__.py` import 注册 + 加 `__all__`，否则 `create_all` 发现不到
  3. Model 继承 `app.db.session.Base`（DeclarativeBase）

## 三层架构硬约束

- 分层：`api/v1/*.py` → `services/*_service.py` → `db/repositories/*_repo.py` → `db/models/*_model.py`
- **事务边界只在 Service 层**：`self.db.flush()` + `self.db.commit()`
  ⚠️ **不要用 `with self.db.begin()`** — 与 FastAPI `get_db` 的默认事务冲突（本仓已踩坑）
- Repository 只能 `self.db.flush()`，**不允许 commit / begin / 写业务逻辑**
- API 层禁止直接查 DB、禁止写业务逻辑、禁止 try/except 业务异常（抛 `BusinessException` 让全局 handler 处理）
- 命名（严格）：`XxxService` / `XxxRepository` / `Xxx`（Model） / `XxxCreate/Update/Response`（Schema）
- 统一响应格式：`{"code": "SUCCESS"|"...", "message": "...", "data": ...}`
- 新增 API 路由要在 `app/api/v1/router.py` 显式 `include_router`

## AIDE（唯一的核心业务模块）

- **`/aide`**（默认落地页）：iframe 嵌入 opencode 官方 Web UI
  - 页面 `pages/aide/AidePage.tsx` — **只管工具条 + 未就绪引导**
  - **iframe 常驻宿主** `components/layout/AideHost.tsx` — 挂在 `AppLayout` 里**跟路由同级**，
    切走路由只 `display:none` **不卸载**。⚠️ 这是硬要求：一旦放进路由，
    React Router 卸载组件时 iframe 会销毁，opencode UI 得重下 bundle + 重建 SSE（实测差 **18.5x**）
  - 共享状态 `stores/aideStore.ts`（status 落 sessionStorage，首屏不等接口直接渲染）
- **opencode ≥ 1.18 的 `serve` 已内置 Web UI**（`GET /` 返回 HTML，
  且响应头无 `X-Frame-Options` / CSP `frame-ancestors`）→ 默认复用 `serve(4096)`，**零额外进程**
- **后端只做 3 件事** (`api/v1/opencode.py`)：
  1. `GET  /api/v1/opencode/web/status` — 探活 + 决策最佳 `embed_url`（`?fast=1` 走 ~2ms 快路径）
  2. `POST /api/v1/opencode/web/start` — 拉起独立 `opencode web`(4097)，serve 无 UI 时兜底
  3. `POST /api/v1/opencode/web/stop`  — 停掉独立 `opencode web`
  - ⚠️ `--version`（500ms 子进程，10min TTL）和 HTML 探测（60s TTL）**都有缓存，别删**
- **开发时启动命令必须带 CORS**：`opencode serve --port 4096 --cors http://localhost:5173`

## 已删除清单（老代码里见到即死代码，勿再引用）

| 模块 | 路由 | 时间 |
|---|---|---|
| 对话工作台 | `/workspace`、`/api/v1/opencode/{health,spawn,session-link}` | 2026-08-03 |
| 感知层 / 认知层 / 决策层 / 执行层 | `/api/v1/{perception,cognition,decision,execution}` | 2026-08-03 |
| 资源管理 | `/api/v1/resources` | 2026-08-03 |
| Agent Looper / Agent Platform | `/api/v1/{agent-looper,agent-platform}` | 2026-08-03 |
| **专家团** | `/api/v1/experts`、`/api/v1/experts/skill-mcp` | 2026-08-03 |
| **算力调度** | `/api/v1/compute` | 2026-08-03 |
| **数据平台** | `/api/v1/data-platform` | 2026-08-03 |
| **知识库** | `/api/v1/knowledge-base` | 2026-08-03 |
| **LLM 配置** | `/api/v1/llm` | 2026-08-03 |
| projects / application | — | 更早 |

**前端所有已删路由都保留为 `<Navigate to="/aide">` 重定向**，老书签不会 404。

同时移除的基础设施：
- 后端：`app/{connectors,scripts,models}/`、`core/{sql_guard,crypto,decorators}.py`、
  `db/{seed_kb,seed_compute,schema_patch}.py`、`alembic/`、`sim/`（数据模拟器）
- 前端：`SqlEditor` / `ResultGrid` / `SchemaTree` / `DataTable` / `monaco-setup` /
  `AgentChatPanel` / `AgentPicker` / `PageHeader` / `SectionTitle` / `StatCard` / `TagPill` / `DangerConfirm`
- 依赖：`monaco-editor`（6.9MB worker）/ `@xterm/*` / `@tanstack/*` / `@ant-design/charts` /
  `@antv/g6` / `echarts` / `langchain` / `openai` / `pandas` / `numpy` / `celery` / `redis` /
  `rdflib` / `asyncssh` / `sqlglot` / `alembic` 等
- **构建产物 ~8MB → 1.1MB，构建时间 914ms → 208ms**

## 前端约定

- 目录：`services/*.service.ts` + `stores/*Store.ts` + `pages/*/` + `components/{common,layout}/`
- API 层：`services/api.ts` 已配 axios 拦截器
  - JWT 自动注入 + 401 自动跳 `/login`
  - **网络错误自动重试**（指数退避 300/600/1200ms）：开发时 `uvicorn --reload` 热重载
    有 1~3s 拒连窗口，重试能让用户无感。GET/HEAD/OPTIONS + `/auth/login`、`/auth/me` 才重试，
    写操作（POST/PATCH/PUT/DELETE）**不重试**避免重复提交
- `services/index.ts` 现在是空壳（只 `export {}`），保留是为了不破坏历史 import 路径；
  新代码直接 import 具体 service
- 状态管理走 Zustand（见 `frontend/STANDARDS.md`）
- **antd 是 v6**：`destroyOnClose`→`destroyOnHidden`、`maskClosable`→`mask.closable`、
  `<Spin tip>` 独立用不生效、`Drawer width`→`size`、`Space direction`→`orientation`
- 环境变量走 Vite：`import.meta.env.VITE_API_BASE_URL`（默认 `http://localhost:8000/api/v1`）；
  AIDE 的 opencode 地址由后端 `/opencode/web/status` 返回，前端不配
- 主题：**Editorial Light**（Fraunces serif + Geist sans + 象牙白 `#fafaf7` + 靛蓝墨水 `#3b52af`），
  见 `styles/global.css`

## 配置与环境

- 后端配置集中在 `app/core/config.py`（`pydantic-settings`），读 `.env`
- `model_config` 设了 `"extra": "ignore"` —— `.env` 里的历史遗留项（`FERNET_KEY`/`REDIS_URL`/
  `OPENAI_API_KEY` 等）不会导致启动失败
- 默认 `SECRET_KEY` 是占位符 — 生产必须换（`openssl rand -hex 32`）
- CORS 白名单在 `Settings.CORS_ORIGINS`，加前端端口时改这里
- opencode 端口在 `Settings.{OPENCODE_HOST,OPENCODE_PORT,OPENCODE_WEB_PORT}`

## 多 Agent 协同

- **`AGENT_LOG.md`**（根目录）是团队约定的协同日志。做完非平凡改动，追加一段：
  **目标 / 决策 / 新增文件 / 修改文件 / 删除文件 / API 端点 / 数据库 / 验证**。照抄已有格式。
- **`HANDOFF.md`**（根目录）是新 agent 冷启动指南。改动大架构后同步更新。

## 参考文档

- **`HANDOFF.md`** — 新 agent 冷启动指南
- **`AGENT_LOG.md`** — 历史变更时间线（做啥前先扫一遍）
- `backend/STANDARDS.md` — 分层 / 事务 / 命名 / DI 规范
- `backend/DESIGN_STANDARDS.md` — API 设计 + DB 命名 + 错误码
- `frontend/STANDARDS.md` — 前端类型 / service / store / 组件规范

## 常见坑速览

- 新增 Model 忘记去 `app/db/models/__init__.py` 注册 → `create_all` 不建表
- Repository 里用 `db.commit()` 而非 `db.flush()` → 破坏 Service 层事务边界
- Service 里用 `with self.db.begin()` → InvalidRequestError（FastAPI 已开事务）
- 前端 lint 跑 `eslint` → 命令不存在，用 `npm run lint`（oxlint）
- **把 `AideHost` 放进路由** → 每次进 AIDE 都要重新加载 opencode UI（慢 18.5x）
- API 直接返回 ORM 对象而不是 dict/Schema → 破坏统一响应格式
- 忘了 `include_router` → 新端点 404
- CORS 报错 → 加端口到 `Settings.CORS_ORIGINS`；opencode serve 记得带 `--cors http://localhost:5173`
- 登录报「无法连接后端」→ 大概率是 `uvicorn --reload` 正在热重载（1~3s 窗口），
  `api.ts` 已自动重试 3 次，稍等即可
