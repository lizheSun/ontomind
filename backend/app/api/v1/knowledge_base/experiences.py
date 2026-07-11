"""经验库（experience）CRUD。"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.schemas.kb_experience_schema import (
    KbExperienceCreate,
    KbExperienceRead,
    KbExperienceUpdate,
)
from app.services.kb_service import KbService

router = APIRouter()


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_experience(
    payload: KbExperienceCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    exp = KbService(db).create_experience(payload, user_id=user_id)
    return {"code": "SUCCESS", "message": "创建成功", "data": exp.model_dump(mode="json")}


@router.get("", response_model=dict)
async def list_experiences(
    owner_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    exps = KbService(db).list_experiences(
        user_id=user_id, owner_only=owner_only, skip=skip, limit=limit
    )
    data = [e.model_dump(mode="json") for e in exps]
    return {"code": "SUCCESS", "message": "操作成功", "data": data, "total": len(data)}


@router.get("/{id}", response_model=dict)
async def get_experience(
    id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    svc = KbService(db)
    row = svc.exp_repo.get_by_id(id)
    if row is None:
        raise NotFoundException(
            message=f"experience id={id} 不存在",
            code="KB_EXP_NOT_FOUND",
        )
    return {
        "code": "SUCCESS",
        "message": "操作成功",
        "data": KbExperienceRead.model_validate(row).model_dump(mode="json"),
    }


@router.put("/{id}", response_model=dict)
async def update_experience(
    id: int,
    payload: KbExperienceUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    exp = KbService(db).update_experience(id, payload, user_id=user_id)
    return {"code": "SUCCESS", "message": "更新成功", "data": exp.model_dump(mode="json")}


@router.delete("/{id}", response_model=dict)
async def delete_experience(
    id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    KbService(db).delete_experience(id, user_id=user_id)
    return {"code": "SUCCESS", "message": "删除成功", "data": None}
