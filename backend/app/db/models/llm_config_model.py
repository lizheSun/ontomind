"""LLM 配置模型."""
from sqlalchemy import Column, String, Text, Boolean, Enum as SAEnum
import enum
from app.db.models.base import BaseModel


class LLMProvider(str, enum.Enum):
    openai = "openai"
    anthropic = "anthropic"


class LLMConfig(BaseModel):
    """LLM 服务配置表"""

    __tablename__ = "llm_configs"

    name = Column(String(128), nullable=False, comment="配置名称")
    provider = Column(
        SAEnum(LLMProvider, name="llm_provider_enum", create_type=False),
        nullable=False,
        comment="服务协议: openai / anthropic",
    )
    base_url = Column(String(512), nullable=False, comment="API Base URL")
    api_key = Column(Text, nullable=False, comment="API Key（加密存储）")
    model_name = Column(String(256), nullable=False, comment="模型名称")
    description = Column(String(512), nullable=True, comment="配置描述")
    is_active = Column(Boolean, default=False, comment="是否设为默认使用")
    extra_headers = Column(Text, nullable=True, comment="额外请求头 JSON")
    extra_body = Column(Text, nullable=True, comment="额外请求体参数 JSON")
    timeout = Column(String(16), nullable=True, default="60", comment="请求超时（秒）")
    max_retries = Column(String(8), nullable=True, default="2", comment="最大重试次数")

    def to_response_dict(self) -> dict:
        provider_val = self.provider
        if hasattr(provider_val, "value"):
            provider_val = provider_val.value
        return {
            "id": self.id,
            "name": self.name,
            "provider": provider_val,
            "base_url": self.base_url,
            "api_key": self.api_key,
            "model_name": self.model_name,
            "description": self.description,
            "is_active": bool(self.is_active),
            "extra_headers": self.extra_headers,
            "extra_body": self.extra_body,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
