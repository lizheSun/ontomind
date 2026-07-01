"""MCP 工具/服务模型."""
from sqlalchemy import Column, String, Text, Boolean, Enum as SAEnum, JSON
import enum
from app.db.models.base import BaseModel


class MCPType(str, enum.Enum):
    sse = "sse"
    stdio = "stdio"
    http = "http"


class MCPConfig(BaseModel):
    """MCP 工具/服务配置表"""

    __tablename__ = "mcp_configs"

    name = Column(String(128), nullable=False, comment="MCP 名称")
    mcp_type = Column(
        SAEnum(MCPType, name="mcp_type_enum", create_type=False),
        nullable=False,
        comment="MCP 类型: sse / stdio / http",
    )
    url = Column(String(512), nullable=True, comment="连接地址（sse/http 模式）")
    command = Column(Text, nullable=True, comment="启动命令（stdio 模式）")
    args = Column(JSON, nullable=True, comment="启动参数")
    env_vars = Column(JSON, nullable=True, comment="环境变量")
    headers = Column(JSON, nullable=True, comment="自定义请求头")
    auto_discovery_url = Column(String(512), nullable=True, comment="自动发现的 API 文档 URL")
    auto_discovery_enabled = Column(Boolean, default=False, comment="是否启用自动发现")
    tools_manifest = Column(JSON, nullable=True, comment="工具清单（自动/手动）")
    description = Column(Text, nullable=True, comment="描述")
    is_active = Column(Boolean, default=True, comment="是否启用")

    def to_response_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "mcp_type": self.mcp_type.value if hasattr(self.mcp_type, "value") else self.mcp_type,
            "url": self.url,
            "command": self.command,
            "args": self.args,
            "env_vars": self.env_vars,
            "headers": self.headers,
            "auto_discovery_url": self.auto_discovery_url,
            "auto_discovery_enabled": bool(self.auto_discovery_enabled),
            "tools_manifest": self.tools_manifest,
            "description": self.description,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
