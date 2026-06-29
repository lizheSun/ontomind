"""认证模块 API - 接口层实现."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.db.session import get_db
from app.services.auth_service import AuthService
from app.schemas.user_schema import UserLogin
from app.core.exceptions import BusinessException

router = APIRouter()


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """依赖注入: 创建 AuthService 实例"""
    return AuthService(db)


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
    user_data: Dict[str, Any],
    auth_service: AuthService = Depends(get_auth_service)
):
    """用户注册."""
    try:
        user = auth_service.register(user_data)
        return {
            "code": "SUCCESS",
            "message": "注册成功",
            "data": user
        }
    except BusinessException as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.code, "message": e.message})


@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_info(
    auth_service: AuthService = Depends(get_auth_service)
):
    """获取当前登录用户信息."""
    # TODO: 从 Token 中获取 user_id
    try:
        user = auth_service.get_current_user(1)  # 临时硬编码
        return {
            "code": "SUCCESS",
            "message": "操作成功",
            "data": user
        }
    except BusinessException as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.code, "message": e.message})
