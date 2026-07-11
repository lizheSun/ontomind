"""Agent Looper 配置路由。

- POST /configs/{id}/publish  — 本任务（T35）完整实现，落盘 .md
- GET  /configs               — TODO(T34): list_by_owner
- POST /configs               — TODO(T34): create

list/create 为 stub，占位便于 aggregator 完整，等 T34 合入后填充真实实现。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.services.agent_looper_writer_service import (
    AgentLooperWriterError,
    AgentLooperWriterService,
)

router = APIRouter()


@router.get("/configs", response_model=dict)
async def list_configs(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """TODO(T34): 委托 AgentLooperService.list_by_owner。此处占位。"""
    return {
        "code": "SUCCESS",
        "message": "TODO(T34): list_by_owner",
        "data": [],
    }


@router.post("/configs", response_model=dict)
async def create_config(
    payload: dict,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """TODO(T34): 委托 AgentLooperService.create。此处占位。"""
    return {
        "code": "PENDING",
        "message": "TODO(T34): create 由 AgentLooperService 提供",
        "data": None,
    }


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
    return {
        "code": "SUCCESS",
        "message": "配置已发布",
        "data": {"path": path},
    }
