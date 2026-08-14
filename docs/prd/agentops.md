# AgentOps PRD — Agent 编排层

> **状态**: 核心功能已实现

## 1. 概述

AgentOps 是 OntoMind 的核心差异化层，涵盖 Agent 的完整生命周期：设计 → 编排 → 发布 → 运行 → 监控 → 优化。

## 2. 已实现功能

| 功能 | 页面 | 说明 |
|------|------|------|
| **Agent 设计器** | `/agentops/agents` | 可视化 Agent 设计（权限矩阵 + 实时 .md 预览 + 版本回滚） |
| **Skill 设计器** | `/agentops/skills` | 可视化 Skill 设计（多文件树 + 双平面导出 + 合规 SKILL.md） |
| **编排方案（Loop）** | `/agentops/bundles` | Agent Loop 编排（SVG 拓扑 + 委派授权 + 任务权限矩阵） |
| **发布中心** | `/agentops/deploy` | Bundle → Docker 容器五阶段发布（解析→校验→写入→重启→回读校验） |
| **Skill 平台** | `/agentops/skill-platform` | 治理元数据 + 参数契约 + 三形态执行面板 + 版本/导出/克隆 |

## 3. 待建设功能

| 功能 | 说明 |
|------|------|
| **Trace Explorer** | Agent 决策链路追踪（工具调用、推理步骤、Token 消耗） |
| **MCP 工具目录** | 工具注册、版本管理、权限控制、API→MCP 自动转换 |
| **多 Agent 工作流** | 管道式/层级式/对等式协作编排画布 |
| **Agent 运行时监控** | 实时状态、健康检查、自动恢复 |
| **Agent 评估** | 端到端测试、回归测试、效果评估 |
| **Agent 分级** | 实验→测试→灰度→正式 生命周期管理 |

## 4. 技术栈

- 后端：FastAPI + SQLAlchemy 2.0 + Docker SDK
- 前端：React 19 + antd v6 + Zustand
- 数据库：MySQL 8（22 张表，含 agent_templates / skill_templates / agent_bundles / deployments 等）
- 运行时：OpenCode（Agent 加载 + 执行 + Skill 发现）