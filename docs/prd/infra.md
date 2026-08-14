# Infra PRD — 基础设施层

> **状态**: 部分已实现（算力管理 + AIDE）

## 1. 概述

基础设施层是 OntoMind 的**运行底座**，管理算力资源、Docker 容器、容器内服务、交互终端、以及 AIDE 嵌入环境。

## 2. 已实现功能

| 功能 | 页面 | 说明 |
|------|------|------|
| **算力节点管理** | `/infra/compute` | 节点（本地/SSH/Docker API）的 CRUD + 测试连接 |
| **Docker 容器管理** | `/infra/compute` | 容器创建（预设/结构化配置）/ 启停 / 删除 / 修改配置（stop→rm→recreate） |
| **容器服务登记** | `/infra/compute` | 容器内 opencode web/serve 的服务状态（MySQL 持久化 + 四步探测） |
| **容器控制台** | `/infra/compute` | xterm.js 交互终端（自动探测 shell + 自动连接） |
| **快速命令** | `/infra/compute` | 容器内执行命令（sync/async + 7 个模板） |
| **镜像管理** | `/infra/compute` | 镜像列表 + 拉取 |
| **AIDE** | `/infra/aide` | opencode Web UI 的 iframe 嵌入（常驻不卸载） |

## 3. 待建设功能

| 功能 | 说明 |
|------|------|
| **存储资源管理** | 卷管理、持久化存储、数据备份 |
| **网络管理** | Docker 网络创建/删除、VLAN、跨节点通信 |
| **集群管理** | 多节点编排、资源调度、负载均衡 |
| **资源监控** | CPU/内存/磁盘/GPU 实时监控 + 告警 |
| **日志聚合** | 容器日志统一收集与检索 |

## 4. 技术栈

- 后端：FastAPI + SQLAlchemy 2.0 + Docker SDK + asyncssh
- 前端：React 19 + antd v6 + xterm.js + Zustand
- 数据库：MySQL 8（22 张表）
- 目标：本地 Docker 节点 + 远程 SSH 节点