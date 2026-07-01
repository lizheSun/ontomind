"""Project ORM model."""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.db.session import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    name = Column(String(128), nullable=False, comment="项目名称")
    key = Column(String(16), nullable=False, unique=True, comment="项目唯一标识，如 PROJ")
    description = Column(Text, nullable=True, comment="项目描述")
    status = Column(String(20), default="active", comment="状态: active / archived")
    icon = Column(String(8), nullable=True, comment="Emoji 图标")
    color = Column(String(7), nullable=True, comment="主题色 #hex")
    extra = Column(JSON, nullable=True, comment="扩展字段")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, onupdate=func.now(), comment="更新时间")
