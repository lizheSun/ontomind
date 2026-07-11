"""Agent Looper 配置模型（T34 契约的 T36 侧最小实现，合并时以 T34 完整版为准）。"""
from sqlalchemy import Boolean, Column, ForeignKey, Integer, JSON, String, Text
from app.db.models.base import BaseModel


class AgentLooperConfig(BaseModel):
    """Agent Looper 配置：一个 Agent（可含多版本）。"""

    __tablename__ = "agent_looper_configs"
    __table_args__ = {"comment": "Agent Looper 配置"}

    name = Column(String(128), nullable=False, comment="Agent 名称")
    type = Column(
        String(32), nullable=False, server_default="custom_looper",
        comment="custom_looper/opencode_native/mcp_agent/imported",
    )
    description = Column(Text, nullable=True, comment="描述")
    current_version_id = Column(
        Integer, ForeignKey("agent_looper_versions.id"),
        nullable=True, comment="当前生效版本",
    )
    active_config_json = Column(Text, nullable=True, comment="LONGTEXT: full JSON schema")
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="拥有者")
    is_active = Column(Boolean, nullable=False, server_default="1", comment="启用")
    is_published = Column(Boolean, nullable=False, server_default="0", comment="已发布")
    settings = Column(JSON, nullable=True, comment="path 覆盖等")
    resource_bindings = Column(JSON, nullable=True, comment="资源绑定")
    credential_ref = Column(JSON, nullable=True, comment="{credential_type, credential_id}")
