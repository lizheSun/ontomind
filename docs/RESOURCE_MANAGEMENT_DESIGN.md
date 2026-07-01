# 资源管理模块设计文档

## 概述

资源管理中心是 Agent 编排配置的核心模块，服务于感知/认知/决策/执行全链路自动化。

## 实体关系

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Instance │     │  Agent   │     │  Skill   │     │   MCP    │
│ (计算节点) │     │ (智能体)  │     │ (技能)   │     │ (工具)   │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                  │
     │        ┌───────┴────────┐       │                  │
     └───────→│  AgentRun      │←──────┘                  │
              │ (运行实例+日志)  │←─────────────────────────┘
              └────────────────┘
```

## 5 个核心实体

### 1. Instance — 计算节点
管理协议: SSH + Docker API
类型: physical / docker / k8s_pod
状态: online / offline / maintenance

### 2. Agent — 智能体定义
运行方式: docker / python / node / binary（混合）
类型: openclaw / opencode / harness / custom
关联: 可引用多个 Skill

### 3. Skill — 技能模块
全局共享，支持 Agent 管理页一键安装
类型: docker / mcp / script / api
初始化方式: Docker 镜像 或 安装命令

### 4. MCP — 工具/服务
从任意 HTTP API + LLM 推断自动生成 MCP 配置
支持: sse / stdio / http 三种协议
自动发现: URL + LLM 推断 parameters

### 5. AgentRun — 运行时
追踪 Agent 在 Instance 上的运行状态
日志: WebSocket 实时流式推送
状态: initializing / running / error / stopped
