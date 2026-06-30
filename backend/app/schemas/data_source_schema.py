"""数据源校验模型."""
from typing import Optional
from pydantic import BaseModel, Field


class DataSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    source_type: str = Field(..., min_length=1, max_length=50)
    host: Optional[str] = Field(None, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, max_length=255)
    database: Optional[str] = Field(None, max_length=128)
    charset: Optional[str] = Field(None, max_length=32)
    description: Optional[str] = Field(None, max_length=512)
    extra_params: Optional[str] = Field(None)
    is_active: bool = Field(True)


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    source_type: Optional[str] = Field(None, max_length=50)
    host: Optional[str] = Field(None, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, max_length=255)
    database: Optional[str] = Field(None, max_length=128)
    charset: Optional[str] = Field(None, max_length=32)
    description: Optional[str] = Field(None, max_length=512)
    extra_params: Optional[str] = Field(None)
    is_active: Optional[bool] = None
    status: Optional[str] = None


class DataSourceResponse(DataSourceBase):
    id: int
    status: str = "inactive"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


class AutoConfigureRequest(BaseModel):
    """智能配置请求"""
    raw_text: str = Field(..., min_length=1, max_length=10000, description="原始配置文本")


class TestConnectionResponse(BaseModel):
    success: bool
    message: str
    details: Optional[str] = None
    diagnosis: Optional[str] = None
