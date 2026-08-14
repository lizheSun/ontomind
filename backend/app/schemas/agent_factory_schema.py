"""Agent 工厂 Pydantic Schemas + 内置预设常量.

字段严格对齐 OpenCode 的 AgentConfig / SKILL.md frontmatter
（依据 https://opencode.ai/config.json 与官方文档，见 docs/PRD-agent-skill-platform.md）。

⚠️ 不要往 SKILL.md frontmatter 里加字段：OpenCode 只认
   name / description / license / compatibility / metadata，其余静默忽略。
"""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# OpenCode 权限系统元数据（校验器与前端共用的唯一真源）
# ---------------------------------------------------------------------------

# 15 个合法权限键。OpenCode 对未知键**静默忽略**，所以必须在平台层白名单校验。
PERMISSION_KEYS: List[str] = [
    "read", "edit", "glob", "grep", "list", "bash", "task", "external_directory",
    "todowrite", "question", "webfetch", "websearch", "lsp", "doom_loop", "skill",
]

# 其中 10 个支持 glob→动作 细粒度映射；其余 5 个只接受简写动作。
GLOB_CAPABLE_KEYS: List[str] = [
    "read", "edit", "glob", "grep", "list", "bash", "task", "external_directory",
    "lsp", "skill",
]

PERMISSION_ACTIONS: List[str] = ["allow", "ask", "deny"]

# 每个权限键管哪些工具 —— 前端做成 tooltip，避免用户猜
PERMISSION_KEY_META: List[Dict[str, Any]] = [
    {"key": "read", "gates": "read", "glob": True, "label": "读取文件"},
    {"key": "edit", "gates": "write, edit, apply_patch", "glob": True, "label": "修改文件"},
    {"key": "glob", "gates": "glob", "glob": True, "label": "按模式找文件"},
    {"key": "grep", "gates": "grep", "glob": True, "label": "全文搜索"},
    {"key": "list", "gates": "list", "glob": True, "label": "列目录"},
    {"key": "bash", "gates": "bash", "glob": True, "label": "执行命令"},
    {"key": "task", "gates": "task", "glob": True, "label": "调用 subagent（Loop 核心旋钮）"},
    {
        "key": "external_directory",
        "gates": "任何读写工作区外文件的工具",
        "glob": True,
        "label": "访问工作区外目录",
    },
    {"key": "todowrite", "gates": "todowrite, todoread", "glob": False, "label": "待办清单"},
    {"key": "question", "gates": "question", "glob": False, "label": "向用户提问"},
    {"key": "webfetch", "gates": "webfetch", "glob": False, "label": "抓取网页"},
    {"key": "websearch", "gates": "websearch", "glob": False, "label": "联网搜索"},
    {"key": "lsp", "gates": "lsp", "glob": True, "label": "语言服务"},
    {"key": "doom_loop", "gates": "卡死时的恢复提示", "glob": False, "label": "死循环恢复"},
    {"key": "skill", "gates": "skill", "glob": True, "label": "加载 Skill"},
]

AGENT_NAME_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
SKILL_NAME_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"


# ---------------------------------------------------------------------------
# 校验结果
# ---------------------------------------------------------------------------

class ValidationIssue(BaseModel):
    """一条校验问题。

    - `error`   阻断保存/发布
    - `warning` 提示「这样写可能不是你想要的」
    - `info`    纯说明（如「本方案用内置 primary 作主对话」），完全合法
    """

    level: Literal["error", "warning", "info"]
    field: str = Field(..., description="出问题的字段路径，如 permission.bash")
    message: str = Field(..., description="可执行的中文说明：错在哪、应该怎么写")


class ValidationResult(BaseModel):
    ok: bool = Field(..., description="无 error 即为 true（warning / info 不阻断）")
    issues: List[ValidationIssue] = []


# ---------------------------------------------------------------------------
# Agent 模板
# ---------------------------------------------------------------------------

class AgentTemplateBase(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=64, pattern=AGENT_NAME_PATTERN,
        description="agent 名（=落盘文件名），小写字母数字与单连字符",
    )
    display_name: Optional[str] = Field(None, max_length=128)
    description: str = Field(
        ..., min_length=1, max_length=1024,
        description="用途描述 —— primary 据此决定何时委派该 subagent，务必具体",
    )
    mode: Literal["subagent", "primary", "all"] = "subagent"
    model: Optional[str] = Field(None, max_length=128, description="provider/model-id，空=继承")
    prompt: Optional[str] = Field(None, description="system prompt（Markdown）")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    steps: Optional[int] = Field(None, ge=1, le=1000, description="迭代上限")
    permission_json: Optional[Dict[str, Any]] = Field(
        None, description="权限配置，键必须来自 PERMISSION_KEYS",
    )
    options_json: Optional[Dict[str, Any]] = Field(None, description="透传给 provider")
    color: Optional[str] = Field(None, max_length=32)
    hidden: bool = False
    disable: bool = False
    category: Optional[str] = Field(None, max_length=64)


class AgentTemplateCreate(AgentTemplateBase):
    pass


class AgentTemplateUpdate(BaseModel):
    """全部可选；name 不允许改（它是落盘文件名，改名等于换 agent）。"""

    display_name: Optional[str] = Field(None, max_length=128)
    description: Optional[str] = Field(None, min_length=1, max_length=1024)
    mode: Optional[Literal["subagent", "primary", "all"]] = None
    model: Optional[str] = Field(None, max_length=128)
    prompt: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    steps: Optional[int] = Field(None, ge=1, le=1000)
    permission_json: Optional[Dict[str, Any]] = None
    options_json: Optional[Dict[str, Any]] = None
    color: Optional[str] = Field(None, max_length=32)
    hidden: Optional[bool] = None
    disable: Optional[bool] = None
    category: Optional[str] = Field(None, max_length=64)


class AgentTemplateResponse(AgentTemplateBase):
    id: int
    is_builtin_preset: bool = False
    source: str = "platform"
    current_version: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgentVersionResponse(BaseModel):
    id: int
    agent_template_id: int
    version: int
    snapshot_json: Dict[str, Any]
    change_note: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VersionCreateRequest(BaseModel):
    change_note: Optional[str] = Field(None, max_length=512, description="本次变更说明")


class RollbackRequest(BaseModel):
    version: int = Field(..., ge=1, description="回滚到哪个版本")


# ---------------------------------------------------------------------------
# Skill 模板
# ---------------------------------------------------------------------------

class SkillFileItem(BaseModel):
    """Skill 附属文件（references/*.md、scripts/*.py 等）。"""

    rel_path: str = Field(
        ..., min_length=1, max_length=512,
        description="相对 skill 目录的路径，如 references/detail.md；禁止 .. 与绝对路径",
    )
    content: str = Field("", description="文件内容")
    is_executable: bool = Field(False, description="脚本类文件设 true，落盘给 0o755")


class SkillTemplateBase(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=64, pattern=SKILL_NAME_PATTERN,
        description="skill 名（=目录名），OpenCode 强制要求与目录同名",
    )
    description: str = Field(
        ..., min_length=1, max_length=1024,
        description="用途描述 —— 模型选择 skill 的唯一依据，OpenCode 限制 ≤1024 字符",
    )
    license: Optional[str] = Field(None, max_length=64, description="如 MIT")
    compatibility: Optional[str] = Field(None, max_length=128, description="如 opencode")
    metadata_json: Optional[Dict[str, str]] = Field(
        None, description="metadata，必须是 string→string",
    )
    body: Optional[str] = Field(None, description="SKILL.md 正文（frontmatter 之后）")
    display_name: Optional[str] = Field(None, max_length=128)
    category: Optional[str] = Field(None, max_length=64)


class SkillTemplateCreate(SkillTemplateBase):
    files: List[SkillFileItem] = Field(default_factory=list, description="附属文件")


class SkillTemplateUpdate(BaseModel):
    description: Optional[str] = Field(None, min_length=1, max_length=1024)
    license: Optional[str] = Field(None, max_length=64)
    compatibility: Optional[str] = Field(None, max_length=128)
    metadata_json: Optional[Dict[str, str]] = None
    body: Optional[str] = None
    display_name: Optional[str] = Field(None, max_length=128)
    category: Optional[str] = Field(None, max_length=64)
    files: Optional[List[SkillFileItem]] = Field(
        None, description="传入即整批替换；不传则保持原样",
    )


class SkillTemplateResponse(SkillTemplateBase):
    id: int
    files: List[SkillFileItem] = []
    is_builtin_preset: bool = False
    source: str = "platform"
    current_version: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Bundle（编排方案）
# ---------------------------------------------------------------------------

class BundleMemberItem(BaseModel):
    member_type: Literal["agent", "skill"]
    agent_template_id: Optional[int] = None
    skill_template_id: Optional[int] = None
    role: Literal["primary", "subagent", "skill"] = "subagent"
    skill_permission: Optional[Literal["allow", "ask", "deny"]] = None
    # 本方案内该 subagent 能否被 primary 委派。
    # 不写回 agent 模板 —— 否则一个方案的授权会污染共享该模板的其它方案。
    task_permission: Optional[Literal["allow", "ask", "deny"]] = Field(
        None, description="subagent 在本方案内的被委派权限；空=继承 agent 模板的 permission.task",
    )
    sort_order: int = 0


class BundleMemberResponse(BundleMemberItem):
    id: int
    # 冗余名称，前端展示与拓扑图用（避免 N+1 查询）
    member_name: Optional[str] = None
    member_description: Optional[str] = None
    member_mode: Optional[str] = None
    # ---- 权限溯源（让"隐性规则"变透明）----
    # 该成员**最终生效**的委派动作，以及它是哪儿来的
    effective_task: Optional[str] = Field(
        None, description="最终生效的委派动作: allow / ask / deny",
    )
    task_source: Optional[str] = Field(
        None,
        description="来源: bundle(本方案覆盖) / template(agent 模板 permission.task) / default(未配置默认 allow)",
    )
    task_source_detail: Optional[str] = Field(
        None, description="人类可读的溯源说明，如「orchestrator 模板规则 \"*\": deny 命中」",
    )

    class Config:
        from_attributes = True


class AgentBundleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="方案名")
    description: Optional[str] = Field(None, max_length=1024)
    pattern: Literal[
        "single", "plan-build", "orchestrator-workers",
        "research-loop", "review-loop", "pipeline", "custom",
    ] = "custom"
    default_agent: Optional[str] = Field(
        None, max_length=64,
        description="默认 primary agent；OpenCode 要求必须是 primary，否则 fallback 到 build",
    )
    subagent_depth: Optional[int] = Field(
        None, ge=0, le=3,
        description="subagent 嵌套深度：0=禁止派生 / 1=默认 / 2=允许再嵌一层",
    )
    global_permission_json: Optional[Dict[str, Any]] = Field(
        None, description="bundle 级全局 permission（如 skill 白名单）",
    )
    topology_json: Optional[Dict[str, Any]] = Field(None, description="拓扑布局（前端渲染）")


class AgentBundleCreate(AgentBundleBase):
    members: List[BundleMemberItem] = Field(default_factory=list)


class AgentBundleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = Field(None, max_length=1024)
    pattern: Optional[str] = None
    default_agent: Optional[str] = Field(None, max_length=64)
    subagent_depth: Optional[int] = Field(None, ge=0, le=3)
    global_permission_json: Optional[Dict[str, Any]] = None
    topology_json: Optional[Dict[str, Any]] = None
    members: Optional[List[BundleMemberItem]] = None


class AgentBundleResponse(AgentBundleBase):
    id: int
    members: List[BundleMemberResponse] = []
    is_builtin_preset: bool = False
    current_version: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 渲染预览
# ---------------------------------------------------------------------------

class RenderedArtifact(BaseModel):
    """一个待落盘产物。"""

    path: str = Field(..., description="相对目标目录的路径，如 agents/reviewer.md")
    content: str = Field(..., description="文件内容")
    sha256: str = Field(..., description="内容摘要（幂等与漂移检测用）")
    bytes: int = 0
    is_executable: bool = False


class PreviewResponse(BaseModel):
    artifacts: List[RenderedArtifact] = []
    validation: ValidationResult
    # 供人快速核对的目标目录树
    tree: List[str] = []


# ---------------------------------------------------------------------------
# 发布
# ---------------------------------------------------------------------------

class DeployRequest(BaseModel):
    node_id: int = Field(..., description="目标算力节点")
    container_id: str = Field(..., min_length=1, max_length=64, description="目标容器")
    scope: Literal["global", "project"] = Field(
        "global",
        description="global=/root/.config/opencode（该容器全局生效）；project=/workspace/.opencode",
    )
    # 实测结论：PATCH /config 不生效、写文件不热感知 → 必须重启才生效。
    # 重启会中断进行中的会话，所以要求前端显式确认。
    restart_confirmed: bool = Field(
        False,
        description="必须为 true：发布需重启容器内 opencode 服务，会中断进行中的会话",
    )
    prune: bool = Field(
        True, description="清理目标目录中本 bundle 之前发布但现已移除的产物（避免孤儿 agent）",
    )


class VerifyItem(BaseModel):
    """单个 agent/skill 的回读比对结果。"""

    kind: Literal["agent", "skill"]
    name: str
    match: bool
    expected: Optional[Dict[str, Any]] = None
    actual: Optional[Dict[str, Any]] = None
    detail: Optional[str] = None


class DeploymentResponse(BaseModel):
    id: int
    bundle_id: int
    bundle_name: str
    bundle_version: int
    node_id: int
    node_name: str
    container_id: str
    container_name: str
    scope: str
    target_dir: str
    status: str
    artifacts_json: Optional[Any] = None
    verify_json: Optional[Any] = None
    restart_used: bool = False
    error_detail: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 导入
# ---------------------------------------------------------------------------

class AgentImportRequest(BaseModel):
    """从 Markdown 文本反向导入 agent（可来自容器或本地文件）。"""

    content: str = Field(..., min_length=1, description="完整的 agent .md 文本")
    name: Optional[str] = Field(
        None, max_length=64,
        description="agent 名；不传则要求文本里能推断（通常来自文件名，故建议显式传）",
    )
    category: Optional[str] = Field(None, max_length=64)
    overwrite: bool = Field(False, description="同名时是否覆盖")


# ---------------------------------------------------------------------------
# 内置预设
# ---------------------------------------------------------------------------

# 8 个 Agent 预设。permission 均只用合法键，可直接作为用户学习范本。
AGENT_PRESETS: List[Dict[str, Any]] = [
    {
        "name": "code-reviewer",
        "display_name": "代码评审",
        "description": "审查代码的正确性、可维护性与潜在缺陷，只读不改。当需要 review 一段改动或一个模块时使用。",
        "mode": "subagent",
        "category": "review",
        "temperature": 0.1,
        "color": "#3b52af",
        "permission": {
            "edit": "deny",
            "bash": {"*": "ask", "git diff": "allow", "git log*": "allow", "git status*": "allow"},
            "read": "allow",
            "grep": "allow",
            "glob": "allow",
        },
        "prompt": """你是资深代码评审专家。只做分析，不修改任何文件。

评审维度（按重要性排序）：
1. **正确性** — 逻辑错误、边界条件、并发问题、错误处理缺失
2. **安全性** — 注入、越权、敏感信息泄露、依赖风险
3. **可维护性** — 命名、分层、重复代码、过度抽象
4. **性能** — N+1 查询、不必要的复制、热路径上的低效操作

输出要求：
- 按「文件:行号」定位每个问题
- 每条给出**为什么是问题**与**建议怎么改**
- 区分「必须修」与「建议改」
- 没有问题就明确说没问题，不要为了凑数硬找""",
    },
    {
        "name": "security-auditor",
        "display_name": "安全审计",
        "description": "识别安全漏洞与配置风险。当需要做安全审计、排查越权/注入/密钥泄露时使用。",
        "mode": "subagent",
        "category": "security",
        "temperature": 0.1,
        "color": "#a5361e",
        "permission": {
            "edit": "deny",
            "bash": {"*": "ask", "grep *": "allow", "git log*": "allow"},
            "read": "allow",
            "grep": "allow",
            "glob": "allow",
            "webfetch": "deny",
        },
        "prompt": """你是安全审计专家。只做识别与建议，不修改代码。

重点排查：
- **注入**：SQL / 命令 / 路径穿越 / 模板注入
- **认证授权**：越权访问、鉴权绕过、会话管理缺陷
- **敏感信息**：硬编码密钥、日志泄露、错误信息过度暴露
- **配置**：默认口令、过宽的 CORS / 权限、不安全的传输
- **依赖**：已知漏洞组件

每条发现给出：位置 / 风险等级（严重·高·中·低）/ 攻击场景 / 修复建议。
不要报「理论上可能但实际不可达」的问题，标注清楚可利用性。""",
    },
    {
        "name": "docs-writer",
        "display_name": "文档撰写",
        "description": "撰写与维护技术文档。当需要写 README、API 文档、架构说明或使用指南时使用。",
        "mode": "subagent",
        "category": "docs",
        "temperature": 0.3,
        "color": "#476a4b",
        "permission": {
            "edit": "allow",
            "read": "allow",
            "grep": "allow",
            "glob": "allow",
            "bash": "deny",
        },
        "prompt": """你是技术写作专家。产出清晰、准确、可执行的文档。

原则：
- **先说结论**，再讲细节
- 每个概念配**最小可运行示例**
- 用表格替代冗长罗列
- 明确写出前置条件与常见坑
- 不写「显然」「众所周知」这类省略推理的表述

结构：用途 → 快速开始 → 核心概念 → 详细用法 → 故障排查。""",
    },
    {
        "name": "debugger",
        "display_name": "缺陷排查",
        "description": "定位并诊断 bug 根因。当出现报错、行为异常、性能问题需要查根因时使用。",
        "mode": "subagent",
        "category": "debug",
        "temperature": 0.1,
        "color": "#a86e12",
        "permission": {
            "read": "allow",
            "grep": "allow",
            "glob": "allow",
            "bash": {"*": "ask", "git log*": "allow", "git diff*": "allow"},
            "edit": "ask",
        },
        "prompt": """你是缺陷排查专家。**先定位根因，再谈修复**。

方法：
1. 复现 — 明确触发条件与最小复现路径
2. 收集证据 — 日志、堆栈、状态快照；**用命令实测而不是猜**
3. 缩小范围 — 二分法定位到具体函数/行
4. 验证假设 — 每个假设都要有可证伪的检验
5. 根因说明 — 解释「为什么会这样」，不止「哪里错了」

禁止：
- 在没有证据前提出多个「可能原因」让用户自己试
- 只改表象不解决根因""",
    },
    {
        "name": "test-writer",
        "display_name": "测试编写",
        "description": "为现有代码编写单元与集成测试。当需要补测试、提高覆盖率或复现缺陷时使用。",
        "mode": "subagent",
        "category": "test",
        "temperature": 0.2,
        "color": "#4A90D9",
        "permission": {
            "edit": "allow",
            "read": "allow",
            "grep": "allow",
            "glob": "allow",
            "bash": {"*": "ask", "pytest*": "allow", "npm test*": "allow", "npm run test*": "allow"},
        },
        "prompt": """你是测试工程专家。

原则：
- **先读现有测试**，沿用项目已有的框架、命名与断言风格
- 优先覆盖：边界条件、异常路径、并发/顺序敏感逻辑
- 一个测试只验一件事，失败信息要能直接定位问题
- 不为覆盖率写无意义的测试（如只调用不断言）
- 写完**实际运行一次**，确认通过再交付""",
    },
    {
        "name": "refactorer",
        "display_name": "重构改进",
        "description": "在不改变外部行为的前提下改进代码结构。当代码重复、职责混乱、难以扩展时使用。",
        "mode": "subagent",
        "category": "refactor",
        "temperature": 0.2,
        "color": "#605c56",
        "permission": {
            "edit": "allow",
            "read": "allow",
            "grep": "allow",
            "glob": "allow",
            "bash": {"*": "ask", "pytest*": "allow", "npm run*": "allow"},
        },
        "prompt": """你是重构专家。**行为不变是硬约束**。

流程：
1. 先确认有测试兜底；没有就先补关键路径测试
2. 小步改，每步保持可运行
3. 每步说明「消除了什么问题」，不做无收益的风格调整
4. 改完跑测试 + 类型检查，确认全绿

禁止：
- 借重构之名改变功能
- 一次性大规模重写
- 引入新抽象层却没有实际复用""",
    },
    {
        "name": "explorer",
        "display_name": "代码探索",
        "description": "快速理解陌生代码库结构与实现。当需要定位功能实现、梳理调用链或回答「代码在哪」时使用。",
        "mode": "subagent",
        "category": "explore",
        "temperature": 0.1,
        "color": "#8f8b84",
        "permission": {
            "read": "allow",
            "grep": "allow",
            "glob": "allow",
            "list": "allow",
            "edit": "deny",
            "bash": "deny",
        },
        "prompt": """你是代码探索专家。只读，绝不修改。

策略：
- 先看目录结构与入口文件建立全局印象
- 用 grep/glob 顺着符号找定义与引用
- 输出时给出「file_path:line_number」，让人能直接跳转
- 梳理调用链时画出层次，不要只罗列文件名

回答要简洁：先给结论（在哪、怎么实现），再按需展开。""",
    },
    {
        "name": "orchestrator",
        "display_name": "任务编排",
        "description": "把复杂任务拆解并分派给专职 subagent，汇总结果。当任务需要多个专业角色协作时使用。",
        "mode": "primary",
        "category": "orchestration",
        "temperature": 0.2,
        "steps": 40,
        "color": "#3b52af",
        "permission": {
            "read": "allow",
            "grep": "allow",
            "glob": "allow",
            "list": "allow",
            "todowrite": "allow",
            "edit": "ask",
            "bash": "ask",
            # Loop 核心：默认禁止调任何 subagent，只放开明确指定的
            # 注意 OpenCode 是「最后匹配胜出」，所以 "*" 必须写在最前
            "task": {"*": "deny", "code-reviewer": "allow", "explorer": "allow", "test-writer": "allow"},
        },
        "prompt": """你是任务编排者。你的价值在于**拆解与调度**，而不是自己动手做全部。

流程：
1. **拆解** — 把任务分成可独立完成、边界清晰的子任务，用 todowrite 记录
2. **分派** — 依据每个 subagent 的专长选择合适的执行者；可并行的就并行发起
3. **汇总** — 收集结果，交叉验证矛盾之处
4. **收敛** — 给出整合后的结论与后续建议

原则：
- 探索类交给 explorer，评审交给 code-reviewer，补测试交给 test-writer
- 自己只做「拆解、判断、汇总」，避免与 subagent 重复劳动
- 子任务描述要自包含：subagent 看不到你的上下文""",
    },
]


# 4 个 Skill 预设 —— 全部演示「渐进披露」：SKILL.md 只放高频规则，细节下沉 references/
SKILL_PRESETS: List[Dict[str, Any]] = [
    {
        "name": "git-release",
        "display_name": "Git 发布",
        "description": "生成一致的版本发布与变更日志。当准备打 tag 发版、需要从合并的 PR 生成 release notes 时使用。",
        "category": "workflow",
        "license": "MIT",
        "compatibility": "opencode",
        "metadata_json": {"audience": "maintainers", "workflow": "github"},
        "body": """# Git 发布

## 我做什么
- 从上一个 tag 至今的提交/PR 里生成 release notes
- 依据变更性质建议版本号（semver）
- 给出可直接粘贴执行的 `gh release create` 命令

## 何时用我
准备发布一个新版本时。若版本方案不明确，先问清楚再动手。

## 快速流程
1. `git describe --tags --abbrev=0` 找上一个 tag
2. `git log <tag>..HEAD --oneline` 收集变更
3. 按 feat/fix/breaking 归类
4. 建议版本号：有 breaking → major；有 feat → minor；只有 fix → patch
5. 生成 notes 并给出发布命令

> 变更日志的详细写法与分类规则见 [references/changelog-style.md](references/changelog-style.md)。
""",
        "files": [
            {
                "rel_path": "references/changelog-style.md",
                "content": """# 变更日志写法

## 分类
| 类别 | 含义 | semver 影响 |
|---|---|---|
| Breaking | 不兼容变更 | major |
| Features | 新功能 | minor |
| Fixes | 缺陷修复 | patch |
| Performance | 性能改进 | patch |
| Docs / Chore | 文档与杂项 | 不发版或 patch |

## 写作原则
- **写给使用者，不是写给自己**：说「能做什么了」而非「改了哪个函数」
- 每条一句话说完，需要细节就链到 PR
- Breaking 必须写**迁移方法**，不能只说「不兼容」

## 反例
- ❌ `refactor: 重构 UserService`（使用者不关心）
- ✅ `fix: 修复用户改邮箱后旧邮箱仍能登录的问题`
""",
                "is_executable": False,
            },
        ],
    },
    {
        "name": "api-contract",
        "display_name": "API 契约",
        "description": "设计与评审 HTTP API 契约。当需要新增接口、变更响应结构或评估兼容性影响时使用。",
        "category": "design",
        "license": "MIT",
        "compatibility": "opencode",
        "metadata_json": {"audience": "backend"},
        "body": """# API 契约

## 我做什么
- 设计符合项目既有风格的接口契约
- 评估变更的**兼容性影响**（哪些是 breaking）
- 检查错误码、分页、幂等性是否一致

## 何时用我
新增/修改 HTTP 接口时，尤其是已有客户端在用的接口。

## 核心检查项
1. 命名与既有接口一致（复数资源名、动词用 HTTP 方法表达）
2. 响应结构统一（本仓库：`{code, message, data}`）
3. 错误码可枚举、可执行
4. 写操作幂等或明确不幂等
5. 分页参数统一（skip/limit）

> 兼容性判定规则见 [references/compatibility.md](references/compatibility.md)。
""",
        "files": [
            {
                "rel_path": "references/compatibility.md",
                "content": """# 兼容性判定

## 安全变更（非 breaking）
- 新增可选请求字段
- 新增响应字段
- 新增端点
- 放宽校验（原来报错现在接受）

## Breaking 变更
- 删除或重命名任何**响应**字段
- 删除或重命名请求字段
- 必填字段新增
- 收紧校验（原来接受现在报错）
- 变更字段类型（含 `number` → `string`）
- 变更错误码或 HTTP 状态码语义
- 变更默认值导致行为不同

## 处理 Breaking 的正确做法
1. 新旧并存 —— 加新字段，旧字段标 deprecated 但继续返回
2. 给出迁移期与迁移指南
3. 真要删时先确认无调用方（搜代码 + 看访问日志）
""",
                "is_executable": False,
            },
        ],
    },
    {
        "name": "db-migration",
        "display_name": "数据库变更",
        "description": "安全地设计与执行数据库结构变更。当需要加表、加字段、改索引或做数据回填时使用。",
        "category": "database",
        "license": "MIT",
        "compatibility": "opencode",
        "metadata_json": {"audience": "backend", "risk": "high"},
        "body": """# 数据库变更

## 我做什么
- 设计向后兼容的表结构变更
- 识别锁表 / 长事务风险
- 给出可回滚方案

## 何时用我
任何涉及生产库结构或数据的变更。

## 铁律
1. **加字段必须可空或有默认值** —— 否则老代码写入会失败
2. **不要在一次上线里同时改代码和删字段** —— 分两次发（先停用，再删）
3. 大表加索引评估锁表时间；MySQL 8 支持 ONLINE DDL 但仍要看数据量
4. 数据回填**分批**，不要一条 UPDATE 扫全表
5. 变更前确认有备份或可回滚路径

> 常见变更的安全操作步骤见 [references/safe-patterns.md](references/safe-patterns.md)。
> 排查锁等待见 [references/lock-troubleshooting.md](references/lock-troubleshooting.md)。
""",
        "files": [
            {
                "rel_path": "references/safe-patterns.md",
                "content": """# 安全变更模式

## 加字段
```sql
ALTER TABLE t ADD COLUMN c VARCHAR(64) NULL COMMENT '...';
```
必须 NULL 或带 DEFAULT。

## 改字段类型（分三步，跨两次发布）
1. 加新字段 `c_new`
2. 双写（代码同时写 c 和 c_new）+ 回填历史数据
3. 切读到 c_new → 下次发布删 c

## 删字段（分两次发布）
1. 发布 A：代码停止读写该字段
2. 确认无残留调用后，发布 B：`ALTER TABLE t DROP COLUMN c`

## 加索引
```sql
ALTER TABLE t ADD INDEX idx_x (col), ALGORITHM=INPLACE, LOCK=NONE;
```
若不支持 LOCK=NONE，评估业务低峰执行。

## 数据回填
```sql
-- 分批，每批限量，避免长事务
UPDATE t SET c_new = c WHERE c_new IS NULL LIMIT 1000;
```
""",
                "is_executable": False,
            },
            {
                "rel_path": "references/lock-troubleshooting.md",
                "content": """# 锁等待排查

## 现象
DDL 卡住不动，状态 `Waiting for table metadata lock`。

## 定位持锁者
```sql
SELECT * FROM performance_schema.metadata_locks
WHERE OBJECT_NAME = '<table>';

SELECT id, user, command, time, state
FROM information_schema.processlist
WHERE command <> 'Sleep' OR time > 60;
```

## 处理
1. 找到长时间 `Sleep` 的孤儿连接（常见于被 kill 掉的进程遗留的未提交事务）
2. `KILL <id>` 释放锁
3. 重新执行 DDL

## 预防
- 应用层不要留长事务
- DDL 前先查 processlist
- 加 `lock_wait_timeout` 避免无限等待
""",
                "is_executable": False,
            },
        ],
    },
    {
        "name": "incident-report",
        "display_name": "故障报告",
        "description": "撰写故障复盘报告。当线上出现故障需要记录时间线、根因与改进项时使用。",
        "category": "ops",
        "license": "MIT",
        "compatibility": "opencode",
        "metadata_json": {"audience": "sre"},
        "body": """# 故障报告

## 我做什么
按标准结构产出故障复盘，重点在**根因**与**可验证的改进项**。

## 何时用我
线上故障处理完成后做复盘。

## 结构
1. **摘要** — 一句话说清影响面与时长
2. **时间线** — 精确到分钟，含发现/定位/缓解/恢复各节点
3. **影响** — 受影响用户量、请求量、数据是否受损
4. **根因** — 追到机制层面，不停在「某个配置错了」
5. **为什么没早发现** — 监控告警的缺口
6. **改进项** — 每条要有负责人与可验证的完成标准

## 原则
- **不指责个人**，指向流程与系统的缺陷
- 根因用「5 Why」追到底
- 改进项拒绝「加强意识」这类不可验证的表述

> 根因分析的深挖方法见 [references/rca-method.md](references/rca-method.md)。
""",
        "files": [
            {
                "rel_path": "references/rca-method.md",
                "content": """# 根因分析方法

## 5 Why 示例

> 现象：用户访问不到容器内服务

1. 为什么访问不到？→ 宿主端口转发落空
2. 为什么落空？→ 容器内进程没在转发目标地址上监听
3. 为什么没监听？→ 进程绑在 127.0.0.1
4. 为什么绑 loopback？→ 启动命令没带 `--hostname 0.0.0.0`，而 CLI 默认就是 127.0.0.1
5. 为什么没带？→ **平台的命令模板里没有这个参数** ← 真正的根因

改进项不是「以后记得加参数」（不可验证），
而是「命令模板默认带 `--hostname 0.0.0.0`，并加一个检测绑定地址的诊断命令」（可验证）。

## 判断是否追到根因
- 修掉它能**杜绝**同类问题再发生 → 是根因
- 修掉它只能避免这一次 → 还是表象，继续追

## 常见的「假根因」
- 「人员操作失误」→ 真根因是缺少校验或防呆设计
- 「配置错误」→ 真根因是配置没有校验、或默认值不安全
- 「监控没告警」→ 这是「为什么没早发现」，不是故障根因
""",
                "is_executable": False,
            },
        ],
    },
]


# 6 个 Loop 编排模式预设。members 用 agent name 引用（播种时解析成 id）。
BUNDLE_PRESETS: List[Dict[str, Any]] = [
    {
        "name": "单体全能",
        "pattern": "single",
        "description": "一个 primary agent 拥有全部权限，直接对话完成所有工作。最简单的形态，适合个人快速上手。",
        "default_agent": "build",
        "subagent_depth": 0,
        "agents": [],
        "skills": [],
        "topology_json": {"layout": "single"},
    },
    {
        "name": "先规划后执行",
        "pattern": "plan-build",
        "description": "两阶段：先用只读的 plan 分析并给方案，确认后切到 build 落地。防止未经确认就改代码。",
        "default_agent": "plan",
        "subagent_depth": 1,
        "agents": [("explorer", "subagent")],
        "skills": [],
        "topology_json": {"layout": "linear", "stages": ["plan", "build"]},
    },
    {
        "name": "编排者与专家团",
        "pattern": "orchestrator-workers",
        "description": "orchestrator 拆解任务并分派给 explorer/code-reviewer/test-writer 等专家，最后汇总。适合复杂多角色任务。",
        "default_agent": "orchestrator",
        "subagent_depth": 1,
        "agents": [
            ("orchestrator", "primary"),
            ("explorer", "subagent"),
            ("code-reviewer", "subagent"),
            ("test-writer", "subagent"),
        ],
        "skills": [("api-contract", "allow")],
        "topology_json": {"layout": "star", "center": "orchestrator"},
    },
    {
        "name": "深度调研环",
        "pattern": "research-loop",
        "description": "Plan → Search → Reflect → Synthesize 迭代范式，steps 放宽到 30 以支撑多轮补全。适合技术选型与竞品调研。",
        "default_agent": "orchestrator",
        "subagent_depth": 2,
        "agents": [("orchestrator", "primary"), ("explorer", "subagent")],
        "skills": [],
        "global_permission_json": {"websearch": "allow", "webfetch": "allow"},
        "topology_json": {"layout": "cycle", "phases": ["plan", "search", "reflect", "synthesize"]},
    },
    {
        "name": "实现与评审环",
        "pattern": "review-loop",
        "description": "build 实现后自动交给只读的 code-reviewer 评审，形成「写-审」闭环。适合对质量要求高的改动。",
        "default_agent": "build",
        "subagent_depth": 1,
        "agents": [("code-reviewer", "subagent"), ("security-auditor", "subagent")],
        "skills": [("api-contract", "allow")],
        "topology_json": {"layout": "cycle", "phases": ["implement", "review"]},
    },
    {
        "name": "顺序流水线",
        "pattern": "pipeline",
        "description": "按固定顺序串行执行：探索 → 实现 → 测试 → 评审。适合流程标准化的重复性任务。",
        "default_agent": "orchestrator",
        "subagent_depth": 1,
        "agents": [
            ("orchestrator", "primary"),
            ("explorer", "subagent"),
            ("test-writer", "subagent"),
            ("code-reviewer", "subagent"),
        ],
        "skills": [("db-migration", "allow"), ("git-release", "allow")],
        "topology_json": {"layout": "linear"},
    },
]
