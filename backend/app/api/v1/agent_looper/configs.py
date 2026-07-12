"""Agent Looper 配置路由（完整 CRUD + 版本管理 + 发布 + 回滚）。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.agent_looper_schema import (
    AgentLooperConfigCreate,
    AgentLooperConfigUpdate,
)
from app.services.agent_looper_service import AgentLooperService
from app.services.agent_looper_writer_service import (
    AgentLooperWriterError,
    AgentLooperWriterService,
)
from app.core.exceptions import BusinessException, NotFoundException

router = APIRouter()


@router.get("/configs", response_model=dict)
async def list_configs(
    skip: int = 0,
    limit: int = 100,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    svc = AgentLooperService(db)
    rows = svc.list_by_owner(user_id=user_id, skip=skip, limit=limit)
    data = [r.model_dump(mode="json") for r in rows]
    return {"code": "SUCCESS", "message": "操作成功", "data": data, "total": len(data)}


@router.post("/configs", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_config(
    payload: AgentLooperConfigCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    svc = AgentLooperService(db)
    row = svc.create(payload, user_id=user_id)
    return {"code": "SUCCESS", "message": "Agent 配置创建成功", "data": row.model_dump(mode="json")}


@router.post("/configs/{config_id}/publish", response_model=dict)
async def publish_config(
    config_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """把配置序列化为 opencode `.md` 并落盘。"""
    svc = AgentLooperWriterService(db)
    try:
        path = svc.publish(config_id=config_id, db=db)
    except AgentLooperWriterError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "AGENT_PUBLISH_FAILED", "message": str(exc)},
        ) from exc
    return {"code": "SUCCESS", "message": "配置已发布", "data": {"path": path}}
