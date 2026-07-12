"""ContainerMCP 关联模型（T44）— 智能体容器 ↔ MCP."""
from sqlalchemy import Column, String, Integer, ForeignKey
from app.db.models.base import BaseModel


class ContainerMCP(BaseModel):
    """智能体容器 ↔ MCP 关联表"""

    __tablename__ = "container_mcps"
    __table_args__ = {"comment": "智能体容器 ↔ MCP 关联表"}

    container_id = Column(
        Integer,
        ForeignKey("agent_containers.id", ondelete="CASCADE"),
        nullable=False,
        comment="容器 ID",
    )
    mcp_id = Column(
        Integer,
        ForeignKey("mcps.id", ondelete="CASCADE"),
        nullable=False,
        comment="MCP ID",
    )
    binding_type = Column(
        String(32),
        nullable=False,
        server_default="inherit",
        comment="inherit/explicit_include/explicit_exclude",
    )
