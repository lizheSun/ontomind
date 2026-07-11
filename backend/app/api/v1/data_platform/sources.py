"""数据平台-数据源路由：CRUD + test + schema."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.dp_data_source_schema import (
    DpDataSourceCreate,
    DpDataSourceUpdate,
)
from app.services.dp_data_source_service import DpDataSourceService

router = APIRouter()


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_source(
    payload: DpDataSourceCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """创建数据源."""
    svc = DpDataSourceService(db)
    row = svc.create(payload, user_id=user_id)
    return {
        "code": "SUCCESS",
        "message": "数据源创建成功",
        "data": row.model_dump(mode="json"),
    }


@router.get("", response_model=dict)
async def list_sources(
    skip: int = 0,
    limit: int = 100,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """列出当前用户的数据源."""
    svc = DpDataSourceService(db)
    rows = svc.list_by_owner(user_id=user_id, skip=skip, limit=limit)
    data = [r.model_dump(mode="json") for r in rows]
    return {
        "code": "SUCCESS",
        "message": "操作成功",
        "data": data,
        "total": len(data),
    }


@router.get("/{source_id}", response_model=dict)
async def get_source(
    source_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """获取数据源详情."""
    svc = DpDataSourceService(db)
    row = svc.get_by_id(source_id, user_id=user_id)
    return {
        "code": "SUCCESS",
        "message": "操作成功",
        "data": row.model_dump(mode="json"),
    }


@router.put("/{source_id}", response_model=dict)
async def update_source(
    source_id: int,
    payload: DpDataSourceUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """更新数据源."""
    svc = DpDataSourceService(db)
    row = svc.update(source_id, payload, user_id=user_id)
    return {
        "code": "SUCCESS",
        "message": "数据源更新成功",
        "data": row.model_dump(mode="json"),
    }


@router.delete("/{source_id}", response_model=dict)
async def delete_source(
    source_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """删除数据源."""
    svc = DpDataSourceService(db)
    svc.delete(source_id, user_id=user_id)
    return {
        "code": "SUCCESS",
        "message": "数据源删除成功",
        "data": None,
    }


@router.post("/{source_id}/test", response_model=dict)
async def test_source(
    source_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """测试数据源连接."""
    svc = DpDataSourceService(db)
    result = svc.test_connection(source_id)
    return {
        "code": "SUCCESS",
        "message": "连接测试完成",
        "data": result.model_dump(mode="json"),
    }


@router.get("/{source_id}/schema", response_model=dict)
async def describe_source_schema(
    source_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """获取数据源 schema（库/表/字段）."""
    svc = DpDataSourceService(db)
    schema = svc.describe_schema(source_id)
    return {
        "code": "SUCCESS",
        "message": "操作成功",
        "data": schema,
    }
