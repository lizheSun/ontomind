"""MCP 校验模型."""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class MCPBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    mcp_type: str = Field(..., description="sse / stdio / http")
    url: Optional[str] = Field(None, max_length=512)
    command: Optional[str] = Field(None, max_length=2000)
    args: Optional[List[str]] = Field(None, description="启动参数")
    env_vars: Optional[Dict[str, Any]] = Field(None)
    headers: Optional[Dict[str, Any]] = Field(None)
    auto_discovery_url: Optional[str] = Field(None, max_length=512)
    auto_discovery_enabled: bool = Field(False)
    tools_manifest: Optional[Dict[str, Any]] = Field(None, description="工具清单")
    description: Optional[str] = Field(None, max_length=2000)
    is_active: bool = Field(True)


class MCPCreate(MCPBase):
    pass


class MCPUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    mcp_type: Optional[str] = None
    url: Optional[str] = Field(None, max_length=512)
    command: Optional[str] = Field(None, max_length=2000)
    args: Optional[List[str]] = None
    env_vars: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, Any]] = None
    auto_discovery_url: Optional[str] = Field(None, max_length=512)
    auto_discovery_enabled: Optional[bool] = None
    tools_manifest: Optional[Dict[str, Any]] = None
    description: Optional[str] = Field(None, max_length=2000)
    is_active: Optional[bool] = None


class MCPResponse(MCPBase):
    id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


class MCPAutoDiscoverRequest(BaseModel):
    """MCP 自动发现请求 — 从任意 API + LLM 推断生成"""
    api_url: str = Field(..., max_length=512, description="API 端点 URL")
    method: str = Field("GET", description="HTTP 方法")
    headers: Optional[Dict[str, Any]] = Field(None, description="请求头")
    request_body_example: Optional[str] = Field(None, description="请求体示例")
    response_body_example: Optional[str] = Field(None, description="响应体示例")
    description_text: Optional[str] = Field(None, description="用自然语言描述这个 API")

    model_config = {"from_attributes": True}
