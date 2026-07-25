# AGENTS.md

面向 OpenCode / 其它编码 Agent 的仓库速查。仅列**容易踩坑或非直觉**的项，其它请读代码。

## 项目一句话

OntoMind — AI 驱动本体自动构建平台。**五层业务架构**（perception / cognition / decision / execution / application）+ 三层**代码架构**（API → Service → Repository）。

## 技术栈关键版本（易猜错）

- Backend: Python 3.12+, FastAPI 0.115, **SQLAlchemy 2.0** (DeclarativeBase), Pydantic **v2**, MySQL 8, Redis 7, Alembic 1.14, LangChain 0.3
- Frontend: React **19**, TypeScript **~6.0**, Vite **8**, **antd v6**（不是 v5，Form API 有差别），Zustand 5, React Router 7
- **前端 lint 用 `oxlint`，不是 eslint**；不要新增 eslint 配置
- 后端 requirements 声明了 `black` + `ruff`，但仓库**没有 pyproject.toml / ruff.toml**，跑之前先确认配置

## 常用命令

```bash
# 起全套（首选，含 MySQL + Redis）
docker compose up -d

# 后端本地：需已有 MySQL/Redis
cd backend && uvicorn app.main:app --reload --port 8000
# API docs: http://localhost:8000/api/docs

# 前端
cd frontend && npm run dev        # Vite → http://localhost:5173
cd frontend && npm run build      # tsc -b && vite build
cd frontend && npm run lint       # oxlint

# 后端测试（pytest 已安装，暂无 tests/ 目录）
cd backend && pytest
```

## 数据库：**Alembic 目前形同虚设**

- `backend/alembic/versions/` **不存在**，没有任何迁移文件。
- `app/main.py` 启动时执行 `Base.metadata.create_all(bind=engine)` — 靠这个自动建表。
- `backend/schema.sql`（330 行）是**参考蓝本**，不由 CI 维护，可能与 ORM 漂移。
- `backend/alembic/env.py` 里写的是 `from app.models import *`，**但实际路径是 `app.db.models`**，直接 `alembic revision --autogenerate` 会 ImportError。修好前不要指望 alembic 能跑。
- **新增 ORM Model 必须**：
  1. 建 `app/db/models/<name>_model.py`
  2. 到 `app/db/models/__init__.py` 里 import 注册，否则 `create_all` 发现不到
  3. Model 继承 `app.db.session.Base`（DeclarativeBase）

## 三层架构硬约束（团队规范，见 `backend/STANDARDS.md` `backend/DESIGN_STANDARDS.md`）

- 分层顺序：`api/v1/*.py` → `services/*_service.py` → `db/repositories/*_repo.py` → `db/models/*_model.py`
- **事务边界只在 Service 层**：`with self.db.begin(): ...`
- Repository 只能 `self.db.flush()`，**不允许 commit / begin / 写业务逻辑**
- API 层禁止直接查 DB、禁止写业务逻辑、禁止 try/except 业务异常（抛 `BusinessException` 让全局 handler 处理）
- 命名（严格）：`XxxService` / `XxxRepository` / `Xxx`（Model） / `XxxCreate/Update/Response`（Schema） / 文件 `xxx_service.py` / `xxx_repo.py` / `xxx_model.py` / `xxx_schema.py`
- 统一响应格式：`{"code": "SUCCESS"|"...", "message": "...", "data": ...}`；错误抛 `BusinessException(msg, code, status_code)`（见 `app/core/exceptions.py`）
- 新增 API 路由要在 `app/api/v1/router.py` 显式 `include_router`

## 五层业务域（router 前缀）

`/api/v1/{auth, users, llm, resources, projects, perception, cognition, decision, execution, application, knowledge-bases, source-code}`

改跨层业务时先明确它属于**哪一层**，路径别乱放。

## 前端约定

- 目录按功能模块拆：`types/ + services/*.service.ts + stores/*Store.ts + pages/*/`
- API 层：`services/api.ts` 已配 axios 拦截器（JWT + 401 自动跳 `/login`），业务模块用 `services/*.service.ts` 复用它
- 状态管理走 Zustand（一个模块一个 store，见 `frontend/STANDARDS.md`）
- **antd 是 v6**，`Form.useForm()`、Table API 与 v5 有区别，写代码前先看 v6 文档
- 环境变量走 Vite：`import.meta.env.VITE_API_BASE_URL`（默认 `http://localhost:8000/api/v1`）

## 配置与环境

- 后端所有配置集中在 `app/core/config.py`（`pydantic-settings`），读 `.env`
- 默认 `SECRET_KEY` 是占位符 — 生产必须换（`openssl rand -hex 32`）
- CORS 白名单在 `Settings.CORS_ORIGINS`，加前端端口时改这里
- Docker 挂 `./backend:/app` 做热重载；改后端不用重建镜像

## 多 Agent 协同

- **`AGENT_LOG.md`**（根目录）是团队约定的协同日志。做完非平凡改动，追加一段：**目标 / 决策 / 新增文件 / 修改文件 / API 端点**。已有 500+ 行例子，照抄格式。
- `.opencode/package.json` 已依赖 `@opencode-ai/plugin` 1.17.15，可挂本地插件到 `.opencode/plugins/`；目前无 `opencode.json`，如需 loop / hooks 见 `docs/RESEARCH_OPENCODE_AGENT_LOOP.md`
- 感知层 Cursor 风格的**流式标注**走 WebSocket，不是普通 REST（见 `app/api/v1/perception.py`）
- 对话工作台 OpenCode：**前端 SDK 直连本机 `opencode serve` (127.0.0.1:4096)**。
  路径 `/agent-platform/chat` → `pages/agent-platform/ChatWorkspacePage.tsx` → `features/opencode/`：
  客户端封装在 `features/opencode/client.ts`（fetch wrapper，与 `@opencode-ai/sdk` 等价），
  状态在 `features/opencode/stores/opencodeStore.ts`，SSE 订阅在 `hooks/useEventStream.ts`。
  后端只做三件事：`GET /api/v1/opencode/health`（探活）、`POST /api/v1/opencode/spawn`（dev-only，
  一键拉起 CLI）、`POST /api/v1/opencode/session-link`（把 opencode session_id 映射到业务侧
  (user, project) → `opencode_sessions` 表）。**不再走** `agent_runner.py` CLI 子进程（已删除）；
  开发时需先启动：`opencode serve --port 4096 --cors http://localhost:5173`。
- 历史：`opencode_serve_manager` / `opencode_session_bridge` (backend/app/services/agent_platform)
  是老的桥接层，为已有 `/agent-platform/runs` 页面服务，**不给新对话工作台用**。新对话不再依赖 CLI `run`。
- Vendor：`frontend/src/features/opencode/vendor/` 预留给 Wave 4 从 `opencode@v1.18.4:packages/web/src/components/`
  搬 UI 组件；当前尚未导入，第一版走 antd 原生 (`MessagePart.tsx`)。Tailwind 隔离方案见 `vendor/VENDOR_META.md`。

## 参考文档（重要，别重复造轮子）

- `backend/STANDARDS.md` — 分层 / 事务 / 命名 / DI 全套规范
- `backend/DESIGN_STANDARDS.md` — API 设计 + DB 命名 + 错误码
- `backend/REFACTORING_GUIDE.md` — 老代码迁三层的分步指南
- `frontend/STANDARDS.md` — 前端类型 / service / store / 组件规范
- `docs/project-plan.md` — 五层路线图
- `docs/RESOURCE_MANAGEMENT_DESIGN.md` — Agent / Skill / MCP 资源模型
- `docs/ONTOLOGY_AIBI_DATA_AGENT.md` — 本体 × AIBI 愿景

## 常见坑速览

- 新增 Model 忘记去 `app/db/models/__init__.py` 注册 → `create_all` 不建表
- 用 `db.commit()` 而不是 `db.flush()` in Repository → 破坏 Service 层事务边界
- 前端 lint 跑 `eslint` → 命令不存在，用 `npm run lint`（oxlint）
- 直接 `alembic upgrade head` → 会因 `env.py` import 路径错误挂掉
- API 直接返回 ORM 对象而不是 dict/Schema → 破坏统一响应格式
- 忘了 `include_router` → 新端点 404
- CORS 报错 → 加端口到 `Settings.CORS_ORIGINS`
