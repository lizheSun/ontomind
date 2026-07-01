"""Task ORM model."""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from app.db.session import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, comment="所属项目")
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="SET NULL"), nullable=True, comment="所属计划")
    requirement_id = Column(Integer, ForeignKey("requirements.id", ondelete="SET NULL"), nullable=True, comment="来源需求")

    title = Column(String(256), nullable=False, comment="任务标题")
    description = Column(Text, nullable=True, comment="任务描述")
    status = Column(String(20), default="todo", comment="状态: todo / in_progress / review / done")
    priority = Column(String(4), default="P2", comment="优先级: P0 / P1 / P2 / P3")

    assignee_agent_type = Column(String(64), nullable=True, comment="分配 Agent 类型，如 openclaw / harness / 需求拆解Agent")
    assignee_agent_id = Column(Integer, nullable=True, comment="分配 Agent 实例 ID")

    estimated_hours = Column(Float, nullable=True, comment="预估工时 (h)")
    actual_hours = Column(Float, nullable=True, comment="实际工时 (h)")
    position = Column(Integer, default=0, comment="看板排序位置")

    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, onupdate=func.now(), comment="更新时间")
