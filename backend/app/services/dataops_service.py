"""DataOps 数据源业务服务."""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessException, ConflictException, NotFoundException
from app.db.models.data_source_model import DataSource, DataSourceStatus, DataSourceType
from app.db.repositories.data_source_repo import DataSourceRepository
from app.schemas.dataops_schema import (
    ConnectionTestRequest,
    DataSourceCreate,
    DataSourceUpdate,
)
from app.services.dataops_connector import DataSourceConnector


class DataOpsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = DataSourceRepository(db)

    def _to_response(self, row: DataSource) -> dict[str, Any]:
        return {
            "id": row.id,
            "name": row.name,
            "source_type": row.source_type.value if hasattr(row.source_type, "value") else row.source_type,
            "host": row.host,
            "port": row.port,
            "username": row.username,
            "database": row.database,
            "charset": row.charset or "utf8mb4",
            "description": row.description,
            "status": row.status.value if hasattr(row.status, "value") else row.status,
            "is_default": bool(row.is_default),
            "has_password": bool(row.password),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    def _connector_for(self, row: DataSource) -> DataSourceConnector:
        st = row.source_type.value if hasattr(row.source_type, "value") else str(row.source_type)
        return DataSourceConnector(
            source_type=st,
            host=row.host,
            port=row.port,
            username=row.username,
            password=row.password,
            database=row.database,
            charset=row.charset or "utf8mb4",
        )

    def list_sources(self) -> list[dict[str, Any]]:
        self.ensure_seed_doris()
        return [self._to_response(r) for r in self.repo.list()]

    def get_source(self, source_id: int) -> dict[str, Any]:
        row = self.repo.get(source_id)
        if not row:
            raise NotFoundException(f"数据源不存在: {source_id}")
        return self._to_response(row)

    def create_source(self, data: DataSourceCreate) -> dict[str, Any]:
        if self.repo.get_by_name(data.name):
            raise ConflictException(f"数据源名称已存在: {data.name}")
        row = DataSource(
            name=data.name.strip(),
            source_type=DataSourceType(data.source_type),
            host=data.host.strip(),
            port=data.port,
            username=data.username.strip(),
            password=data.password,
            database=data.database.strip() if data.database else None,
            charset=data.charset or "utf8mb4",
            description=data.description,
            status=DataSourceStatus.UNKNOWN,
            is_default=False,
        )
        self.repo.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_response(row)

    def update_source(self, source_id: int, data: DataSourceUpdate) -> dict[str, Any]:
        row = self.repo.get(source_id)
        if not row:
            raise NotFoundException(f"数据源不存在: {source_id}")
        payload = data.model_dump(exclude_unset=True)
        if "name" in payload and payload["name"]:
            other = self.repo.get_by_name(payload["name"])
            if other and other.id != source_id:
                raise ConflictException(f"数据源名称已存在: {payload['name']}")
            row.name = payload["name"].strip()
        for key in ("host", "username", "database", "charset", "description"):
            if key in payload:
                val = payload[key]
                if isinstance(val, str):
                    setattr(row, key, val.strip() or None if key == "database" else val.strip())
                else:
                    setattr(row, key, val)
        if "port" in payload and payload["port"] is not None:
            row.port = payload["port"]
        if "password" in payload and payload["password"] is not None:
            row.password = payload["password"]
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_response(row)

    def delete_source(self, source_id: int) -> None:
        row = self.repo.get(source_id)
        if not row:
            raise NotFoundException(f"数据源不存在: {source_id}")
        self.repo.delete(row)
        self.db.commit()

    def test_connection(self, req: ConnectionTestRequest) -> dict[str, Any]:
        if req.source_id is not None:
            row = self.repo.get(req.source_id)
            if not row:
                raise NotFoundException(f"数据源不存在: {req.source_id}")
            connector = self._connector_for(row)
            try:
                result = connector.test()
                row.status = DataSourceStatus.ONLINE
                self.db.add(row)
                self.db.commit()
                return result
            except Exception:
                row.status = DataSourceStatus.OFFLINE
                self.db.add(row)
                self.db.commit()
                raise

        if not (req.source_type and req.host and req.port and req.username):
            raise BusinessException("探活缺少必要字段", code="TEST_PARAMS_REQUIRED")
        connector = DataSourceConnector(
            source_type=req.source_type,
            host=req.host,
            port=req.port,
            username=req.username,
            password=req.password,
            database=req.database,
            charset=req.charset or "utf8mb4",
        )
        return connector.test()

    def list_databases(self, source_id: int) -> list[str]:
        row = self._require(source_id)
        return self._connector_for(row).list_databases()

    def list_tables(self, source_id: int, database: str) -> list[dict[str, Any]]:
        row = self._require(source_id)
        return self._connector_for(row).list_tables(database)

    def list_columns(self, source_id: int, database: str, table: str) -> list[dict[str, Any]]:
        row = self._require(source_id)
        return self._connector_for(row).list_columns(database, table)

    def sample(
        self, source_id: int, *, database: Optional[str], table: str, limit: int = 10
    ) -> dict[str, Any]:
        row = self._require(source_id)
        return self._connector_for(row).sample(database, table, limit)

    def execute_sql(
        self,
        source_id: int,
        *,
        sql: str,
        database: Optional[str] = None,
        max_rows: int = 200,
    ) -> dict[str, Any]:
        row = self._require(source_id)
        db = database if database is not None else row.database
        return self._connector_for(row).execute(sql, database=db, max_rows=max_rows)

    def _require(self, source_id: int) -> DataSource:
        row = self.repo.get(source_id)
        if not row:
            raise NotFoundException(f"数据源不存在: {source_id}")
        return row

    def ensure_seed_doris(self) -> None:
        """若配置了 DORIS_HOST，幂等写入默认 Doris 源。"""
        if not settings.DORIS_HOST:
            return
        existing = self.repo.get_by_name(settings.DORIS_SOURCE_NAME)
        if existing:
            return
        row = DataSource(
            name=settings.DORIS_SOURCE_NAME,
            source_type=DataSourceType.DORIS,
            host=settings.DORIS_HOST,
            port=settings.DORIS_PORT,
            username=settings.DORIS_USER,
            password=settings.DORIS_PASSWORD,
            database=settings.DORIS_DATABASE or None,
            charset=settings.DORIS_CHARSET or "utf8mb4",
            description="环境变量种子 · Doris 数仓",
            status=DataSourceStatus.UNKNOWN,
            is_default=True,
        )
        self.repo.add(row)
        self.db.commit()
