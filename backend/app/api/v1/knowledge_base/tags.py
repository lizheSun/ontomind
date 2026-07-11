"""标签池 read-only。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.services.kb_service import KbService

router = APIRouter()


@router.get("", response_model=dict)
async def list_tags(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """列出全部标签（KB 标签池）。"""
    tags = KbService(db).list_tags()
    data = [t.model_dump(mode="json") for t in tags]
    return {"code": "SUCCESS", "message": "操作成功", "data": data, "total": len(data)}
