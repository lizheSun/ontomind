"""ORM models.

当前 22 张表：

| 表 | 用途 | 引入 |
|---|---|---|
| users / roles / user_roles / audit_logs | 用户与审计 | 早期 |
| compute_nodes | 算力节点（SSH / 本地 Docker） | 2026-08-03 |
| container_services | 容器内常驻服务登记（AIDE 源） | 2026-08-04 |
| agent_templates / agent_template_versions | Agent 模板 + 版本快照 | 2026-08-04 |
| skill_templates / skill_files | Skill 模板 + 多文件（渐进披露） | 2026-08-04 |
| agent_bundles / bundle_members | 编排方案（Agent Loop）+ 成员 | 2026-08-04 |
| deployments | Bundle → 容器 的发布记录 | 2026-08-04 |
| skill_meta / skill_params | Skill 治理元数据 + 参数契约 | 2026-08-04 |
| skill_exec_prompt / skill_exec_api / skill_exec_flow_nodes | 三形态执行配置 | 2026-08-04 |
| skill_policy | 容错熔断 + 安全权限策略 | 2026-08-04 |
| skill_versions / skill_audit_logs / skill_invocations | 版本快照 / 审计 / 调用 Trace | 2026-08-04 |

⚠️ 新增 Model 必须在此 import 并加入 __all__，否则 create_all 发现不到、不建表。
"""

from app.db.models.user_model import User
from app.db.models.role_model import Role, UserRole
from app.db.models.audit_log_model import AuditLog
from app.db.models.compute_node_model import ComputeNode
from app.db.models.container_service_model import (
    ContainerService,
    ServiceKind,
    ServiceStatus,
)
from app.db.models.agent_template_model import (
    AgentTemplate,
    AgentTemplateVersion,
    AgentMode,
    TemplateSource,
)
from app.db.models.skill_template_model import SkillTemplate, SkillFile
from app.db.models.agent_bundle_model import (
    AgentBundle,
    BundleMember,
    BundlePattern,
    MemberType,
    MemberRole,
    SkillPermission,
)
from app.db.models.deployment_model import Deployment, DeployScope, DeployStatus
from app.db.models.skill_platform_model import (
    SkillMeta,
    SkillParam,
    SkillExecPrompt,
    SkillExecApi,
    SkillExecFlowNode,
    SkillPolicy,
    SkillVersion,
    SkillAuditLog,
    SkillInvocation,
    SkillKind,
    RiskLevel,
    Lifecycle,
    LIFECYCLE_TRANSITIONS,
    LIFECYCLE_GATED,
    ParamDirection,
    ParamSource,
    MaskRule,
    AuthType,
    FallbackMode,
    FlowNodeType,
    InvocationStatus,
)
from app.db.models.data_source_model import (
    DataSource,
    DataSourceType,
    DataSourceStatus,
)

__all__ = [
    # 用户与审计
    "User",
    "Role",
    "UserRole",
    "AuditLog",
    # 算力
    "ComputeNode",
    "ContainerService",
    "ServiceKind",
    "ServiceStatus",
    # Agent 工厂
    "AgentTemplate",
    "AgentTemplateVersion",
    "AgentMode",
    "TemplateSource",
    "SkillTemplate",
    "SkillFile",
    "AgentBundle",
    "BundleMember",
    "BundlePattern",
    "MemberType",
    "MemberRole",
    "SkillPermission",
    "Deployment",
    "DeployScope",
    "DeployStatus",
    # Skill 平台（治理平面）
    "SkillMeta",
    "SkillParam",
    "SkillExecPrompt",
    "SkillExecApi",
    "SkillExecFlowNode",
    "SkillPolicy",
    "SkillVersion",
    "SkillAuditLog",
    "SkillInvocation",
    "SkillKind",
    "RiskLevel",
    "Lifecycle",
    "LIFECYCLE_TRANSITIONS",
    "LIFECYCLE_GATED",
    "ParamDirection",
    "ParamSource",
    "MaskRule",
    "AuthType",
    "FallbackMode",
    "FlowNodeType",
    "InvocationStatus",
    # DataOps
    "DataSource",
    "DataSourceType",
    "DataSourceStatus",
]
