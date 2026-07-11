"""AgentLooper 版本快照模型 — 每次 create/update/rollback 追加一行（T34）。

版本号在 (config_id, version_number) 上唯一，通过 COALESCE(MAX(version_number),0)+1 自增。
删除 config 时通过 ON DELETE CASCADE 级联删除所有 versions。
"""
from sqlalchemy import Column, String, Integer, Text, ForeignKey, Index
from app.db.models.base import BaseModel


class AgentLooperVersion(BaseModel):
    """AgentLooper 版本快照：一次配置修改 = 一行版本记录。"""

    __tablename__ = "agent_looper_versions"
    __table_args__ = (
        Index(
            "ix_agent_looper_versions_config_id_version",
            "config_id", "version_number",
            unique=True,
        ),
        {"comment": "AgentLooper 版本快照表"},
    )

    config_id = Column(
        Integer,
        ForeignKey("agent_looper_configs.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属 config id（删除 config 级联删除本表）",
    )
    version_number = Column(
        Integer, nullable=False, server_default="1",
        comment="版本号（同 config 下自增，从 1 起）",
    )
    config_json = Column(
        Text, nullable=False,
        comment="LONGTEXT: 该版本完整 JSON schema 快照",
    )
    model_snapshot = Column(
        String(256), nullable=True, comment="使用的模型标识（快照记录）",
    )
    prompt_snapshot = Column(
        Text, nullable=True, comment="使用的主 prompt（快照记录）",
    )
    note = Column(String(256), nullable=True, comment="版本备注")
    created_by_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False,
        comment="创建该版本的 user_id",
    )
