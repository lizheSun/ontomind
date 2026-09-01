"""任务看板服务。列 = 工作流位置；run_status = 会话执行态。"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException, NotFoundException
from app.db.models.kanban_model import KanbanBoard, KanbanColumn, KanbanTask
from app.db.repositories.kanban_repo import KanbanRepository
from app.schemas.harness_schema import SessionCreate
from app.schemas.kanban_schema import (
    BoardCreate,
    BoardUpdate,
    ColumnCreate,
    ColumnUpdate,
    TaskCreate,
    TaskMove,
    TaskUpdate,
)

DEFAULT_COLUMNS: list[tuple[str, str, str]] = [
    ("待处理", "#F59E0B", "clock"),
    ("进行中", "#3371fc", "sync"),
    ("已完成", "#00c853", "check"),
]


class KanbanService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = KanbanRepository(db)

    def list_boards(self, user_id: int) -> list[dict[str, Any]]:
        self.ensure_default(user_id)
        return [self._board_resp(b, with_columns=True) for b in self.repo.list_boards(user_id)]

    def ensure_default(self, user_id: int) -> None:
        if self.repo.list_boards(user_id):
            return
        self.create_board(user_id, BoardCreate(name="默认看板", from_template=True))

    def create_board(self, user_id: int, data: BoardCreate) -> dict[str, Any]:
        pos = len(self.repo.list_boards(user_id))
        board = self.repo.add_board(
            KanbanBoard(
                user_id=user_id,
                name=data.name.strip(),
                icon=data.icon or "kanban",
                color=data.color or "#3371fc",
                position=pos + 1,
            )
        )
        if data.from_template:
            for i, (name, color, icon) in enumerate(DEFAULT_COLUMNS, start=1):
                self.repo.add_column(
                    KanbanColumn(board_id=board.id, name=name, color=color, icon=icon, position=i)
                )
        else:
            self.repo.add_column(
                KanbanColumn(board_id=board.id, name="待办", color="#F59E0B", icon="clock", position=1)
            )
        self.db.commit()
        self.db.refresh(board)
        return self._board_resp(board, with_columns=True)

    def get_board(self, user_id: int, board_id: int) -> dict[str, Any]:
        return self._board_resp(self._owned_board(user_id, board_id), with_columns=True)

    def update_board(self, user_id: int, board_id: int, data: BoardUpdate) -> dict[str, Any]:
        row = self._owned_board(user_id, board_id)
        payload = data.model_dump(exclude_unset=True)
        for k, v in payload.items():
            setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        return self._board_resp(row, with_columns=True)

    def delete_board(self, user_id: int, board_id: int) -> None:
        row = self._owned_board(user_id, board_id)
        self.repo.delete_board(row)
        self.db.commit()

    def create_column(self, user_id: int, board_id: int, data: ColumnCreate) -> dict[str, Any]:
        self._owned_board(user_id, board_id)
        pos = self.repo.max_column_position(board_id) + 1
        col = self.repo.add_column(
            KanbanColumn(
                board_id=board_id,
                name=data.name.strip(),
                icon=data.icon,
                color=data.color,
                position=pos,
            )
        )
        self.db.commit()
        self.db.refresh(col)
        return self._column_resp(col)

    def update_column(self, user_id: int, column_id: int, data: ColumnUpdate) -> dict[str, Any]:
        col = self._owned_column(user_id, column_id)
        payload = data.model_dump(exclude_unset=True)
        for k, v in payload.items():
            setattr(col, k, v)
        self.db.commit()
        self.db.refresh(col)
        return self._column_resp(col)

    def delete_column(self, user_id: int, column_id: int) -> None:
        col = self._owned_column(user_id, column_id)
        others = [c for c in self.repo.list_columns(col.board_id) if c.id != col.id]
        if not others:
            raise BusinessException("至少保留一列", code="LAST_COLUMN")
        fallback = others[0].id
        for t in self.repo.list_tasks_in_column(col.id):
            t.column_id = fallback
            t.position = self.repo.max_task_position(fallback) + 1
        self.repo.delete_column(col)
        self.db.commit()

    def reorder_columns(self, user_id: int, board_id: int, column_ids: list[int]) -> dict[str, Any]:
        board = self._owned_board(user_id, board_id)
        existing = {c.id: c for c in self.repo.list_columns(board_id)}
        if set(column_ids) != set(existing):
            raise BusinessException("列 ID 不完整", code="COLUMN_MISMATCH")
        for i, cid in enumerate(column_ids, start=1):
            existing[cid].position = i
        self.db.commit()
        return self._board_resp(board, with_columns=True)

    def list_tasks(self, user_id: int, board_id: int, run_status: Optional[str] = None) -> list[dict[str, Any]]:
        self._owned_board(user_id, board_id)
        rows = self.repo.list_tasks(board_id)
        if run_status and run_status != "all":
            rows = [t for t in rows if t.run_status == run_status]
        return [self._task_resp(t) for t in rows]

    def create_task(self, user_id: int, board_id: int, data: TaskCreate) -> dict[str, Any]:
        board = self._owned_board(user_id, board_id)
        cols = self.repo.list_columns(board.id)
        if not cols:
            raise BusinessException("看板没有列", code="NO_COLUMN")
        column_id = data.column_id or cols[0].id
        col = self.repo.get_column(column_id)
        if col is None or col.board_id != board.id:
            raise NotFoundException("列不存在")

        from app.services.harness_service import HarnessService

        sess = HarnessService(self.db).create_session(
            user_id, SessionCreate(title=data.title.strip(), plugin_id=data.plugin_id)
        )
        task = self.repo.add_task(
            KanbanTask(
                board_id=board.id,
                column_id=col.id,
                session_id=sess["id"],
                title=data.title.strip(),
                plugin_id=data.plugin_id,
                run_status="pending",
                position=self.repo.max_task_position(col.id) + 1,
            )
        )
        self.db.commit()
        self.db.refresh(task)
        return self._task_resp(task)

    def update_task(self, user_id: int, task_id: int, data: TaskUpdate) -> dict[str, Any]:
        task = self._owned_task(user_id, task_id)
        payload = data.model_dump(exclude_unset=True)
        for k, v in payload.items():
            setattr(task, k, v)
        self.db.commit()
        self.db.refresh(task)
        return self._task_resp(task)

    def delete_task(self, user_id: int, task_id: int) -> None:
        task = self._owned_task(user_id, task_id)
        self.repo.delete_task(task)
        self.db.commit()

    def move_task(self, user_id: int, task_id: int, data: TaskMove) -> dict[str, Any]:
        task = self._owned_task(user_id, task_id)
        dest = self.repo.get_column(data.column_id)
        if dest is None or dest.board_id != task.board_id:
            raise NotFoundException("目标列不存在")

        old_col = task.column_id
        old_pos = task.position or 1
        new_pos = data.position

        if old_col == dest.id:
            siblings = [t for t in self.repo.list_tasks_in_column(dest.id) if t.id != task.id]
            new_pos = max(1, min(new_pos, len(siblings) + 1))
            if old_pos < new_pos:
                for t in siblings:
                    if old_pos < (t.position or 0) <= new_pos:
                        t.position = (t.position or 1) - 1
            elif old_pos > new_pos:
                for t in siblings:
                    if new_pos <= (t.position or 0) < old_pos:
                        t.position = (t.position or 1) + 1
            task.position = new_pos
        else:
            if old_col:
                for t in self.repo.list_tasks_in_column(old_col):
                    if t.id != task.id and (t.position or 0) > old_pos:
                        t.position = (t.position or 1) - 1
            dest_tasks = self.repo.list_tasks_in_column(dest.id)
            new_pos = max(1, min(new_pos, len(dest_tasks) + 1))
            for t in dest_tasks:
                if (t.position or 0) >= new_pos:
                    t.position = (t.position or 1) + 1
            task.column_id = dest.id
            task.position = new_pos

        self.db.commit()
        self.db.refresh(task)
        return self._task_resp(task)

    def _owned_board(self, user_id: int, board_id: int) -> KanbanBoard:
        row = self.repo.get_board(board_id)
        if row is None or row.user_id != user_id:
            raise NotFoundException("看板不存在")
        return row

    def _owned_column(self, user_id: int, column_id: int) -> KanbanColumn:
        col = self.repo.get_column(column_id)
        if col is None:
            raise NotFoundException("列不存在")
        self._owned_board(user_id, col.board_id)
        return col

    def _owned_task(self, user_id: int, task_id: int) -> KanbanTask:
        task = self.repo.get_task(task_id)
        if task is None:
            raise NotFoundException("任务不存在")
        self._owned_board(user_id, task.board_id)
        return task

    def _board_resp(self, row: KanbanBoard, *, with_columns: bool) -> dict[str, Any]:
        cols = self.repo.list_columns(row.id) if with_columns else []
        tasks = self.repo.list_tasks(row.id) if with_columns else []
        counts: dict[int, int] = {}
        for t in tasks:
            if t.column_id:
                counts[t.column_id] = counts.get(t.column_id, 0) + 1
        return {
            "id": row.id,
            "name": row.name,
            "icon": row.icon,
            "color": row.color,
            "position": row.position or 0,
            "task_count": len(tasks),
            "columns": [self._column_resp(c, counts.get(c.id, 0)) for c in cols],
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def _column_resp(self, row: KanbanColumn, task_count: int = 0) -> dict[str, Any]:
        return {
            "id": row.id,
            "board_id": row.board_id,
            "name": row.name,
            "icon": row.icon,
            "color": row.color,
            "position": row.position or 0,
            "collapsed": bool(row.collapsed),
            "task_count": task_count,
        }

    def _task_resp(self, row: KanbanTask) -> dict[str, Any]:
        return {
            "id": row.id,
            "board_id": row.board_id,
            "column_id": row.column_id,
            "session_id": row.session_id,
            "title": row.title,
            "plugin_id": row.plugin_id,
            "run_status": row.run_status or "pending",
            "position": row.position or 0,
            "summary": row.summary,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
