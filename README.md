# OntoMind — AI 驱动本体自动构建平台

构建一个以 **AI 驱动** 为核心的 **本体自动构建平台**，通过五层产品架构实现从数据感知到智能决策、再到业务执行与应用的完整闭环。

## 五层架构

| 层级 | 定位 | 核心能力 |
|------|------|---------|
| **感知层** | 信息入口 | 数据源连接器、文档解析、数据仓库、代码库接入 |
| **认知层** | 知识提炼 | 本体图谱构建、语义理解、知识推理 |
| **决策层** | 策略生成 | 特征挖掘、ML模型训练、规则策略引擎 |
| **执行层** | 策略下发 | 策略分发引擎、风控/营销系统适配器 |
| **应用层** | 用户产品 | AIbi 智能分析、数据可视化、策略工作台 |

## 技术栈

| 类别 | 技术选型 |
|------|---------|
| **前端** | React 19 + TypeScript + Vite + Ant Design 5 |
| **后端** | Python 3.12+ + FastAPI + SQLAlchemy 2.0 |
| **数据库** | MySQL 8.0 |
| **缓存** | Redis 7 |
| **AI/ML** | LangChain + OpenAI / 本地 LLM |
| **容器化** | Docker + Docker Compose |

## 快速开始

```bash
# 克隆项目
git clone git@github.com:lizheSun/ontomind.git
cd ontomind

# 启动所有服务（MySQL + Redis + 后端 + 前端）
docker compose up -d

# 或手动启动：
# 1. 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 2. 前端
cd frontend
npm install
npm run dev
```

- 后端 API 文档：http://localhost:8000/api/docs
- 前端页面：http://localhost:5173

## 项目结构

```
ontomind/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/             # 五层 API 路由
│   │   │   ├── auth.py         # 认证模块
│   │   │   ├── perception.py   # 感知层 API
│   │   │   ├── cognition.py    # 认知层 API
│   │   │   ├── decision.py     # 决策层 API
│   │   │   ├── execution.py    # 执行层 API
│   │   │   └── application.py  # 应用层 API
│   │   ├── core/               # 核心配置 & 安全
│   │   ├── db/                 # 数据库会话
│   │   ├── models/             # SQLAlchemy ORM 模型
│   │   ├── schemas/            # Pydantic 校验模型
│   │   ├── services/           # 业务逻辑层
│   │   └── main.py             # FastAPI 入口
│   ├── alembic/                # 数据库迁移
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── components/         # 组件
│   │   ├── pages/              # 五层页面 + 仪表盘 + 登录
│   │   ├── services/           # API 调用层
│   │   ├── stores/             # Zustand 状态管理
│   │   └── types/              # TypeScript 类型
│   └── Dockerfile
├── docs/
│   └── project-plan.md         # 详细项目计划
├── docker-compose.yml          # 本地开发环境
└── README.md
```

## 开发路线图

| 阶段 | 时间 | 内容 |
|------|------|------|
| Phase 1 | 1-3月 | 感知层 — 数据源连接器 & 文档管理 |
| Phase 2 | 3-6月 | 认知层 — 本体图谱构建 & 语义搜索 |
| Phase 3 | 6-9月 | 决策层 — 特征挖掘 & ML模型 & 策略引擎 |
| Phase 4 | 9-11月 | 执行层 — 策略下发 & 执行监控 |
| Phase 5 | 11-14月 | 应用层 — AIbi & 数据可视化 |

## License

MIT
