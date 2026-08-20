"""ORM models.

当前 **46** 张表：

| 表 | 用途 | 引入 |
|---|---|---|
| users / roles / user_roles / audit_logs | 用户与审计 | 早期 |
| compute_nodes / container_services | 算力节点 / 容器服务 | 2026-08 |
| agent_templates / agent_template_versions | Agent 模板 + 版本 | 2026-08-04 |
| skill_templates / skill_files | Skill 模板 + 文件 | 2026-08-04 |
| agent_bundles / bundle_members / deployments | 编排与发布 | 2026-08-04 |
| skill_meta / skill_params / skill_exec_* / skill_policy / skill_versions / skill_audit_logs / skill_invocations | Skill 平台治理 | 2026-08-04 |
| data_sources | DataOps 数据源 | 2026-08-13 |
| wiki_spaces / wiki_documents / wiki_document_versions | Wiki 知识库 | 2026-08-14 |
| meta_scan_jobs / meta_tables / meta_columns / glossary_terms / annotations | 元数据扫描与标注 | 2026-08-14 |
| meta_standards / meta_standard_versions / meta_column_standards / meta_column_standard_history / meta_database_briefs | 标准项与库概况 | 2026-08-14 |
| platform_llm_settings | 平台 LLM 配置 | 2026-08-14 |
| ontologies / ontology_*（9） | 本体建模 / CQ / 版本 | 2026-08-14 |

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
from app.db.models.wiki_model import (
    WikiSpace,
    WikiDocument,
    WikiDocumentVersion,
    WikiSourceType,
    WikiDocStatus,
)
from app.db.models.meta_model import (
    MetaScanJob,
    MetaTable,
    MetaColumn,
    GlossaryTerm,
    Annotation,
    MetaStandard,
    MetaStandardVersion,
    MetaColumnStandard,
    MetaColumnStandardHistory,
    MetaDatabaseBrief,
    PlatformLlmSetting,
    ScanStatus,
    JobKind,
    AnnotationTargetType,
    AnnotationLabelKind,
    AnnotationSource,
    AnnotationStatus,
    GlossarySource,
    MetaStandardStatus,
    MetaBindStatus,
    MetaBindSource,
)
from app.db.models.ontology_model import (
    Ontology,
    OntologyBuildJob,
    OntologyObjectType,
    OntologyProperty,
    OntologyLinkType,
    OntologyMapping,
    OntologyMetric,
    OntologyCQ,
    OntologyVersion,
    OntologyJobStatus,
    OntologyBuildPhase,
    OntologyElementSource,
    OntologyElementStatus,
    OntologyMappingElementType,
    OntologyCQVerifyStatus,
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
    # Wiki
    "WikiSpace",
    "WikiDocument",
    "WikiDocumentVersion",
    "WikiSourceType",
    "WikiDocStatus",
    # Metadata / Annotation
    "MetaScanJob",
    "MetaTable",
    "MetaColumn",
    "GlossaryTerm",
    "Annotation",
    "MetaStandard",
    "MetaStandardVersion",
    "MetaColumnStandard",
    "MetaColumnStandardHistory",
    "MetaDatabaseBrief",
    "PlatformLlmSetting",
    "ScanStatus",
    "JobKind",
    "AnnotationTargetType",
    "AnnotationLabelKind",
    "AnnotationSource",
    "AnnotationStatus",
    "GlossarySource",
    "MetaStandardStatus",
    "MetaBindStatus",
    "MetaBindSource",
    # Ontology
    "Ontology",
    "OntologyBuildJob",
    "OntologyObjectType",
    "OntologyProperty",
    "OntologyLinkType",
    "OntologyMapping",
    "OntologyMetric",
    "OntologyCQ",
    "OntologyVersion",
    "OntologyJobStatus",
    "OntologyBuildPhase",
    "OntologyElementSource",
    "OntologyElementStatus",
    "OntologyMappingElementType",
    "OntologyCQVerifyStatus",
]
