"""Skill 技能模块模型（T44 — 扩展支持 opencode SKILL.md）.

在原 `skills` 表基础上扩展 opencode SKILL.md 相关字段：
`type / source_path / body_markdown / version / requires_bins` 等。
"""
from enum import Enum

from sqlalchemy import Column, String, Text, Boolean, JSON
from app.db.models.base import BaseModel


class SkillType(str, Enum):
    """Legacy enum retained for callers written against the pre-T44 model."""

    opencode_prompt = "opencode_prompt"
    docker = "docker"
    mcp = "mcp"
    script = "script"
    api = "api"


class Skill(BaseModel):
    """技能模块（扩展支持 opencode SKILL.md）"""

    __tablename__ = "skills"
    __table_args__ = {"comment": "技能模块（扩展支持 opencode SKILL.md）"}

    name = Column(String(128), nullable=False, unique=True, comment="技能名称")
    type = Column(
        String(32),
        nullable=False,
        server_default="opencode_prompt",
        comment="opencode_prompt/docker/mcp/script/api",
    )
    source_path = Column(
        String(512),
        nullable=True,
        comment="opencode SKILL.md 源路径",
    )
    body_markdown = Column(Text, nullable=True, comment="SKILL.md body 内容")
    version = Column(String(32), nullable=True, comment="版本号")
    requires_bins = Column(JSON, nullable=True, comment="依赖的二进制文件列表")
    description = Column(Text, nullable=True, comment="描述")
    parameters_schema = Column(JSON, nullable=True, comment="参数定义（JSON Schema）")
    output_schema = Column(JSON, nullable=True, comment="输出定义（JSON Schema）")
    env_vars = Column(JSON, nullable=True, comment="环境变量模板")
    tags = Column(JSON, nullable=True, comment="标签分类")
    is_installed = Column(
        Boolean,
        nullable=False,
        server_default="0",
        comment="是否已安装",
    )
    is_active = Column(
        Boolean,
        nullable=False,
        server_default="1",
        comment="是否启用",
    )

    def to_response_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
