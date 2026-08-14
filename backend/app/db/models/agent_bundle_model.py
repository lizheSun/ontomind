"""Agent Bundle（编排方案）ORM 模型 — Agent Loop 的载体.

为什么发布单元是 Bundle 而不是单个 Agent：

Agent Loop 的本质是「一组 agent + 一套全局旋钮」的**整体**：

    Primary Agent（主对话）
       ├─ permission.task  决定它能调哪些 subagent（glob，deny 会把该 subagent
       │                   从 Task 工具描述里整条移除，模型看不到就不会调）
       ├─ subagent_depth   全局旋钮，决定能嵌几层（0=禁止派生）
       └─ steps            单 agent 迭代上限

单独发布一个 subagent 而不带上调用方的 task 权限，会产生「装了但没人能调」
的半成品状态；单独改 subagent_depth 又可能让已有编排失效。
所以以 Bundle 为原子发布单元。
"""
import enum

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)

from app.db.models.base import BaseModel


class BundlePattern(str, enum.Enum):
    """内置 Loop 编排模式 —— 每个模式对应一套拓扑与旋钮预设。"""

    SINGLE = "single"                            # 单体：1 primary 全权限
    PLAN_BUILD = "plan-build"                    # 双阶段：plan(只读) → build(全开)
    ORCHESTRATOR_WORKERS = "orchestrator-workers"  # 编排：1 编排者 + N 专家
    RESEARCH_LOOP = "research-loop"              # 调研环：Plan→Search→Reflect→Synthesize
    REVIEW_LOOP = "review-loop"                  # 评审环：implementer + reviewer(只读)
    PIPELINE = "pipeline"                        # 流水线：按 sort_order 串行
    CUSTOM = "custom"                            # 自定义


class MemberType(str, enum.Enum):
    AGENT = "agent"
    SKILL = "skill"


class MemberRole(str, enum.Enum):
    PRIMARY = "primary"     # 主对话 agent
    SUBAGENT = "subagent"   # 被调 agent
    SKILL = "skill"         # skill 成员


class SkillPermission(str, enum.Enum):
    """该 skill 在此 bundle 中对 agent 的可见性。"""

    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


class AgentBundle(BaseModel):
    """编排方案（Agent Loop 模式）。"""

    __tablename__ = "agent_bundles"
    __table_args__ = {"comment": "Agent 编排方案表（Loop 模式，发布的原子单元）"}

    name = Column(String(128), nullable=False, unique=True, comment="方案名")
    description = Column(String(1024), nullable=True, comment="方案说明")
    pattern = Column(
        String(32), nullable=False, default=BundlePattern.CUSTOM.value,
        comment="编排模式: single/plan-build/orchestrator-workers/research-loop/review-loop/pipeline/custom",
    )

    # ---- 全局旋钮（落到容器内 opencode.jsonc）----
    default_agent = Column(
        String(64), nullable=True,
        comment="默认 primary agent；OpenCode 要求必须是 primary，否则 fallback 到 build",
    )
    subagent_depth = Column(
        Integer, nullable=True,
        comment="subagent 嵌套深度：0=禁止派生 / 1=默认 / 2=允许再嵌一层",
    )
    global_permission_json = Column(
        JSON, nullable=True, comment="bundle 级全局 permission（如 skill 的 glob 白名单）",
    )

    # ---- 可视化 ----
    topology_json = Column(JSON, nullable=True, comment="拓扑布局（前端 SVG 渲染用）")

    # ---- 平台治理 ----
    is_builtin_preset = Column(
        Boolean, nullable=False, default=False, index=True, comment="内置预设（不可删除）",
    )
    current_version = Column(Integer, nullable=False, default=1, comment="当前版本号")
    created_by_user_id = Column(Integer, nullable=True, comment="创建人")


class BundleMember(BaseModel):
    """Bundle 成员（agent 或 skill）。"""

    __tablename__ = "bundle_members"
    __table_args__ = (
        # 同一 bundle 内同一个 agent/skill 只能出现一次
        UniqueConstraint(
            "bundle_id", "member_type", "agent_template_id", "skill_template_id",
            name="uq_bundle_member",
        ),
        {"comment": "Bundle 成员表"},
    )

    bundle_id = Column(
        Integer,
        ForeignKey("agent_bundles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属 bundle",
    )
    member_type = Column(String(16), nullable=False, comment="成员类型: agent / skill")

    # 二者互斥：member_type=agent 时用前者，=skill 时用后者
    agent_template_id = Column(
        Integer,
        ForeignKey("agent_templates.id", ondelete="CASCADE"),
        nullable=True,
        comment="agent 模板（member_type=agent）",
    )
    skill_template_id = Column(
        Integer,
        ForeignKey("skill_templates.id", ondelete="CASCADE"),
        nullable=True,
        comment="skill 模板（member_type=skill）",
    )

    role = Column(
        String(16), nullable=False, default=MemberRole.SUBAGENT.value,
        comment="角色: primary / subagent / skill",
    )
    skill_permission = Column(
        String(8), nullable=True,
        comment="skill 成员的可见性: allow / ask / deny",
    )
    # ---- 方案内的委派授权（关键设计）----
    # OpenCode 把 task 规则放在 agent 定义里，但它的**语义是方案级**的：
    # 「在这个编排里，谁能调谁」。如果直接改 agent 模板，
    # A 方案的授权会污染共享同一模板的 B 方案（实际踩过这个坑：
    # 在一个方案里授权 docs-writer，另一个没有该成员的方案就报「规则不会生效」）。
    #
    # 所以这里为**每个 subagent 成员**记录「本方案是否允许被调用」，
    # 发布时由渲染器按 bundle 合成 permission.task 写进产物，绝不回写模板。
    task_permission = Column(
        String(8), nullable=True,
        comment="subagent 成员在本方案内的被委派权限: allow / ask / deny；空=继承模板",
    )
    sort_order = Column(
        Integer, nullable=False, default=0,
        comment="排序（pipeline 模式下决定串行顺序）",
    )
