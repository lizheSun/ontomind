"""数据平台-保存的查询路由：CRUD."""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.dp_query_schema import SavedQueryCreate, SavedQueryUpdate
from app.services.dp_query_service import DpQueryService

router = APIRouter()


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_saved_query(
    payload: SavedQueryCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """创建一条保存的查询."""
    svc = DpQueryService(db)
    row = svc.create_saved(payload, user_id=user_id)
    return {
        "code": "SUCCESS",
        "message": "保存成功",
        "data": row.model_dump(mode="json"),
    }


@router.get("", response_model=dict)
async def list_saved_queries(
    source_id: Optional[int] = Query(None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """列出当前用户的保存查询."""
    svc = DpQueryService(db)
    rows = svc.list_saved(user_id=user_id, source_id=source_id)
    data = [r.model_dump(mode="json") for r in rows]
    return {
        "code": "SUCCESS",
        "message": "操作成功",
        "data": data,
        "total": len(data),
    }


@router.put("/{saved_id}", response_model=dict)
async def update_saved_query(
    saved_id: int,
    payload: SavedQueryUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """更新保存的查询."""
    svc = DpQueryService(db)
    row = svc.update_saved(saved_id, payload, user_id=user_id)
    return {
        "code": "SUCCESS",
        "message": "更新成功",
        "data": row.model_dump(mode="json"),
    }


@router.delete("/{saved_id}", response_model=dict)
async def delete_saved_query(
    saved_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """删除保存的查询."""
    svc = DpQueryService(db)
    svc.delete_saved(saved_id, user_id=user_id)
    return {
        "code": "SUCCESS",
        "message": "删除成功",
        "data": None,
    }
