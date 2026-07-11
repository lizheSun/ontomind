"""数据平台-数据源 Schema：Create/Update/Read。密码字段永不出 Read。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, SecretStr


Dialect = Literal["mysql", "postgresql", "sqlite", "mysql_readonly"]
DsStatus = Literal["active", "inactive", "error"]


class DpDataSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="数据源名称")
    source_type: str = Field(..., min_length=1, max_length=32, description="类型")
    dialect: Dialect = Field(..., description="方言")
    host: Optional[str] = Field(None, max_length=255, description="主机")
    port: Optional[int] = Field(None, ge=1, le=65535, description="端口")
    username: Optional[str] = Field(None, max_length=128, description="用户名")
    database: str = Field(..., min_length=1, max_length=128, description="数据库名")
    default_schema: Optional[str] = Field(None, max_length=128, description="默认 schema")
    charset: str = Field("utf8mb4", max_length=32, description="字符集")
    description: Optional[str] = Field(None, description="描述")
    read_only_flag: bool = Field(True, description="只读标记")
    extra_params: Optional[dict[str, Any]] = Field(None, description="额外连接参数")


class DpDataSourceCreate(DpDataSourceBase):
    password: Optional[SecretStr] = Field(None, description="密码（明文，仅创建时传入；后端 Fernet 加密后落库）")


class DpDataSourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    source_type: Optional[str] = Field(None, max_length=32)
    dialect: Optional[Dialect] = None
    host: Optional[str] = Field(None, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: Optional[str] = Field(None, max_length=128)
    password: Optional[SecretStr] = Field(None, description="留空/未提供 = 保留原密码")
    database: Optional[str] = Field(None, max_length=128)
    default_schema: Optional[str] = Field(None, max_length=128)
    charset: Optional[str] = Field(None, max_length=32)
    description: Optional[str] = None
    status: Optional[DsStatus] = None
    read_only_flag: Optional[bool] = None
    extra_params: Optional[dict[str, Any]] = None


class DpDataSourceRead(BaseModel):
    """读取响应：绝不含 password / password_enc。"""
    id: int
    name: str
    source_type: str
    dialect: Dialect
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    database: str
    default_schema: Optional[str] = None
    charset: str
    description: Optional[str] = None
    status: DsStatus
    read_only_flag: bool
    has_password: bool = Field(..., description="是否已存密码（用于前端 UI）")
    owner_user_id: int
    created_by_user_id: int
    extra_params: Optional[dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DpDataSourceTestResult(BaseModel):
    """POST /sources/{id}/test 返回。"""
    ok: bool
    elapsed_ms: int
    server_version: Optional[str] = None
    error: Optional[str] = None
