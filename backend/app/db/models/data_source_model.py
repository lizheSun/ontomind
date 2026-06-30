"""数据源配置模型."""
from sqlalchemy import Column, String, Text, Boolean, Integer
from app.db.models.base import BaseModel


class DataSource(BaseModel):
    """数据源连接配置表"""

    __tablename__ = "data_sources"

    name = Column(String(128), nullable=False, comment="数据源名称")
    source_type = Column(String(50), nullable=False, comment="类型: mysql/postgresql/doris/clickhouse/kafka/api/file")
    host = Column(String(255), nullable=True, comment="主机地址")
    port = Column(Integer, nullable=True, comment="端口号")
    username = Column(String(100), nullable=True, comment="用户名")
    password = Column(String(255), nullable=True, comment="密码")
    database = Column(String(128), nullable=True, comment="数据库名")
    charset = Column(String(32), nullable=True, comment="字符集")
    description = Column(String(512), nullable=True, comment="描述")
    status = Column(String(20), default="inactive", comment="状态: active/inactive/error")
    extra_params = Column(Text, nullable=True, comment="额外连接参数 JSON")
    is_active = Column(Boolean, default=True, comment="是否启用")

    def to_response_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "source_type": self.source_type,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "database": self.database,
            "charset": self.charset,
            "description": self.description,
            "status": self.status,
            "extra_params": self.extra_params,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
