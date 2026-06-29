"""基础模型类 - 所有 ORM Model 的基类."""
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func
from app.db.session import Base

class BaseModel(Base):
    """基础模型类 - 提供通用字段和方法"""
    
    __abstract__ = True  # 设置为抽象类，不会创建表
    
    id = Column(Integer, primary_key=True, index=True, comment="主键ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")
    
    def to_dict(self):
        """转换为字典"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"
