"""跨库聚合搜索。"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.services.kb_service import KbService

router = APIRouter()


@router.get("", response_model=dict)
async def search_kb(
    q: str = Query(..., min_length=1),
    library_code: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """跨 4 子库聚合 LIKE 搜索，返回按 library_code 分组结果。"""
    grouped = KbService(db).search_all(q=q, library_code=library_code, limit=limit)
    return {
        "code": "SUCCESS",
        "message": "操作成功",
        "data": grouped.model_dump(mode="json"),
    }
