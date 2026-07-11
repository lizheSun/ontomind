"""知识库子库列表：read-only。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.services.kb_service import KbService

router = APIRouter()


@router.get("", response_model=dict)
async def list_libraries(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """列出全部 4 个知识库子库（seed）。"""
    libs = KbService(db).list_libraries()
    data = [lib.model_dump(mode="json") for lib in libs]
    return {"code": "SUCCESS", "message": "操作成功", "data": data, "total": len(data)}
