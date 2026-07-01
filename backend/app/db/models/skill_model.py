"""Skill 技能模块模型."""
from sqlalchemy import Column, String, Text, Boolean, DateTime, Enum as SAEnum, JSON
import enum
from app.db.models.base import BaseModel


class SkillType(str, enum.Enum):
    docker = "docker"
    mcp = "mcp"
    script = "script"
    api = "api"


class Skill(BaseModel):
    """技能模块表（全局共享，多 Agent 可引用）"""

    __tablename__ = "skills"

    name = Column(String(128), nullable=False, comment="技能名称")
    skill_type = Column(
        SAEnum(SkillType, name="skill_type_enum", create_type=False),
        nullable=False,
        comment="技能类型: docker / mcp / script / api",
    )
    docker_image = Column(String(256), nullable=True, comment="Docker 镜像（skill_type=docker）")
    entrypoint = Column(Text, nullable=True, comment="启动/入口命令")
    install_cmd = Column(Text, nullable=True, comment="一键安装命令")
    parameters_schema = Column(JSON, nullable=True, comment="参数定义（JSON Schema）")
    output_schema = Column(JSON, nullable=True, comment="输出定义（JSON Schema）")
    env_vars = Column(JSON, nullable=True, comment="环境变量模板")
    description = Column(Text, nullable=True, comment="描述")
    tags = Column(JSON, nullable=True, comment="标签分类")
    icon = Column(String(128), nullable=True, comment="图标（ant-design icon 名称）")
    is_installed = Column(Boolean, default=False, comment="是否已安装")
    installed_at = Column(DateTime(timezone=True), nullable=True, comment="安装时间")
    is_active = Column(Boolean, default=True, comment="是否启用")

    def to_response_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "skill_type": self.skill_type.value if hasattr(self.skill_type, "value") else self.skill_type,
            "docker_image": self.docker_image,
            "entrypoint": self.entrypoint,
            "install_cmd": self.install_cmd,
            "parameters_schema": self.parameters_schema,
            "output_schema": self.output_schema,
            "env_vars": self.env_vars,
            "description": self.description,
            "tags": self.tags,
            "icon": self.icon,
            "is_installed": bool(self.is_installed),
            "installed_at": self.installed_at.isoformat() if self.installed_at else None,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
