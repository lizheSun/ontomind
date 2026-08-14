"""Skill 平台治理模型 —— 双平面架构的「治理平面」.

**为什么需要这套表**（关键背景，见 docs/PRD-skill-platform.md §1）：

实测（OpenCode v1.18.12 真机）确认 SKILL.md frontmatter **只认 5 个字段**：
name / description / license / compatibility / metadata。
往顶层塞 risk_level / qps_limit 这类治理字段，OpenCode 会**静默忽略** ——
skill 照样加载，但配置永远不生效。用户以为配了限流，实际没有。

所以采用双平面：
- **执行平面**：SKILL.md（仅 5 合法字段）+ references/ + scripts/ → OpenCode 直接加载
- **治理平面**：本文件这些表 → 由平台 Skill 网关在调用链上强制执行

治理摘要会以 `metadata.omd_*` 形式导出到 SKILL.md（实测 metadata 内容会保留），
全量配置导出到 `_ontomind/skill.manifest.json`（刻意放在 OpenCode 扫描路径之外）。
"""
import enum

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)

from app.db.models.base import BaseModel


# ---------------------------------------------------------------------------
# 枚举
# ---------------------------------------------------------------------------

class SkillKind(str, enum.Enum):
    """三类技能形态（约束 4）—— 决定执行配置面板与产出物差异。"""

    PROMPT = "prompt"   # Prompt 原生推理型
    API = "api"         # API 工具调用型
    FLOW = "flow"       # 可视化编排组合型


class RiskLevel(str, enum.Enum):
    LOW = "low"        # 低危查询
    MEDIUM = "medium"
    HIGH = "high"      # 高危资金操作


class Lifecycle(str, enum.Enum):
    """生命周期。合法迁移见 LIFECYCLE_TRANSITIONS。"""

    DRAFT = "draft"
    TESTING = "testing"
    CANARY = "canary"
    RELEASED = "released"
    FROZEN = "frozen"
    ARCHIVED = "archived"


# 合法状态迁移。非法路径在校验器里拦截、前端按钮置灰。
LIFECYCLE_TRANSITIONS: dict = {
    Lifecycle.DRAFT.value: [Lifecycle.TESTING.value, Lifecycle.ARCHIVED.value],
    Lifecycle.TESTING.value: [
        Lifecycle.DRAFT.value, Lifecycle.CANARY.value, Lifecycle.ARCHIVED.value,
    ],
    Lifecycle.CANARY.value: [
        Lifecycle.TESTING.value, Lifecycle.RELEASED.value, Lifecycle.ARCHIVED.value,
    ],
    Lifecycle.RELEASED.value: [Lifecycle.FROZEN.value, Lifecycle.ARCHIVED.value],
    # 冻结后可恢复上线（线上出问题先冻，修好再放）
    Lifecycle.FROZEN.value: [Lifecycle.RELEASED.value, Lifecycle.ARCHIVED.value],
    Lifecycle.ARCHIVED.value: [],   # 终态
}

# 需要「已配置完整」才能进入的状态（上线门禁）
LIFECYCLE_GATED = {Lifecycle.CANARY.value, Lifecycle.RELEASED.value}


class ParamDirection(str, enum.Enum):
    IN = "in"
    OUT = "out"


class ParamSource(str, enum.Enum):
    """入参来源（模块 2）。"""

    DIALOG = "dialog"     # 对话抽取
    CONTEXT = "context"   # 会话上下文变量
    SYSTEM = "system"     # 系统内置参数（如 user_id / trace_id）
    CONST = "const"       # 固定值


class MaskRule(str, enum.Enum):
    """脱敏规则（模块 2 + 5）。"""

    NONE = "none"
    PHONE = "phone"
    IDCARD = "idcard"
    BANKCARD = "bankcard"
    EMAIL = "email"
    ALL = "all"          # 整体替换为 ***
    CUSTOM = "custom"    # 用 mask_pattern 正则


class AuthType(str, enum.Enum):
    NONE = "none"
    BEARER = "bearer"
    AK_SK = "ak_sk"
    API_KEY = "api_key"
    BASIC = "basic"


class FallbackMode(str, enum.Enum):
    NONE = "none"
    STATIC = "static"   # 返回固定兜底内容
    SKILL = "skill"     # 转调另一个 skill
    PROMPT = "prompt"   # 交给模型自行处理并给出话术


class FlowNodeType(str, enum.Enum):
    START = "start"
    SKILL = "skill"
    BRANCH = "branch"   # if-else
    LOOP = "loop"
    END = "end"


class InvocationStatus(str, enum.Enum):
    """调用结果。三类异常（参数/网络/服务）+ 治理拦截。"""

    SUCCESS = "success"
    PARAM_ERROR = "param_error"       # 入参校验失败
    NETWORK_ERROR = "network_error"   # 网络异常
    SERVICE_ERROR = "service_error"   # 下游服务报错
    TIMEOUT = "timeout"
    CIRCUIT_OPEN = "circuit_open"     # 熔断中
    DENIED = "denied"                 # 鉴权/限流拒绝


# ---------------------------------------------------------------------------
# ① 治理元数据（模块 1）
# ---------------------------------------------------------------------------

class SkillMeta(BaseModel):
    """Skill 治理元数据（与 skill_templates 1:1）。

    这些字段 OpenCode 一个都不认，靠平台网关执行；
    摘要会以 metadata.omd_* 导出到 SKILL.md 供追溯。
    """

    __tablename__ = "skill_meta"
    __table_args__ = (
        UniqueConstraint("skill_template_id", name="uq_skill_meta_tpl"),
        {"comment": "Skill 治理元数据表（模块1）"},
    )

    skill_template_id = Column(
        Integer,
        ForeignKey("skill_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属 skill 定义",
    )

    # 形态（约束 4）—— 决定用哪个执行配置表
    skill_kind = Column(
        String(16), nullable=False, default=SkillKind.PROMPT.value,
        index=True, comment="形态: prompt / api / flow",
    )

    name_zh = Column(String(128), nullable=True, comment="中文名")
    name_en = Column(String(128), nullable=True, comment="英文名")
    biz_tags_json = Column(JSON, nullable=True, comment="业务标签数组")

    risk_level = Column(
        String(16), nullable=False, default=RiskLevel.LOW.value,
        index=True, comment="风险等级: low(低危查询) / medium / high(高危资金操作)",
    )
    owner = Column(String(64), nullable=True, comment="责任人")
    owner_email = Column(String(128), nullable=True, comment="责任人邮箱")
    biz_line = Column(String(64), nullable=True, index=True, comment="归属业务线")

    # 限流（由网关执行）
    qps_limit = Column(Integer, nullable=True, comment="限流 QPS，空=不限")
    session_call_limit = Column(
        Integer, nullable=True, comment="单会话调用频次上限，空=不限",
    )

    lifecycle = Column(
        String(16), nullable=False, default=Lifecycle.DRAFT.value,
        index=True, comment="生命周期: draft/testing/canary/released/frozen/archived",
    )
    lifecycle_note = Column(String(512), nullable=True, comment="最近一次状态变更说明")


# ---------------------------------------------------------------------------
# ② 参数契约（模块 2）
# ---------------------------------------------------------------------------

class SkillParam(BaseModel):
    """入参 / 出参字段定义。

    出参外壳固定为 {code, msg, data, session_vars}（需求指定），
    direction=out 的记录描述的是 `data` 内部结构。
    """

    __tablename__ = "skill_params"
    __table_args__ = (
        UniqueConstraint(
            "skill_template_id", "direction", "name", name="uq_skill_param",
        ),
        {"comment": "Skill 参数契约表（模块2）"},
    )

    skill_template_id = Column(
        Integer,
        ForeignKey("skill_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    direction = Column(String(8), nullable=False, comment="in / out")

    name = Column(String(64), nullable=False, comment="参数名（合法标识符）")
    title = Column(String(128), nullable=True, comment="展示名")
    description = Column(String(512), nullable=True, comment="说明（会进 JSON Schema）")
    data_type = Column(
        String(16), nullable=False, default="string",
        comment="string/number/integer/boolean/object/array",
    )
    required = Column(Boolean, nullable=False, default=False)
    default_value = Column(String(512), nullable=True, comment="默认值（字符串形式，按类型转换）")
    enum_json = Column(JSON, nullable=True, comment="枚举可选值数组")
    regex_pattern = Column(String(512), nullable=True, comment="正则校验（仅 string）")
    min_val = Column(Float, nullable=True, comment="最小值/最短长度")
    max_val = Column(Float, nullable=True, comment="最大值/最长长度")

    # 入参来源（模块 2）
    source = Column(
        String(16), nullable=True, default=ParamSource.DIALOG.value,
        comment="来源: dialog(对话抽取)/context(会话变量)/system(内置)/const",
    )
    context_key = Column(String(128), nullable=True, comment="source=context 时读的会话变量名")
    const_value = Column(String(512), nullable=True, comment="source=const 时的固定值")

    # 出参处理（模块 2 + 5）
    mask_rule = Column(
        String(16), nullable=False, default=MaskRule.NONE.value,
        comment="脱敏规则",
    )
    mask_pattern = Column(String(512), nullable=True, comment="custom 脱敏的正则")
    filtered = Column(
        Boolean, nullable=False, default=False,
        comment="是否过滤掉不返回给模型（敏感字段只落 Trace 不出参）",
    )
    write_to_context = Column(
        Boolean, nullable=False, default=False, comment="是否写回会话上下文",
    )
    context_write_key = Column(String(128), nullable=True, comment="写回的会话变量名")

    sort_order = Column(Integer, nullable=False, default=0)


# ---------------------------------------------------------------------------
# ③ 执行配置 —— 三形态各一张表（模块 3）
# ---------------------------------------------------------------------------

class SkillExecPrompt(BaseModel):
    """Prompt 原生推理型执行配置。"""

    __tablename__ = "skill_exec_prompt"
    __table_args__ = (
        UniqueConstraint("skill_template_id", name="uq_exec_prompt_tpl"),
        {"comment": "Prompt 推理型执行配置（模块3）"},
    )

    skill_template_id = Column(
        Integer, ForeignKey("skill_templates.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    system_prompt = Column(Text, nullable=True, comment="系统提示词")
    few_shots_json = Column(JSON, nullable=True, comment="[{input, output}] 示例")
    output_constraint = Column(Text, nullable=True, comment="输出约束规则")
    output_format = Column(
        String(16), nullable=False, default="text", comment="text/json/markdown",
    )
    temperature = Column(Float, nullable=True)
    max_tokens = Column(Integer, nullable=True)


class SkillExecApi(BaseModel):
    """API 工具调用型执行配置。

    ⚠️ 约束 5：**本表没有明文密钥列**。
    只存配置中心引用键 `secret_ref`（如 cc://skill/pay-query/aksk），
    校验器会拒绝任何疑似明文密钥的值。
    """

    __tablename__ = "skill_exec_api"
    __table_args__ = (
        UniqueConstraint("skill_template_id", name="uq_exec_api_tpl"),
        {"comment": "API 调用型执行配置（模块3）；密钥仅存配置中心引用键"},
    )

    skill_template_id = Column(
        Integer, ForeignKey("skill_templates.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    http_method = Column(String(8), nullable=False, default="POST")

    # 多环境隔离（需求明确要求）
    url_test = Column(String(1024), nullable=True, comment="测试环境地址")
    url_staging = Column(String(1024), nullable=True, comment="预发环境地址")
    url_prod = Column(String(1024), nullable=True, comment="生产环境地址")

    headers_json = Column(JSON, nullable=True, comment="静态请求头（禁含密钥）")
    auth_type = Column(
        String(16), nullable=False, default=AuthType.NONE.value,
        comment="none/bearer/ak_sk/api_key/basic",
    )
    secret_ref = Column(
        String(256), nullable=True,
        comment="配置中心引用键，如 cc://skill/<name>/aksk —— 禁止明文密钥",
    )

    param_mapping_json = Column(
        JSON, nullable=True, comment="入参→请求字段映射 {paramName: {in: query|body|header|path, field}}",
    )
    timeout_ms = Column(Integer, nullable=False, default=5000)
    retry_times = Column(Integer, nullable=False, default=0)
    retry_backoff_ms = Column(Integer, nullable=False, default=200)

    success_path = Column(String(256), nullable=True, comment="判定成功的 JSONPath，如 $.code")
    success_value = Column(String(64), nullable=True, comment="成功时该路径的期望值，如 0")
    data_path = Column(String(256), nullable=True, comment="业务数据 JSONPath，如 $.data")


class SkillExecFlowNode(BaseModel):
    """可视化编排组合型的流程节点。"""

    __tablename__ = "skill_exec_flow_nodes"
    __table_args__ = (
        UniqueConstraint("skill_template_id", "node_key", name="uq_flow_node"),
        {"comment": "编排型流程节点（模块3）"},
    )

    skill_template_id = Column(
        Integer, ForeignKey("skill_templates.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    node_key = Column(String(64), nullable=False, comment="节点唯一键（流程内）")
    node_type = Column(
        String(16), nullable=False, comment="start/skill/branch/loop/end",
    )
    label = Column(String(128), nullable=True, comment="节点显示名")

    # node_type=skill 时引用的原子 Skill
    ref_skill_id = Column(
        Integer, ForeignKey("skill_templates.id", ondelete="SET NULL"),
        nullable=True, comment="引用的原子 Skill",
    )
    condition_expr = Column(String(512), nullable=True, comment="branch 的判断表达式")
    loop_config_json = Column(
        JSON, nullable=True, comment="loop 配置 {over: varName, maxIter: 10}",
    )
    var_mapping_json = Column(
        JSON, nullable=True, comment="上下游变量透传映射 {targetParam: sourceExpr}",
    )
    next_keys_json = Column(JSON, nullable=True, comment="后继节点键数组（branch 可多个）")
    on_fail_next = Column(String(64), nullable=True, comment="失败跳转的节点键")

    pos_x = Column(Float, nullable=True, comment="画布坐标 X")
    pos_y = Column(Float, nullable=True, comment="画布坐标 Y")
    sort_order = Column(Integer, nullable=False, default=0)


# ---------------------------------------------------------------------------
# ④+⑤ 治理策略：容错熔断 + 安全权限（模块 4、5）
# ---------------------------------------------------------------------------

class SkillPolicy(BaseModel):
    """容错熔断 + 安全权限策略（与 skill_templates 1:1）。

    全部由平台 Skill 网关执行 —— OpenCode 不认识这些配置。
    """

    __tablename__ = "skill_policy"
    __table_args__ = (
        UniqueConstraint("skill_template_id", name="uq_skill_policy_tpl"),
        {"comment": "Skill 治理策略表（模块4 容错熔断 + 模块5 安全权限）"},
    )

    skill_template_id = Column(
        Integer, ForeignKey("skill_templates.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # ---- 模块 4：异常容错、熔断降级 ----
    timeout_ms = Column(Integer, nullable=True, comment="整体超时（覆盖执行配置）")
    retry_times = Column(Integer, nullable=True, comment="重试次数")
    circuit_threshold = Column(
        Integer, nullable=True, comment="熔断阈值：窗口内失败率百分比，如 50",
    )
    circuit_window_sec = Column(Integer, nullable=True, default=60, comment="统计窗口秒")
    circuit_min_calls = Column(
        Integer, nullable=True, default=10, comment="窗口内最小样本数（避免小样本误熔断）",
    )
    circuit_cooldown_sec = Column(Integer, nullable=True, default=30, comment="熔断冷却秒")

    fallback_mode = Column(
        String(16), nullable=False, default=FallbackMode.NONE.value,
        comment="降级方式: none/static/skill/prompt",
    )
    fallback_payload = Column(Text, nullable=True, comment="static 兜底内容 / skill 名 / prompt")
    # 错误码 → 用户友好话术；同时区分三类异常场景
    error_map_json = Column(
        JSON, nullable=True,
        comment="[{match, scene(param|network|service), user_msg, suggest}]",
    )

    # ---- 模块 5：安全权限与会话管控 ----
    allowed_agents_json = Column(JSON, nullable=True, comment="可调用的智能体名单（空=不限）")
    allowed_roles_json = Column(JSON, nullable=True, comment="可调用的业务角色（RBAC）")
    require_confirm = Column(
        Boolean, nullable=False, default=False, comment="高危技能二次确认开关",
    )
    confirm_prompt = Column(String(512), nullable=True, comment="二次确认话术")
    account_whitelist_json = Column(JSON, nullable=True, comment="账号白名单（非空=仅这些可调）")
    account_blacklist_json = Column(JSON, nullable=True, comment="账号黑名单")

    ctx_read_keys_json = Column(JSON, nullable=True, comment="允许读取的会话变量键")
    ctx_write_keys_json = Column(JSON, nullable=True, comment="允许写入的会话变量键")
    session_isolation = Column(
        String(16), nullable=False, default="session",
        comment="会话数据隔离级别: none/session/account/tenant",
    )


# ---------------------------------------------------------------------------
# ⑥ 版本与审计（模块 6）
# ---------------------------------------------------------------------------

class SkillVersion(BaseModel):
    """全配置快照 —— 支持一键回滚。

    存整份而非 diff：回滚必须绝对可靠，不能依赖 diff 重放的正确性。
    """

    __tablename__ = "skill_versions"
    __table_args__ = (
        UniqueConstraint("skill_template_id", "version", name="uq_skill_version"),
        {"comment": "Skill 全配置快照表（模块6）"},
    )

    skill_template_id = Column(
        Integer, ForeignKey("skill_templates.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    version = Column(Integer, nullable=False, comment="版本号（从 1 递增）")
    snapshot_json = Column(
        JSON, nullable=False, comment="全配置快照（定义+元数据+参数+执行+策略）",
    )
    change_note = Column(String(512), nullable=True)
    lifecycle_at_snapshot = Column(String(16), nullable=True, comment="快照时的生命周期")

    # 灰度放量（模块 6）
    canary_json = Column(
        JSON, nullable=True,
        comment="灰度配置 {mode: percent|whitelist, percent: 10, accounts: [...]}",
    )
    created_by_user_id = Column(Integer, nullable=True)
    created_by_name = Column(String(64), nullable=True)


class SkillAuditLog(BaseModel):
    """配置变更审计日志（模块 6，满足合规审计）。"""

    __tablename__ = "skill_audit_logs"
    __table_args__ = {"comment": "Skill 配置变更审计日志表（模块6）"}

    skill_template_id = Column(
        Integer, ForeignKey("skill_templates.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    skill_name = Column(String(64), nullable=False, comment="skill 名快照")
    action = Column(
        String(32), nullable=False, index=True,
        comment="create/update/lifecycle/snapshot/rollback/export/clone/delete",
    )
    field_path = Column(String(128), nullable=True, comment="变更字段路径，如 meta.qps_limit")
    before_json = Column(JSON, nullable=True)
    after_json = Column(JSON, nullable=True)
    summary = Column(String(512), nullable=True, comment="人类可读的变更摘要")

    operator_user_id = Column(Integer, nullable=True)
    operator_name = Column(String(64), nullable=True)
    operator_ip = Column(String(64), nullable=True)


# ---------------------------------------------------------------------------
# ⑦ 调用 Trace（模块 7）
# ---------------------------------------------------------------------------

class SkillInvocation(BaseModel):
    """单次调用的全链路 Trace（模块 7）。

    入参/出参落库前**必须先按 mask_rule 脱敏**，避免 Trace 成为泄露通道。
    """

    __tablename__ = "skill_invocations"
    __table_args__ = (
        UniqueConstraint("trace_id", name="uq_invocation_trace"),
        {"comment": "Skill 调用 Trace 表（模块7）"},
    )

    trace_id = Column(String(64), nullable=False, comment="全链路 trace id")
    skill_template_id = Column(
        Integer, ForeignKey("skill_templates.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    skill_name = Column(String(64), nullable=False, index=True)
    skill_version = Column(Integer, nullable=True)

    agent_name = Column(String(64), nullable=True, comment="调用方智能体")
    session_id = Column(String(128), nullable=True, index=True)
    account_id = Column(String(128), nullable=True, index=True)
    env = Column(String(16), nullable=True, comment="test/staging/prod")

    status = Column(
        String(24), nullable=False, index=True,
        comment="success/param_error/network_error/service_error/timeout/circuit_open/denied",
    )
    error_code = Column(String(64), nullable=True)
    error_msg = Column(String(1024), nullable=True)

    input_json = Column(JSON, nullable=True, comment="入参（已脱敏）")
    output_json = Column(JSON, nullable=True, comment="出参（已脱敏）")

    duration_ms = Column(Integer, nullable=True, index=True)
    retry_count = Column(Integer, nullable=False, default=0)
    fallback_used = Column(Boolean, nullable=False, default=False)
    is_canary = Column(Boolean, nullable=False, default=False, comment="是否灰度流量")
