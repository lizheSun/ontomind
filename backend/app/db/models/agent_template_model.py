"""Agent 工厂 ORM 模型 — Agent 模板 + 版本快照.

设计要点：
- `agent_templates` 是**设计态**：用户在平台里编辑的 agent 定义
- `agent_template_versions` 是**版本快照**：每次显式存版本时把整份配置 JSON 化留存，可回滚
- 字段命名严格对齐 OpenCode 的 AgentConfig（见 docs/PRD-agent-skill-platform.md §2.1），
  避免"平台字段"与"OpenCode 字段"两套语义打架

⚠️ 权限（permission_json）在写入前必须经 agent_validate_service 校验：
   OpenCode 对未知权限键是**静默忽略**的，写错了不会报错、只会不生效，事后极难排查。
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


class AgentMode(str, enum.Enum):
    """OpenCode agent 模式。"""

    SUBAGENT = "subagent"   # 只能被 primary 经 Task 调用 / @ 召唤
    PRIMARY = "primary"     # 可直接对话（Tab 切换）
    ALL = "all"             # 两者皆可（OpenCode 默认）


class TemplateSource(str, enum.Enum):
    """模板来源 —— 区分平台原创与外部导入，便于治理。"""

    PLATFORM = "platform"   # 平台内创建
    IMPORTED = "imported"   # 从容器/文件反向导入
    PRESET = "preset"       # 内置预设播种


class AgentTemplate(BaseModel):
    """Agent 模板（设计态）。"""

    __tablename__ = "agent_templates"
    __table_args__ = {"comment": "Agent 模板表（OpenCode agent 设计态）"}

    # ---- 身份 ----
    # name 即最终落盘的文件名（<name>.md），也是 OpenCode 里的 agent 标识
    name = Column(String(64), nullable=False, unique=True, comment="agent 名（=文件名，小写连字符）")
    display_name = Column(String(128), nullable=True, comment="展示名")
    # description 是 primary 决定「何时委派该 subagent」的唯一依据，语义上必填
    description = Column(String(1024), nullable=False, comment="用途描述（决定自动委派）")

    # ---- OpenCode AgentConfig 字段 ----
    mode = Column(
        String(16), nullable=False, default=AgentMode.SUBAGENT.value,
        comment="模式: subagent / primary / all",
    )
    model = Column(String(128), nullable=True, comment="provider/model-id，空=继承调用方")
    prompt = Column(Text, nullable=True, comment="system prompt（Markdown 正文）")
    temperature = Column(Float, nullable=True, comment="0.0-1.0")
    top_p = Column(Float, nullable=True, comment="0.0-1.0")
    steps = Column(Integer, nullable=True, comment="迭代上限（maxSteps 已废弃）")
    permission_json = Column(JSON, nullable=True, comment="权限配置（15 个合法键）")
    options_json = Column(JSON, nullable=True, comment="透传给 provider 的额外参数")
    color = Column(String(32), nullable=True, comment="#RRGGBB 或主题色名")
    hidden = Column(Boolean, nullable=False, default=False, comment="是否从 @ 补全中隐藏")
    disable = Column(Boolean, nullable=False, default=False, comment="是否禁用")

    # ---- 平台治理 ----
    category = Column(String(64), nullable=True, index=True, comment="分类: review/security/docs/...")
    is_builtin_preset = Column(
        Boolean, nullable=False, default=False, index=True, comment="内置预设（不可删除）",
    )
    source = Column(
        String(16), nullable=False, default=TemplateSource.PLATFORM.value,
        comment="来源: platform / imported / preset",
    )
    current_version = Column(Integer, nullable=False, default=1, comment="当前版本号")
    created_by_user_id = Column(Integer, nullable=True, comment="创建人")


class AgentTemplateVersion(BaseModel):
    """Agent 模板版本快照 —— 整份配置 JSON 留存，支持回滚。"""

    __tablename__ = "agent_template_versions"
    __table_args__ = (
        UniqueConstraint("agent_template_id", "version", name="uq_agent_version"),
        {"comment": "Agent 模板版本快照表"},
    )

    agent_template_id = Column(
        Integer,
        ForeignKey("agent_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属 agent 模板",
    )
    version = Column(Integer, nullable=False, comment="版本号（从 1 递增）")
    # 存整份而非 diff：回滚要绝对可靠，不能依赖 diff 重放的正确性
    snapshot_json = Column(JSON, nullable=False, comment="该版本的完整配置快照")
    change_note = Column(String(512), nullable=True, comment="变更说明")
    created_by_user_id = Column(Integer, nullable=True, comment="操作人")
