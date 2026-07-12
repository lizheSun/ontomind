"""Agent 智能体模型（T44 — 合并 agents + agent_looper_configs）.

新版 Agent 模型合并了原 `agents` 和 `agent_looper_configs` 两张表的核心字段，
支持 `custom_looper / opencode_native / mcp_agent / imported` 四种类型。
"""
from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, JSON
from app.db.models.base import BaseModel


class Agent(BaseModel):
    """智能体（原 agent_looper_configs + agents 合并）"""

    __tablename__ = "agents"
    __table_args__ = {"comment": "智能体（原 agent_looper_configs + agents 合并）"}

    name = Column(String(128), nullable=False, unique=True, comment="智能体名称")
    type = Column(
        String(32),
        nullable=False,
        server_default="custom_looper",
        comment="custom_looper/opencode_native/mcp_agent/imported",
    )
    container_id = Column(
        Integer,
        ForeignKey("agent_containers.id", ondelete="SET NULL"),
        nullable=True,
        comment="所属容器 ID",
    )
    description = Column(Text, nullable=True, comment="描述")
    model = Column(String(256), nullable=True, comment="模型名称")
    temperature = Column(Integer, nullable=True, comment="温度 * 100（存整数避免浮点）")
    loop_strategy = Column(
        String(32),
        nullable=True,
        server_default="react",
        comment="single_shot/react/plan_execute/reflect",
    )
    system_prompt = Column(Text, nullable=True, comment="系统提示词")
    tool_permissions = Column(JSON, nullable=True, comment="工具权限 JSON")
    custom_tools = Column(JSON, nullable=True, comment="自定义工具 JSON")
    memory_window = Column(
        Integer,
        nullable=True,
        server_default="0",
        comment="记忆窗口大小",
    )
    guardrails = Column(JSON, nullable=True, comment="护栏配置 JSON")
    resource_bindings = Column(JSON, nullable=True, comment="资源绑定 JSON")
    credential_ref = Column(JSON, nullable=True, comment="凭据引用 JSON")
    is_active = Column(
        Boolean,
        nullable=False,
        server_default="1",
        comment="是否激活",
    )
    is_published = Column(
        Boolean,
        nullable=False,
        server_default="0",
        comment="是否已发布",
    )
    version = Column(
        Integer,
        nullable=False,
        server_default="1",
        comment="当前版本号",
    )
    published_path = Column(
        String(512),
        nullable=True,
        comment="发布到 opencode 的文件路径",
    )
    owner_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        comment="Agent 所有者（统一平台新增，旧数据可为空）",
    )
    current_version_id = Column(
        Integer,
        ForeignKey(
            "agent_versions.id",
            use_alter=True,
            name="fk_agents_current_version",
            ondelete="SET NULL",
        ),
        nullable=True,
        comment="当前发布的不可变 AgentVersion",
    )
