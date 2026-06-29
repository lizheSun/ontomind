"""用户模型 - 用户表 ORM 定义."""
from sqlalchemy import Column, String, Boolean
from app.db.models.base import BaseModel

class User(BaseModel):
    """用户表模型"""
    
    __tablename__ = "users"
    __table_args__ = {"comment": "用户表"}
    
    username = Column(
        String(50), 
        unique=True, 
        nullable=False, 
        index=True, 
        comment="用户名"
    )
    email = Column(
        String(100), 
        unique=True, 
        nullable=False, 
        index=True, 
        comment="邮箱"
    )
    password_hash = Column(
        String(255), 
        nullable=False, 
        comment="密码哈希"
    )
    full_name = Column(
        String(100), 
        nullable=True, 
        comment="全名"
    )
    is_active = Column(
        Boolean, 
        default=True, 
        nullable=False, 
        comment="是否激活"
    )
    is_superuser = Column(
        Boolean, 
        default=False, 
        nullable=False, 
        comment="是否超级管理员"
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"
    
    @property
    def is_active_user(self) -> bool:
        """检查用户是否激活"""
        return self.is_active
    
    def check_password(self, password: str) -> bool:
        """检查密码 - 需要配合 password_hash 工具使用"""
        # TODO: 实现密码验证逻辑
        from app.core.security import verify_password
        return verify_password(password, self.password_hash)
