# OntoMind 设计标准规范

> **版本**: v1.0.0  
> **更新日期**: 2026-06-29  
> **适用范围**: OntoMind 项目 API 设计和数据库设计

---

## 目录

1. [API 设计标准](#1-api-设计标准)
2. [数据库设计标准](#2-数据库设计标准)
3. [错误码定义](#3-错误码定义)
4. [最佳实践](#4-最佳实践)

---

## 1. API 设计标准

### 1.1 RESTful API 规范

#### 1.1.1 资源命名

- **使用名词复数形式**: `/users`, `/orders`, `/datasources`
- **使用小写字母**: `/userProfiles` ❌, `/user-profiles` ✅
- **使用连字符分隔单词**: `/user-profiles` (kebab-case)
- **避免特殊字符**: 不使用下划线、空格等

#### 1.1.2 HTTP 方法

| 方法 | 用途 | 示例 |
|------|------|------|
| GET | 查询资源 | `GET /users` - 获取用户列表 |
| POST | 创建资源 | `POST /users` - 创建用户 |
| PUT | 更新资源（完整） | `PUT /users/{id}` - 更新用户信息 |
| PATCH | 更新资源（部分） | `PATCH /users/{id}` - 部分更新用户 |
| DELETE | 删除资源 | `DELETE /users/{id}` - 删除用户 |

#### 1.1.3 响应状态码

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证 |
| 403 | Forbidden | 无权限 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突（如邮箱已存在） |
| 422 | Unprocessable Entity | 数据验证失败 |
| 500 | Internal Server Error | 服务器内部错误 |

### 1.2 API 版本管理

**URL 路径版本控制**（推荐）:
```
/api/v1/users
/api/v2/users
```

**不推荐**: 使用请求头或查询参数进行版本控制。

### 1.3 请求参数规范

#### 1.3.1 查询参数

**分页参数**:
```
GET /users?skip=0&limit=10
```

**过滤参数**:
```
GET /users?is_active=true&role=admin
```

**排序参数**:
```
GET /users?order_by=created_at&order=desc
```

**搜索参数**:
```
GET /users?q=keyword
```

#### 1.3.2 请求体规范

**创建资源**:
```json
POST /users
{
  "username": "zhangsan",
  "email": "zhangsan@example.com",
  "password": "123456",
  "full_name": "张三"
}
```

**更新资源**:
```json
PUT /users/1
{
  "username": "zhangsan_new",
  "email": "zhangsan_new@example.com"
}
```

### 1.4 响应格式规范

#### 1.4.1 成功响应

**单个资源**:
```json
{
  "code": "SUCCESS",
  "message": "操作成功",
  "data": {
    "id": 1,
    "username": "zhangsan",
    "email": "zhangsan@example.com"
  }
}
```

**资源列表**:
```json
{
  "code": "SUCCESS",
  "message": "操作成功",
  "data": [
    { "id": 1, "username": "zhangsan" },
    { "id": 2, "username": "lisi" }
  ],
  "total": 100,
  "skip": 0,
  "limit": 10
}
```

**创建资源**:
```json
{
  "code": "SUCCESS",
  "message": "用户创建成功",
  "data": {
    "id": 1,
    "username": "zhangsan"
  }
}
```

#### 1.4.2 错误响应

**业务错误**:
```json
{
  "code": "EMAIL_EXISTS",
  "message": "邮箱已存在",
  "data": null
}
```

**验证错误**:
```json
{
  "code": "VALIDATION_ERROR",
  "message": "数据验证失败",
  "data": {
    "errors": [
      { "field": "email", "message": "请输入有效的邮箱地址" },
      { "field": "password", "message": "密码长度至少6位" }
    ]
  }
}
```

**系统错误**:
```json
{
  "code": "INTERNAL_ERROR",
  "message": "服务器内部错误",
  "data": null
}
```

### 1.5 认证和授权

#### 1.5.1 认证方式

**JWT Token**（推荐）:
```
Authorization: Bearer <token>
```

**OAuth 2.0**: 用于第三方登录（如 GitHub、Google）

#### 1.5.2 Token 管理

- **Access Token**: 短期有效（如 30 分钟）
- **Refresh Token**: 长期有效（如 7 天）
- **Token 刷新**: 使用 Refresh Token 获取新的 Access Token

#### 1.5.3 权限控制

**基于角色的访问控制 (RBAC)**:
```
用户角色: admin, user, guest
资源权限: user:create, user:read, user:update, user:delete
```

**权限检查**:
```python
@router.post("/users", dependencies=[Depends(require_permissions("user:create"))])
async def create_user(...):
    ...
```

### 1.6 API 文档规范

**使用 FastAPI 自动生成文档**:
- Swagger UI: `/api/docs`
- ReDoc: `/api/redoc`

**文档注解规范**:
```python
@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建用户",
    description="创建新用户，需要管理员权限",
    responses={
        201: {"description": "用户创建成功"},
        400: {"description": "请求参数错误"},
        409: {"description": "用户名或邮箱已存在"}
    }
)
async def create_user(...):
    ...
```

---

## 2. 数据库设计标准

### 2.1 表命名规范

- **使用小写字母**: `users` ✅, `Users` ❌
- **使用下划线分隔单词**: `user_profiles` ✅, `userProfiles` ❌
- **使用复数形式**: `users` ✅, `user` ❌
- **避免保留字**: 不使用 `order`, `select` 等 SQL 保留字

**示例**:
```sql
-- 用户表
CREATE TABLE users (...);

-- 用户资料表
CREATE TABLE user_profiles (...);

-- 数据源表
CREATE TABLE data_sources (...);
```

### 2.2 字段命名规范

- **使用小写字母和下划线**: `created_at` ✅, `createdAt` ❌
- **使用描述性名称**: `email` ✅, `e` ❌
- **外键命名**: `{table_singular}_id` (如 `user_id`, `order_id`)
- **布尔字段**: 使用 `is_` 前缀 (如 `is_active`, `is_deleted`)
- **时间字段**: 使用 `_at` 后缀 (如 `created_at`, `updated_at`)

**示例**:
```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
    email = Column(String(100), unique=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

### 2.3 字段类型规范

| 数据类型 | Python 类型 | 说明 |
|----------|-------------|------|
| 主键 | `Integer` | 自增 ID |
| 字符串 | `String(length)` | 指定长度 |
| 文本 | `Text` | 长文本 |
| 整数 | `Integer` | 整数 |
| 浮点数 | `Float` | 浮点数 |
|  Decimal | `Numeric(precision, scale)` | 精确小数（如金额） |
| 布尔值 | `Boolean` | 布尔值 |
| 日期 | `Date` | 日期 |
| 时间 | `DateTime` | 日期时间 |
| JSON | `JSON` | JSON 数据 |
| 枚举 | `Enum` | 枚举类型 |

**示例**:
```python
class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    order_no = Column(String(50), unique=True, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)  # 总金额，精确到分
    status = Column(Enum(OrderStatus), nullable=False)
    items = Column(JSON, nullable=False)  # 订单项
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 2.4 索引规范

#### 2.4.1 索引类型

- **主键索引**: 自动创建
- **唯一索引**: 保证唯一性（如 `username`, `email`）
- **普通索引**: 提高查询速度（如 `created_at`, `status`）
- **复合索引**: 多字段查询（如 `(user_id, created_at)`）

#### 2.4.2 索引创建规范

**自动创建**:
```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)  # 主键索引自动创建
    username = Column(String(50), unique=True, index=True)  # 唯一索引
    email = Column(String(100), unique=True, index=True)  # 唯一索引
    created_at = Column(DateTime, index=True)  # 普通索引
```

**手动创建复合索引**:
```python
from sqlalchemy import Index

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False)
    
    # 复合索引：提高按用户和创建时间查询的速度
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
    )
```

#### 2.4.3 索引最佳实践

1. ✅ 为常用查询字段创建索引
2. ✅ 为外键字段创建索引
3. ✅ 使用复合索引优化多字段查询
4. ❌ 避免过度索引（影响写入性能）
5. ❌ 避免为低区分度字段创建索引（如 `gender`）

### 2.5 表关系规范

#### 2.5.1 一对一关系

```python
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    profile = relationship("UserProfile", back_populates="user", uselist=False)

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    user = relationship("User", back_populates="profile")
```

#### 2.5.2 一对多关系

```python
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    orders = relationship("Order", back_populates="user")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="orders")
```

#### 2.5.3 多对多关系

```python
# 中间表
user_role = Table(
    "user_role",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    roles = relationship("Role", secondary=user_role, back_populates="users")

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    users = relationship("User", secondary=user_role, back_populates="roles")
```

### 2.6 迁移管理规范

#### 2.6.1 迁移工具

使用 **Alembic** 进行数据库迁移。

#### 2.6.2 迁移文件命名

```
alembic/versions/
├── 001_create_users_table.py
├── 002_add_phone_to_users.py
├── 003_create_orders_table.py
└── ...
```

#### 2.6.3 迁移最佳实践

1. ✅ 每次修改模型都生成迁移文件
2. ✅ 迁移文件要可回滚（实现 `downgrade` 函数）
3. ✅ 在生产环境执行迁移前，先在测试环境验证
4. ❌ 不要手动修改数据库结构（要通过迁移文件）
5. ❌ 不要删除旧的迁移文件

---

## 3. 错误码定义

### 3.1 错误码格式

**格式**: `{模块}_{错误类型}`

**示例**:
- `USER_NOT_FOUND`: 用户不存在
- `EMAIL_EXISTS`: 邮箱已存在
- `PERMISSION_DENIED`: 权限不足

### 3.2 通用错误码

| 错误码 | 含义 | HTTP 状态码 |
|--------|------|-------------|
| SUCCESS | 操作成功 | 200 |
| BAD_REQUEST | 请求参数错误 | 400 |
| UNAUTHORIZED | 未认证 | 401 |
| PERMISSION_DENIED | 权限不足 | 403 |
| NOT_FOUND | 资源不存在 | 404 |
| RESOURCE_CONFLICT | 资源冲突 | 409 |
| VALIDATION_ERROR | 数据验证失败 | 422 |
| INTERNAL_ERROR | 服务器内部错误 | 500 |

### 3.3 业务错误码

| 错误码 | 含义 | HTTP 状态码 |
|--------|------|-------------|
| USER_NOT_FOUND | 用户不存在 | 404 |
| EMAIL_EXISTS | 邮箱已存在 | 409 |
| USERNAME_EXISTS | 用户名已存在 | 409 |
| INVALID_PASSWORD | 密码错误 | 400 |
| USER_DISABLED | 用户已禁用 | 403 |
| TOKEN_EXPIRED | Token 已过期 | 401 |
| TOKEN_INVALID | Token 无效 | 401 |

---

## 4. 最佳实践

### 4.1 API 设计最佳实践

1. ✅ 使用 RESTful 风格设计 API
2. ✅ 使用复数名词表示资源
3. ✅ 使用 HTTP 状态码表示请求结果
4. ✅ 使用统一的响应格式
5. ✅ 使用版本控制管理 API 变更
6. ✅ 使用 Swagger/OpenAPI 文档化 API
7. ❌ 不在 URL 中使用动词（如 `/users/create`）
8. ❌ 不在响应中返回敏感信息（如密码哈希）

### 4.2 数据库设计最佳实践

1. ✅ 使用 InnoDB 存储引擎（支持事务）
2. ✅ 为常用查询字段创建索引
3. ✅ 使用外键约束保证数据一致性
4. ✅ 使用迁移工具管理数据库变更
5. ✅ 为表添加 `created_at` 和 `updated_at` 字段
6. ❌ 避免使用 `NULL`（使用默认值代替）
7. ❌ 避免过度规范化（适当冗余提高查询性能）
8. ❌ 避免在大表上创建过多索引

### 4.3 性能优化

#### 4.3.1 API 性能优化

1. **分页**: 避免一次返回过多数据
2. **缓存**: 使用 Redis 缓存热点数据
3. **压缩**: 启用 Gzip 压缩
4. **CDN**: 静态资源使用 CDN 加速

#### 4.3.2 数据库性能优化

1. **索引优化**: 使用 `EXPLAIN` 分析查询计划
2. **查询优化**: 避免 `SELECT *`，只查询需要的字段
3. **连接优化**: 避免过多的表连接
4. **读写分离**: 主库写，从库读

---

**本规范将随着项目发展不断更新和完善。如有疑问或建议，请提交 Issue 或 Pull Request。**
