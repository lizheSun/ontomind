"""专家团 API — /api/v1/experts.

一个专家 = 一份 opencode 配置 + 可选 Docker 容器。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.expert_schema import ExpertCreate, ExpertUpdate
from app.services.expert_service import ExpertService, seed_default_experts

router = APIRouter()


def _ok(data, message: str = "操作成功"):
    return {"code": "SUCCESS", "message": message, "data": data}


@router.get("")
def list_experts(
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    svc = ExpertService(db)
    return _ok(svc.list(skip, limit))


@router.post("/seed")
def seed_experts(
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    """幂等：为空库注入 4 个内置专家（数据分析 / 前端 / 后端 / 产品）."""
    added = seed_default_experts(db)
    return _ok({"added": added}, message=f"已 seed {added} 个专家")


@router.post("")
def create_expert(
    payload: ExpertCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    svc = ExpertService(db)
    return _ok(svc.create(payload, user_id), message="专家已创建")


@router.get("/{expert_id}")
def get_expert(
    expert_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    svc = ExpertService(db)
    return _ok(svc.get(expert_id))


@router.patch("/{expert_id}")
def update_expert(
    expert_id: int,
    payload: ExpertUpdate,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    svc = ExpertService(db)
    return _ok(svc.update(expert_id, payload), message="专家已更新")


@router.delete("/{expert_id}")
def delete_expert(
    expert_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    svc = ExpertService(db)
    svc.delete(expert_id)
    return _ok(None, message="专家已删除")


@router.post("/{expert_id}/start")
def start_expert(
    expert_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    svc = ExpertService(db)
    return _ok(svc.start(expert_id), message="专家已启动")


@router.post("/{expert_id}/stop")
def stop_expert(
    expert_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    svc = ExpertService(db)
    return _ok(svc.stop(expert_id), message="专家已关闭")