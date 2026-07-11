"""Agent Looper 版本模型（版本链）。"""
from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text
from app.db.models.base import BaseModel


class AgentLooperVersion(BaseModel):
    """Agent Looper 版本快照：每次 update 都创建一条新记录。"""

    __tablename__ = "agent_looper_versions"
    __table_args__ = (
        Index(
            "ix_agent_looper_versions_config_id_version",
            "config_id", "version_number", unique=True,
        ),
        {"comment": "Agent Looper 版本快照"},
    )

    config_id = Column(
        Integer,
        ForeignKey("agent_looper_configs.id", ondelete="CASCADE"),
        nullable=False, comment="所属配置",
    )
    version_number = Column(Integer, nullable=False, server_default="1", comment="版本号")
    config_json = Column(Text, nullable=False, comment="LONGTEXT: 完整快照 JSON")
    model_snapshot = Column(String(256), nullable=True, comment="模型快照")
    prompt_snapshot = Column(Text, nullable=True, comment="prompt 快照")
    note = Column(String(256), nullable=True, comment="变更说明")
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="创建人")
