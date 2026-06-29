"""用户服务层 - 用户业务逻辑实现."""
from typing import Optional
from sqlalchemy.orm import Session
from app.db.repositories.user_repo import UserRepository
from app.schemas.user_schema import UserCreate, UserUpdate
from app.core.exceptions import BusinessException, ConflictException, NotFoundException
from app.core.security import get_password_hash, verify_password

class UserService:
    """用户服务 - 处理用户相关业务逻辑"""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
    
    def create_user(self, user_data: UserCreate) -> dict:
        """创建用户 - 服务层控制事务"""
        with self.db.begin():
            # 1. 业务规则验证
            if self.user_repo.username_exists(user_data.username):
                raise ConflictException("用户名已存在", code="USERNAME_EXISTS")
            
            if self.user_repo.email_exists(user_data.email):
                raise ConflictException("邮箱已存在", code="EMAIL_EXISTS")
            
            # 2. 密码加密
            password_hash = get_password_hash(user_data.password)
            
            # 3. 创建用户
            user_dict = user_data.model_dump(exclude={"password"})
            user_dict["password_hash"] = password_hash
            
            user = self.user_repo.create(user_dict)
            
            # 4. 可以调用其他服务（如发送欢迎邮件）
            # self.email_service.send_welcome_email(user.email)
            
            return self._to_response(user)
    
    def get_user_by_id(self, user_id: int) -> dict:
        """根据 ID 获取用户"""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(f"用户不存在: {user_id}")
        return self._to_response(user)
    
    def get_user_by_username(self, username: str) -> Optional[dict]:
        """根据用户名获取用户"""
        user = self.user_repo.get_by_username(username)
        return self._to_response(user) if user else None
    
    def get_user_by_email(self, email: str) -> Optional[dict]:
        """根据邮箱获取用户"""
        user = self.user_repo.get_by_email(email)
        return self._to_response(user) if user else None
    
    def update_user(self, user_id: int, user_data: UserUpdate) -> dict:
        """更新用户 - 服务层控制事务"""
        with self.db.begin():
            # 1. 检查用户是否存在
            user = self.user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundException(f"用户不存在: {user_id}")
            
            # 2. 检查用户名/邮箱是否冲突
            update_data = user_data.model_dump(exclude_unset=True, exclude={"password"})
            
            if user_data.username and user_data.username != user.username:
                if self.user_repo.username_exists(user_data.username, exclude_id=user_id):
                    raise ConflictException("用户名已存在", code="USERNAME_EXISTS")
            
            if user_data.email and user_data.email != user.email:
                if self.user_repo.email_exists(user_data.email, exclude_id=user_id):
                    raise ConflictException("邮箱已存在", code="EMAIL_EXISTS")
            
            # 3. 如果更新密码，需要加密
            if user_data.password:
                update_data["password_hash"] = get_password_hash(user_data.password)
                del update_data["password"]  # 删除明文密码字段
            
            # 4. 更新用户
            user = self.user_repo.update(user_id, update_data)
            return self._to_response(user)
    
    def delete_user(self, user_id: int) -> bool:
        """删除用户 - 服务层控制事务"""
        with self.db.begin():
            if not self.user_repo.delete(user_id):
                raise NotFoundException(f"用户不存在: {user_id}")
            return True
    
    def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        """认证用户 - 验证用户名和密码"""
        # 支持用户名或邮箱登录
        user = self.user_repo.get_by_username(username)
        if not user:
            user = self.user_repo.get_by_email(username)
        
        if not user:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        if not user.is_active:
            raise BusinessException("用户已禁用", code="USER_DISABLED")
        
        return self._to_response(user)
    
    def list_users(self, skip: int = 0, limit: int = 100, active_only: bool = False) -> list[dict]:
        """获取用户列表"""
        if active_only:
            users = self.user_repo.get_active_users(skip, limit)
        else:
            users = self.user_repo.get_all(skip, limit)
        return [self._to_response(user) for user in users]
    
    def _to_response(self, user) -> dict:
        """将 ORM Model 转换为响应字典"""
        if not user:
            return None
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "display_name": user.full_name or user.username
        }
