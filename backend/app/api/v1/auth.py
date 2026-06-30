"""认证模块 API - 接口层实现."""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from app.db.session import get_db
from app.services.auth_service import AuthService
from app.schemas.user_schema import UserLogin, UserCreate
from app.core.exceptions import BusinessException, UnauthorizedException
from app.core.security import get_current_user_id_from_token

router = APIRouter()


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """依赖注入: 创建 AuthService 实例"""
    return AuthService(db)


def get_current_user_id(authorization: Optional[str] = Header(None)) -> int:
    """从 Authorization Header 提取用户 ID"""
    if not authorization:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "未提供认证Token"})
    
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "认证格式错误"})
    
    user_id = get_current_user_id_from_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail={"code": "INVALID_TOKEN", "message": "Token无效或已过期"})
    
    return user_id


@router.post("/login", response_model=Dict[str, Any])
async def login(
    login_data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
):
    """用户登录 - 获取 JWT Token."""
    try:
        access_token, user = auth_service.login(login_data)
        return {
            "code": "SUCCESS",
            "message": "登录成功",
            "data": {
                "access_token": access_token,
                "token_type": "bearer",
                "user": user
            }
        }
    except BusinessException as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.code, "message": e.message})


@router.post("/register", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
):
    """用户注册."""
    try:
        user = auth_service.register(user_data.model_dump())
        return {
            "code": "SUCCESS",
            "message": "注册成功",
            "data": user
        }
    except BusinessException as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.code, "message": e.message})


@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_info(
    user_id: int = Depends(get_current_user_id),
    auth_service: AuthService = Depends(get_auth_service)
):
    """获取当前登录用户信息."""
    try:
        user = auth_service.get_current_user(user_id)
        return {
            "code": "SUCCESS",
            "message": "操作成功",
            "data": user
        }
    except BusinessException as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.code, "message": e.message})
