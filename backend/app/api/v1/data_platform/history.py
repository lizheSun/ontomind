"""数据平台-查询历史路由."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.services.dp_query_service import DpQueryService

router = APIRouter()


@router.get("", response_model=dict)
async def list_history(
    source_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """列出当前用户的查询历史（sql_text 已截断到 500 字）."""
    svc = DpQueryService(db)
    rows = svc.list_history(user_id=user_id, source_id=source_id, limit=limit)
    data = [r.model_dump(mode="json") for r in rows]
    return {
        "code": "SUCCESS",
        "message": "操作成功",
        "data": data,
        "total": len(data),
    }
