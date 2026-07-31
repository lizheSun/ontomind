"""容器模板模型 — 可复用的容器创建配置（镜像+命令+端口+环境变量+...）."""
from sqlalchemy import Boolean, Column, Integer, String, Text

from app.db.models.base import BaseModel


class ContainerTemplate(BaseModel):
    __tablename__ = "container_templates"

    name = Column(String(128), nullable=False, unique=True, comment="模板名称")
    image = Column(String(256), nullable=False, comment="镜像名，如 smanx/opencode")
    description = Column(String(512), nullable=True, comment="模板简短描述（卡片展示）")
    long_description = Column(Text, nullable=True, comment="详细说明（Markdown，展开面板展示）")
    icon = Column(String(64), nullable=True, comment="图标 emoji 或 antd icon 名称")
    category = Column(String(64), nullable=True, comment="分类，如 app / db / devtool")
    command = Column(String(512), nullable=True, comment="默认启动命令，覆盖镜像 CMD")
    ports = Column(Text, nullable=True, comment='JSON 数组，如 ["4096:4096"]')
    env_vars = Column(Text, nullable=True, comment='JSON 数组，如 ["K=V"]')
    volumes = Column(Text, nullable=True, comment='JSON 数组，如 ["/h:/c"]')
    restart_policy = Column(String(20), nullable=True, comment="no/always/on-failure/unless-stopped")
    network = Column(String(64), nullable=True, comment="docker 网络")
    extra_args = Column(String(512), nullable=True, comment="docker run 额外参数（镜像名之前）")
    is_builtin = Column(Boolean, nullable=False, server_default="0", comment="是否内置模板")
    sort_order = Column(Integer, nullable=False, server_default="0", comment="排序权重")


__all__ = ["ContainerTemplate"]
