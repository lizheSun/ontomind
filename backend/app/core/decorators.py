"""装饰器集合 - 提供事务管理、权限检查等装饰器."""
from functools import wraps
from sqlalchemy.orm import Session
from app.core.exceptions import BusinessException

def transactional(func):
    """事务装饰器 - 自动管理事务提交和回滚
    
    使用方式:
        class UserService:
            @transactional
            def create_user(self, data):
                # 这里的操作会在同一个事务中
                user = self.user_repo.create(data)
                profile = self.profile_repo.create({"user_id": user.id})
                return user
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # 假设 self 有 db 属性（Session）
        if not hasattr(self, 'db'):
            raise AttributeError("使用 @transactional 装饰器需要类有 db 属性")
        
        db = self.db
        try:
            with db.begin():
                return func(self, *args, **kwargs)
        except BusinessException:
            # 业务异常不包装，直接抛出
            raise
        except Exception as e:
            # 其他异常包装为业务异常
            raise BusinessException(f"操作失败: {str(e)}", code="TRANSACTION_ERROR")
    
    return wrapper

def require_permissions(*permissions):
    """权限检查装饰器 - 检查用户是否拥有指定权限
    
    使用方式:
        @router.post("/users")
        @require_permissions("user:create")
        async def create_user(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # TODO: 实现权限检查逻辑
            # 可以从 token 中获取用户权限，然后检查
            return await func(*args, **kwargs)
        return wrapper
    return decorator
