"""Kanban Repository — 仅 flush。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.kanban_model import KanbanBoard, KanbanColumn, KanbanTask


class KanbanRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_boards(self, user_id: int) -> list[KanbanBoard]:
        return (
            self.db.query(KanbanBoard)
            .filter(KanbanBoard.user_id == user_id)
            .order_by(KanbanBoard.position.asc(), KanbanBoard.id.asc())
            .all()
        )

    def get_board(self, board_id: int) -> Optional[KanbanBoard]:
        return self.db.get(KanbanBoard, board_id)

    def add_board(self, row: KanbanBoard) -> KanbanBoard:
        self.db.add(row)
        self.db.flush()
        return row

    def delete_board(self, row: KanbanBoard) -> None:
        self.db.query(KanbanTask).filter(KanbanTask.board_id == row.id).delete()
        self.db.query(KanbanColumn).filter(KanbanColumn.board_id == row.id).delete()
        self.db.delete(row)
        self.db.flush()

    def list_columns(self, board_id: int) -> list[KanbanColumn]:
        return (
            self.db.query(KanbanColumn)
            .filter(KanbanColumn.board_id == board_id)
            .order_by(KanbanColumn.position.asc(), KanbanColumn.id.asc())
            .all()
        )

    def get_column(self, column_id: int) -> Optional[KanbanColumn]:
        return self.db.get(KanbanColumn, column_id)

    def add_column(self, row: KanbanColumn) -> KanbanColumn:
        self.db.add(row)
        self.db.flush()
        return row

    def delete_column(self, row: KanbanColumn) -> None:
        self.db.delete(row)
        self.db.flush()

    def max_column_position(self, board_id: int) -> int:
        val = (
            self.db.query(KanbanColumn.position)
            .filter(KanbanColumn.board_id == board_id)
            .order_by(KanbanColumn.position.desc())
            .first()
        )
        return int(val[0]) if val and val[0] is not None else 0

    def list_tasks(self, board_id: int) -> list[KanbanTask]:
        return (
            self.db.query(KanbanTask)
            .filter(KanbanTask.board_id == board_id)
            .order_by(KanbanTask.position.asc(), KanbanTask.id.asc())
            .all()
        )

    def list_tasks_in_column(self, column_id: int) -> list[KanbanTask]:
        return (
            self.db.query(KanbanTask)
            .filter(KanbanTask.column_id == column_id)
            .order_by(KanbanTask.position.asc(), KanbanTask.id.asc())
            .all()
        )

    def get_task(self, task_id: int) -> Optional[KanbanTask]:
        return self.db.get(KanbanTask, task_id)

    def add_task(self, row: KanbanTask) -> KanbanTask:
        self.db.add(row)
        self.db.flush()
        return row

    def delete_task(self, row: KanbanTask) -> None:
        self.db.delete(row)
        self.db.flush()

    def max_task_position(self, column_id: int) -> int:
        val = (
            self.db.query(KanbanTask.position)
            .filter(KanbanTask.column_id == column_id)
            .order_by(KanbanTask.position.desc())
            .first()
        )
        return int(val[0]) if val and val[0] is not None else 0

    def tasks_by_session(self, session_id: int) -> list[KanbanTask]:
        return self.db.query(KanbanTask).filter(KanbanTask.session_id == session_id).all()
