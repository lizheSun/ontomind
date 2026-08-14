"""数据源 ORM — DataOps 资产地图 · 数据仓库."""
from __future__ import annotations

import enum

from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy import Enum as SAEnum

from app.db.models.base import BaseModel


class DataSourceType(str, enum.Enum):
    DORIS = "doris"
    MYSQL = "mysql"
    HIVE = "hive"


class DataSourceStatus(str, enum.Enum):
    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"


class DataSource(BaseModel):
    """外部数据源连接配置（密码不落前端列表明文）。"""

    __tablename__ = "data_sources"
    __table_args__ = {"comment": "DataOps 数据源"}

    name = Column(String(128), nullable=False, unique=True, comment="显示名称")
    source_type = Column(
        SAEnum(DataSourceType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        comment="doris / mysql / hive",
    )
    host = Column(String(256), nullable=False, comment="主机")
    port = Column(Integer, nullable=False, comment="端口")
    username = Column(String(128), nullable=False, comment="用户名")
    password = Column(Text, nullable=True, comment="密码（服务端存储）")
    database = Column(String(128), nullable=True, comment="默认库")
    charset = Column(String(32), nullable=False, default="utf8mb4", comment="字符集")
    description = Column(String(512), nullable=True, comment="备注")
    status = Column(
        SAEnum(DataSourceStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=DataSourceStatus.UNKNOWN,
        comment="最近探活状态",
    )
    is_default = Column(Boolean, nullable=False, default=False, comment="是否默认种子源")
