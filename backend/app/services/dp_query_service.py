"""数据平台-查询服务：guarded execute + SSE stream + history + saved queries。"""
from __future__ import annotations

import time
from typing import Any, AsyncIterator, Optional

from loguru import logger
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.exceptions import BusinessException, NotFoundException
from app.core.sql_guard import SqlGuardError, validate_and_shape
from app.db.repositories.dp_query_history_repo import DpQueryHistoryRepository
from app.db.repositories.dp_sql_query_repo import DpSqlQueryRepository
from app.schemas.dp_query_schema import (
    ColumnMeta,
    QueryHistoryRead,
    SavedQueryCreate,
    SavedQueryRead,
    SavedQueryUpdate,
    SqlExecuteResponse,
)
from app.services.dp_data_source_service import DpDataSourceService


EXPORT_MAX = 100_000
STREAM_BATCH = 500


class DpQueryService:
    """查询编排：守卫 → 执行 → 审计。每次写库前必先 `_reset_autobegin`。"""

    def __init__(self, db: Session, ds_service: Optional[DpDataSourceService] = None) -> None:
        self.db = db
        self.history_repo = DpQueryHistoryRepository(db)
        self.saved_repo = DpSqlQueryRepository(db)
        self.ds_service = ds_service or DpDataSourceService(db)

    # === execute_sync =================================================

    async def execute_sync(
        self,
        *,
        source_id: int,
        sql: str,
        max_rows: int,
        user_id: int,
    ) -> SqlExecuteResponse:
        row = self.ds_service.repo.get_by_id(source_id)
        if row is None:
            raise NotFoundException(f"数据源 id={source_id} 不存在", "DP_DS_NOT_FOUND")

        # Step 1: create running history
        self._reset_autobegin()
        with self.db.begin():
            history = self.history_repo.create_running(
                user_id=user_id, source_id=source_id, sql_text=sql,
            )
        history_id = history.id

        # Step 2: schema whitelist (best-effort)
        try:
            schema = self.ds_service.describe_schema(source_id)
            allowed = _flatten_table_names(schema)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[dp-query] describe_schema failed source={source_id}: {exc}")
            allowed = None

        # Step 3: guard + shape
        try:
            shaped = validate_and_shape(
                sql,
                dialect=_dialect_for_guard(row.dialect),
                max_rows=max_rows,
                allowed_tables=allowed,
            )
        except SqlGuardError as guard_err:
            self._reset_autobegin()
            with self.db.begin():
                self.history_repo.mark_error(
                    history_id, error_message=str(guard_err), status="error",
                )
            raise BusinessException(
                message=str(guard_err),
                code=f"SQL_GUARD_{guard_err.reason.upper()}",
                status_code=400,
            ) from guard_err

        # Step 4: execute (thread-pooled)
        engine = self.ds_service.get_engine(source_id)
        started = time.perf_counter()
        try:
            result = await run_in_threadpool(_run_query_capture, engine, shaped.sql)
        except SQLAlchemyError as db_err:
            elapsed_ms = int((time.perf_counter() - started) * 1000)  # noqa: F841
            is_timeout = (
                "timeout" in str(db_err).lower()
                or "max_execution_time" in str(db_err).lower()
            )
            self._reset_autobegin()
            with self.db.begin():
                self.history_repo.mark_error(
                    history_id,
                    error_message=str(db_err),
                    status="timeout" if is_timeout else "error",
                )
            raise BusinessException(
                message=f"查询失败：{db_err}"[:512],
                code="DP_QUERY_TIMEOUT" if is_timeout else "DP_QUERY_DB_ERROR",
                status_code=504 if is_timeout else 500,
            ) from db_err

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        columns_meta = [ColumnMeta(name=c) for c in result["columns"]]
        rows = result["rows"]
        truncated = len(rows) >= max_rows

        self._reset_autobegin()
        with self.db.begin():
            self.history_repo.mark_success(
                history_id,
                row_count=len(rows),
                elapsed_ms=elapsed_ms,
                columns_json=[c.model_dump() for c in columns_meta],
            )
        return SqlExecuteResponse(
            columns=columns_meta,
            rows=rows,
            row_count=len(rows),
            elapsed_ms=elapsed_ms,
            truncated=truncated,
        )

    # === execute_stream ===============================================

    async def execute_stream(
        self,
        *,
        source_id: int,
        sql: str,
        user_id: int,
        max_rows: int = EXPORT_MAX,
    ) -> AsyncIterator[dict]:
        row = self.ds_service.repo.get_by_id(source_id)
        if row is None:
            raise NotFoundException(f"数据源 id={source_id} 不存在", "DP_DS_NOT_FOUND")

        self._reset_autobegin()
        with self.db.begin():
            history = self.history_repo.create_running(
                user_id=user_id, source_id=source_id, sql_text=sql,
            )
        history_id = history.id

        try:
            schema = self.ds_service.describe_schema(source_id)
            allowed = _flatten_table_names(schema)
        except Exception:  # noqa: BLE001
            allowed = None

        try:
            shaped = validate_and_shape(
                sql,
                dialect=_dialect_for_guard(row.dialect),
                max_rows=min(max_rows, EXPORT_MAX),
                allowed_tables=allowed,
            )
        except SqlGuardError as guard_err:
            self._reset_autobegin()
            with self.db.begin():
                self.history_repo.mark_error(history_id, error_message=str(guard_err))
            yield {
                "event": "error",
                "data": {
                    "code": f"SQL_GUARD_{guard_err.reason.upper()}",
                    "message": str(guard_err),
                },
            }
            return

        engine = self.ds_service.get_engine(source_id)
        started = time.perf_counter()
        total = 0
        columns: list[str] = []

        try:
            def _open_stream():
                conn = engine.connect().execution_options(
                    stream_results=True, yield_per=STREAM_BATCH,
                )
                res = conn.execute(text(shaped.sql))
                return conn, res

            conn, res = await run_in_threadpool(_open_stream)
            columns = list(res.keys())
            yield {"event": "columns", "data": columns}
            try:
                while True:
                    batch = await run_in_threadpool(_fetch_batch, res, STREAM_BATCH)
                    if not batch:
                        break
                    total += len(batch)
                    yield {"event": "rows", "data": [list(r) for r in batch]}
                    if total >= EXPORT_MAX:
                        break
            finally:
                await run_in_threadpool(conn.close)
        except SQLAlchemyError as db_err:
            self._reset_autobegin()
            with self.db.begin():
                self.history_repo.mark_error(history_id, error_message=str(db_err))
            yield {
                "event": "error",
                "data": {
                    "code": "DP_QUERY_DB_ERROR",
                    "message": str(db_err)[:512],
                },
            }
            return

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        self._reset_autobegin()
        with self.db.begin():
            self.history_repo.mark_success(
                history_id,
                row_count=total,
                elapsed_ms=elapsed_ms,
                columns_json=[{"name": c} for c in columns],
            )
        yield {"event": "done", "data": {"row_count": total, "elapsed_ms": elapsed_ms}}

    # === history + saved =============================================

    def list_history(
        self,
        *,
        user_id: int,
        source_id: Optional[int] = None,
        limit: int = 50,
    ) -> list[QueryHistoryRead]:
        rows = self.history_repo.list_recent(
            user_id=user_id, source_id=source_id, limit=limit,
        )
        return [self._history_read(r) for r in rows]

    def create_saved(self, payload: SavedQueryCreate, user_id: int) -> SavedQueryRead:
        self._reset_autobegin()
        with self.db.begin():
            row = self.saved_repo.create(
                {**payload.model_dump(), "owner_user_id": user_id}
            )
        return SavedQueryRead.model_validate(row)

    def list_saved(
        self, *, user_id: int, source_id: Optional[int] = None,
    ) -> list[SavedQueryRead]:
        rows = self.saved_repo.list_by_owner(user_id=user_id, source_id=source_id)
        return [SavedQueryRead.model_validate(r) for r in rows]

    def update_saved(
        self, id: int, payload: SavedQueryUpdate, user_id: int,
    ) -> SavedQueryRead:
        row = self.saved_repo.get_by_id(id)
        if row is None or row.owner_user_id != user_id:
            raise NotFoundException(
                f"保存的查询 id={id} 不存在或无权限", "DP_SQ_NOT_FOUND",
            )
        self._reset_autobegin()
        with self.db.begin():
            self.saved_repo.update(id, payload.model_dump(exclude_unset=True))
        return SavedQueryRead.model_validate(self.saved_repo.get_by_id(id))

    def delete_saved(self, id: int, user_id: int) -> None:
        row = self.saved_repo.get_by_id(id)
        if row is None or row.owner_user_id != user_id:
            raise NotFoundException(
                f"保存的查询 id={id} 不存在或无权限", "DP_SQ_NOT_FOUND",
            )
        self._reset_autobegin()
        with self.db.begin():
            self.saved_repo.delete(id)

    # === helpers =====================================================

    def _reset_autobegin(self) -> None:
        """SQLAlchemy 2.0 gotcha: rollback pending autobegun read txn so
        `with self.db.begin()` can start cleanly."""
        if self.db.in_transaction():
            self.db.rollback()

    def _history_read(self, row) -> QueryHistoryRead:
        return QueryHistoryRead(
            id=row.id,
            source_id=row.source_id,
            user_id=row.user_id,
            sql_text=(row.sql_text or "")[:500],
            status=row.status,
            row_count=row.row_count,
            elapsed_ms=row.elapsed_ms,
            error_message=row.error_message,
            columns_json=row.columns_json,
            started_at=row.started_at,
            finished_at=row.finished_at,
            created_at=row.created_at,
        )


# ==== module helpers =============================================


def _flatten_table_names(schema: dict) -> set[str]:
    names: set[str] = set()
    for db_ in schema.get("databases", []):
        for tbl in db_.get("tables", []):
            names.add(tbl["name"])
    return names


def _dialect_for_guard(model_dialect: str) -> str:
    if model_dialect.startswith("postgres"):
        return "postgres"
    if model_dialect.startswith("mysql"):
        return "mysql"
    if model_dialect.startswith("sqlite"):
        return "sqlite"
    return model_dialect


def _run_query_capture(engine, sql: str) -> dict[str, Any]:
    with engine.connect() as conn:
        res = conn.execute(text(sql))
        columns = list(res.keys())
        rows = [list(r) for r in res.fetchall()]
    return {"columns": columns, "rows": rows}


def _fetch_batch(result, n: int) -> list:
    return result.fetchmany(n)
