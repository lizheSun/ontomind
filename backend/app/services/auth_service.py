"""认证服务层 - 认证业务逻辑实现."""
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.db.repositories.user_repo import UserRepository
from app.schemas.user_schema import UserLogin, Token, UserResponse
from app.core.security import create_access_token, verify_password
from app.core.exceptions import BusinessException, UnauthorizedException

class AuthService:
    """认证服务 - 处理登录、注册、Token 管理等业务逻辑"""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
    
    def login(self, login_data: UserLogin) -> Tuple[str, dict]:
        """用户登录 - 验证用户名密码，返回 Token 和用户信息"""
        # 1. 查找用户（支持用户名或邮箱登录）
        user = self.user_repo.get_by_username(login_data.username)
        if not user:
            user = self.user_repo.get_by_email(login_data.username)
        
        # 2. 验证用户是否存在
        if not user:
            raise UnauthorizedException("用户名或密码错误", code="INVALID_CREDENTIALS")
        
        # 3. 验证用户是否激活
        if not user.is_active:
            raise UnauthorizedException("用户已禁用", code="USER_DISABLED")
        
        # 4. 验证密码
        if not verify_password(login_data.password, user.password_hash):
            raise UnauthorizedException("用户名或密码错误", code="INVALID_CREDENTIALS")
        
        # 5. 生成 Token
        access_token = create_access_token(data={"sub": user.username, "user_id": user.id})
        
        # 6. 返回 Token 和用户信息
        user_response = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "display_name": user.full_name or user.username
        }
        
        return access_token, user_response
    
    def register(self, user_data: dict) -> dict:
        """用户注册 - 创建新用户"""
        with self.db.begin():
            # 1. 检查用户名是否已存在
            if self.user_repo.username_exists(user_data.get("username")):
                raise BusinessException("用户名已存在", code="USERNAME_EXISTS")
            
            # 2. 检查邮箱是否已存在
            if self.user_repo.email_exists(user_data.get("email")):
                raise BusinessException("邮箱已存在", code="EMAIL_EXISTS")
            
            # 3. 密码加密
            from app.core.security import get_password_hash
            password_hash = get_password_hash(user_data.get("password"))
            
            # 4. 创建用户
            user_dict = {
                "username": user_data.get("username"),
                "email": user_data.get("email"),
                "password_hash": password_hash,
                "full_name": user_data.get("full_name")
            }
            
            user = self.user_repo.create(user_dict)
            
            # 5. 返回用户信息
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "display_name": user.full_name or user.username
            }
    
    def get_current_user(self, user_id: int) -> dict:
        """获取当前登录用户信息"""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("用户不存在")
        
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "display_name": user.full_name or user.username
        }
