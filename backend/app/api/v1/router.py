"""API v1 route aggregation.

模块清单（2026-08-03）：
- auth      认证（登录 / 注册 / me）
- users     用户管理（用户 / 角色 / 权限 / 审计）
- opencode  AIDE：opencode Web UI 探活 + 启停
- compute   算力管理：节点管理 + Docker 操作 + 容器终端 + 容器服务登记
- agent-factory  Agent 工厂：Agent/Skill 模板、Loop 编排、发布到容器

🗑️ 已删除的模块（勿再引用，老代码里见到即死代码）：

| 路由 | 删除时间 |
|---|---|
| `/api/v1/{perception, cognition, decision, execution}` | 2026-08-03 |
| `/api/v1/resources` | 2026-08-03 |
| `/api/v1/{agent-looper, agent-platform}` | 2026-08-03 |
| `/api/v1/opencode/{health, spawn, session-link}` | 2026-08-03 |
| `/api/v1/{experts, experts/skill-mcp}` | 2026-08-03 |
| `/api/v1/data-platform` | 2026-08-03 |
| `/api/v1/knowledge-base` | 2026-08-03 |
| `/api/v1/llm` | 2026-08-03 |
| `/api/v1/{projects, application}` | 更早 |
"""

from fastapi import APIRouter

from app.api.v1 import agent_factory, auth, compute, dataops, opencode, skill_platform, users

api_router = APIRouter()

# --- 认证 & 用户 ---
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])

# --- AIDE（opencode Web UI 嵌入）---
api_router.include_router(opencode.router, prefix="/opencode", tags=["AIDE / OpenCode"])

# --- 算力管理（节点 + Docker + 容器终端）---
api_router.include_router(compute.router, tags=["算力管理"])

# --- Agent 工厂（Agent/Skill 模板 + Loop 编排 + 发布到容器）---
api_router.include_router(agent_factory.router, tags=["Agent 工厂"])

# --- Skill 平台（可视化设计 & 统一管理）---
api_router.include_router(skill_platform.router, tags=["Skill 平台"])

# --- DataOps（数据源 / 元数据 / 样例）---
api_router.include_router(dataops.router, tags=["DataOps"])
