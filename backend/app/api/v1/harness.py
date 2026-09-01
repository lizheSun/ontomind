"""统一会话 API：插件探活 + 会话 CRUD + SSE 发消息。"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.core.exceptions import BusinessException
from app.db.session import get_db
from app.schemas.harness_schema import (
    MessageCreate,
    MessageResponse,
    PluginInfoResponse,
    PromptOptimizeRequest,
    PromptOptimizeResponse,
    SessionCreate,
    SessionResponse,
    SessionUpdate,
    UploadedFile,
    WorkspaceListResponse,
)
from app.services.harness_service import HarnessService

router = APIRouter(prefix="/harness", tags=["统一会话"])


def get_svc(db: Session = Depends(get_db)) -> HarnessService:
    return HarnessService(db)


@router.get("/plugins", response_model=list[PluginInfoResponse])
def list_plugins(svc: HarnessService = Depends(get_svc), _uid: int = Depends(get_current_user_id)):
    return svc.list_plugins()


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(svc: HarnessService = Depends(get_svc), uid: int = Depends(get_current_user_id)):
    return svc.list_sessions(uid)


@router.post("/sessions", response_model=SessionResponse)
def create_session(
    data: SessionCreate,
    svc: HarnessService = Depends(get_svc),
    uid: int = Depends(get_current_user_id),
):
    return svc.create_session(uid, data)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: int,
    svc: HarnessService = Depends(get_svc),
    uid: int = Depends(get_current_user_id),
):
    return svc.get_session(uid, session_id)


@router.patch("/sessions/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: int,
    data: SessionUpdate,
    svc: HarnessService = Depends(get_svc),
    uid: int = Depends(get_current_user_id),
):
    return svc.update_session(uid, session_id, data)


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    svc: HarnessService = Depends(get_svc),
    uid: int = Depends(get_current_user_id),
):
    svc.delete_session(uid, session_id)
    return {"code": "SUCCESS", "message": "已删除", "data": None}


@router.get("/workspaces", response_model=WorkspaceListResponse)
def list_workspaces(svc: HarnessService = Depends(get_svc), uid: int = Depends(get_current_user_id)):
    return svc.list_workspaces(uid)


@router.post("/prompt/optimize", response_model=PromptOptimizeResponse)
def optimize_prompt(
    data: PromptOptimizeRequest,
    svc: HarnessService = Depends(get_svc),
    _uid: int = Depends(get_current_user_id),
):
    return {"text": svc.optimize_prompt(data.text, data.plugin_id)}


@router.post("/sessions/{session_id}/files", response_model=list[UploadedFile])
async def upload_files(
    session_id: int,
    files: list[UploadFile] = File(...),
    svc: HarnessService = Depends(get_svc),
    uid: int = Depends(get_current_user_id),
):
    if not files:
        return []
    if len(files) > 8:
        raise BusinessException("一次最多 8 个文件", code="TOO_MANY_FILES")
    blobs: list[tuple[str, bytes]] = []
    for f in files:
        blobs.append((f.filename or "file", await f.read()))
    return svc.save_uploads(uid, session_id, blobs)


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
def list_messages(
    session_id: int,
    svc: HarnessService = Depends(get_svc),
    uid: int = Depends(get_current_user_id),
):
    return svc.list_messages(uid, session_id)


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: int,
    data: MessageCreate,
    request: Request,
    svc: HarnessService = Depends(get_svc),
    uid: int = Depends(get_current_user_id),
):
    svc.get_session(uid, session_id)
    cancel = asyncio.Event()

    async def watch_disconnect() -> None:
        while not cancel.is_set():
            if await request.is_disconnected():
                cancel.set()
                return
            await asyncio.sleep(0.25)

    async def event_gen():
        watcher = asyncio.create_task(watch_disconnect())
        try:
            async for ev in svc.stream_message(
                user_id=uid,
                session_id=session_id,
                content=data.content,
                plugin_id=data.plugin_id,
                attachments=data.attachments,
                cancel=cancel,
            ):
                payload = json.dumps(ev.to_sse_dict(), ensure_ascii=False)
                yield f"event: chunk\ndata: {payload}\n\n"
            yield "event: done\ndata: {}\n\n"
        finally:
            cancel.set()
            watcher.cancel()

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
