"""用户 Schema - Pydantic 校验模型."""
from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    """用户基础 Schema"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")

class UserCreate(UserBase):
    """创建用户 Schema"""
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    
    @model_validator(mode='after')
    def validate_password_complexity(self):
        """验证密码复杂度"""
        password = self.password
        if len(password) < 6:
            raise ValueError("密码长度至少6位")
        # 可以在这里添加更多密码复杂度验证
        return self

class UserUpdate(BaseModel):
    """更新用户 Schema - 所有字段可选"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=6, max_length=50)
    is_active: Optional[bool] = None

class UserInDB(UserBase):
    """用户数据库 Schema - 包含数据库字段"""
    id: int
    is_active: bool = True
    is_superuser: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}  # Pydantic v2 配置

class UserResponse(UserInDB):
    """用户响应 Schema"""
    # 可以添加额外的计算字段
    display_name: Optional[str] = None
    
    @model_validator(mode='before')
    @classmethod
    def set_display_name(cls, data):
        """设置显示名称"""
        if isinstance(data, dict):
            if not data.get('display_name') and data.get('full_name'):
                data['display_name'] = data['full_name']
            elif not data.get('display_name'):
                data['display_name'] = data.get('username')
        return data

class UserLogin(BaseModel):
    """用户登录 Schema"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")

class Token(BaseModel):
    """Token 响应 Schema"""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Token 数据 Schema"""
    username: Optional[str] = None
    user_id: Optional[int] = None
