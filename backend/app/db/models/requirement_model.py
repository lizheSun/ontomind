"""Requirement ORM model."""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.db.session import Base


class Requirement(Base):
    __tablename__ = "requirements"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, comment="所属项目")
    title = Column(String(256), nullable=False, comment="需求标题")
    req_type = Column(String(20), nullable=False, default="feature", comment="类型: feature / bug / improvement / performance")
    priority = Column(String(4), default="P2", comment="优先级: P0 / P1 / P2 / P3")
    status = Column(String(20), default="pending_review", comment="状态: pending_review / passed / rejected / in_progress / done")
    description = Column(Text, nullable=True, comment="详细描述")
    acceptance_criteria = Column(Text, nullable=True, comment="验收标准")
    impact_scope = Column(Text, nullable=True, comment="影响范围")
    related_modules = Column(JSON, nullable=True, comment="关联模块列表")

    # Agent 评审结果
    score_clarity = Column(Float, nullable=True, comment="需求清晰度 1-10")
    score_feasibility = Column(Float, nullable=True, comment="技术可行性 1-10")
    score_value = Column(Float, nullable=True, comment="业务价值 1-10")
    score_total = Column(Float, nullable=True, comment="综合评分")
    review_comment = Column(Text, nullable=True, comment="Agent 评审意见")
    review_agent_id = Column(Integer, nullable=True, comment="评审 Agent ID")

    # 拆解结果
    is_decomposed = Column(Boolean, default=False, comment="是否已拆解为 Task")
    decompose_agent_id = Column(Integer, nullable=True, comment="拆解 Agent ID")

    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, onupdate=func.now(), comment="更新时间")
