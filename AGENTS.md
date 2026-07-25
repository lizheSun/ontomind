# AGENTS.md

面向 OpenCode / 其它编码 Agent 的仓库速查。仅列**容易踩坑或非直觉**的项，其它请读代码。

> 🆕 **新 agent 冷启动请先读 [HANDOFF.md](./HANDOFF.md)**（数据库初始化、启动步骤、冒烟脚本）

## 项目一句话

OntoMind — AI 驱动本体自动构建平台。**五层业务架构**（perception / cognition / decision / execution） +
**对话工作台**（前端 SDK 直连 opencode serve） + **专家团**（管理 opencode agent 配置）。

## 技术栈关键版本（易猜错）

- Backend: Python 3.12+, FastAPI 0.115, **SQLAlchemy 2.0** (DeclarativeBase), Pydantic **v2**, MySQL 8, Redis 7
- Frontend: React **19**, TypeScript **~6.0**, Vite **8**, **antd v6**（不是 v5，Form API 有差别），Zustand 5, React Router 7
- **前端 lint 用 `oxlint`，不是 eslint**；不要新增 eslint 配置
- 后端 requirements 声明了 `black` + `ruff`，但仓库**没有 pyproject.toml / ruff.toml**，跑之前先确认配置
- **opencode CLI ≥ 1.17**（专家团 + 对话工作台的运行时依赖）

## 常用命令

```bash
# 起 3 个终端（推荐）
opencode serve --port 4096 --cors http://localhost:5173   # 终端 1：opencode 服务
cd backend && uvicorn app.main:app --reload --port 8000   # 终端 2：后端（API docs: /api/docs）
cd frontend && npm run dev                                # 终端 3：Vite → http://localhost:5173

# 前端
cd frontend && npm run build      # tsc -b && vite build
cd frontend && npm run lint       # oxlint

# 后端测试
cd backend && pytest
```

## 数据库：**Alembic 目前形同虚设**

- `backend/alembic/versions/` **不存在**，没有任何迁移文件。
- `app/main.py` 启动时执行 `Base.metadata.create_all(bind=engine)` — 靠这个自动建表。
- `backend/schema.sql` 只手动维护了 9 张核心表，**不完整**（`experts` / `agent_versions` / `agent_deployments` 等新表只靠 create_all）。
- `backend/alembic/env.py` 里写的是 `from app.models import *`，**但实际路径是 `app.db.models`**，直接 `alembic revision --autogenerate` 会 ImportError。修好前不要指望 alembic 能跑。
- **首次建表**：起一次 `uvicorn app.main:app --reload` 就会自动 `create_all`。之后跑 seed 脚本创建 admin 用户 + 4 个内置专家（见 HANDOFF §1.6）。
- **新增 ORM Model 必须**：
  1. 建 `app/db/models/<name>_model.py`
  2. 到 `app/db/models/__init__.py` 里 import 注册 + 加 `__all__`，否则 `create_all` 发现不到
  3. Model 继承 `app.db.session.Base`（DeclarativeBase）

## 三层架构硬约束

- 分层：`api/v1/*.py` → `services/*_service.py` → `db/repositories/*_repo.py` → `db/models/*_model.py`
- **事务边界只在 Service 层**：`self.db.flush()` + `self.db.commit()`
  ⚠️ **不要用 `with self.db.begin()`** — 与 FastAPI `get_db` 的默认事务冲突（本仓已踩坑，见 AGENT_LOG "保存专家 500 错误"）
- Repository 只能 `self.db.flush()`，**不允许 commit / begin / 写业务逻辑**
- API 层禁止直接查 DB、禁止写业务逻辑、禁止 try/except 业务异常（抛 `BusinessException` 让全局 handler 处理）
- 命名（严格）：`XxxService` / `XxxRepository` / `Xxx`（Model） / `XxxCreate/Update/Response`（Schema） / 文件 `xxx_service.py` / `xxx_repo.py` / `xxx_model.py` / `xxx_schema.py`
- 统一响应格式：`{"code": "SUCCESS"|"...", "message": "...", "data": ...}`；错误抛 `BusinessException(msg, code, status_code)`（见 `app/core/exceptions.py`）
- 新增 API 路由要在 `app/api/v1/router.py` 显式 `include_router`

## 五层业务域（router 前缀）

`/api/v1/{auth, users, llm, resources, perception, cognition, decision, execution, data-platform, knowledge-base, agent-platform, agent-looper, opencode, experts}`

⚠️ **已删除**：`/api/v1/{projects, application}` + `/api/v1/agent-platform/{runs, approvals, sessions}`。老代码里若见到相关调用是死代码。

## 对话工作台 + 专家团（当前活跃架构）

- **对话工作台 `/workspace`**：前端 SDK 直连本机 `opencode serve` (127.0.0.1:4096)
  - 客户端 `features/opencode/client.ts`（fetch wrapper，与 `@opencode-ai/sdk` 等价）
  - 状态 `features/opencode/stores/opencodeStore.ts`
  - SSE 订阅 `features/opencode/hooks/useEventStream.ts`
- **后端只做 3 件事** (`api/v1/opencode.py`)：
  1. `GET /api/v1/opencode/health` — 探活
  2. `POST /api/v1/opencode/spawn` — dev-only 一键拉起 opencode CLI
  3. `POST /api/v1/opencode/session-link` — 把 opencode session_id 映射到业务侧 `opencode_sessions` 表
- **专家团 `/experts`**（`api/v1/experts.py` + `services/expert_service.py`）：
  - 1 个专家 = 1 个 `~/.config/opencode/agent/{slug}.md` 文件
  - `ExpertService._write_agent_md(e)` 生成 YAML frontmatter + Markdown body
  - 4 个内置专家：`data-analyst` / `frontend` / `backend` / `product-manager`
- **⚠️ opencode 不热加载 agent 目录**：新增/编辑专家后必须重启 `opencode serve` 才能通过 `@slug` 路由。UI 已提示（未加载的专家会有橙色小圆点）
- **开发时启动命令必须带 CORS**：`opencode serve --port 4096 --cors http://localhost:5173`

## 前端约定

- 目录按功能模块拆：`types/ + services/*.service.ts + stores/*Store.ts + pages/*/ + features/*/`
- API 层：`services/api.ts` 已配 axios 拦截器（JWT + 401 自动跳 `/login`），业务模块用 `services/*.service.ts` 复用它
- 状态管理走 Zustand（一个模块一个 store，见 `frontend/STANDARDS.md`）
- **antd 是 v6**，`Form.useForm()`、Table API 与 v5 有区别，写代码前先看 v6 文档
- 环境变量走 Vite：`import.meta.env.VITE_API_BASE_URL`（默认 `http://localhost:8000/api/v1`）、`VITE_OPENCODE_URL`（默认 `http://127.0.0.1:4096`）
- 主题：**Editorial Light**（Fraunces serif + Geist sans + 象牙白 `#fafaf7` + 靛蓝墨水 `#3b52af`），见 `styles/global.css`
- opencode 视觉在 `features/opencode/vendor/styles/opencode.css`（scoped 到 `.oc-scope`）

## 配置与环境

- 后端所有配置集中在 `app/core/config.py`（`pydantic-settings`），读 `.env`
- 默认 `SECRET_KEY` 是占位符 — 生产必须换（`openssl rand -hex 32`）
- CORS 白名单在 `Settings.CORS_ORIGINS`，加前端端口时改这里
- Docker 挂 `./backend:/app` 做热重载；改后端不用重建镜像

## 多 Agent 协同

- **`AGENT_LOG.md`**（根目录）是团队约定的协同日志。做完非平凡改动，追加一段：**目标 / 决策 / 新增文件 / 修改文件 / 删除文件 / API 端点 / 数据库 / 验证**。已有 900+ 行例子，照抄格式。
- **`HANDOFF.md`**（根目录）是新 agent 冷启动 30 分钟指南，包含数据库初始化、启动步骤、冒烟脚本。改动大架构后同步更新它。
- 感知层 Cursor 风格的**流式标注**走 WebSocket，不是普通 REST（见 `app/api/v1/perception.py`）
- Vendor：`frontend/src/features/opencode/vendor/` 预留给后续从 `opencode@v1.18.4:packages/web/src/components/` 搬 UI 组件；当前只搬了极简样式，第一版走 antd 原生 (`MessagePart.tsx`)。方案见 `vendor/VENDOR_META.md`。

## 参考文档（重要，别重复造轮子）

- **`HANDOFF.md`** — 新 agent 冷启动指南（数据库/启动/冒烟脚本）
- **`AGENT_LOG.md`** — 历史变更时间线（做啥前先扫一遍）
- `backend/STANDARDS.md` — 分层 / 事务 / 命名 / DI 全套规范
- `backend/DESIGN_STANDARDS.md` — API 设计 + DB 命名 + 错误码
- `frontend/STANDARDS.md` — 前端类型 / service / store / 组件规范
- `docs/project-plan.md` — 五层路线图
- `docs/ONTOLOGY_AIBI_DATA_AGENT.md` — 本体 × AIBI 愿景

## 常见坑速览

- 新增 Model 忘记去 `app/db/models/__init__.py` 注册 → `create_all` 不建表
- 用 `db.commit()` 而不是 `db.flush()` in Repository → 破坏 Service 层事务边界
- **Service 里用 `with self.db.begin()`** → InvalidRequestError（FastAPI 已开事务）；改成 `flush()` + `commit()`
- 前端 lint 跑 `eslint` → 命令不存在，用 `npm run lint`（oxlint）
- 直接 `alembic upgrade head` → 会因 `env.py` import 路径错误挂掉
- API 直接返回 ORM 对象而不是 dict/Schema → 破坏统一响应格式
- 忘了 `include_router` → 新端点 404
- CORS 报错 → 加端口到 `Settings.CORS_ORIGINS`；opencode serve 记得带 `--cors http://localhost:5173`
- 新建专家后 opencode 不认识 → 重启 `opencode serve`（agent 目录不热加载）
- 中文输入法组词按 Enter 发送 → `ChatComposer` 里已用 `isComposing` 检测

