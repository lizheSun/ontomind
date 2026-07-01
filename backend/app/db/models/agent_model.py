"""Agent 智能体定义模型."""
from sqlalchemy import Column, String, Integer, Text, Boolean, Enum as SAEnum, JSON
import enum
from app.db.models.base import BaseModel


class AgentType(str, enum.Enum):
    openclaw = "openclaw"
    opencode = "opencode"
    harness = "harness"
    custom = "custom"


class RuntimeType(str, enum.Enum):
    docker = "docker"
    python = "python"
    node = "node"
    binary = "binary"


class Agent(BaseModel):
    """Agent 智能体定义表"""

    __tablename__ = "agents"

    name = Column(String(128), nullable=False, comment="Agent 名称")
    agent_type = Column(
        SAEnum(AgentType, name="agent_type_enum", create_type=False),
        nullable=False,
        comment="Agent 类型: openclaw / opencode / harness / custom",
    )
    version = Column(String(32), default="latest", comment="版本号")
    runtime = Column(
        SAEnum(RuntimeType, name="runtime_type_enum", create_type=False),
        nullable=False,
        comment="运行方式: docker / python / node / binary",
    )
    docker_image = Column(String(256), nullable=True, comment="Docker 镜像地址")
    entrypoint = Column(Text, nullable=True, comment="启动命令/入口脚本")
    env_template = Column(JSON, nullable=True, comment="环境变量模板")
    config_template = Column(Text, nullable=True, comment="配置文件模板")
    ports = Column(JSON, nullable=True, comment="需要暴露的端口列表")
    volume_mounts = Column(JSON, nullable=True, comment="挂载卷配置")
    resource_limit = Column(JSON, nullable=True, comment="资源限制（cpu/memory）")
    skill_ids = Column(JSON, nullable=True, comment="关联的技能 ID 列表")
    description = Column(Text, nullable=True, comment="描述")
    is_active = Column(Boolean, default=True, comment="是否启用")

    def to_response_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "agent_type": self.agent_type.value if hasattr(self.agent_type, "value") else self.agent_type,
            "version": self.version,
            "runtime": self.runtime.value if hasattr(self.runtime, "value") else self.runtime,
            "docker_image": self.docker_image,
            "entrypoint": self.entrypoint,
            "env_template": self.env_template,
            "config_template": self.config_template,
            "ports": self.ports,
            "volume_mounts": self.volume_mounts,
            "resource_limit": self.resource_limit,
            "skill_ids": self.skill_ids,
            "description": self.description,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
