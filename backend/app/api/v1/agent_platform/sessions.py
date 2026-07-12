"""Session and message REST routes."""
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.agent_platform_schema import MessageCreateRequest, SessionCreateRequest
from app.services.agent_platform.session import SessionService, execute_run_in_background

router = APIRouter()


def _ok(data, message: str = "操作成功"):
    return {"code": "SUCCESS", "message": message, "data": data}


@router.post("")
def create_session(
    payload: SessionCreateRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return _ok(
        SessionService(db).create(
            payload.agent_id,
            payload.deployment_id,
            payload.title,
            payload.metadata,
            user_id,
        )
    )


@router.get("")
def list_sessions(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return _ok(SessionService(db).list(user_id))


@router.get("/{session_id}")
def get_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return _ok(SessionService(db).get(session_id, user_id))


@router.post("/{session_id}/messages")
def add_message(
    session_id: int,
    payload: MessageCreateRequest,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    result = SessionService(db).send_message(
        session_id,
        payload.content,
        payload.content_type,
        payload.metadata,
        user_id,
    )
    if result.get("queued"):
        background_tasks.add_task(execute_run_in_background, result["run_id"])
    return _ok(result)


@router.get("/{session_id}/messages")
def list_messages(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return _ok(SessionService(db).list_messages(session_id, user_id))
