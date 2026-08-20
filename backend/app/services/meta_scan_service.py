"""元数据扫描服务。"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.db.models.data_source_model import DataSource
from app.db.models.meta_model import JobKind, MetaColumn, MetaScanJob, MetaTable, ScanStatus
from app.db.repositories.data_source_repo import DataSourceRepository
from app.db.repositories.meta_repo import (
    MetaColumnRepository,
    MetaScanJobRepository,
    MetaTableRepository,
)
from app.schemas.metadata_schema import MetaColumnUpdate, MetaScanCreate, MetaTableUpdate
from app.services.dataops_connector import DataSourceConnector
from app.services.job_runner import open_job_session, run_in_background

logger = logging.getLogger(__name__)

_BATCH_SIZE = 20


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MetaScanService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.jobs = MetaScanJobRepository(db)
        self.tables = MetaTableRepository(db)
        self.columns = MetaColumnRepository(db)
        self.sources = DataSourceRepository(db)

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

    def create_scan(self, req: MetaScanCreate) -> MetaScanJob:
        src = self.sources.get(req.source_id)
        if not src:
            raise NotFoundException(f"数据源不存在: {req.source_id}")
        job = MetaScanJob(
            source_id=req.source_id,
            database=req.database.strip(),
            job_kind=JobKind.SCAN,
            status=ScanStatus.PENDING,
            progress=0.0,
            with_profile=bool(req.with_profile),
            tables_json=list(req.tables) if req.tables else None,
        )
        self.jobs.add(job)
        self.db.commit()
        self.db.refresh(job)
        job_id = job.id
        run_in_background(MetaScanService._run_scan_entrypoint, job_id)
        return job

    @staticmethod
    def _run_scan_entrypoint(job_id: int) -> None:
        db = open_job_session()
        try:
            MetaScanService(db)._run_scan(job_id)
        finally:
            db.close()

    def get_scan(self, job_id: int) -> MetaScanJob:
        job = self.jobs.get(job_id)
        if not job:
            raise NotFoundException(f"扫描任务不存在: {job_id}")
        return job

    def list_scans(
        self,
        *,
        source_id: Optional[int] = None,
        database: Optional[str] = None,
        job_kind: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MetaScanJob]:
        return self.jobs.list(
            source_id=source_id,
            database=database,
            job_kind=job_kind,
            status=status,
            limit=limit,
            offset=offset,
        )

    def _run_scan(self, job_id: int) -> None:
        job = self.jobs.get(job_id)
        if not job:
            return
        started = time.perf_counter()
        job.status = ScanStatus.RUNNING
        job.started_at = _utcnow()
        job.progress = 0.0
        job.error_detail = None
        self.db.add(job)
        self.db.commit()

        warnings: list[str] = []
        table_count = 0
        column_count = 0
        profiled_count = 0
        try:
            src = self.sources.get(job.source_id)
            if not src:
                raise NotFoundException(f"数据源不存在: {job.source_id}")
            connector = self._connector_for(src)
            meta_tables = connector.list_tables_meta(job.database)
            wanted = set(job.tables_json) if job.tables_json else None
            if wanted is not None:
                meta_tables = [t for t in meta_tables if t.get("name") in wanted]

            total = max(len(meta_tables), 1)
            names = [str(t["name"]) for t in meta_tables]

            upserted: list[MetaTable] = []
            for tmeta in meta_tables:
                row = self._upsert_table(job.source_id, job.database, tmeta)
                upserted.append(row)
            table_count = len(upserted)
            self.db.commit()

            for i in range(0, len(names), _BATCH_SIZE):
                batch = names[i : i + _BATCH_SIZE]
                cols_map = connector.batch_columns(job.database, batch)
                for tname in batch:
                    mt = next((x for x in upserted if x.table_name == tname), None)
                    if not mt:
                        continue
                    cols = cols_map.get(tname) or []
                    for cmeta in cols:
                        self._upsert_column(mt.id, cmeta)
                        column_count += 1
                    mt.column_count = len(cols)
                    self.db.add(mt)
                self.db.commit()

                if job.with_profile:
                    for tname in batch:
                        mt = next((x for x in upserted if x.table_name == tname), None)
                        if not mt:
                            continue
                        cols = self.columns.list_by_table(mt.id)
                        profile_cols = cols
                        if len(cols) > 200:
                            profile_cols = cols[:50]
                            warnings.append(f"{tname}: column_count={len(cols)} 仅画像前 50 列")
                        for col in profile_cols:
                            try:
                                profile = connector.profile_column(
                                    job.database, tname, col.column_name
                                )
                                col.profile_json = profile
                                self.db.add(col)
                                profiled_count += 1
                            except Exception as exc:
                                warnings.append(
                                    f"{tname}.{col.column_name}: profile failed: {exc}"
                                )
                        mt.profiled_at = _utcnow()
                        self.db.add(mt)
                        self.db.commit()

                done = min(i + len(batch), total)
                job.progress = round(done / total, 4)
                self.db.add(job)
                self.db.commit()

            job.status = ScanStatus.SUCCEEDED
            job.progress = 1.0
            job.stats_json = {
                "table_count": table_count,
                "column_count": column_count,
                "profiled_count": profiled_count,
                "warnings": warnings[:100],
            }
            job.finished_at = _utcnow()
            job.duration_ms = int((time.perf_counter() - started) * 1000)
            job.error_detail = None
            self.db.add(job)
            self.db.commit()
        except Exception as exc:
            logger.exception("meta scan failed job_id=%s", job_id)
            job.status = ScanStatus.FAILED
            job.error_detail = str(exc)[:2000]
            job.finished_at = _utcnow()
            job.duration_ms = int((time.perf_counter() - started) * 1000)
            job.stats_json = {
                "table_count": table_count,
                "column_count": column_count,
                "profiled_count": profiled_count,
                "warnings": warnings[:100],
            }
            self.db.add(job)
            self.db.commit()

    def _upsert_table(self, source_id: int, database: str, tmeta: dict[str, Any]) -> MetaTable:
        name = str(tmeta["name"])
        existing = self.tables.get_by_uq(source_id, database, name)
        if existing:
            existing.table_type = tmeta.get("type")
            existing.table_comment = tmeta.get("comment")
            existing.row_count = tmeta.get("row_count")
            existing.engine = tmeta.get("engine")
            self.db.add(existing)
            self.db.flush()
            return existing
        row = MetaTable(
            source_id=source_id,
            database=database,
            table_name=name,
            table_type=tmeta.get("type"),
            table_comment=tmeta.get("comment"),
            row_count=tmeta.get("row_count"),
            engine=tmeta.get("engine"),
        )
        return self.tables.add(row)

    def _upsert_column(self, table_id: int, cmeta: dict[str, Any]) -> MetaColumn:
        cname = str(cmeta["name"])
        existing = self.columns.get_by_uq(table_id, cname)
        if existing:
            existing.ordinal = int(cmeta.get("ordinal") or 0)
            existing.data_type = cmeta.get("data_type") or ""
            existing.column_type = cmeta.get("type") or cmeta.get("data_type")
            existing.nullable = bool(cmeta.get("nullable", True))
            existing.column_key = cmeta.get("key") or ""
            default = cmeta.get("default")
            existing.column_default = None if default is None else str(default)
            existing.extra = cmeta.get("extra") or ""
            existing.column_comment = cmeta.get("comment")
            self.db.add(existing)
            self.db.flush()
            return existing
        row = MetaColumn(
            table_id=table_id,
            column_name=cname,
            ordinal=int(cmeta.get("ordinal") or 0),
            data_type=cmeta.get("data_type") or "",
            column_type=cmeta.get("type") or cmeta.get("data_type"),
            nullable=bool(cmeta.get("nullable", True)),
            column_key=cmeta.get("key") or "",
            column_default=None if cmeta.get("default") is None else str(cmeta.get("default")),
            extra=cmeta.get("extra") or "",
            column_comment=cmeta.get("comment"),
        )
        return self.columns.add(row)

    def list_tables(
        self,
        *,
        source_id: Optional[int] = None,
        database: Optional[str] = None,
        keyword: Optional[str] = None,
        domain: Optional[str] = None,
        annotated: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MetaTable]:
        return self.tables.list(
            source_id=source_id,
            database=database,
            keyword=keyword,
            domain=domain,
            annotated=annotated,
            limit=limit,
            offset=offset,
        )

    def get_table(self, table_id: int) -> MetaTable:
        row = self.tables.get(table_id)
        if not row:
            raise NotFoundException(f"元数据表不存在: {table_id}")
        return row

    def get_table_with_columns(self, table_id: int) -> tuple[MetaTable, list[MetaColumn]]:
        row = self.get_table(table_id)
        cols = self.columns.list_by_table(table_id)
        return row, cols

    def update_table(self, table_id: int, data: MetaTableUpdate) -> MetaTable:
        row = self.get_table(table_id)
        payload = data.model_dump(exclude_unset=True)
        for k, v in payload.items():
            setattr(row, k, v)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update_column(self, column_id: int, data: MetaColumnUpdate) -> MetaColumn:
        row = self.columns.get(column_id)
        if not row:
            raise NotFoundException(f"元数据列不存在: {column_id}")
        payload = data.model_dump(exclude_unset=True)
        for k, v in payload.items():
            setattr(row, k, v)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def profile_one_column(self, column_id: int) -> MetaColumn:
        col = self.columns.get(column_id)
        if not col:
            raise NotFoundException(f"元数据列不存在: {column_id}")
        table = self.tables.get(col.table_id)
        if not table:
            raise NotFoundException(f"元数据表不存在: {col.table_id}")
        src = self.sources.get(table.source_id)
        if not src:
            raise NotFoundException(f"数据源不存在: {table.source_id}")
        connector = self._connector_for(src)
        profile = connector.profile_column(table.database, table.table_name, col.column_name)
        col.profile_json = profile
        table.profiled_at = _utcnow()
        self.db.add(col)
        self.db.add(table)
        self.db.commit()
        self.db.refresh(col)
        return col
