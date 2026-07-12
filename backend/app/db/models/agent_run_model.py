"""AgentRun 运行实例模型（兼容旧运行追踪并承载统一 Run 领域）."""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON
import enum
from app.db.models.base import BaseModel


class RunStatus(str, enum.Enum):
    initializing = "initializing"
    running = "running"
    error = "error"
    stopped = "stopped"


class AgentRun(BaseModel):
    """Agent 运行实例追踪表"""

    __tablename__ = "agent_runs"

    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, comment="关联 Agent ID")
    instance_id = Column(Integer, ForeignKey("instances.id", ondelete="SET NULL"), nullable=True, comment="关联 Instance ID")
    run_name = Column(String(128), nullable=False, comment="运行实例名称")
    status = Column(String(32), nullable=False, default="initializing")
    container_id = Column(String(128), nullable=True, comment="Docker 容器 ID")
    pid = Column(Integer, nullable=True, comment="进程 PID")
    config_override = Column(JSON, nullable=True, comment="运行时配置覆盖")
    env_override = Column(JSON, nullable=True, comment="运行时环境变量覆盖")
    started_at = Column(DateTime(timezone=True), nullable=True, comment="启动时间")
    stopped_at = Column(DateTime(timezone=True), nullable=True, comment="停止时间")
    exit_code = Column(Integer, nullable=True, comment="退出码")
    error_message = Column(Text, nullable=True, comment="错误信息")
    log_offset = Column(Integer, default=0, comment="日志读取偏移量")
    agent_version_id = Column(Integer, ForeignKey("agent_versions.id", ondelete="SET NULL"), nullable=True)
    deployment_id = Column(Integer, ForeignKey("agent_deployments.id", ondelete="SET NULL"), nullable=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id", ondelete="SET NULL"), nullable=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    strategy = Column(String(32), nullable=True)
    kind = Column(String(32), nullable=False, server_default="chat")
    parent_run_id = Column(
        Integer, ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True
    )
    attempt = Column(Integer, nullable=False, server_default="1")
    goal = Column(Text, nullable=True)
    checkpoint = Column(JSON, nullable=True)
    input = Column(JSON, nullable=True)
    output = Column(JSON, nullable=True)
    state_version = Column(Integer, nullable=False, server_default="1")
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def to_response_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "instance_id": self.instance_id,
            "run_name": self.run_name,
            "run_key": f"run_{self.id}",
            "status": self.status.value if hasattr(self.status, "value") else self.status,
            "container_id": self.container_id,
            "pid": self.pid,
            "config_override": self.config_override,
            "env_override": self.env_override,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "exit_code": self.exit_code,
            "error_message": self.error_message,
            "agent_version_id": self.agent_version_id,
            "deployment_id": self.deployment_id,
            "session_id": self.session_id,
            "owner_user_id": self.owner_user_id,
            "strategy": self.strategy,
            "kind": self.kind,
            "parent_run_id": self.parent_run_id,
            "attempt": self.attempt,
            "goal": self.goal,
            "checkpoint": self.checkpoint,
            "input": self.input,
            "input_snapshot": self.input,
            "output": self.output,
            "output_snapshot": self.output,
            "state_version": self.state_version,
            "concurrency_version": self.state_version,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "finished_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
