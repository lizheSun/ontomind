"""认证模块 API."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter()


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """用户登录 - 获取 JWT Token."""
    # TODO: validate user from DB
    return {"access_token": "placeholder", "token_type": "bearer"}


@router.post("/register")
async def register():
    """用户注册."""
    return {"message": "register endpoint - to be implemented"}
