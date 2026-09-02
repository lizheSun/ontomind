# HANDOFF — 新 Agent 冷启动指南

> 目标：任何新 agent 拿到这份文档 + 仓库，**15 分钟内**能把项目跑起来并开始改代码。

---

## 0 · TL;DR — 这个项目现在是什么

**OntoMind = AI Agent 工作平台 + DataOps/本体语义层**。落地页 `/overview`。

| 模块 | 路由 | 说明 |
|---|---|---|
| **Overview / 六域壳** | `/overview` 等 | CodeOps / DataOps / ModelOps / AgentOps / GovOps / Infra |
| **会话** | `/chat` | 原生聊天；OpenCode 优先 serve SSE；DSH 走 JSON-RPC 源码运行时（不是 Web UI） |
| **看板** | `/board` | 任务看板；卡片绑定会话，列是工作流，`/api/v1/kanban` |
| **AIDE** | `/infra/aide`（旧 `/aide`） | iframe 嵌入 OpenCode / DeepSeek Harness Web（`AideHost` 常驻，**未改**） |
| **用户管理** | `/users` | 用户 / 角色 / 权限 / 审计 |
| **DataOps** | `/dataops/*` | 仓库、智能数开、Wiki、元数据标注、本体建模 |
| **AgentOps / Infra** | `/agentops/*` `/infra/*` | Agent/Skill 工厂；Infra「电脑」对齐 Yao computers |

规模（2026-09-01）：
- 后端 **12 个路由域**（… + `harness` / `kanban`）、**51 张表**（含会话 + 看板）
- 主题：**Yao Agents CUI**（Outfit + `#3371fc`）；依赖含 monaco / xterm / xyflow
- 测试：`pytest` 以最新一次本地跑数为准；`npm run build` / `npm run lint` 须 0 error

> 🗑️ 2026-08-03 曾大清理历史模块；之后已增量恢复 Compute/Agent/DataOps/Wiki/Ontology。  
> **以 [AGENTS.md](./AGENTS.md) 与当前代码为准**，勿盲信下文旧「4 张表」残留描述（已逐步改写）。

---

## 1 · 环境准备

### 1.1 依赖版本（易猜错，别装错）

| 组件 | 版本 | 备注 |
|---|---|---|
| Python | 3.12+ | |
| Node | 20+ | |
| MySQL | 8 | |
| **opencode CLI** | **≥ 1.18** | AIDE 硬依赖；1.18 起 `serve` 内置 Web UI |
| FastAPI | 0.115 | |
| SQLAlchemy | **2.0** | DeclarativeBase 风格 |
| Pydantic | **v2** | |
| React | **19** | |
| Vite | **8** | |
| **antd** | **v6** | 不是 v5！API 有 breaking change |

### 1.2 装 opencode CLI（AIDE 必需）

```bash
curl -fsSL https://opencode.ai/install | bash
opencode --version   # 必须 ≥ 1.18
```

### 1.3 后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 1.4 前端依赖

```bash
cd frontend
npm install
```

### 1.5 数据库

```sql
CREATE DATABASE IF NOT EXISTS ontomind
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

建表**不用手动跑 SQL** —— 后端启动时 `Base.metadata.create_all()` 会自动建 **40** 张表。
`backend/schema.sql` 只是 ORM 导出的参考文档。

### 1.6 `.env`

`backend/.env`：

```ini
DB_HOST=localhost
DB_PORT=3306
DB_USER=ontomind
DB_PASSWORD=你的密码
DB_NAME=ontomind

SECRET_KEY=用 openssl rand -hex 32 生成

# 可选：元数据 LLM 标注 / 本体生成（OpenAI 兼容）；空则仅 rules 模式可用
# LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
# LLM_API_KEY=
# LLM_MODEL=
```

> `Settings.model_config` 设了 `"extra": "ignore"`，所以 `.env` 里的历史遗留项
> （`FERNET_KEY` / `REDIS_URL` / `OPENAI_API_KEY` 等）不会导致启动失败，可以不清。

---

## 2 · 启动（3 个终端）

**终端 1 · opencode**（AIDE 的核心依赖，**必须带 `--cors`**）

```bash
opencode serve --port 4096 --cors http://localhost:5173
```

**终端 2 · 后端**

```bash
cd backend && uvicorn app.main:app --reload --port 8000
# API 文档：http://localhost:8000/api/docs
```

**终端 3 · 前端**

```bash
cd frontend && npm run dev
# → http://localhost:5173
```

**验证**：浏览器打开 `http://localhost:5173`，登录后进 `/overview`；
AIDE 在 `/aide`，工具条应显示「已连接 · 复用 serve」。

---

## 3 · 核心架构（必读）

### 3.1 AIDE = iframe 嵌 opencode 官方 UI

**关键事实**：opencode ≥ 1.18 的 `serve` 已内置完整 Web UI —— `GET /` 直接返回 HTML，
且响应头**没有 `X-Frame-Options`，CSP 也没有 `frame-ancestors`** → 可以直接 iframe。

所以我们**复用同一个 `serve(4096)` 进程**，零额外开销、无反向代理跳转。

前端 3 个文件：

| 文件 | 职责 |
|---|---|
| `pages/aide/AidePage.tsx` | 只管工具条 + 未就绪引导 |
| `components/layout/AideHost.tsx` | **iframe 常驻宿主** |
| `stores/aideStore.ts` | 两者共享状态（status 落 sessionStorage） |

⚠️⚠️ **`AideHost` 必须挂在 `AppLayout` 里、跟路由同级，绝对不能放进 `<Route>`**：
React Router 切走路由会卸载组件，iframe 一销毁 opencode UI 就得重下 bundle + 重建 SSE。
实测「切走再回来」耗时 **2076ms → 112ms（18.5x）**，iframe 请求数 **11 → 0**。
切走时只做 `display: none`，iframe 在后台继续活着。

后端 3 个端点（`api/v1/opencode.py`）：

```
GET  /api/v1/opencode/web/status   探活 + 决策 embed_url；?fast=1 走 ~2ms 快路径
POST /api/v1/opencode/web/start    拉起独立 opencode web(4097)，serve 无 UI 时兜底
POST /api/v1/opencode/web/stop     停掉独立 opencode web
```

⚠️ `opencode --version` 是 500ms 的子进程调用，`serve` 是否带 UI 要发 HTTP —— **两者都有 TTL 缓存
（10min / 60s），别删**。删了每次进 AIDE 都要多等 600ms。

**iframe 内的消息/事件流平台后端完全不参与**（跨域 iframe，我们读不到也不需要读）。

### 3.2 数据流

```
浏览器
   ├── <iframe src=127.0.0.1:4096> ──→ opencode serve   (AIDE：session/message/event 全在 iframe 内)
   │
   └── HTTP ─→ FastAPI:8000                             (登录 / 用户管理 / AIDE 探活)
                    │
                    └── SQLAlchemy → MySQL              (40 张表)
```

---

## 4 · 数据库

### 4.1 当前 **40** 张表

权威清单与分组见 `backend/app/db/models/__init__.py` 文件头。核心分组：

```
users / roles / user_roles / audit_logs
compute_nodes / container_services
agent_* / skill_* / deployments
data_sources
wiki_spaces / wiki_documents / wiki_document_versions
meta_scan_jobs / meta_tables / meta_columns / glossary_terms / annotations
ontologies / ontology_*（9）
```

### 4.2 建表靠 `create_all`

`app/main.py` 启动时 `Base.metadata.create_all(bind=engine)` 自动建缺失的表。

**新增 ORM Model 必做 3 件事**：
1. 建 `app/db/models/<name>_model.py`（继承 `app.db.session.Base`）
2. 到 `app/db/models/__init__.py` `from ... import Xxx` — **忘了这步 `create_all` 发现不到，表不建**
3. 到 `__all__` 加名字

### 4.3 alembic 已删除

`alembic/` + `alembic.ini` 于 2026-08-03 移除。改列直接改 Model + 手动 `ALTER TABLE`，或写一次性脚本。

### 4.4 `schema.sql` 是导出物不是权威

`backend/schema.sql` 由 ORM 自动生成（文件末尾附再生成命令），只作参考文档。
**建表权威永远是 `app/db/models/` 下的 Model。**

---

## 5 · 后端硬约束（改代码前必读）

- 分层：`api/v1/*.py` → `services/*_service.py` → `db/repositories/*_repo.py` → `db/models/*_model.py`
- **事务边界只在 Service 层**：`self.db.flush()` + `self.db.commit()`
  ⚠️ **不要用 `with self.db.begin()`** — 与 FastAPI `get_db` 的默认事务冲突（本仓踩过坑，会抛 `InvalidRequestError`）
- Repository 只能 `flush()`，**不允许 commit / begin / 写业务逻辑**
- API 层禁止直接查 DB、禁止写业务逻辑、禁止 try/except 业务异常
  → 抛 `BusinessException(msg, code, status_code)`，让全局 handler 转成统一响应
- 命名（严格）：`XxxService` / `XxxRepository` / `Xxx`(Model) / `XxxCreate|Update|Response`(Schema)
- 统一响应：`{"code": "SUCCESS", "message": "...", "data": ...}`
- 新增路由要在 `app/api/v1/router.py` 显式 `include_router`

---

## 6 · 前端硬约束

- **antd v6**，与 v5 的 breaking change：
  `destroyOnClose`→`destroyOnHidden`、`maskClosable`→`mask.closable`、
  `Drawer width`→`size`、`Space direction`→`orientation`、`<Spin tip>` 独立用不生效
- **lint 用 `oxlint`**：`npm run lint`；**不要装 eslint**
- `services/api.ts` 的 axios 拦截器已配：
  - JWT 自动注入 + 401 自动跳 `/login`
  - **网络错误自动重试**（指数退避 300/600/1200ms）—— 开发时 `uvicorn --reload` 热重载
    有 1~3s 拒连窗口，重试让用户无感。只有 GET/HEAD/OPTIONS + `/auth/login`、`/auth/me` 重试；
    写操作不重试，避免重复提交
- `services/index.ts` 是空壳（`export {}`），保留只为不破坏历史 import 路径 —— 新代码直接 import 具体 service
- 状态管理走 Zustand（一个模块一个 store）
- Vite 环境变量前缀 `VITE_`

---

## 7 · 常见问题排查

| 症状 | 排查 |
|---|---|
| `/aide` 显示「opencode 未就绪」 | 终端 1 起 `opencode serve --port 4096 --cors http://localhost:5173` |
| AIDE iframe 空白 / CORS 报错 | `opencode serve` 必须带 `--cors http://localhost:5173` |
| **每次进 AIDE 都在加载** | 检查 `AideHost` 是否挂在 `AppLayout`（**不能放路由里**，否则会被卸载） |
| 登录报「无法连接后端」 | `uvicorn --reload` 热重载有 1~3s 窗口；`api.ts` 已自动重试 3 次，稍等即可 |
| 登录后白屏 | 检查 `SECRET_KEY` 是否配好；后端启动日志有无报错 |
| `create_all` 未建新表 | 检查 `db/models/__init__.py` 是否 import 了新 model |
| 「transaction already begun」 | Service 里用了 `with self.db.begin()` → 改成 `flush()` + `commit()` |
| 标注/本体 llm 模式报 `LLM_NOT_CONFIGURED` | `.env` 设 `LLM_API_KEY`；rules/hybrid 的 rules 部分仍可跑 |
| 扫描无表/列注释 | 必须走 `information_schema`，勿用裸 `DESCRIBE` |
| `/users` 返回 403 | 权限系统正常工作 —— 该用户没有平台管理员角色 |
| pydantic `extra_forbidden` | `.env` 有 Settings 未声明的项；`config.py` 已设 `extra: ignore`，若报错检查是否被改回 |

---

## 8 · 参考文档

| 文件 | 内容 |
|---|---|
| `AGENTS.md` | 项目规范速查（本文的精简版） |
| `AGENT_LOG.md` | **历史变更时间线 — 动手前先扫一遍** |
| `docs/prd/ontology.md` | Wiki / 元数据 / 本体实现说明 |
| `docs/ONTOLOGY_AIBI_DATA_AGENT.md` | 本体产品愿景 |
| `backend/STANDARDS.md` | 分层 / 事务 / 命名 / DI 完整规范 |
| `backend/DESIGN_STANDARDS.md` | API 设计 + DB 命名 + 错误码 |
| `frontend/STANDARDS.md` | 前端类型 / service / store 规范 |

---

## 9 · 一键冒烟（新机器最后一步）

```bash
# 后端探活
curl -s http://localhost:8000/health && echo " ← backend OK"

# opencode 探活
curl -s http://127.0.0.1:4096/global/health | grep -q healthy && echo "opencode OK"

# 数据库探活（应约 40 张表）
mysql -uroot ontomind -e "SHOW TABLES;"

# 登录 + AIDE 探活
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"你的用户名","password":"你的密码"}' \
  | python3 -c 'import json,sys;print(json.load(sys.stdin)["data"]["access_token"])')

curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/opencode/web/status?fast=1" | python3 -m json.tool | head -8
# 期望：healthy=true, embed_source="serve"

# 后端测试
cd backend && pytest -q

# 前端构建 / lint
cd frontend && npm run build     # 期望 0 error
cd frontend && npm run lint
```

**任一步失败 → 回到对应章节排查。全部通过 → 可以开工。**
