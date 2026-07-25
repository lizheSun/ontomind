# HANDOFF · 新 Agent 冷启动指南

> 目标：任何新 agent 拿到这份文档 + 仓库，**30 分钟内**能跑起对话工作台、专家团、感知/认知全链路。
>
> 假设：macOS/Linux 开发机，已装 Python 3.12+、Node 22+、MySQL 8、Redis 7、Docker（可选）、
> **opencode CLI ≥ 1.17**（`curl -fsSL https://opencode.ai/install | bash`）。

## 0 · 项目定位（30 秒理解）

- **OntoMind** = AI 驱动的本体自动构建平台，五层业务架构（perception / cognition / decision / execution / application）
- **当前活跃模块**：对话工作台（前端 SDK 直连 opencode serve）+ 专家团（管理 opencode agent 配置）+ 感知层（数据源→元数据→本体）
- **已删除模块**：dashboard / application / projects / runs 4 个页面 + 后端配套；老 `agent_platform/run,approval,session` 编排层
- **技术栈**：FastAPI 0.115 + SQLAlchemy 2.0 + MySQL 8 + Pydantic v2 · React 19 + antd v6 + Vite 8 + Zustand 5

## 1 · 一次性初始化（新机器第一次）

### 1.1 安装依赖

```bash
# 后端
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 前端
cd ../frontend
npm install

# opencode CLI（专家团 + 对话工作台必需）
curl -fsSL https://opencode.ai/install | bash
opencode --version   # 应 ≥ 1.17
```

### 1.2 起 MySQL / Redis

```bash
# 简单方式：本机已装 MySQL 8 + Redis 7 直接跑
mysql.server start
redis-server --daemonize yes

# 或用 docker compose（如果仓库有 compose 文件；无则跳过）
docker compose up -d mysql redis   # 只启依赖，不启 backend
```

### 1.3 创建数据库 + 用户

```bash
mysql -uroot -e "CREATE DATABASE IF NOT EXISTS ontomind DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

⚠️ 默认连接：`root` / 空密码 / `127.0.0.1:3306`。**用别的账号请改 `backend/.env`**。

### 1.4 配置 `.env`

```bash
# 后端 backend/.env
cat > backend/.env <<EOF
DB_USER=root
DB_PASSWORD=
DB_NAME=ontomind
SECRET_KEY=$(openssl rand -hex 32)
FERNET_KEY=u4-7Q3fuoXMKKtNINjtZx4XzFynNyT9FST3hs_LI004=
DEBUG=true
EOF

# 前端 frontend/.env（也可用 .env.example 直接复制）
cat > frontend/.env <<EOF
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_OPENCODE_URL=http://127.0.0.1:4096
EOF
```

**Fernet 密钥**：`.env.example` 里那个可以直接用于开发；生产必换（`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`）。

### 1.5 建表（关键步骤）

⚠️ **不要用 alembic**（本仓库 alembic 目前坏的，见"数据库"章）。用两种方式之一：

**方式 A · 自动建表（推荐）**：让 `app.main` 启动时的 `Base.metadata.create_all(engine)` 帮你建所有表。

```bash
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
# 启动日志里能看到 "create_all done" / 或至少无报错
```

**方式 B · 直接跑 schema.sql**（更快、更彻底）：

```bash
mysql -uroot ontomind < backend/schema.sql
```

⚠️ `backend/schema.sql` 已同步到最新结构（54 张表），但 `agent_versions` / `agent_deployments` / `experts` 等**只在 create_all 里定义**，不在 schema.sql 里。**首选方式 A**，跑一次 uvicorn 之后表就齐了。

### 1.6 初始化用户 + 内置专家

```bash
cd backend && source .venv/bin/activate

# 1. 创建 admin 用户（如果已存在跳过）
python3 << 'PY'
from app.db.session import SessionLocal
from app.db.models.user_model import User
from app.core.security import get_password_hash
db = SessionLocal()
u = db.query(User).filter_by(username='admin').first()
if not u:
    u = User(username='admin', email='admin@local', password_hash=get_password_hash('admin123'), is_active=True)
    db.add(u); db.commit()
    print('admin created (pw=admin123)')
else:
    u.password_hash = get_password_hash('admin123')
    db.commit()
    print('admin password reset to admin123')
db.close()
PY

# 2. 注入 4 个内置专家（data-analyst / frontend / backend / product-manager）
python3 << 'PY'
from app.db.session import SessionLocal
from app.services.expert_service import seed_default_experts
db = SessionLocal()
n = seed_default_experts(db)
print(f'seeded {n} experts')
db.close()
PY

# 3. 检查 opencode agent 文件是否生成
ls ~/.config/opencode/agent/
# 应看到：backend.md  data-analyst.md  frontend.md  product-manager.md
```

## 2 · 日常启动（3 个终端）

**终端 1 · opencode serve**（专家团 + 对话工作台的核心依赖）

```bash
opencode serve --port 4096 --cors http://localhost:5173
```

**终端 2 · 后端**

```bash
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
# http://localhost:8000/api/docs
```

**终端 3 · 前端**

```bash
cd frontend && npm run dev
# http://localhost:5173
# 登录：admin / admin123
```

**验证**：浏览器打开 `/workspace`，发一条消息应能收到 AI 回复。

## 3 · 核心架构（新 agent 必读）

### 3.1 对话工作台走 opencode 原生

- 前端 `features/opencode/client.ts` 是纯 fetch wrapper（与 `@opencode-ai/sdk` 等价），
  直接调 `http://127.0.0.1:4096/*`（opencode serve）
- 后端只做 3 件事（`api/v1/opencode.py`）：
  1. `GET /health` — 探活
  2. `POST /spawn` — dev-only 一键拉起 opencode CLI
  3. `POST /session-link` — 把 opencode session_id 落到业务侧 `opencode_sessions` 表
- 消息 / 事件流全走 opencode 直连，**后端不做转发**

### 3.2 专家团 = opencode agent 配置管理

**核心公式**：**1 个专家 = 1 个 `~/.config/opencode/agent/{slug}.md` 文件**

- 数据表：`experts`（`backend/app/db/models/expert_model.py`）
- 创建/编辑专家：`ExpertService._write_agent_md(e)` 生成对应 md 文件
- 启动 = 写文件；关闭 = 删文件
- 对话工作台切专家 → `store.currentAgent = expert.slug` → 请求 body.agent = slug
- opencode 收到 body.agent 直接走原生路由（用户可 `@slug` 触发）

⚠️ **opencode 不热加载 agent 目录**！新增/编辑专家后需 `Ctrl+C` 重启 `opencode serve`
才能被 `GET /agent` 发现。UI 已提示（未加载的专家有橙色小圆点）。

### 3.3 前端 → 后端 → opencode 三方数据流

```
浏览器 ── HTTP + SSE ─→ opencode:4096          (session/message/event/agent)
   │
   └── HTTP ─→ FastAPI:8000                    (登录 / 专家团 / 感知/认知/决策/执行 / 用户)
                    │
                    └── SQLAlchemy → MySQL     (ontomind 数据库)
```

## 4 · 数据库真相（新 agent 最容易踩坑的地方）

### 4.1 Alembic 是坏的

- `backend/alembic/versions/` 空的，无迁移文件
- `backend/alembic/env.py` 里 import 路径错误（`from app.models import *` 实际是 `app.db.models`）
- **别跑 `alembic upgrade head`** — 会 ImportError

### 4.2 建表靠 `create_all`

- `backend/app/main.py` 启动时 `Base.metadata.create_all(bind=engine)` 自动建缺失的表
- **新增 ORM Model 必做 3 件事**：
  1. 建 `app/db/models/xxx_model.py`
  2. 到 `app/db/models/__init__.py` `from app.db.models.xxx_model import Xxx` **必须**
  3. 到 `__all__` 加名字
- 忘了第 2 步 → `create_all` 找不到，表不建

### 4.3 `schema.sql` 是参考不是权威

- 位置 `backend/schema.sql`（约 260 行）
- 只手动维护了 9 张核心表；`agent_versions` / `agent_deployments` / `experts` 等**新表只靠 create_all**
- 用 `schema.sql` 初始化后仍要跑一次 `uvicorn` 让 create_all 补齐

### 4.4 完整重置数据库

```bash
mysql -uroot -e "DROP DATABASE IF EXISTS ontomind; CREATE DATABASE ontomind DEFAULT CHARACTER SET utf8mb4;"
cd backend && source .venv/bin/activate
python3 -c "import app.db.models; from app.db.session import engine, Base; Base.metadata.create_all(engine); print('OK')"
# 然后重跑 §1.6 的用户 + 专家 seed
```

### 4.5 现有 54 张表按域分组（心里有数）

- **用户 & 权限**：users / roles / user_roles / credentials / audit_logs
- **LLM**：llm_configs
- **数据源 + 元数据**：data_sources / meta_tables / meta_columns / meta_profiles
- **本体**：onto_versions / onto_classes / onto_properties / onto_relationships / onto_constraints
- **资源管理（T44）**：compute_nodes / node_connections / agent_containers / agents /
  skills / mcps / node_containers / container_agents / container_skills / container_mcps /
  agent_skills / agent_mcps / instances / mcp_configs / discovery_runs / discovery_items
- **Agent Looper（T34）**：agent_looper_configs / agent_looper_versions / agent_looper_test_runs
- **Agent 版本 & 部署**：agent_versions / agent_deployments
- **数据平台**：dp_data_sources / dp_sql_queries / dp_query_history / dp_chat_sessions / dp_chat_messages
- **知识库**：kb_libraries / kb_data_assets / kb_code_repos / kb_documents / kb_experiences / kb_tags
  （+ 遗留 knowledge_bases / knowledge_chunks / knowledge_documents / source_code_repos / source_code_files）
- **OpenCode 集成**：opencode_sessions
- **专家团**：experts

## 5 · 三层架构硬约束（改代码前必读）

- 分层：`api/v1/*.py` → `services/*_service.py` → `db/repositories/*_repo.py` → `db/models/*_model.py`
- **事务边界只在 Service 层**。Service 里用 `self.db.flush()` + `self.db.commit()`。
  ⚠️ **不要用 `with self.db.begin()`** — 与 FastAPI `get_db` 的默认事务冲突（本仓已踩坑）
- Repository 只能 `self.db.flush()`，不允许 commit / begin / 业务逻辑
- API 层禁止直接查 DB / 写业务 / 抓业务异常；抛 `BusinessException(msg, code, status_code)`
- 命名：`XxxService` / `XxxRepository` / `Xxx`(Model) / `XxxCreate|Update|Response`(Schema)
- 统一响应 `{"code": "SUCCESS", "message": ..., "data": ...}`
- 新增 API 路由要在 `app/api/v1/router.py` 显式 `include_router`

## 6 · 前端硬约束

- **antd v6**（Form/Table/Drawer API 与 v5 有差别）
- **lint 用 `oxlint`**：`npm run lint`；**不要装 eslint**
- axios 拦截器已配 JWT + 401 → `/login`
- 状态管理走 Zustand（一个模块一个 store）
- Vite 环境变量前缀 `VITE_`

## 7 · 常见问题快速排查

| 症状 | 排查 |
|---|---|
| 前端登录后白屏 | 检查 `SECRET_KEY` / `FERNET_KEY` 是否配好；后端启动无报错 |
| `/workspace` 显示"opencode server 未启动" | 终端 1 起 `opencode serve --port 4096 --cors http://localhost:5173` |
| 发消息 CORS 报错 | `opencode serve` 必须带 `--cors http://localhost:5173` |
| 选专家后 `@agent` 不生效 | opencode 只在启动时扫 `~/.config/opencode/agent/`，重启 opencode CLI |
| `create_all` 未建新表 | 检查 `db/models/__init__.py` 是否 import 了新 model |
| 保存出现 "transaction already begun" | Service 里用了 `with self.db.begin()` → 改为 `flush()` + `commit()` |
| 前端 tsc 一堆存量错误 | AgentStudioPage / AgentLooperWizard / AgentDetailPage 等老代码问题，非本次 wave 触发 |

## 8 · 手上活的接头协议

- 每次做完非平凡改动，**必须追加**一段 `AGENT_LOG.md` 记录：
  ```markdown
  ## [YYYY-MM-DD] 标题

  ### 目标
  ### 决策
  ### 新增文件
  ### 修改文件
  ### 删除文件
  ### API 端点
  ### 数据库
  ### 验证
  ```
- 已有 900+ 行例子在 `AGENT_LOG.md` 里，照抄格式
- Commit message 起头用一个中/英文动词（`feat:` `fix:` `refactor:` `docs:` `test:` 均可）

## 9 · 参考文档索引

| 文件 | 用途 |
|---|---|
| `AGENTS.md` | 项目最新规范速查（本文的精简版） |
| `AGENT_LOG.md` | 历史变更时间线（做啥前先扫一遍） |
| `backend/STANDARDS.md` | 分层 / 事务 / 命名 完整规范 |
| `backend/DESIGN_STANDARDS.md` | API 设计 + DB 命名 + 错误码 |
| `frontend/STANDARDS.md` | 前端类型 / service / store 规范 |
| `docs/project-plan.md` | 五层路线图 |
| `frontend/src/features/opencode/vendor/VENDOR_META.md` | opencode 组件 vendor 计划 |

## 10 · 一键冒烟脚本（新机器最后一步）

```bash
# 后端 API 探活
curl -s http://localhost:8000/api/docs > /dev/null && echo "backend OK"

# opencode 探活
curl -s http://127.0.0.1:4096/global/health | grep -q healthy && echo "opencode OK"

# 数据库探活
mysql -uroot ontomind -e "SELECT COUNT(*) AS user_count FROM users; SELECT COUNT(*) AS expert_count FROM experts;"

# 登录并列专家
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["data"]["access_token"])')
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/experts | python3 -m json.tool | head -20
```

**任一步失败 → 回到对应章节排查。全部通过 → 可以开工。**
