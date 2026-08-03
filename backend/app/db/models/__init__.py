"""ORM models.

当前只剩 4 张表（2026-08-03 深度精简后）：
- users       用户
- roles       角色
- user_roles  用户-角色关联
- audit_logs  审计日志

🗑️ 已删除的 model（2026-08-03 分两批清理）：

**第一批**（五层业务域 + resources + agent-looper/platform）：
- 感知层：DataSource / MetaTable / MetaColumn / MetaProfile
- 认知层：OntologyVersion / OntologyClass / OntologyProperty
          / OntologyRelationship / OntologyConstraint
- 资源管理：Instance / Agent / Credential
- T44 平台：ComputeNode / AgentContainer / NodeContainer / ContainerAgent
            / ContainerSkill / ContainerMCP / AgentSkill / AgentMCP
            / NodeConnection / DiscoveryRun / DiscoveryItem
- Agent Looper：AgentLooperConfig / AgentLooperVersion / AgentLooperTestRun
- Agent Platform：AgentVersion / AgentDeployment
- 对话工作台：OpencodeSession

**第二批**（专家团 + 算力调度 + 数据平台 + 知识库 + LLM）：
- 专家团：Expert / AgentRelation / Skill / MCP
- 算力调度：DockerHost / ScheduleTask / TaskRun / ContainerTemplate
- 数据平台：DpDataSource / DpSqlQuery / DpQueryHistory
            / DpChatSession / DpChatMessage
- 知识库：KbLibrary / KbDataAsset / KbCodeRepo / KbDocument / KbExperience / KbTag
- LLM 配置：LLMConfig
"""

from app.db.models.user_model import User
from app.db.models.role_model import Role, UserRole
from app.db.models.audit_log_model import AuditLog

__all__ = ["User", "Role", "UserRole", "AuditLog"]
