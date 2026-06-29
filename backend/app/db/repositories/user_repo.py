"""用户 Repository - 用户数据访问层."""
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models.user_model import User
from app.db.repositories.base_repo import BaseRepository

class UserRepository(BaseRepository[User]):
    """用户 Repository - 封装用户相关数据操作"""
    
    def __init__(self, db: Session):
        super().__init__(User, db)
    
    def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名查询用户"""
        return self.db.query(User).filter(User.username == username).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱查询用户"""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_active_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """查询所有激活的用户"""
        return (
            self.db.query(User)
            .filter(User.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def username_exists(self, username: str, exclude_id: int = None) -> bool:
        """检查用户名是否存在"""
        query = self.db.query(User).filter(User.username == username)
        if exclude_id:
            query = query.filter(User.id != exclude_id)
        return query.first() is not None
    
    def email_exists(self, email: str, exclude_id: int = None) -> bool:
        """检查邮箱是否存在"""
        query = self.db.query(User).filter(User.email == email)
        if exclude_id:
            query = query.filter(User.id != exclude_id)
        return query.first() is not None
