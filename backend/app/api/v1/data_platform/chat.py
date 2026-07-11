"""数据平台-Text2SQL 会话路由：sessions + messages + apply."""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.dp_chat_schema import MessageCreate, SessionCreate
from app.services.dp_chat_service import DpChatService

router = APIRouter()


# ---- sessions ----------------------------------------------------


@router.post("/sessions", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """创建 Text2SQL 会话."""
    svc = DpChatService(db)
    row = svc.create_session(payload, user_id=user_id)
    return {
        "code": "SUCCESS",
        "message": "会话创建成功",
        "data": row.model_dump(mode="json"),
    }


@router.get("/sessions", response_model=dict)
async def list_sessions(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """列出当前用户的会话."""
    svc = DpChatService(db)
    rows = svc.list_sessions(user_id=user_id)
    data = [r.model_dump(mode="json") for r in rows]
    return {
        "code": "SUCCESS",
        "message": "操作成功",
        "data": data,
        "total": len(data),
    }


@router.get("/sessions/{session_id}", response_model=dict)
async def get_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """获取会话详情."""
    svc = DpChatService(db)
    row = svc.get_session(session_id, user_id=user_id)
    return {
        "code": "SUCCESS",
        "message": "操作成功",
        "data": row.model_dump(mode="json"),
    }


@router.delete("/sessions/{session_id}", response_model=dict)
async def delete_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """删除会话（级联删除消息）."""
    svc = DpChatService(db)
    svc.delete_session(session_id, user_id=user_id)
    return {
        "code": "SUCCESS",
        "message": "会话已删除",
        "data": None,
    }


# ---- messages ---------------------------------------------------


@router.get("/sessions/{session_id}/messages", response_model=dict)
async def list_messages(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """列出指定会话的全部消息."""
    svc = DpChatService(db)
    rows = svc.list_messages(session_id, user_id=user_id)
    data = [r.model_dump(mode="json") for r in rows]
    return {
        "code": "SUCCESS",
        "message": "操作成功",
        "data": data,
        "total": len(data),
    }


@router.post("/sessions/{session_id}/messages", response_model=dict, status_code=status.HTTP_201_CREATED)
async def send_message(
    session_id: int,
    payload: MessageCreate,
    stream: bool = Query(False, description="占位：Wave-6 才真正接 SSE，目前忽略"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """发送一条用户消息，返回 LLM 生成的 assistant 消息（含 generated_sql）。

    `stream` 参数当前被忽略：T15 `send_message` 返回单条 `MessageRead`，非 async
    iterator。Wave-6 会把 LLM 流式接进来并把这里改成 EventSourceResponse。
    """
    _ = stream  # explicitly ignored for now
    svc = DpChatService(db)
    row = await svc.send_message(
        session_id=session_id,
        content=payload.content,
        user_id=user_id,
    )
    return {
        "code": "SUCCESS",
        "message": "消息已生成",
        "data": row.model_dump(mode="json"),
    }


# ---- apply ------------------------------------------------------


@router.post("/sessions/{session_id}/apply/{message_id}", response_model=dict)
async def apply_message(
    session_id: int,
    message_id: int,
    max_rows: int = Query(1000, ge=1, le=100_000),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """把 assistant 消息里的 generated_sql 送去守卫 + 执行，返回结果集."""
    svc = DpChatService(db)
    result = await svc.apply_message(
        session_id=session_id,
        message_id=message_id,
        user_id=user_id,
        max_rows=max_rows,
    )
    return {
        "code": "SUCCESS",
        "message": "执行成功",
        "data": result.model_dump(mode="json"),
    }
