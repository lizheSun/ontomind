"""数据平台-数据源模型（T06 完整列定义）。"""
from sqlalchemy import (
    Column, String, Integer, Boolean, Text, ForeignKey, JSON, Enum as SAEnum,
)
from app.db.models.base import BaseModel


class DpDataSource(BaseModel):
    """数据平台-数据源：dp_ 前缀，与 legacy data_sources 并存，密码字段用 Fernet 加密。"""

    __tablename__ = "dp_data_sources"
    __table_args__ = {"comment": "数据平台-数据源（Fernet 加密）"}

    name = Column(String(128), nullable=False, unique=True, comment="数据源名称")
    source_type = Column(String(32), nullable=False, comment="类型: mysql/postgresql/sqlite/…")
    dialect = Column(
        SAEnum("mysql", "postgresql", "sqlite", "mysql_readonly", name="dp_ds_dialect"),
        nullable=False,
        comment="方言：SQLAlchemy engine URL 前缀",
    )
    host = Column(String(255), nullable=True, comment="主机 / hostname")
    port = Column(Integer, nullable=True, comment="端口")
    username = Column(String(128), nullable=True, comment="用户名")
    password_enc = Column(Text, nullable=True, comment="密码密文（Fernet），永不出库明文")
    database = Column(String(128), nullable=False, comment="数据库名")
    default_schema = Column(String(128), nullable=True, comment="默认 schema（PG 用）")
    charset = Column(String(32), nullable=False, server_default="utf8mb4", comment="字符集")
    description = Column(Text, nullable=True, comment="描述")
    status = Column(
        SAEnum("active", "inactive", "error", name="dp_ds_status"),
        nullable=False,
        server_default="active",
        comment="状态: active/inactive/error",
    )
    owner_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, comment="拥有者 user_id",
    )
    created_by_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, comment="创建者 user_id",
    )
    read_only_flag = Column(
        Boolean, nullable=False, server_default="1", comment="只读标记（true = 拒绝写）",
    )
    extra_params = Column(JSON, nullable=True, comment="额外连接参数 JSON")
