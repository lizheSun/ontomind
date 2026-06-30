"""统一异常处理 - 自定义业务异常和全局异常处理器."""
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.requests import Request

class BusinessException(Exception):
    """业务异常基类"""
    
    def __init__(
        self, 
        message: str = "业务处理失败", 
        code: str = "BUSINESS_ERROR", 
        status_code: int = status.HTTP_400_BAD_REQUEST
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)

class NotFoundException(BusinessException):
    """资源不存在异常"""
    
    def __init__(self, message: str = "资源不存在", code: str = "NOT_FOUND"):
        super().__init__(message, code, status.HTTP_404_NOT_FOUND)

class ValidationException(BusinessException):
    """数据验证异常"""
    
    def __init__(self, message: str = "数据验证失败", code: str = "VALIDATION_ERROR"):
        super().__init__(message, code, status.HTTP_422_UNPROCESSABLE_ENTITY)

class PermissionException(BusinessException):
    """权限异常"""
    
    def __init__(self, message: str = "权限不足", code: str = "PERMISSION_DENIED"):
        super().__init__(message, code, status.HTTP_403_FORBIDDEN)

class ConflictException(BusinessException):
    """资源冲突异常（如邮箱已存在）"""
    
    def __init__(self, message: str = "资源冲突", code: str = "RESOURCE_CONFLICT"):
        super().__init__(message, code, status.HTTP_409_CONFLICT)

class UnauthorizedException(BusinessException):
    """认证失败异常"""
    
    def __init__(self, message: str = "认证失败", code: str = "UNAUTHORIZED"):
        super().__init__(message, code, status.HTTP_401_UNAUTHORIZED)

__all__ = [
    "BusinessException",
    "NotFoundException", 
    "ValidationException",
    "PermissionException", 
    "ConflictException",
    "UnauthorizedException",
    "add_exception_handlers",
]

# 全局异常处理器
def business_exception_handler(request: Request, exc: BusinessException) -> JSONResponse:
    """处理业务异常"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None
        }
    )

def add_exception_handlers(app):
    """添加异常处理器到 FastAPI 应用"""
    from fastapi import FastAPI
    if isinstance(app, FastAPI):
        app.add_exception_handler(BusinessException, business_exception_handler)
