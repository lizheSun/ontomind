"""AgentRun 运行实例模型."""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Enum as SAEnum, JSON
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
    status = Column(
        SAEnum(RunStatus, name="run_status_enum", create_type=False),
        default=RunStatus.initializing,
        comment="状态: initializing / running / error / stopped",
    )
    container_id = Column(String(128), nullable=True, comment="Docker 容器 ID")
    pid = Column(Integer, nullable=True, comment="进程 PID")
    config_override = Column(JSON, nullable=True, comment="运行时配置覆盖")
    env_override = Column(JSON, nullable=True, comment="运行时环境变量覆盖")
    started_at = Column(DateTime(timezone=True), nullable=True, comment="启动时间")
    stopped_at = Column(DateTime(timezone=True), nullable=True, comment="停止时间")
    exit_code = Column(Integer, nullable=True, comment="退出码")
    error_message = Column(Text, nullable=True, comment="错误信息")
    log_offset = Column(Integer, default=0, comment="日志读取偏移量")

    def to_response_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "instance_id": self.instance_id,
            "run_name": self.run_name,
            "status": self.status.value if hasattr(self.status, "value") else self.status,
            "container_id": self.container_id,
            "pid": self.pid,
            "config_override": self.config_override,
            "env_override": self.env_override,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "exit_code": self.exit_code,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
