"""数据平台-执行历史仓储。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional

from sqlalchemy.orm import Session

from app.db.models.dp_query_history_model import DpQueryHistory
from app.db.repositories.base_repo import BaseRepository


def _utcnow_naive() -> datetime:
    """返回 tz-naive UTC datetime（模型列是 DateTime，无 timezone=True）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DpQueryHistoryRepository(BaseRepository[DpQueryHistory]):
    """DpQueryHistory 仓储：执行审计生命周期（running→success/error）。"""

    def __init__(self, db: Session) -> None:
        super().__init__(DpQueryHistory, db)

    def list_recent(
        self,
        user_id: int,
        source_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[DpQueryHistory]:
        q = self.db.query(DpQueryHistory).filter(DpQueryHistory.user_id == user_id)
        if source_id is not None:
            q = q.filter(DpQueryHistory.source_id == source_id)
        return q.order_by(DpQueryHistory.started_at.desc()).limit(limit).all()

    def create_running(
        self, *, user_id: int, source_id: int, sql_text: str
    ) -> DpQueryHistory:
        row = DpQueryHistory(
            user_id=user_id,
            source_id=source_id,
            sql_text=sql_text,
            status="running",
            started_at=_utcnow_naive(),
        )
        self.db.add(row)
        self.db.flush()
        return row

    def mark_success(
        self,
        id: int,
        *,
        row_count: int,
        elapsed_ms: int,
        columns_json: Any,
    ) -> Optional[DpQueryHistory]:
        row = self.get_by_id(id)
        if row is None:
            return None
        row.status = "success"
        row.row_count = row_count
        row.elapsed_ms = elapsed_ms
        row.columns_json = columns_json
        row.finished_at = _utcnow_naive()
        self.db.flush()
        return row

    def mark_error(
        self,
        id: int,
        *,
        error_message: str,
        status: str = "error",
    ) -> Optional[DpQueryHistory]:
        row = self.get_by_id(id)
        if row is None:
            return None
        row.status = status  # "error" | "canceled" | "timeout"
        row.error_message = error_message[:64000] if error_message else None
        row.finished_at = _utcnow_naive()
        self.db.flush()
        return row
