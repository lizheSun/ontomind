"""MCP 工具连接模型（T44 — 扩展支持 opencode 原生格式）.

在原 `mcp_configs` 表基础上重命名为 `mcps` 表，并扩展 opencode 原生 MCP
配置格式（command 数组、transport_type、source 等）。
"""
from enum import Enum

from sqlalchemy import Column, String, Boolean, JSON
from app.db.models.base import BaseModel


class MCP(BaseModel):
    """MCP 工具连接（扩展支持 opencode 原生格式）"""

    __tablename__ = "mcps"
    __table_args__ = {"comment": "MCP 工具连接（扩展支持 opencode 原生格式）"}

    name = Column(String(128), nullable=False, unique=True, comment="MCP 名称")
    transport_type = Column(
        String(32),
        nullable=False,
        server_default="stdio",
        comment="local/remote/sse/stdio/http",
    )
    command = Column(JSON, nullable=True, comment="命令数组（opencode 格式）")
    url = Column(String(512), nullable=True, comment="URL（remote/sse/http）")
    args = Column(JSON, nullable=True, comment="参数")
    env_vars = Column(JSON, nullable=True, comment="环境变量")
    headers = Column(JSON, nullable=True, comment="HTTP 头")
    auto_discovery_url = Column(String(512), nullable=True, comment="自动发现的 API 文档 URL")
    auto_discovery_enabled = Column(
        Boolean,
        nullable=False,
        server_default="0",
        comment="是否启用自动发现",
    )
    tools_manifest = Column(JSON, nullable=True, comment="工具清单")
    source = Column(
        String(32),
        nullable=False,
        server_default="manual",
        comment="manual/opencode_config/auto_discover",
    )
    is_active = Column(
        Boolean,
        nullable=False,
        server_default="1",
        comment="是否启用",
    )

    def to_response_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# Backwards-compat alias: 旧代码 `from app.db.models.mcp_model import MCPConfig`
MCPConfig = MCP


class MCPType(str, Enum):
    """Legacy enum retained for callers written against the pre-T44 model.

    T44 renamed the transport-kind column to `MCP.transport_type` (String) and
    dropped the SA `Enum` column. Downstream services (opencode_sync_service,
    opencode_config_discovery_service) still reference `MCPType.stdio` etc.,
    so this string-enum keeps them working until they migrate.
    """

    stdio = "stdio"
    sse = "sse"
    http = "http"
    local = "local"
    remote = "remote"
