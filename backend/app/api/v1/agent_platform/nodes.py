"""Agent Platform 节点 API。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.agent_platform_schema import HostKeyConfirmation, NodeCreate
from app.services.agent_platform.node_service import NodeService

router = APIRouter()


@router.post("/nodes/register-local", status_code=201)
def register_local_node(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        result = NodeService(db).register_local(user_id)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"code": "SUCCESS", "data": result}


@router.get("/nodes/{node_id}/inventory")
async def get_node_inventory(
    node_id: int,
    refresh: bool = False,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    from app.services.agent_platform.inventory_service import InventoryService

    try:
        result = await InventoryService(db).get(node_id, refresh=refresh, user_id=user_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"code": "SUCCESS", "data": result}


@router.get("/nodes")
def list_nodes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return {"code": "SUCCESS", "data": NodeService(db).list(skip, limit)}


@router.post("/nodes", status_code=201)
def create_node(
    data: NodeCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        result = NodeService(db).create(data, user_id)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"code": "SUCCESS", "data": result}


@router.get("/nodes/{node_id}")
def get_node(
    node_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    result = NodeService(db).get(node_id)
    if result is None:
        raise HTTPException(status_code=404, detail="node not found")
    return {"code": "SUCCESS", "data": result}


@router.post("/nodes/{node_id}/connection-tests")
async def test_node_connection(
    node_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    try:
        report = await NodeService(db).connector_for(node_id).test_connection()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"code": "SUCCESS" if report.ok else "ERROR", "data": report.__dict__}


@router.post("/nodes/{node_id}/host-key-confirmations")
def confirm_node_host_key(
    node_id: int,
    data: HostKeyConfirmation,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        result = NodeService(db).confirm_host_key(node_id, data, user_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"code": "SUCCESS", "data": result}
