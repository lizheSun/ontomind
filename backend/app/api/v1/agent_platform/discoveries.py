"""Agent Platform 发现预览与显式决策 API。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.agent_platform_schema import (
    DiscoveryApply,
    DiscoveryCreate,
    DiscoveryDecision,
)
from app.services.agent_platform.discovery_service import DiscoveryService

router = APIRouter()


@router.post("/nodes/{node_id}/discoveries", status_code=201)
async def start_discovery(
    node_id: int,
    data: DiscoveryCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        result = await DiscoveryService(db).start(
            node_id=node_id, user_id=user_id, provider_type=data.provider_type
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"code": "SUCCESS", "data": result}


@router.get("/discoveries/{run_id}")
def get_discovery(
    run_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    result = DiscoveryService(db).get(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="discovery not found")
    return {"code": "SUCCESS", "data": result}


@router.get("/discoveries/{run_id}/items")
def list_discovery_items(
    run_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    if DiscoveryService(db).get(run_id) is None:
        raise HTTPException(status_code=404, detail="discovery not found")
    return {"code": "SUCCESS", "data": DiscoveryService(db).items(run_id)}


@router.post("/discoveries/{run_id}/items/{item_id}/decisions")
def decide_discovery_item(
    run_id: int,
    item_id: int,
    data: DiscoveryDecision,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        result = DiscoveryService(db).decide(run_id, item_id, data.decision, user_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"code": "SUCCESS", "data": result}


@router.post("/discoveries/{run_id}/apply")
def apply_discovery(
    data: DiscoveryApply,
    run_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        result = DiscoveryService(db).apply(run_id, user_id, data.item_ids)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"code": "SUCCESS", "data": result}
