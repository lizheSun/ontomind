# OntoMind 代码重构指南

> **版本**: v1.0.0  
> **更新日期**: 2026-06-29  
> **适用范围**: 将现有代码重构为符合新开发规范的代码结构

---

## 目录

1. [概述](#1-概述)
2. [重构步骤](#2-重构步骤)
3. [示例：重构 perception.py](#3-示例重构-perceptionpy)
4. [检查清单](#4-检查清单)

---

## 1. 概述

### 1.1 为什么要重构？

新的开发规范采用了**三层架构**（接口层、服务层、数据层），具有以下优势：

1. **职责清晰**: 每层只负责自己的职责
2. **易于维护**: 修改业务逻辑不会影响接口层
3. **易于测试**: 可以单独测试每一层
4. **代码复用**: 服务层可以被多个接口层调用

### 1.2 重构目标

将现有的 API 文件（如 `perception.py`、`cognition.py` 等）重构为符合三层架构的代码。

---

## 2. 重构步骤

### 2.1 步骤概览

1. **创建 Model**（如果不存在）：在 `app/db/models/` 目录下创建 ORM Model
2. **创建 Repository**：在 `app/db/repositories/` 目录下创建 Repository 类
3. **创建 Schema**：在 `app/schemas/` 目录下创建 Pydantic Schema
4. **创建 Service**：在 `app/services/` 目录下创建 Service 类
5. **重构 API**：修改 `app/api/v1/` 目录下的 API 文件，使其调用 Service 层

### 2.2 详细步骤

#### 步骤 1: 创建 Model

**文件位置**: `app/db/models/{module}_model.py`

**示例**:
```python
# app/db/models/data_source_model.py

from sqlalchemy import Column, String, Integer, DateTime, Boolean
from sqlalchemy.sql import func
from app.db.models.base import BaseModel

class DataSource(BaseModel):
    __tablename__ = "data_sources"
    
    name = Column(String(100), nullable=False, comment="数据源名称")
    type = Column(String(50), nullable=False, comment="数据源类型")
    host = Column(String(255), nullable=True, comment="主机地址")
    port = Column(Integer, nullable=True, comment="端口")
    username = Column(String(100), nullable=True, comment="用户名")
    password = Column(String(255), nullable=True, comment="密码")
    is_active = Column(Boolean, default=True, comment="是否激活")
    
    def __repr__(self):
        return f"<DataSource(id={self.id}, name={self.name})>"
```

#### 步骤 2: 创建 Repository

**文件位置**: `app/db/repositories/{module}_repo.py`

**示例**:
```python
# app/db/repositories/data_source_repo.py

from typing import Optional, List
from sqlalchemy.orm import Session
from app.db.models.data_source_model import DataSource
from app.db.repositories.base_repo import BaseRepository

class DataSourceRepository(BaseRepository[DataSource]):
    def __init__(self, db: Session):
        super().__init__(DataSource, db)
    
    def get_by_name(self, name: str) -> Optional[DataSource]:
        """根据名称查询数据源"""
        return self.db.query(DataSource).filter(DataSource.name == name).first()
    
    def get_active_sources(self) -> List[DataSource]:
        """查询所有激活的数据源"""
        return self.db.query(DataSource).filter(DataSource.is_active == True).all()
```

#### 步骤 3: 创建 Schema

**文件位置**: `app/schemas/{module}_schema.py`

**示例**:
```python
# app/schemas/data_source_schema.py

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class DataSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., min_length=1, max_length=50)
    host: Optional[str] = None
    port: Optional[int] = None

class DataSourceCreate(DataSourceBase):
    password: Optional[str] = None

class DataSourceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class DataSourceResponse(DataSourceBase):
    id: int
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}
```

#### 步骤 4: 创建 Service

**文件位置**: `app/services/{module}_service.py`

**示例**:
```python
# app/services/data_source_service.py

from sqlalchemy.orm import Session
from app.db.repositories.data_source_repo import DataSourceRepository
from app.schemas.data_source_schema import DataSourceCreate, DataSourceUpdate
from app.core.exceptions import BusinessException, NotFoundException

class DataSourceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DataSourceRepository(db)
    
    def create_data_source(self, data: DataSourceCreate) -> dict:
        """创建数据源"""
        with self.db.begin():
            # 检查名称是否已存在
            if self.repo.get_by_name(data.name):
                raise BusinessException("数据源名称已存在", code="DATA_SOURCE_NAME_EXISTS")
            
            # 创建数据源
            data_dict = data.model_dump()
            data_source = self.repo.create(data_dict)
            
            return self._to_response(data_source)
    
    def get_data_source(self, id: int) -> dict:
        """获取数据源详情"""
        data_source = self.repo.get_by_id(id)
        if not data_source:
            raise NotFoundException(f"数据源不存在: {id}")
        return self._to_response(data_source)
    
    def _to_response(self, data_source) -> dict:
        """转换为响应格式"""
        return {
            "id": data_source.id,
            "name": data_source.name,
            "type": data_source.type,
            "host": data_source.host,
            "port": data_source.port,
            "is_active": data_source.is_active,
            "created_at": data_source.created_at,
            "updated_at": data_source.updated_at,
        }
```

#### 步骤 5: 重构 API

**文件位置**: `app/api/v1/{module}.py`

**示例**:
```python
# app/api/v1/perception.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.services.data_source_service import DataSourceService
from app.schemas.data_source_schema import DataSourceCreate, DataSourceResponse

router = APIRouter(prefix="/datasources", tags=["数据源管理"])

def get_data_source_service(db: Session = Depends(get_db)) -> DataSourceService:
    return DataSourceService(db)

@router.post("", response_model=dict)
async def create_data_source(
    data: DataSourceCreate,
    service: DataSourceService = Depends(get_data_source_service)
):
    """创建数据源"""
    result = service.create_data_source(data)
    return {"code": "SUCCESS", "message": "创建成功", "data": result}

@router.get("/{id}", response_model=dict)
async def get_data_source(
    id: int,
    service: DataSourceService = Depends(get_data_source_service)
):
    """获取数据源详情"""
    result = service.get_data_source(id)
    return {"code": "SUCCESS", "message": "操作成功", "data": result}
```

---

## 3. 示例：重构 perception.py

### 3.1 原代码分析

**原文件**: `app/api/v1/perception.py`

**问题**:
1. 直接在接口层返回硬编码数据
2. 没有调用服务层
3. 没有使用 Pydantic Schema 进行参数校验

### 3.2 重构后的代码

**Service 层**: `app/services/perception_service.py`

```python
# app/services/perception_service.py

from sqlalchemy.orm import Session
from app.core.exceptions import BusinessException

class PerceptionService:
    def __init__(self, db: Session):
        self.db = db
    
    def list_data_sources(self, skip: int = 0, limit: int = 100) -> list:
        """获取数据源列表"""
        # TODO: 实际实现需要从数据库查询
        # 这里返回示例数据
        return [
            {"id": 1, "name": "MySQL 数据库", "type": "mysql"},
            {"id": 2, "name": "MongoDB", "type": "mongodb"}
        ]
    
    def create_data_source(self, data: dict) -> dict:
        """创建数据源"""
        with self.db.begin():
            # TODO: 实际实现需要保存到数据库
            return {"id": 3, "name": data.get("name"), "type": data.get("type")}
```

**接口层**: `app/api/v1/perception.py`

```python
# app/api/v1/perception.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.services.perception_service import PerceptionService

router = APIRouter()

def get_perception_service(db: Session = Depends(get_db)) -> PerceptionService:
    return PerceptionService(db)

@router.get("/datasources", response_model=dict)
async def list_data_sources(
    skip: int = 0,
    limit: int = 100,
    service: PerceptionService = Depends(get_perception_service)
):
    """获取数据源列表"""
    result = service.list_data_sources(skip, limit)
    return {"code": "SUCCESS", "message": "操作成功", "data": result, "total": len(result)}

@router.post("/datasources", response_model=dict)
async def create_data_source(
    data: dict,
    service: PerceptionService = Depends(get_perception_service)
):
    """创建数据源"""
    result = service.create_data_source(data)
    return {"code": "SUCCESS", "message": "创建成功", "data": result}
```

---

## 4. 检查清单

在重构完成后，请检查：

- [ ] 是否创建了 Model 文件？
- [ ] 是否创建了 Repository 文件？
- [ ] 是否创建了 Schema 文件？
- [ ] 是否创建了 Service 文件？
- [ ] 接口层是否只调用 Service 层？
- [ ] Service 层是否控制了事务边界？
- [ ] 是否使用了 Pydantic Schema 进行参数校验？
- [ ] 是否使用了统一的响应格式？
- [ ] 是否处理了可能的异常？
- [ ] 是否添加了必要的类型注解？

---

## 5. 常见问题

### 5.1 如何处理跨模块调用？

**问题**: Service A 需要调用 Service B 的方法。

**解决方案**: 在 Service A 中创建 Service B 的实例。

```python
# app/services/order_service.py

class OrderService:
    def __init__(self, db: Session):
        self.db = db
        self.order_repo = OrderRepository(db)
        self.inventory_service = InventoryService(db)  # 调用其他 Service
    
    def create_order(self, data: OrderCreate):
        with self.db.begin():
            # 创建订单
            order = self.order_repo.create(data.model_dump())
            
            # 扣减库存（调用其他 Service）
            self.inventory_service.reduce_stock(data.product_id, data.quantity)
            
            return order
```

### 5.2 如何处理复杂查询？

**问题**: 需要在 Repository 层实现复杂查询（如多表连接）。

**解决方案**: 在 Repository 中添加专门的查询方法。

```python
# app/db/repositories/order_repo.py

class OrderRepository(BaseRepository[Order]):
    def get_orders_with_items(self, user_id: int) -> list:
        """获取订单及其订单项"""
        return (
            self.db.query(Order)
            .options(joinedload(Order.items))  # 预加载订单项
            .filter(Order.user_id == user_id)
            .all()
        )
```

---

**本指南将随着项目发展不断更新和完善。如有疑问或建议，请提交 Issue 或 Pull Request。**
