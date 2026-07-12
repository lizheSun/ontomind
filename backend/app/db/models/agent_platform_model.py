"""Unified Agent Platform lifecycle models.

AgentVersion is an append-only configuration snapshot. Deployments, sessions,
messages, run traces, approvals and eval definitions reference that snapshot
instead of the legacy ``agent_looper_configs`` table.
"""
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
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


class AgentSession(BaseModel):
    __tablename__ = "agent_sessions"

    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    agent_version_id = Column(
        Integer, ForeignKey("agent_versions.id", ondelete="RESTRICT"), nullable=False
    )
    deployment_id = Column(
        Integer, ForeignKey("agent_deployments.id", ondelete="SET NULL"), nullable=True
    )
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(256), nullable=True)
    status = Column(String(32), nullable=False, server_default="active")
    session_metadata = Column(JSON, nullable=False, default=dict)


class AgentMessage(BaseModel):
    __tablename__ = "agent_messages"
    __table_args__ = (
        UniqueConstraint("session_id", "sequence", name="uq_agent_message_sequence"),
    )

    session_id = Column(
        Integer, ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False
    )
    sequence = Column(Integer, nullable=False)
    role = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(32), nullable=False, server_default="text")
    run_id = Column(
        Integer,
        ForeignKey("agent_runs.id", use_alter=True, name="fk_agent_messages_run"),
        nullable=True,
    )
    message_metadata = Column(JSON, nullable=False, default=dict)


class AgentRunStep(BaseModel):
    __tablename__ = "agent_run_steps"
    __table_args__ = (
        UniqueConstraint("run_id", "sequence", name="uq_agent_run_step_sequence"),
    )

    run_id = Column(Integer, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False)
    sequence = Column(Integer, nullable=False)
    role = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, server_default="completed")
    input = Column(JSON, nullable=True)
    output = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class AgentRunEvent(BaseModel):
    __tablename__ = "agent_run_events"
    __table_args__ = (
        UniqueConstraint("run_id", "sequence", name="uq_agent_run_event_sequence"),
        Index("ix_agent_run_events_replay", "run_id", "sequence"),
    )

    run_id = Column(Integer, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False)
    sequence = Column(Integer, nullable=False)
    event_type = Column(String(64), nullable=False)
    data = Column(JSON, nullable=False, default=dict)
    visibility = Column(String(32), nullable=False, server_default="user")


class AgentToolApproval(BaseModel):
    __tablename__ = "agent_tool_approvals"

    run_id = Column(Integer, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False)
    step_id = Column(
        Integer, ForeignKey("agent_run_steps.id", ondelete="SET NULL"), nullable=True
    )
    tool_name = Column(String(128), nullable=False)
    arguments = Column(JSON, nullable=False, default=dict)
    status = Column(String(32), nullable=False, server_default="pending")
    lock_version = Column(Integer, nullable=False, server_default="1")
    requested_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    decided_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    decision_reason = Column(Text, nullable=True)


class EvalSuite(BaseModel):
    __tablename__ = "eval_suites"

    name = Column(String(128), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="1")


class EvalCase(BaseModel):
    __tablename__ = "eval_cases"
    __table_args__ = (
        UniqueConstraint("suite_id", "name", name="uq_eval_case_suite_name"),
    )

    suite_id = Column(Integer, ForeignKey("eval_suites.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(128), nullable=False)
    input = Column(JSON, nullable=False)
    expected = Column(JSON, nullable=True)
    evaluator_config = Column(JSON, nullable=False, default=dict)


@event.listens_for(AgentVersion, "before_update")
def _reject_agent_version_update(_mapper, _connection, _target) -> None:
    """Agent versions are append-only at the ORM boundary."""
    raise ValueError("AgentVersion is immutable; create a new version")


__all__ = [
    "AgentVersion",
    "AgentDeployment",
    "AgentSession",
    "AgentMessage",
    "AgentRunStep",
    "AgentRunEvent",
    "AgentToolApproval",
    "EvalSuite",
    "EvalCase",
]
