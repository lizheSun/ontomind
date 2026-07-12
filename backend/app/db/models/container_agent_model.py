"""ContainerAgent 关联模型（T44）— 智能体容器 ↔ 智能体."""
from sqlalchemy import Column, String, Integer, ForeignKey
from app.db.models.base import BaseModel


class ContainerAgent(BaseModel):
    """智能体容器 ↔ 智能体 关联表"""

    __tablename__ = "container_agents"
    __table_args__ = {"comment": "智能体容器 ↔ 智能体 关联表"}

    container_id = Column(
        Integer,
        ForeignKey("agent_containers.id", ondelete="CASCADE"),
        nullable=False,
        comment="容器 ID",
    )
    agent_id = Column(
        Integer,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        comment="智能体 ID",
    )
    binding_type = Column(
        String(32),
        nullable=False,
        server_default="inherit",
        comment="inherit/explicit_include/explicit_exclude",
    )
