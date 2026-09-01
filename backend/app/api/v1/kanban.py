"""任务看板 API。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.kanban_schema import (
    BoardCreate,
    BoardResponse,
    BoardUpdate,
    ColumnCreate,
    ColumnReorder,
    ColumnResponse,
    ColumnUpdate,
    TaskCreate,
    TaskMove,
    TaskResponse,
    TaskUpdate,
)
from app.services.kanban_service import KanbanService

router = APIRouter(prefix="/kanban", tags=["任务看板"])


def get_svc(db: Session = Depends(get_db)) -> KanbanService:
    return KanbanService(db)


@router.get("/boards", response_model=list[BoardResponse])
def list_boards(svc: KanbanService = Depends(get_svc), uid: int = Depends(get_current_user_id)):
    return svc.list_boards(uid)


@router.post("/boards", response_model=BoardResponse)
def create_board(
    data: BoardCreate,
    svc: KanbanService = Depends(get_svc),
    uid: int = Depends(get_current_user_id),
):
    return svc.create_board(uid, data)


@router.get("/boards/{board_id}", response_model=BoardResponse)
def get_board(
    board_id: int,
    svc: KanbanService = Depends(get_svc),
    uid: int = Depends(get_current_user_id),
):
    return svc.get_board(uid, board_id)


@router.patch("/boards/{board_id}", response_model=BoardResponse)
def update_board(
    board_id: int,
    data: BoardUpdate,
    svc: KanbanService = Depends(get_svc),
    uid: int = Depends(get_current_user_id),
):
    return svc.update_board(uid, board_id, data)


@router.delete("/boards/{board_id}")
def delete_board(
    board_id: int,
    svc: KanbanService = Depends(get_svc),
    uid: int = Depends(get_current_user_id),
):
    svc.delete_board(uid, board_id)
    return {"code": "SUCCESS", "message": "已删除", "data": None}


@router.post("/boards/{board_id}/columns", response_model=ColumnResponse)
def create_column(
    board_id: int,
    data: ColumnCreate,
    svc: KanbanService = Depends(get_svc),
    uid: int = Depends(get_current_user_id),
):
    return svc.create_column(uid, board_id, data)


@router.put("/boards/{board_id}/columns/reorder", response_model=BoardResponse)
def reorder_columns(
    board_id: int,
    data: ColumnReorder,
    svc: KanbanService = Depends(get_svc),
    uid: int = Depends(get_current_user_id),
):
    return svc.reorder_columns(uid, board_id, data.column_ids)


@router.patch("/columns/{column_id}", response_model=ColumnResponse)
def update_column(
    column_id: int,
    data: ColumnUpdate,
    svc: KanbanService = Depends(get_svc),
    uid: int = Depends(get_current_user_id),
):
    return svc.update_column(uid, column_id, data)


@router.delete("/columns/{column_id}")
def delete_column(
    column_id: int,
    svc: KanbanService = Depends(get_svc),
    uid: int = Depends(get_current_user_id),
):
    svc.delete_column(uid, column_id)
    return {"code": "SUCCESS", "message": "已删除", "data": None}


@router.get("/boards/{board_id}/tasks", response_model=list[TaskResponse])
def list_tasks(
    board_id: int,
    run_status: Optional[str] = Query(None),
    svc: KanbanService = Depends(get_svc),
    uid: int = Depends(get_current_user_id),
):
    return svc.list_tasks(uid, board_id, run_status=run_status)


@router.post("/boards/{board_id}/tasks", response_model=TaskResponse)
def create_task(
    board_id: int,
    data: TaskCreate,
    svc: KanbanService = Depends(get_svc),
    uid: int = Depends(get_current_user_id),
):
    return svc.create_task(uid, board_id, data)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    data: TaskUpdate,
    svc: KanbanService = Depends(get_svc),
    uid: int = Depends(get_current_user_id),
):
    return svc.update_task(uid, task_id, data)


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    svc: KanbanService = Depends(get_svc),
    uid: int = Depends(get_current_user_id),
):
    svc.delete_task(uid, task_id)
    return {"code": "SUCCESS", "message": "已删除", "data": None}


@router.put("/tasks/{task_id}/move", response_model=TaskResponse)
def move_task(
    task_id: int,
    data: TaskMove,
    svc: KanbanService = Depends(get_svc),
    uid: int = Depends(get_current_user_id),
):
    return svc.move_task(uid, task_id, data)
