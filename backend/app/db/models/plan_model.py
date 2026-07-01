"""Plan / Sprint ORM model."""
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey
from sqlalchemy.sql import func
from app.db.session import Base


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, comment="所属项目")
    name = Column(String(256), nullable=False, comment="计划/迭代名称")
    plan_type = Column(String(20), default="sprint", comment="类型: sprint / release / milestone")
    goal = Column(Text, nullable=True, comment="迭代目标")
    start_date = Column(Date, nullable=True, comment="开始日期")
    end_date = Column(Date, nullable=True, comment="结束日期")
    status = Column(String(20), default="planned", comment="状态: planned / active / completed / cancelled")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, onupdate=func.now(), comment="更新时间")
