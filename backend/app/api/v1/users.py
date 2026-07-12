"""用户模块 API - 接口层实现."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.user_service import UserService
from app.schemas.user_schema import UserCreate, UserUpdate
from app.core.exceptions import BusinessException
from app.core.authorization import (
    PlatformPermission,
    require_permission,
)

router = APIRouter(
    dependencies=[Depends(require_permission(PlatformPermission.USER_MANAGE))]
)

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """依赖注入: 创建 UserService 实例"""
    return UserService(db)

# NOTE: GET "" (列表) 必须在 GET "/{user_id}" (详情) 之前，避免路由冲突

@router.get("", response_model=dict)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    user_service: UserService = Depends(get_user_service)
):
    """获取用户列表"""
    users = user_service.list_users(skip, limit, active_only)
    return {
        "code": "SUCCESS",
        "message": "操作成功",
        "data": users,
        "total": len(users)
    }

@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """创建用户"""
    try:
        user = user_service.create_user(user_data)
        return {
            "code": "SUCCESS",
            "message": "用户创建成功",
            "data": user
        }
    except BusinessException as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.code, "message": e.message})

@router.get("/{user_id}", response_model=dict)
async def get_user(
    user_id: int,
    user_service: UserService = Depends(get_user_service)
):
    """获取用户详情"""
    try:
        user = user_service.get_user_by_id(user_id)
        return {
            "code": "SUCCESS",
            "message": "操作成功",
            "data": user
        }
    except BusinessException as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.code, "message": e.message})

@router.put("/{user_id}", response_model=dict)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    user_service: UserService = Depends(get_user_service)
):
    """更新用户信息"""
    try:
        user = user_service.update_user(user_id, user_data)
        return {
            "code": "SUCCESS",
            "message": "用户更新成功",
            "data": user
        }
    except BusinessException as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.code, "message": e.message})

@router.delete("/{user_id}", response_model=dict)
async def delete_user(
    user_id: int,
    user_service: UserService = Depends(get_user_service)
):
    """删除用户"""
    try:
        user_service.delete_user(user_id)
        return {
            "code": "SUCCESS",
            "message": "用户删除成功",
            "data": None
        }
    except BusinessException as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.code, "message": e.message})
