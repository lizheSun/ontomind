# OntoMind — AI-XOps 工业级平台总体 PRD

> **版本**: v1.0 | **日期**: 2026-08-04 | **项目**: OntoMind

---

## 1. 平台定位

OntoMind 是一个 **AI-XOps 工业级生产平台**，将 AI 全生命周期的开发、部署、运维、治理统一到一个平台中。

### 1.1 核心差异化

| 维度 | 传统平台 | OntoMind |
|------|---------|----------|
| 覆盖范围 | 单领域（如仅 MLOps） | CodeOps + DataOps + ModelOps + AgentOps + GovOps 五域融合 |
| 数据血缘 | 数据→数据 | 数据→特征→模型→Agent→应用 跨域血缘 |
| AI 深度 | 辅助工具 | AI Agent 深度参与全流程，人类从执行者变为审核者 |
| 治理 | 事后审计 | 内置安全护栏 + 实时合规 + 成本归因 + 统一策略 |

### 1.2 五域架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         GovOps 统一治理层                        │
│  资产目录 · 跨域血缘 · 安全合规 · 成本归因 · 审计 · 策略         │
├─────────────────────────────────────────────────────────────────┤
│            │            │            │            │            │
│   CodeOps  │  DataOps   │  ModelOps  │  AgentOps  │   Infra    │
│   软件开发  │  数据开发  │  模型开发  │  Agent 编排 │  基础设施  │
│            │            │            │            │            │
│  · 编码工作台│ · 资产目录 │ · 实验管理  │ · Agent 管理│ · 算力资源 │
│  · CI/CD   │ · 数据管线 │ · 模型注册  │ · Trace    │ · 容器管理 │
│  · 代码质量 │ · 数据质量 │ · 推理网关  │ · MCP 工具 │ · 网络存储 │
│  · 部署    │ · 血缘    │ · 监控评估  │ · 编排工作流│           │
│            │ · 特征存储 │ · Prompt   │            │           │
│            │ · RAG     │            │            │           │
│            │ · NL 查询 │            │            │           │
└────────────┴───────────┴────────────┴────────────┴───────────┘
```

---

## 2. 产品路线图

### Phase 1: 基础设施与骨架（当前）

| 模块 | 状态 | 说明 |
|------|------|------|
| AIDE | ✅ 已上线 | opencode Web UI iframe 嵌入 |
| 算力管理 | ✅ 已上线 | Docker 节点/容器/服务管理 |
| Agent 工厂 | ✅ 已上线 | Agent 设计/编排方案/发布到容器 |
| Skill 平台 | ✅ 已上线 | Skill 可视化设计/治理/合规导出 |
| 用户管理 | ✅ 已上线 | 用户/角色/权限 |

### Phase 2: 原型骨架（本次）

搭建 7 域导航骨架 + 占位页面，使整体产品架构可感知。

### Phase 3: 各域深度实现

参见各域独立 PRD。

---

## 3. 导航结构

```
/
├── overview/                    # 平台总览仪表盘
├── codeops/                     # 软件开发
│   ├── workspace/               # AI 编码工作台
│   ├── pipelines/               # CI/CD 流水线
│   ├── code-quality/            # 代码质量与安全
│   └── deployments/             # 部署管理
├── dataops/                     # 数据开发
│   ├── catalog/                 # 数据资产目录
│   ├── pipelines/               # 数据管线
│   ├── quality/                 # 数据质量
│   ├── lineage/                 # 数据血缘
│   ├── feature-store/           # 特征存储
│   ├── vector-store/            # 向量数据库/RAG
│   └── nl-query/                # 自然语言查询
├── modelops/                    # 模型开发
│   ├── experiments/             # 实验管理
│   ├── registry/                # 模型注册表
│   ├── prompt-hub/              # Prompt 管理中心
│   ├── gateway/                 # 推理网关
│   ├── evaluation/              # 评估中心
│   └── monitoring/              # 模型监控
├── agentops/                    # Agent 编排
│   ├── agents/                  # Agent 列表
│   ├── trace-explorer/          # Trace Explorer
│   ├── tools/                   # MCP 工具目录
│   ├── workflows/               # 多 Agent 工作流
│   └── runtime/                 # Agent 运行时状态
├── govops/                      # 统一治理
│   ├── catalog/                 # 统一资产目录
│   ├── lineage/                 # 跨域血缘全景
│   ├── security/                # 安全合规
│   ├── cost/                    # 成本归因
│   ├── audit/                   # 审计日志
│   └── policies/                # 策略管理
└── infra/                       # 基础设施
    ├── compute/                 # 算力资源（现有）
    ├── aide/                    # AIDE（现有）
    ├── storage/                 # 存储资源
    ├── network/                 # 网络
    └── clusters/                # 集群管理
```

---

## 4. 核心设计原则

1. **统一状态系统**：所有资产遵循同一状态定义（活跃/运行中/成功/失败/等待/审批中/警告/归档）
2. **Drill-Down 三层信息**：L1 概览 → L2 详情 → L3 深入
3. **跨域血缘**：数据→特征→模型→Agent→应用 全链路追踪
4. **AI Agent 深度参与**：每个域都有 AI Agent 辅助，人类从执行者变为审核者
5. **安全内置**：每个域都内置安全护栏，非事后补丁

---

## 5. PRD 文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| 总体 PRD | `docs/prd/overview.md` | 本文件 |
| infra PRD | `docs/prd/infra.md` | 基础设施层（现有功能） |
| codeops PRD | `docs/prd/codeops.md` | 软件开发流水线 |
| dataops PRD | `docs/prd/dataops.md` | 数据开发流水线 |
| modelops PRD | `docs/prd/modelops.md` | 模型开发流水线 |
| agentops PRD | `docs/prd/agentops.md` | Agent 编排层 |
| govops PRD | `docs/prd/govops.md` | 统一治理层 |