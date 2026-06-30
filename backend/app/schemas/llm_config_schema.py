"""LLM 配置校验模型."""
from typing import Optional
from pydantic import BaseModel, Field, model_validator


VALID_PROVIDERS = {"openai", "anthropic"}


class LLMConfigBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    provider: str = Field(..., description="openai / anthropic")
    base_url: str = Field(..., min_length=1, max_length=512)
    api_key: str = Field(..., min_length=1)
    model_name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = Field(None, max_length=512)
    is_active: bool = Field(False)
    extra_headers: Optional[str] = Field(None)
    extra_body: Optional[str] = Field(None)
    timeout: str = Field("60")
    max_retries: str = Field("2")

    @model_validator(mode="after")
    def validate_provider(self):
        if self.provider not in VALID_PROVIDERS:
            raise ValueError(f"provider 必须是 {VALID_PROVIDERS}")
        return self


class LLMConfigCreate(LLMConfigBase):
    pass


class LLMConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    provider: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    extra_headers: Optional[str] = None
    extra_body: Optional[str] = None
    timeout: Optional[str] = None
    max_retries: Optional[str] = None

    @model_validator(mode="after")
    def validate_provider(self):
        if self.provider is not None and self.provider not in VALID_PROVIDERS:
            raise ValueError(f"provider 必须是 {VALID_PROVIDERS}")
        return self


class LLMConfigResponse(LLMConfigBase):
    id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


class LLMChatRequest(BaseModel):
    """LLM 调用请求"""
    messages: list[dict] = Field(..., min_length=1, description="对话消息列表")
    config_id: Optional[int] = Field(None, description="指定配置 ID，不传则使用默认激活配置")
    temperature: Optional[float] = Field(0.7, ge=0, le=2)
    max_tokens: Optional[int] = Field(2048, ge=1, le=128000)
    stream: bool = Field(False)


class LLMChatResponse(BaseModel):
    """LLM 调用响应"""
    content: str
    model: str
    usage: Optional[dict] = None
