"""代码仓库（code_repo）CRUD。"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.schemas.kb_code_repo_schema import (
    KbCodeRepoCreate,
    KbCodeRepoRead,
    KbCodeRepoUpdate,
)
from app.services.kb_service import KbService

router = APIRouter()


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_code_repo(
    payload: KbCodeRepoCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    repo = KbService(db).create_code_repo(payload, user_id=user_id)
    return {"code": "SUCCESS", "message": "创建成功", "data": repo.model_dump(mode="json")}


@router.get("", response_model=dict)
async def list_code_repos(
    owner_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    repos = KbService(db).list_code_repos(
        user_id=user_id, owner_only=owner_only, skip=skip, limit=limit
    )
    data = [r.model_dump(mode="json") for r in repos]
    return {"code": "SUCCESS", "message": "操作成功", "data": data, "total": len(data)}


@router.get("/{id}", response_model=dict)
async def get_code_repo(
    id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    svc = KbService(db)
    row = svc.repo_repo.get_by_id(id)
    if row is None:
        raise NotFoundException(
            message=f"code_repo id={id} 不存在",
            code="KB_REPO_NOT_FOUND",
        )
    return {
        "code": "SUCCESS",
        "message": "操作成功",
        "data": KbCodeRepoRead.model_validate(row).model_dump(mode="json"),
    }


@router.put("/{id}", response_model=dict)
async def update_code_repo(
    id: int,
    payload: KbCodeRepoUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    repo = KbService(db).update_code_repo(id, payload, user_id=user_id)
    return {"code": "SUCCESS", "message": "更新成功", "data": repo.model_dump(mode="json")}


@router.delete("/{id}", response_model=dict)
async def delete_code_repo(
    id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    KbService(db).delete_code_repo(id, user_id=user_id)
    return {"code": "SUCCESS", "message": "删除成功", "data": None}
