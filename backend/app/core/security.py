"""安全工具 - 密码哈希、JWT Token 生成与验证."""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT Access Token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_websocket_ticket(user_id: int, expires_seconds: int = 60) -> str:
    """Mint a short-lived WebSocket ticket safe for legacy query transport."""
    lifetime = max(10, min(expires_seconds, 120))
    return create_access_token(
        {"user_id": user_id, "token_use": "websocket"},
        expires_delta=timedelta(seconds=lifetime),
    )

def decode_access_token(token: str) -> Dict[str, Any]:
    """解码 JWT Token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

def get_current_user_id_from_token(token: str) -> Optional[int]:
    """从 Token 中获取用户 ID"""
    payload = decode_access_token(token)
    if payload:
        user_id = payload.get("user_id")
        if user_id:
            return int(user_id)
    return None
