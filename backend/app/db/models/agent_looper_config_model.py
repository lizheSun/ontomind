"""AgentLooper 配置模型 — 用户定义的 agent 循环器主表（T34）。

关联版本表 agent_looper_versions（一对多），并通过 current_version_id 指向当前生效版本。
支持 soft-delete（is_active=False）与发布态（is_published）。
"""
from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, JSON
from app.db.models.base import BaseModel


class AgentLooperConfig(BaseModel):
    """AgentLooper 主表：每个 owner 唯一 name，指向当前生效的 version。"""

    __tablename__ = "agent_looper_configs"
    __table_args__ = {"comment": "AgentLooper 配置主表"}

    name = Column(String(128), nullable=False, comment="配置名称（同 owner 下唯一）")
    type = Column(
        String(32),
        nullable=False,
        server_default="custom_looper",
        comment="custom_looper/opencode_native/mcp_agent/imported",
    )
    description = Column(Text, nullable=True, comment="描述")
    # NOTE: current_version_id 引用 agent_looper_versions.id；反向由 versions.config_id 引用 configs.id。
    # 为避免循环级联删除，此侧使用 SET NULL / 不级联；配置删除时业务层先清 current_version_id。
    current_version_id = Column(
        Integer,
        ForeignKey("agent_looper_versions.id", use_alter=True, name="fk_alc_current_version"),
        nullable=True,
        comment="当前生效版本 id（引用 agent_looper_versions.id）",
    )
    active_config_json = Column(
        Text, nullable=True, comment="LONGTEXT: 当前版本完整 JSON schema 快照",
    )
    owner_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, comment="拥有者 user_id",
    )
    is_active = Column(
        Boolean, nullable=False, server_default="1", comment="是否激活（soft-delete = False）",
    )
    is_published = Column(
        Boolean, nullable=False, server_default="0", comment="是否已发布",
    )
    settings = Column(JSON, nullable=True, comment="path overrides 等运行时设置")
    resource_bindings = Column(JSON, nullable=True, comment="资源绑定：LLM/数据源/知识库等")
    credential_ref = Column(
        JSON, nullable=True,
        comment="{credential_type: dp_source, credential_id: int}",
    )
