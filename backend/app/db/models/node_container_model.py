"""NodeContainer 关联模型（T44）— 计算节点 ↔ 智能体容器."""
from sqlalchemy import Column, String, Integer, ForeignKey
from app.db.models.base import BaseModel


class NodeContainer(BaseModel):
    """计算节点 ↔ 智能体容器 关联表"""

    __tablename__ = "node_containers"
    __table_args__ = {"comment": "计算节点 ↔ 智能体容器 关联表"}

    node_id = Column(
        Integer,
        ForeignKey("compute_nodes.id", ondelete="CASCADE"),
        nullable=False,
        comment="计算节点 ID",
    )
    container_id = Column(
        Integer,
        ForeignKey("agent_containers.id", ondelete="CASCADE"),
        nullable=False,
        comment="容器 ID",
    )
    binding_type = Column(
        String(32),
        nullable=False,
        server_default="inherit",
        comment="inherit/explicit_include/explicit_exclude",
    )
