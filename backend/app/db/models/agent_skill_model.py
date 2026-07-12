"""AgentSkill 关联模型（T44）— 智能体 ↔ 技能."""
from sqlalchemy import Column, String, Integer, ForeignKey
from app.db.models.base import BaseModel


class AgentSkill(BaseModel):
    """智能体 ↔ 技能 关联表"""

    __tablename__ = "agent_skills"
    __table_args__ = {"comment": "智能体 ↔ 技能 关联表"}

    agent_id = Column(
        Integer,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        comment="智能体 ID",
    )
    skill_id = Column(
        Integer,
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        comment="技能 ID",
    )
    binding_type = Column(
        String(32),
        nullable=False,
        server_default="inherit",
        comment="inherit/explicit_include/explicit_exclude",
    )
