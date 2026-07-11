"""数据资产（data_asset）CRUD。"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.schemas.kb_data_asset_schema import (
    KbDataAssetCreate,
    KbDataAssetRead,
    KbDataAssetUpdate,
)
from app.services.kb_service import KbService

router = APIRouter()


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_data_asset(
    payload: KbDataAssetCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    asset = KbService(db).create_data_asset(payload, user_id=user_id)
    return {"code": "SUCCESS", "message": "创建成功", "data": asset.model_dump(mode="json")}


@router.get("", response_model=dict)
async def list_data_assets(
    owner_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    assets = KbService(db).list_data_assets(
        user_id=user_id, owner_only=owner_only, skip=skip, limit=limit
    )
    data = [a.model_dump(mode="json") for a in assets]
    return {"code": "SUCCESS", "message": "操作成功", "data": data, "total": len(data)}


@router.get("/{id}", response_model=dict)
async def get_data_asset(
    id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    svc = KbService(db)
    row = svc.asset_repo.get_by_id(id)
    if row is None:
        raise NotFoundException(
            message=f"data_asset id={id} 不存在",
            code="KB_ASSET_NOT_FOUND",
        )
    return {
        "code": "SUCCESS",
        "message": "操作成功",
        "data": KbDataAssetRead.model_validate(row).model_dump(mode="json"),
    }


@router.put("/{id}", response_model=dict)
async def update_data_asset(
    id: int,
    payload: KbDataAssetUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    asset = KbService(db).update_data_asset(id, payload, user_id=user_id)
    return {"code": "SUCCESS", "message": "更新成功", "data": asset.model_dump(mode="json")}


@router.delete("/{id}", response_model=dict)
async def delete_data_asset(
    id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    KbService(db).delete_data_asset(id, user_id=user_id)
    return {"code": "SUCCESS", "message": "删除成功", "data": None}
