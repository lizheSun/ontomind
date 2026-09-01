"""把统一会话的执行态回写到绑定的看板卡片。独立模块，避免和 HarnessService 循环 import。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.kanban_model import KanbanTask


def sync_session_run_status(
    db: Session,
    session_id: int,
    run_status: str,
    *,
    title: Optional[str] = None,
    summary: Optional[str] = None,
) -> None:
    rows = db.query(KanbanTask).filter(KanbanTask.session_id == session_id).all()
    if not rows:
        return
    for row in rows:
        row.run_status = run_status
        if title and (not row.title or row.title == "新任务"):
            row.title = title[:256]
        if summary is not None:
            row.summary = summary[:2000] if summary else None
    db.flush()
