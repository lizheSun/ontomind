"""Tool approval REST routes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.agent_platform_schema import (
    ApprovalCreateRequest,
    ApprovalDecisionRequest,
)
from app.services.agent_platform.approval import ApprovalService

router = APIRouter()


@router.post("")
def create_approval(
    payload: ApprovalCreateRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return ApprovalService(db).create(
        payload.run_id,
        payload.step_id,
        payload.tool_name,
        payload.arguments,
        user_id,
    )


@router.get("")
def list_approvals(
    status: str | None = Query(default=None),
    _user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return ApprovalService(db).list(status)


@router.get("/{approval_id}")
def get_approval(
    approval_id: int,
    _user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return ApprovalService(db).get(approval_id)


@router.post("/{approval_id}/decision")
def decide_approval(
    approval_id: int,
    payload: ApprovalDecisionRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return ApprovalService(db).decide(
        approval_id,
        payload.decision,
        payload.expected_version,
        user_id,
        payload.reason,
    )
