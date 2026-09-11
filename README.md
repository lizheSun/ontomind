# OntoMind

**面向 Agent 应用交付的设计态平台** —— 先把 Agent 造对、造齐、造可治理，再谈规模化运行。

未来 OntoMind 交付的是完整的 **Agent 应用**。通常一个 Agent 应用分为：

| 形态 | 解决什么 | 当前阶段 |
|------|----------|----------|
| **设计态** | 能力编排、流水线定制、知识体系建设、评测与治理 | **正在做** |
| **运行态** | 线上推理、会话编排、策略执行、业务系统对接 | 后续 |

本仓库当前重心是 **设计态**：让团队能定义 Agent、装配 Skill / 记忆 / 模型 / 运行环境，用流水线把数据和知识做成高密度表征，并为未来的风险 / 营销 / AIBI 应用层与 SDK 对接打地基。

---

## 愿景

> 让企业能 **设计、组装、校验** 可落地的 Agent 应用；让数据与业务知识自动沉淀为本体与图谱；让 AI 风险、AI 营销、AIBI 等应用层可插拔地接到真实业务系统。

一句话：**OntoMind 是 Agent 应用的「设计车间」**，不是一次性聊天 Demo。

---

## 产品目标（设计态四件事）

### 1. 能力管理 —— Agent 的「零件库」

统一管理构成 Agent 应用的核心资产：

| 资产 | 说明 |
|------|------|
| **Agent** | 角色、目标、工具边界、发布形态 |
| **Skill** | 可复用技能包（提示、工具、工作流片段） |
| **记忆** | 会话 / 长期记忆的设计与挂载（设计态配置） |
| **运行环境** | 节点、容器、「电脑」与服务（OpenCode / DSH 等） |
| **大模型** | 平台级 LLM 配置与路由（GovOps） |
| **Agent Core / Harness** | 会话运行时插件（OpenCode、DeepSeek Harness 等） |

对应落地入口：`/agentops/*`、`/infra/*`、`/chat`、`/board`、AIDE。

### 2. 设计态流水线 —— 把「造 Agent」变成可重复流程

按域提供可定制流水线，而不是散点脚本：

- **DataOps**：数仓接入 → 元数据采集 / 标注 → 智能数开 → Wiki 沉淀
- **ModelOps / 评测**（规划增强）：模型评测、Agent 评测、回归与对比
- **AgentOps**：Agent / Skill 设计 → 容器化发布 → 在会话与看板中验证

目标是：换一批业务、换一套标准，仍能走同一条「设计 → 校验 → 发布」路径。

### 3. 知识体系 —— 高密度业务信息表征

自动化 / 半自动化构建企业可消费的语义资产：

- **元数据标准与标注**：字段级标准项、别名、域（如消金种子标准）
- **本体（Ontology）**：类、属性、关系 —— 领域「字典 + 语法」
- **知识图谱 / 语义层**（持续增强）：实例与指标口径，供 Agent 接地与审计

对应落地入口：`/dataops/*`（仓库、智能数开、Wiki、元数据、本体）。

> 详述见 [`docs/ONTOLOGY_AIBI_DATA_AGENT.md`](./docs/ONTOLOGY_AIBI_DATA_AGENT.md)。

### 4. 应用层抽象（下一阶段）—— 场景化交付 + SDK

在设计态资产就绪后，应用层收敛为三大板块，并通过 **SDK** 嵌入具体场景与业务系统：

```text
┌─────────────────────────────────────────────────────────┐
│  AI 风险  ·  AI 营销  ·  AIBI（本体约束的 Data Agent）   │
│              ↑ SDK / API 接入业务系统                     │
├─────────────────────────────────────────────────────────┤
│  设计态平台：能力管理 · 流水线 · 知识体系 · 评测治理       │
└─────────────────────────────────────────────────────────┘
```

- **AI 风险**：授信、反欺诈、催收等 Agent 应用形态  
- **AI 营销**：获客、运营、触达策略类 Agent  
- **AIBI**：受本体约束的智能分析（问业务概念、取已治理口径、答案可追溯）

当前仓库已具备会话 / 看板 / DataOps / 本体等设计态底座；三大应用板块与对外 SDK 为明确演进方向。

---

## 当前已落地能力（对照代码）

| 能力域 | 用户入口 | 说明 |
|--------|----------|------|
| 总览壳层 | `/overview` | CodeOps / DataOps / ModelOps / AgentOps / GovOps / Infra |
| 统一会话 | `/chat` | Harness 插件：OpenCode（优先 serve SSE）/ DSH JSON-RPC |
| 任务看板 | `/board` | 卡片绑定会话；列 = 工作流，运行状态独立 |
| AIDE | `/infra/aide` | iframe 嵌 OpenCode 或 DeepSeek Harness Web |
| Agent / Skill | `/agentops/*` | Agent 工厂、Skill 平台 |
| 算力与电脑 | `/infra/*` | 节点、容器、服务发现与启停 |
| DataOps | `/dataops/*` | 数仓、智能数开、Wiki、元数据标准标注、本体建模 |
| 用户与治理 | `/users`、GovOps | 账号权限；平台 LLM 配置 |

后端路由域：`auth` / `users` / `opencode` / `harness` / `kanban` / `compute` / `agent-factory` / `skill-platform` / `dataops` / `wiki` / `metadata` / `ontology`。

更细的工程约定见 [`AGENTS.md`](./AGENTS.md)；新成员冷启动见 [`HANDOFF.md`](./HANDOFF.md)。

---

## 设计态 vs 运行态（边界）

| | 设计态（现在） | 运行态（未来） |
|--|----------------|----------------|
| 产物 | Agent / Skill / 本体 / 流水线定义 / 评测报告 | 线上 Agent 服务、策略执行、业务回调 |
| 使用者 | 平台研发、数开、算法、业务专家 | 业务系统、终端用户、调度系统 |
| 交互 | 工作台、会话验证、看板、AIDE | SDK、API、嵌入式 Agent、批处理 |
| 成功标准 | 可组装、可版本、可评测、可追溯 | 可扩缩、可观测、可降级、可合规审计 |

---

## 技术栈

| 类别 | 选型 |
|------|------|
| 后端 | Python 3.12+ · FastAPI · SQLAlchemy 2.0 · Pydantic v2 · MySQL 8 |
| 前端 | React 19 · TypeScript · Vite 8 · antd v6 · Zustand · React Router 7 |
| Agent 运行时（本地） | OpenCode CLI ≥ 1.18 · DeepSeek Harness（Web / JSON-RPC） |
| 主题 | Yao Agents CUI（Outfit · `#3371fc`） |

架构约束：`api/v1` → `services` → `repositories` → `models`；建表由 ORM `create_all`（无 Alembic）。

---

## 快速开始

```bash
git clone git@github.com:lizheSun/ontomind.git
cd ontomind

# 数据库
# CREATE DATABASE ontomind DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
# 配置 backend/.env（DB_* / SECRET_KEY）

# 终端 1 · OpenCode（会话 + AIDE 常用）
opencode serve --port 4096 --cors http://localhost:5173

# 终端 2 · 后端
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 终端 3 · 前端
cd frontend && npm install && npm run dev
```

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| API 文档 | http://localhost:8000/api/docs |
| OpenCode serve | http://127.0.0.1:4096 |

可选：`dsh --profile web` → DeepSeek Harness Web（默认 `http://127.0.0.1:3080/`，供 AIDE 嵌入）。

---

## 仓库结构（简图）

```text
ontomind/
├── backend/                 # FastAPI：harness / kanban / dataops / ontology / …
├── frontend/                # 工作台：chat / board / dataops / agentops / infra
├── docs/                    # 产品与领域文档（本体 × AIBI 等）
├── AGENTS.md                # 编码 Agent 速查（易踩坑）
├── HANDOFF.md               # 新成员 / 新 Agent 冷启动
├── AGENT_LOG.md             # 协作操作日志
└── README.md                # 本文件：定位与愿景
```

---

## 演进路线（摘要）

1. **现在**：夯实设计态 —— 能力资产、DataOps / 本体流水线、会话与看板验证环  
2. **接着**：评测体系（模型 / Agent）、知识图谱实例化、本体服务化查询  
3. **然后**：应用层三大板块（风险 / 营销 / AIBI）产品化  
4. **最终**：运行态与 **SDK** —— 把设计好的 Agent 应用接到具体业务系统  

---

## License

MIT
