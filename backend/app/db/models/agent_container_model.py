"""AgentContainer 智能体容器模型（T44）.

opencode / openclaw / harness 等运行时容器 / 进程的抽象表示。
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON
from app.db.models.base import BaseModel


class AgentContainer(BaseModel):
    """智能体容器（opencode/openclaw/harness 运行时）"""

    __tablename__ = "agent_containers"
    __table_args__ = {"comment": "智能体容器（opencode/openclaw/harness 运行时）"}

    name = Column(String(128), nullable=False, comment="容器名称")
    container_type = Column(
        String(32),
        nullable=False,
        comment="opencode/openclaw/harness/custom",
    )
    version = Column(String(32), nullable=True, comment="版本")
    port = Column(Integer, nullable=True, comment="端口")
    host = Column(String(255), nullable=True, comment="宿主机地址")
    health_url = Column(String(512), nullable=True, comment="健康检查 URL")
    status = Column(
        String(32),
        nullable=False,
        server_default="running",
        comment="running/stopped/error",
    )
    process_name = Column(String(128), nullable=True, comment="进程名")
    pid = Column(Integer, nullable=True, comment="进程 PID")
    cli_path = Column(String(512), nullable=True, comment="CLI 路径")
    env = Column(JSON, nullable=True, comment="环境变量 JSON")
    skills_auto_inherit = Column(
        Boolean,
        nullable=False,
        server_default="1",
        comment="是否自动继承所有 Skill",
    )
    mcps_auto_inherit = Column(
        Boolean,
        nullable=False,
        server_default="1",
        comment="是否自动继承所有 MCP",
    )
    last_heartbeat = Column(DateTime, nullable=True, comment="最后心跳时间")
