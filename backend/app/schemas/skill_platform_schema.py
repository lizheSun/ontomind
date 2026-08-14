"""Skill 平台 Pydantic Schemas.

字段与 app/db/models/skill_platform_model.py 对应。

⚠️ 双平面约定（见 docs/PRD-skill-platform.md §2）：
本文件里绝大多数字段 OpenCode **不认识** —— 它们属于「治理平面」，
由平台 Skill 网关执行；导出到 SKILL.md 时只保留 5 个合法 frontmatter 字段，
治理摘要走 `metadata.omd_*`，全量配置走 `_ontomind/skill.manifest.json`。
"""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# 常量（前后端共用的唯一真源）
# ---------------------------------------------------------------------------

SKILL_KINDS = ["prompt", "api", "flow"]
RISK_LEVELS = ["low", "medium", "high"]
LIFECYCLES = ["draft", "testing", "canary", "released", "frozen", "archived"]
PARAM_SOURCES = ["dialog", "context", "system", "const"]
DATA_TYPES = ["string", "number", "integer", "boolean", "object", "array"]
MASK_RULES = ["none", "phone", "idcard", "bankcard", "email", "all", "custom"]
AUTH_TYPES = ["none", "bearer", "ak_sk", "api_key", "basic"]
FALLBACK_MODES = ["none", "static", "skill", "prompt"]
FLOW_NODE_TYPES = ["start", "skill", "branch", "loop", "end"]
ERROR_SCENES = ["param", "network", "service"]

SKILL_NAME_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"

# 前端展示用的元数据（附带说明，避免用户猜）
SKILL_KIND_META: List[Dict[str, str]] = [
    {
        "value": "prompt",
        "label": "Prompt 原生推理型",
        "desc": "靠系统提示词 + Few-shot 让模型直接推理，无外部调用。适合信息抽取、分类、改写。",
    },
    {
        "value": "api",
        "label": "API 工具调用型",
        "desc": "调用后端接口取数或执行动作。需配多环境地址与鉴权（密钥走配置中心）。",
    },
    {
        "value": "flow",
        "label": "可视化编排组合型",
        "desc": "按流程图编排多个原子 Skill，支持分支、循环、变量透传与失败跳转。",
    },
]

LIFECYCLE_META: List[Dict[str, str]] = [
    {"value": "draft", "label": "草稿", "desc": "自由编辑，不可被调用"},
    {"value": "testing", "label": "测试", "desc": "仅测试环境可调用"},
    {"value": "canary", "label": "灰度", "desc": "按比例/白名单放量观测"},
    {"value": "released", "label": "正式", "desc": "全量生效"},
    {"value": "frozen", "label": "冻结", "desc": "暂停调用，配置保留（线上出问题先冻结）"},
    {"value": "archived", "label": "归档", "desc": "终态，不可恢复"},
]


# ---------------------------------------------------------------------------
# 校验结果（复用 Agent 工厂的三级语义）
# ---------------------------------------------------------------------------

class SkillIssue(BaseModel):
    level: Literal["error", "warning", "info"]
    field: str
    message: str
    module: Optional[str] = Field(None, description="所属模块，便于前端定位到对应面板")


class SkillValidation(BaseModel):
    ok: bool = Field(..., description="无 error 即为 true")
    issues: List[SkillIssue] = []


# ---------------------------------------------------------------------------
# ① 元数据（模块 1）
# ---------------------------------------------------------------------------

class SkillMetaPayload(BaseModel):
    skill_kind: Literal["prompt", "api", "flow"] = "prompt"
    name_zh: Optional[str] = Field(None, max_length=128)
    name_en: Optional[str] = Field(None, max_length=128)
    biz_tags: List[str] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high"] = "low"
    owner: Optional[str] = Field(None, max_length=64)
    owner_email: Optional[str] = Field(None, max_length=128)
    biz_line: Optional[str] = Field(None, max_length=64)
    qps_limit: Optional[int] = Field(None, ge=1, le=100000, description="限流 QPS，空=不限")
    session_call_limit: Optional[int] = Field(
        None, ge=1, le=1000, description="单会话调用频次上限，空=不限",
    )
    lifecycle: Literal[
        "draft", "testing", "canary", "released", "frozen", "archived"
    ] = "draft"
    lifecycle_note: Optional[str] = Field(None, max_length=512)


class LifecycleChangeRequest(BaseModel):
    to: Literal["draft", "testing", "canary", "released", "frozen", "archived"]
    note: Optional[str] = Field(None, max_length=512, description="变更说明（进审计日志）")


# ---------------------------------------------------------------------------
# ② 参数契约（模块 2）
# ---------------------------------------------------------------------------

class SkillParamPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    title: Optional[str] = Field(None, max_length=128)
    description: Optional[str] = Field(None, max_length=512)
    data_type: Literal["string", "number", "integer", "boolean", "object", "array"] = "string"
    required: bool = False
    default_value: Optional[str] = Field(None, max_length=512)
    enum_values: List[str] = Field(default_factory=list)
    regex_pattern: Optional[str] = Field(None, max_length=512)
    min_val: Optional[float] = None
    max_val: Optional[float] = None

    # 入参
    source: Optional[Literal["dialog", "context", "system", "const"]] = "dialog"
    context_key: Optional[str] = Field(None, max_length=128)
    const_value: Optional[str] = Field(None, max_length=512)

    # 出参
    mask_rule: Literal[
        "none", "phone", "idcard", "bankcard", "email", "all", "custom"
    ] = "none"
    mask_pattern: Optional[str] = Field(None, max_length=512)
    filtered: bool = False
    write_to_context: bool = False
    context_write_key: Optional[str] = Field(None, max_length=128)

    sort_order: int = 0


class SkillParamResponse(SkillParamPayload):
    id: int
    direction: Literal["in", "out"]

    class Config:
        from_attributes = True


class SkillParamsUpdate(BaseModel):
    """整批替换某个方向的参数。"""

    direction: Literal["in", "out"]
    params: List[SkillParamPayload] = Field(default_factory=list)


class ParamDebugRequest(BaseModel):
    """在线调试入参样例（模块 2）—— 只做 Schema 校验，不真正执行。"""

    sample_json: Dict[str, Any] = Field(default_factory=dict)


class ParamDebugFieldResult(BaseModel):
    name: str
    ok: bool
    value: Optional[Any] = None
    message: Optional[str] = None


class ParamDebugResult(BaseModel):
    ok: bool
    fields: List[ParamDebugFieldResult] = []
    json_schema: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# ③ 执行配置（模块 3）
# ---------------------------------------------------------------------------

class FewShot(BaseModel):
    input: str = ""
    output: str = ""


class ExecPromptPayload(BaseModel):
    system_prompt: Optional[str] = None
    few_shots: List[FewShot] = Field(default_factory=list)
    output_constraint: Optional[str] = None
    output_format: Literal["text", "json", "markdown"] = "text"
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=200000)


class ParamMappingItem(BaseModel):
    param: str = Field(..., description="入参名")
    location: Literal["query", "body", "header", "path"] = "body"
    field: str = Field(..., description="目标字段名")


class ExecApiPayload(BaseModel):
    http_method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = "POST"
    # 多环境隔离（需求明确）
    url_test: Optional[str] = Field(None, max_length=1024)
    url_staging: Optional[str] = Field(None, max_length=1024)
    url_prod: Optional[str] = Field(None, max_length=1024)

    headers: Dict[str, str] = Field(default_factory=dict, description="静态请求头（禁含密钥）")
    auth_type: Literal["none", "bearer", "ak_sk", "api_key", "basic"] = "none"
    # ⚠️ 约束 5：只能是配置中心引用键，明文密钥会被校验器拦截
    secret_ref: Optional[str] = Field(
        None, max_length=256,
        description="配置中心引用键，如 cc://skill/<name>/aksk；严禁明文密钥",
    )
    param_mappings: List[ParamMappingItem] = Field(default_factory=list)
    timeout_ms: int = Field(5000, ge=100, le=120000)
    retry_times: int = Field(0, ge=0, le=5)
    retry_backoff_ms: int = Field(200, ge=0, le=10000)
    success_path: Optional[str] = Field(None, max_length=256)
    success_value: Optional[str] = Field(None, max_length=64)
    data_path: Optional[str] = Field(None, max_length=256)


class FlowNodePayload(BaseModel):
    node_key: str = Field(..., min_length=1, max_length=64)
    node_type: Literal["start", "skill", "branch", "loop", "end"]
    label: Optional[str] = Field(None, max_length=128)
    ref_skill_id: Optional[int] = None
    condition_expr: Optional[str] = Field(None, max_length=512)
    loop_config: Optional[Dict[str, Any]] = None
    var_mappings: Dict[str, str] = Field(default_factory=dict)
    next_keys: List[str] = Field(default_factory=list)
    on_fail_next: Optional[str] = Field(None, max_length=64)
    pos_x: Optional[float] = None
    pos_y: Optional[float] = None
    sort_order: int = 0


class FlowNodeResponse(FlowNodePayload):
    id: int
    ref_skill_name: Optional[str] = None
    ref_skill_lifecycle: Optional[str] = None

    class Config:
        from_attributes = True


class ExecFlowPayload(BaseModel):
    nodes: List[FlowNodePayload] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# ④+⑤ 治理策略（模块 4、5）
# ---------------------------------------------------------------------------

class ErrorMapItem(BaseModel):
    match: str = Field(..., description="匹配的错误码或关键词")
    scene: Literal["param", "network", "service"] = "service"
    user_msg: str = Field(..., description="给用户的友好话术")
    suggest: Optional[str] = Field(None, description="建议动作")


class SkillPolicyPayload(BaseModel):
    # 模块 4
    timeout_ms: Optional[int] = Field(None, ge=100, le=120000)
    retry_times: Optional[int] = Field(None, ge=0, le=5)
    circuit_threshold: Optional[int] = Field(
        None, ge=1, le=100, description="窗口内失败率阈值（百分比）",
    )
    circuit_window_sec: Optional[int] = Field(60, ge=10, le=3600)
    circuit_min_calls: Optional[int] = Field(10, ge=1, le=10000)
    circuit_cooldown_sec: Optional[int] = Field(30, ge=5, le=3600)
    fallback_mode: Literal["none", "static", "skill", "prompt"] = "none"
    fallback_payload: Optional[str] = None
    error_maps: List[ErrorMapItem] = Field(default_factory=list)

    # 模块 5
    allowed_agents: List[str] = Field(default_factory=list)
    allowed_roles: List[str] = Field(default_factory=list)
    require_confirm: bool = False
    confirm_prompt: Optional[str] = Field(None, max_length=512)
    account_whitelist: List[str] = Field(default_factory=list)
    account_blacklist: List[str] = Field(default_factory=list)
    ctx_read_keys: List[str] = Field(default_factory=list)
    ctx_write_keys: List[str] = Field(default_factory=list)
    session_isolation: Literal["none", "session", "account", "tenant"] = "session"


# ---------------------------------------------------------------------------
# 聚合视图（设计器一次拿全）
# ---------------------------------------------------------------------------

class SkillFullResponse(BaseModel):
    """Skill 全量配置 —— 设计器一次请求拿到三段所需的所有数据。"""

    # 定义主体（复用 skill_templates）
    id: int
    name: str
    description: str
    license: Optional[str] = None
    compatibility: Optional[str] = None
    metadata_json: Optional[Dict[str, str]] = None
    body: Optional[str] = None
    display_name: Optional[str] = None
    category: Optional[str] = None
    files: List[Dict[str, Any]] = []
    current_version: int = 1
    is_builtin_preset: bool = False

    # 治理平面
    meta: SkillMetaPayload = Field(default_factory=SkillMetaPayload)
    params_in: List[SkillParamResponse] = []
    params_out: List[SkillParamResponse] = []
    exec_prompt: Optional[ExecPromptPayload] = None
    exec_api: Optional[ExecApiPayload] = None
    exec_flow: Optional[ExecFlowPayload] = None
    policy: Optional[SkillPolicyPayload] = Field(default=None)

    validation: Optional[SkillValidation] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SkillListItem(BaseModel):
    """列表项 —— 只带列表需要的字段，避免拖慢。"""

    id: int
    name: str
    description: str
    display_name: Optional[str] = None
    skill_kind: str = "prompt"
    risk_level: str = "low"
    lifecycle: str = "draft"
    biz_line: Optional[str] = None
    owner: Optional[str] = None
    current_version: int = 1
    file_count: int = 0
    param_in_count: int = 0
    param_out_count: int = 0
    is_builtin_preset: bool = False
    updated_at: Optional[datetime] = None


class SkillCreateRequest(BaseModel):
    """新建 Skill（定义 + 元数据一步到位）。"""

    name: str = Field(
        ..., min_length=1, max_length=64, pattern=SKILL_NAME_PATTERN,
        description="kebab-case，= 落盘目录名（约束 3）",
    )
    description: str = Field(..., min_length=1, max_length=1024)
    display_name: Optional[str] = Field(None, max_length=128)
    category: Optional[str] = Field(None, max_length=64)
    license: Optional[str] = Field("MIT", max_length=64)
    compatibility: Optional[str] = Field("opencode", max_length=128)
    body: Optional[str] = None
    meta: SkillMetaPayload = Field(default_factory=SkillMetaPayload)


class SkillUpdateRequest(BaseModel):
    """更新（各段独立可选，前端按段保存）。"""

    description: Optional[str] = Field(None, min_length=1, max_length=1024)
    display_name: Optional[str] = Field(None, max_length=128)
    category: Optional[str] = Field(None, max_length=64)
    license: Optional[str] = Field(None, max_length=64)
    compatibility: Optional[str] = Field(None, max_length=128)
    metadata_json: Optional[Dict[str, str]] = None
    body: Optional[str] = None
    files: Optional[List[Dict[str, Any]]] = None

    meta: Optional[SkillMetaPayload] = None
    exec_prompt: Optional[ExecPromptPayload] = None
    exec_api: Optional[ExecApiPayload] = None
    exec_flow: Optional[ExecFlowPayload] = None
    policy: Optional[SkillPolicyPayload] = None


# ---------------------------------------------------------------------------
# 导出（约束 1、2、非功能 3）
# ---------------------------------------------------------------------------

class SkillExportRequest(BaseModel):
    scope: Literal["project", "global"] = Field(
        "project",
        description="project → .opencode/skills/<name>/；global → ~/.config/opencode/skills/<name>/",
    )
    include_manifest: bool = Field(
        True, description="是否附带 _ontomind/skill.manifest.json（治理全量配置）",
    )


class ExportedFile(BaseModel):
    path: str
    content: str
    sha256: str
    bytes: int = 0
    is_executable: bool = False
    plane: Literal["data", "control"] = Field(
        "data", description="data=OpenCode 执行平面 / control=平台治理平面",
    )


class SkillExportResponse(BaseModel):
    skill_name: str
    scope: str
    files: List[ExportedFile] = []
    tree: List[str] = []
    validation: SkillValidation
    # 明确告知哪些治理字段没有进 SKILL.md（避免用户误以为已生效）
    control_plane_note: str = ""


# ---------------------------------------------------------------------------
# 版本与审计（模块 6）
# ---------------------------------------------------------------------------

class CanaryConfig(BaseModel):
    mode: Literal["percent", "whitelist"] = "percent"
    percent: int = Field(10, ge=1, le=100)
    accounts: List[str] = Field(default_factory=list)


class SkillVersionCreate(BaseModel):
    change_note: Optional[str] = Field(None, max_length=512)
    canary: Optional[CanaryConfig] = None


class SkillVersionResponse(BaseModel):
    id: int
    skill_template_id: int
    version: int
    change_note: Optional[str] = None
    lifecycle_at_snapshot: Optional[str] = None
    canary_json: Optional[Dict[str, Any]] = None
    created_by_name: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SkillAuditResponse(BaseModel):
    id: int
    skill_name: str
    action: str
    field_path: Optional[str] = None
    summary: Optional[str] = None
    operator_name: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
