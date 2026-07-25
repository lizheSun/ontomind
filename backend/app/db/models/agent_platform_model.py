"""Agent Platform models — 当前仅保留 AgentVersion（版本配置快照）与 AgentDeployment（部署记录）.

⚠️ 已删除：AgentSession / AgentMessage / AgentRunStep / AgentRunEvent /
AgentToolApproval / EvalSuite / EvalCase（与旧 RunsPage 一起被清理）。
如有新业务需要，再按需重建，不建议直接恢复旧表。
"""
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    event,
)

from app.db.models.base import BaseModel


class AgentVersion(BaseModel):
    __tablename__ = "agent_versions"
    __table_args__ = (
        UniqueConstraint("agent_id", "version_number", name="uq_agent_version_number"),
        {"comment": "不可变 Agent 配置快照"},
    )

    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    config = Column(JSON, nullable=False)
    config_hash = Column(String(64), nullable=False)
    note = Column(String(256), nullable=True)
    status = Column(String(32), nullable=False, server_default="draft")
    config_schema_version = Column(String(32), nullable=False, server_default="1")
    source = Column(String(32), nullable=False, server_default="manual")
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)


class AgentDeployment(BaseModel):
    __tablename__ = "agent_deployments"

    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    agent_version_id = Column(
        Integer, ForeignKey("agent_versions.id", ondelete="RESTRICT"), nullable=False
    )
    environment = Column(String(64), nullable=False, server_default="default")
    status = Column(String(32), nullable=False, server_default="draft")
    runtime_config = Column(JSON, nullable=False, default=dict)
    status_version = Column(Integer, nullable=False, server_default="1")
    previous_deployment_id = Column(
        Integer, ForeignKey("agent_deployments.id", ondelete="SET NULL"), nullable=True
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    failure_code = Column(String(64), nullable=True)
    failure_message = Column(Text, nullable=True)
    deployed_at = Column(DateTime(timezone=True), nullable=True)
    stopped_at = Column(DateTime(timezone=True), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)


@event.listens_for(AgentVersion, "before_update")
def _reject_agent_version_update(_mapper, _connection, _target) -> None:
    raise ValueError("AgentVersion is immutable; create a new version")


__all__ = ["AgentVersion", "AgentDeployment"]