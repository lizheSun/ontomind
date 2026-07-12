"""LLM 资源管理 API."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.llm_config_schema import (
    LLMConfigCreate, LLMConfigUpdate, LLMConfigResponse,
    LLMChatRequest, LLMChatResponse,
)
from app.services.llm_config_service import LLMConfigService
from app.core.authorization import PlatformPermission, require_permission

router = APIRouter(
    dependencies=[Depends(require_permission(PlatformPermission.LLM_MANAGE))]
)


def get_llm_service(db: Session = Depends(get_db)) -> LLMConfigService:
    return LLMConfigService(db)


@router.get("")
async def list_configs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    svc: LLMConfigService = Depends(get_llm_service),
):
    data = svc.list_configs(skip, limit)
    return {"code": "SUCCESS", "message": "查询成功", "data": data, "total": len(data)}


@router.post("")
async def create_config(
    payload: LLMConfigCreate,
    svc: LLMConfigService = Depends(get_llm_service),
):
    data = svc.create_config(payload)
    return {"code": "SUCCESS", "message": "创建成功", "data": data}


@router.get("/{config_id}")
async def get_config(
    config_id: int,
    svc: LLMConfigService = Depends(get_llm_service),
):
    data = svc.get_config(config_id)
    return {"code": "SUCCESS", "message": "查询成功", "data": data}


@router.put("/{config_id}")
async def update_config(
    config_id: int,
    payload: LLMConfigUpdate,
    svc: LLMConfigService = Depends(get_llm_service),
):
    data = svc.update_config(config_id, payload)
    return {"code": "SUCCESS", "message": "更新成功", "data": data}


@router.delete("/{config_id}")
async def delete_config(
    config_id: int,
    svc: LLMConfigService = Depends(get_llm_service),
):
    svc.delete_config(config_id)
    return {"code": "SUCCESS", "message": "删除成功"}


@router.post("/chat")
async def chat_completion(
    payload: LLMChatRequest,
    svc: LLMConfigService = Depends(get_llm_service),
):
    """调用已配置的 LLM 进行对话"""
    try:
        data = await svc.chat_completion(
            messages=payload.messages,
            config_id=payload.config_id,
            temperature=payload.temperature or 0.7,
            max_tokens=payload.max_tokens or 2048,
        )
        return {"code": "SUCCESS", "message": "调用成功", "data": data}
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/active/info")
async def get_active_config(
    svc: LLMConfigService = Depends(get_llm_service),
):
    """获取当前默认激活的配置信息"""
    data = svc.get_active_config()
    return {"code": "SUCCESS", "message": "查询成功", "data": data}
