"""Persistent Run REST controls and resumable SSE event stream."""
import asyncio
import json

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db, get_session_factory
from app.schemas.agent_platform_schema import (
    RunActionRequest,
    RunControlRequest,
    RunCreateRequest,
)
from app.services.agent_platform.run import RunService

router = APIRouter()

_TERMINAL_EVENTS = {
    "run.completed",
    "run.failed",
    "run.cancelled",
    "run.needs_review",
}


@router.post("")
def create_run(
    payload: RunCreateRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return RunService(db).create(
        version_id=payload.agent_version_id,
        deployment_id=payload.deployment_id,
        session_id=payload.session_id,
        strategy=payload.strategy,
        kind=payload.kind,
        input_data=payload.input,
        user_id=user_id,
    )


@router.get("")
def list_runs(
    user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)
):
    return RunService(db).list(user_id)


@router.get("/{run_id}")
def get_run(
    run_id: int,
    _user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return RunService(db).get(run_id)


@router.post("/{run_id}/control")
def control_run(
    run_id: int,
    payload: RunControlRequest,
    _user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return RunService(db).control(
        run_id, payload.action, payload.expected_version
    )


@router.post("/{run_id}/start")
def start_run(
    run_id: int,
    payload: RunActionRequest | None = None,
    _user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return RunService(db).control(
        run_id, "start", payload.expected_version if payload else None
    )


@router.post("/{run_id}/cancel")
def cancel_run(
    run_id: int,
    payload: RunActionRequest | None = None,
    _user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return RunService(db).control(
        run_id, "cancel", payload.expected_version if payload else None
    )


@router.post("/{run_id}/pause")
def pause_run(
    run_id: int,
    payload: RunActionRequest | None = None,
    _user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return RunService(db).control(
        run_id, "pause", payload.expected_version if payload else None
    )


@router.post("/{run_id}/resume")
def resume_run(
    run_id: int,
    payload: RunActionRequest | None = None,
    _user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return RunService(db).control(
        run_id, "resume", payload.expected_version if payload else None
    )


@router.post("/{run_id}/retry")
def retry_run(
    run_id: int,
    payload: RunActionRequest | None = None,
    _user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return RunService(db).control(
        run_id, "retry", payload.expected_version if payload else None
    )


@router.get("/{run_id}/events")
async def stream_run_events(
    run_id: int,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    _user_id: int = Depends(get_current_user_id),
    session_factory=Depends(get_session_factory),
):
    """回放已有事件后保持长连接，实时推送新事件直到 Run 终态。"""
    try:
        cursor = max(0, int(last_event_id or "0"))
    except ValueError:
        cursor = 0

    async def generate():
        nonlocal cursor
        idle = 0
        # 约 10 分钟空闲上限（OpenCode 单次通常 < 3 分钟）
        max_idle = 2000
        while idle < max_idle:
            db = session_factory()
            try:
                svc = RunService(db)
                run = svc.get_model(run_id)
                events = svc.events_after(run_id, cursor)
                terminal_seen = False
                for event in events:
                    cursor = int(event["sequence"])
                    idle = 0
                    yield {
                        "id": str(event["sequence"]),
                        "event": event["type"],
                        "data": json.dumps(event, ensure_ascii=False),
                    }
                    if event["type"] in _TERMINAL_EVENTS:
                        terminal_seen = True
                if terminal_seen:
                    return
                if run.status in RunService.TERMINAL and not events:
                    return
            finally:
                db.close()

            yield {"comment": "keepalive"}
            idle += 1
            await asyncio.sleep(0.3)

    return EventSourceResponse(generate())
