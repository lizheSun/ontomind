# OntoMind 后端开发规范

> **版本**: v1.0.0  
> **更新日期**: 2026-06-29  
> **适用范围**: OntoMind 项目后端开发

---

## 目录

1. [架构概览](#1-架构概览)
2. [分层架构规范](#2-分层架构规范)
3. [事务控制规范](#3-事务控制规范)
4. [命名规范](#4-命名规范)
5. [代码组织规范](#5-代码组织规范)
6. [错误处理规范](#6-错误处理规范)
7. [依赖注入规范](#7-依赖注入规范)
8. [测试规范](#8-测试规范)
9. [最佳实践](#9-最佳实践)

---

## 1. 架构概览

### 1.1 三层架构模式

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (接口层)                    │
│  - FastAPI Routers (app/api/v1/)                        │
│  - 请求参数校验 (Pydantic v2 Schemas)                   │
│  - 响应格式化                                           │
│  - 认证/授权检查                                        │
│  - 调用 Service 层                                      │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                  Service Layer (服务层)                  │
│  - 业务逻辑实现 (app/services/)                        │
│  - 事务管理 (session.begin())                          │
│  - 数据验证与业务规则                                   │
│  - 调用 Repository 层获取数据                           │
│  - 复杂业务编排                                         │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                Data Layer (数据层)                       │
│  - ORM Models (app/db/models/)                         │
│  - Repository/DAO 模式 (app/db/repositories/)          │
│  - 数据库查询封装                                       │
│  - 不处理业务逻辑                                       │
└─────────────────────────────────────────────────────────┘
```

### 1.2 核心原则

1. **单一职责原则**: 每层只负责自己的职责
2. **依赖倒置原则**: 高层模块不应依赖低层模块，二者都应依赖抽象
3. **接口隔离原则**: 层间通过接口通信，不直接依赖实现
4. **事务边界清晰**: 服务层控制事务，确保业务操作的原子性

---

## 2. 分层架构规范

### 2.1 接口层 (API Layer)

**职责**:
- 接收 HTTP 请求
- 参数校验（使用 Pydantic Schemas）
- 调用服务层处理业务
- 返回 HTTP 响应

**规范**:
```python
# app/api/v1/users.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.user_service import UserService
from app.schemas.user_schema import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["用户管理"])

@router.post("", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """创建用户 - 接口层只做参数校验和响应格式化"""
    user_service = UserService(db)
    user = user_service.create_user(user_data)
    return user

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """获取用户详情"""
    user_service = UserService(db)
    user = user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user
```

**禁止事项**:
- ❌ 不允许在接口层直接操作数据库
- ❌ 不允许在接口层写业务逻辑
- ❌ 不允许在接口层处理异常（应该抛出，由全局异常处理器处理）

### 2.2 服务层 (Service Layer)

**职责**:
- 实现业务逻辑
- 控制事务边界
- 调用 Repository 层获取数据
- 业务规则验证

**规范**:
```python
# app/services/user_service.py

from sqlalchemy.orm import Session
from app.db.repositories.user_repo import UserRepository
from app.schemas.user_schema import UserCreate
from app.core.exceptions import BusinessException

class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
    
    def create_user(self, user_data: UserCreate) -> User:
        """创建用户 - 服务层控制事务"""
        with self.db.begin():
            # 1. 业务规则验证
            if self.user_repo.get_by_email(user_data.email):
                raise BusinessException("邮箱已存在", code="EMAIL_EXISTS")
            
            # 2. 数据持久化
            user = self.user_repo.create(user_data.model_dump())
            
            # 3. 可以调用其他服务或发送事件
            # self.email_service.send_welcome_email(user)
            
            return user
    
    def get_user(self, user_id: int) -> User:
        """获取用户 - 查询操作不需要事务"""
        user = self.user_repo.get_by_id(user_id)
        return user
```

**关键点**:
- ✅ 使用 `with self.db.begin()` 控制事务边界
- ✅ 事务内的所有操作要么全部成功，要么全部回滚
- ✅ 查询操作可以不使用事务（取决于业务需求）

### 2.3 数据层 (Data Layer)

**职责**:
- ORM 模型定义
- 数据库查询封装（Repository 模式）
- 不处理业务逻辑

**模型定义规范**:
```python
# app/db/models/user_model.py

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.models.base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"
```

**Repository 规范**:
```python
# app/db/repositories/user_repo.py

from sqlalchemy.orm import Session
from app.db.models.user_model import User
from typing import Optional, List

class UserRepository:
    def __init__(self, db: Session):
        self.db = db
        self.model = User
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """根据 ID 查询用户"""
        return self.db.query(self.model).filter(self.model.id == user_id).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱查询用户"""
        return self.db.query(self.model).filter(self.model.email == email).first()
    
    def create(self, obj_in: dict) -> User:
        """创建用户"""
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        self.db.flush()  # 刷新以获取 ID
        return db_obj
    
    def update(self, user_id: int, obj_in: dict) -> Optional[User]:
        """更新用户"""
        user = self.get_by_id(user_id)
        if user:
            for key, value in obj_in.items():
                setattr(user, key, value)
            self.db.flush()
        return user
    
    def delete(self, user_id: int) -> bool:
        """删除用户"""
        user = self.get_by_id(user_id)
        if user:
            self.db.delete(user)
            self.db.flush()
            return True
        return False
```

**禁止事项**:
- ❌ 不允许在 Repository 层写业务逻辑
- ❌ 不允许在 Repository 层控制事务（事务由服务层控制）
- ❌ 不允许返回 Pydantic Schema（应该返回 ORM Model）

---

## 3. 事务控制规范

### 3.1 事务边界定义

**原则**: 事务边界必须在服务层控制，接口层和数据层不参与事务管理。

### 3.2 事务管理模式

**模式 1: 上下文管理器（推荐）**
```python
# app/services/order_service.py

class OrderService:
    def __init__(self, db: Session):
        self.db = db
        self.order_repo = OrderRepository(db)
        self.inventory_repo = InventoryRepository(db)
    
    def create_order(self, order_data: OrderCreate) -> Order:
        """创建订单 - 需要事务保证订单和库存的原子性"""
        with self.db.begin():
            # 1. 创建订单
            order = self.order_repo.create(order_data.model_dump())
            
            # 2. 扣减库存
            for item in order_data.items:
                inventory = self.inventory_repo.get_by_product_id(item.product_id)
                if inventory.quantity < item.quantity:
                    raise BusinessException("库存不足", code="INVENTORY_INSUFFICIENT")
                inventory.quantity -= item.quantity
            
            # 3. 如果任何操作失败，整个事务自动回滚
            return order
```

**模式 2: 装饰器（可选）**
```python
# app/core/decorators.py

from functools import wraps
from sqlalchemy.orm import Session

def transactional(func):
    """事务装饰器 - 自动管理事务"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with self.db.begin():
            return func(self, *args, **kwargs)
    return wrapper

# 使用方式
class UserService:
    @transactional
    def create_user_with_profile(self, data: UserCreate) -> User:
        user = self.user_repo.create(data.model_dump())
        profile = self.profile_repo.create({"user_id": user.id, **data.profile})
        return user
```

### 3.3 事务隔离级别

**默认隔离级别**: `READ COMMITTED`（MySQL 默认）

**需要更高隔离级别的场景**:
```python
# 在服务层指定隔离级别
def transfer_funds(self, from_account: int, to_account: int, amount: Decimal):
    with self.db.begin():
        # 设置当前事务的隔离级别
        self.db.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
        
        # 转账逻辑
        from_acc = self.account_repo.get_by_id(from_account)
        to_acc = self.account_repo.get_by_id(to_account)
        
        if from_acc.balance < amount:
            raise BusinessException("余额不足", code="INSUFFICIENT_BALANCE")
        
        from_acc.balance -= amount
        to_acc.balance += amount
```

### 3.4 事务最佳实践

1. **保持事务简短**: 事务内只做必要的数据库操作，避免耗时操作（如调用外部 API）
2. **避免长事务**: 长时间持有数据库连接会导致性能问题
3. **合理选择隔离级别**: 根据业务需求选择合适的隔离级别，避免不必要的性能开销
4. **使用 `flush()` 而非 `commit()`**: 在 Repository 层使用 `flush()` 刷新到数据库但不提交，由服务层统一提交

---

## 4. 命名规范

### 4.1 文件命名

| 层级 | 命名模式 | 示例 |
|------|---------|------|
| 接口层 | `{module}.py` | `users.py`, `auth.py`, `perception.py` |
| 服务层 | `{module}_service.py` | `user_service.py`, `auth_service.py` |
| 模型层 | `{module}_model.py` | `user_model.py`, `order_model.py` |
| Repository | `{module}_repo.py` | `user_repo.py`, `order_repo.py` |
| Schema | `{module}_schema.py` | `user_schema.py`, `order_schema.py` |

### 4.2 类命名

| 类型 | 命名模式 | 示例 |
|------|---------|------|
| ORM Model | `{Module}` (PascalCase) | `User`, `Order`, `DataSource` |
| Repository | `{Module}Repository` | `UserRepository`, `OrderRepository` |
| Service | `{Module}Service` | `UserService`, `OrderService` |
| Schema | `{Module}{Type}` | `UserCreate`, `UserResponse`, `UserUpdate` |
| Exception | `{Module}Exception` | `UserException`, `BusinessException` |

### 4.3 函数命名

| 类型 | 命名模式 | 示例 |
|------|---------|------|
| 接口层路由 | `动词_名词` 或 `HTTP 方法` | `create_user`, `get_user`, `list_users` |
| 服务层方法 | `动词_名词` | `create_user`, `validate_user_status` |
| Repository 方法 | `动词_名词` 或 `查询条件` | `get_by_id`, `get_by_email`, `list_active` |

### 4.4 变量命名

- **变量**: `snake_case`（Python 惯例）
- **常量**: `UPPER_SNAKE_CASE`
- **私有属性**: `_leading_underscore`（单下划线）
- **避免缩写**: 使用 `user_id` 而非 `uid`，使用 `password_hash` 而非 `pwd_hash`

---

## 5. 代码组织规范

### 5.1 目录结构

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── users.py          # 用户模块接口
│   │       ├── auth.py           # 认证模块接口
│   │       ├── perception.py     # 感知层接口
│   │       ├── cognition.py      # 认知层接口
│   │       ├── decision.py       # 决策层接口
│   │       ├── execution.py      # 执行层接口
│   │       └── application.py    # 应用层接口
│   ├── services/
│   │   ├── __init__.py
│   │   ├── user_service.py       # 用户服务
│   │   ├── auth_service.py       # 认证服务
│   │   ├── perception_service.py # 感知层服务
│   │   └── ...
│   ├── db/
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # 基础模型类
│   │   │   ├── user_model.py    # 用户模型
│   │   │   └── ...
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── base_repo.py     # 基础 Repository
│   │   │   ├── user_repo.py     # 用户 Repository
│   │   │   └── ...
│   │   ├── session.py           # Session 管理
│   │   └── __init__.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user_schema.py       # 用户 Schema
│   │   ├── base_schema.py       # 基础 Schema
│   │   └── ...
│   ├── core/
│   │   ├── config.py            # 配置管理
│   │   ├── security.py          # 安全工具（JWT、密码哈希）
│   │   ├── dependencies.py      # FastAPI 依赖注入
│   │   ├── exceptions.py        # 自定义异常
│   │   └── decorators.py        # 装饰器（如 @transactional）
│   └── main.py                  # FastAPI 入口
├── tests/
│   ├── api/                     # 接口层测试
│   ├── services/                # 服务层测试
│   └── db/                      # 数据层测试
├── alembic/                     # 数据库迁移
├── requirements.txt
└── STANDARDS.md                 # 本文件
```

### 5.2 导入顺序

```python
# 1. 标准库
import os
import sys
from datetime import datetime
from typing import Optional, List

# 2. 第三方库
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

# 3. 本地模块（按层顺序）
from app.core.config import settings
from app.core.exceptions import BusinessException
from app.db.session import get_db
from app.services.user_service import UserService
from app.schemas.user_schema import UserCreate, UserResponse
```

---

## 6. 错误处理规范

### 6.1 异常层次

```python
# app/core/exceptions.py

from fastapi import HTTPException, status

class BusinessException(Exception):
    """业务异常基类"""
    def __init__(self, message: str, code: str = None, status_code: int = status.HTTP_400_BAD_REQUEST):
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
```

### 6.2 全局异常处理器

```python
# app/main.py

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.exceptions import BusinessException

app = FastAPI()

@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    """业务异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None
        }
    )
```

### 6.3 错误响应格式

**统一响应格式**:
```json
{
  "code": "USER_NOT_FOUND",
  "message": "用户不存在",
  "data": null
}
```

**成功响应格式**:
```json
{
  "code": "SUCCESS",
  "message": "操作成功",
  "data": { ... }
}
```

---

## 7. 依赖注入规范

### 7.1 Session 注入

```python
# app/db/session.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

engine = create_engine(settings.db_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    """FastAPI 依赖: 提供数据库 Session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 7.2 服务层注入

```python
# app/api/v1/users.py

from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.user_service import UserService

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """依赖注入: 创建 UserService 实例"""
    return UserService(db)

@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """创建用户"""
    return user_service.create_user(user_data)
```

---

## 8. 测试规范

### 8.1 测试层次

1. **单元测试**: 测试单个函数或类的方法
2. **集成测试**: 测试多个组件的集成（如 Service + Repository）
3. **API 测试**: 测试 HTTP 接口（使用 FastAPI 的 TestClient）

### 8.2 测试示例

```python
# tests/services/test_user_service.py

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models.base import Base
from app.services.user_service import UserService
from app.schemas.user_schema import UserCreate

@pytest.fixture
def db_session():
    """创建测试数据库 Session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_create_user(db_session):
    """测试创建用户"""
    user_service = UserService(db_session)
    user_data = UserCreate(username="test", email="test@example.com", password="123456")
    user = user_service.create_user(user_data)
    
    assert user.id is not None
    assert user.username == "test"
    assert user.email == "test@example.com"
```

---

## 9. 最佳实践

### 9.1 接口层最佳实践

1. ✅ 使用 Pydantic v2 进行严格的参数校验
2. ✅ 使用 `response_model` 控制响应格式
3. ✅ 使用 FastAPI 的 `Depends` 进行依赖注入
4. ❌ 不在接口层写业务逻辑
5. ❌ 不在接口层直接操作数据库

### 9.2 服务层最佳实践

1. ✅ 在服务层控制事务边界
2. ✅ 保持服务方法的原子性（一个方法做一个业务操作）
3. ✅ 使用自定义异常（`BusinessException`）抛出业务错误
4. ❌ 不在服务层返回 ORM Model（应该转换为 Schema）
5. ❌ 不在服务层处理 HTTP 异常

### 9.3 数据层最佳实践

1. ✅ 使用 Repository 模式封装数据库操作
2. ✅ 使用 `flush()` 而非 `commit()`（事务由服务层控制）
3. ✅ 为常用查询创建专门的方法（如 `get_by_email`）
4. ❌ 不在 Repository 层写业务逻辑
5. ❌ 不在 Repository 层控制事务

### 9.4 Schema 最佳实践

1. ✅ 为创建、更新、响应分别定义 Schema
2. ✅ 使用 Pydantic v2 的 `model_validator` 进行复杂校验
3. ✅ 使用 `model_config = {"from_attributes": True}` 支持从 ORM Model 转换
4. ❌ 不在 Schema 中写业务逻辑
5. ❌ 不返回 ORM Model（应该返回 Schema）

---

## 10. 检查清单

在提交代码前，请检查：

- [ ] 接口层是否只做参数校验和响应格式化？
- [ ] 服务层是否控制了事务边界？
- [ ] 数据层是否没有直接处理业务逻辑？
- [ ] 是否遵循了命名规范？
- [ ] 是否添加了必要的类型注解？
- [ ] 是否处理了可能的异常？
- [ ] 是否编写了单元测试？
- [ ] 是否更新了 API 文档？

---

## 11. 参考资源

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 文档](https://docs.sqlalchemy.org/en/20/)
- [Pydantic v2 文档](https://docs.pydantic.dev/latest/)
- [Domain-Driven Design (DDD)](https://domainlanguage.com/ddd/)
- [Repository 模式](https://martinfowler.com/eaaCatalog/repository.html)

---

**本规范将随着项目发展不断更新和完善。如有疑问或建议，请提交 Issue 或 Pull Request。**
