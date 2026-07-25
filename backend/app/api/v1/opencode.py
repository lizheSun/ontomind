"""OpenCode 对话工作台后端桥接.

前端直接以 SDK 方式访问本机 ``opencode serve``（默认 127.0.0.1:4096）。
此模块只负责三件事：
1. **/health** — 探活本机 opencode server（前端 Guard 用）。
2. **/spawn** — dev-only：一键 spawn ``opencode serve``（仅 ``DEBUG=True`` 挂载）。
3. **/session-link** — 把 opencode 侧的 session.id 映射到业务侧 user。

⚠️ **不做**：消息转发 / 事件透传 / 会话数据存储。这些直接走前端 → opencode
的 HTTP + SSE，是产品刻意选择的架构（AGENTS.md 会补章节）。
"""
from __future__ import annotations

import asyncio
import os
import shutil
import socket
import subprocess
from typing import Optional

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.core.config import settings
from app.core.exceptions import BusinessException
from app.db.models.opencode_session_model import OpencodeSession
from app.db.session import get_db


router = APIRouter()

# 前端预期端点：默认 127.0.0.1:4096（跟 opencode serve 默认一致）
OPENCODE_HOST = os.environ.get("OPENCODE_HOST", "127.0.0.1")
OPENCODE_PORT = int(os.environ.get("OPENCODE_PORT", "4096"))
OPENCODE_BASE = f"http://{OPENCODE_HOST}:{OPENCODE_PORT}"


def _port_open(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@router.get("/health")
async def health():
    """探活本机 opencode server. 前端 OpencodeGuard 每次进 /chat 会调."""
    if not _port_open(OPENCODE_HOST, OPENCODE_PORT):
        return {
            "code": "SUCCESS",
            "message": "opencode server 未启动",
            "data": {
                "healthy": False,
                "base_url": OPENCODE_BASE,
                "reason": "port_closed",
            },
        }
    try:
        async with httpx.AsyncClient(timeout=3.0) as cli:
            resp = await cli.get(f"{OPENCODE_BASE}/global/health")
            resp.raise_for_status()
            body = resp.json()
        return {
            "code": "SUCCESS",
            "message": "opencode server 就绪",
            "data": {
                "healthy": bool(body.get("healthy", True)),
                "version": body.get("version"),
                "base_url": OPENCODE_BASE,
            },
        }
    except Exception as exc:  # pragma: no cover - 网络异常
        return {
            "code": "SUCCESS",
            "message": "opencode server 响应异常",
            "data": {
                "healthy": False,
                "base_url": OPENCODE_BASE,
                "reason": str(exc),
            },
        }


# ============================================================
# /spawn 仅在 DEBUG 模式挂载，避免生产环境暴露任意 subprocess
# ============================================================
if settings.DEBUG:

    class SpawnRequest(BaseModel):
        port: int = Field(4096, ge=1024, le=65535)
        cors: str = Field("http://localhost:5173", description="前端开发地址")

    @router.post("/spawn")
    async def spawn(payload: SpawnRequest, _user_id: int = Depends(get_current_user_id)):
        """一键 spawn ``opencode serve`` (仅 DEBUG 模式)."""
        if _port_open(OPENCODE_HOST, payload.port):
            return {
                "code": "SUCCESS",
                "message": "opencode server 已在运行",
                "data": {"already_running": True, "port": payload.port},
            }

        cli = shutil.which("opencode")
        if not cli:
            raise BusinessException(
                "本机未找到 opencode CLI，请先安装：curl -fsSL https://opencode.ai/install | bash",
                code="OPENCODE_CLI_NOT_FOUND",
                status_code=400,
            )

        args = [
            cli, "serve",
            "--port", str(payload.port),
            "--hostname", "127.0.0.1",
            "--cors", payload.cors,
        ]
        proc = subprocess.Popen(  # noqa: S603 - dev-only endpoint
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # 轮询 3s 等端口起来
        for _ in range(30):
            if _port_open(OPENCODE_HOST, payload.port):
                return {
                    "code": "SUCCESS",
                    "message": "opencode server 已启动",
                    "data": {
                        "pid": proc.pid,
                        "port": payload.port,
                        "base_url": f"http://{OPENCODE_HOST}:{payload.port}",
                    },
                }
            await asyncio.sleep(0.1)

        raise BusinessException(
            "opencode server 启动超时（3s 内端口未就绪），请手工执行 `opencode serve` 排查",
            code="OPENCODE_SPAWN_TIMEOUT",
            status_code=500,
        )


# ============================================================
# /session-link 业务侧会话映射
# ============================================================
class SessionLinkRequest(BaseModel):
    opencode_session_id: str = Field(..., min_length=1, max_length=64)
    title: Optional[str] = Field(None, max_length=255)


@router.post("/session-link")
def session_link(
    payload: SessionLinkRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """把 opencode 侧 session.id 绑定到业务侧 user."""
    existing = (
        db.query(OpencodeSession)
        .filter_by(opencode_session_id=payload.opencode_session_id)
        .first()
    )
    if existing:
        # 幂等：更新 title
        if payload.title is not None:
            existing.title = payload.title
        db.commit()
        db.refresh(existing)
        record = existing
    else:
        record = OpencodeSession(
            opencode_session_id=payload.opencode_session_id,
            user_id=user_id,
            title=payload.title,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

    return {
        "code": "SUCCESS",
        "message": "绑定成功",
        "data": {
            "id": record.id,
            "opencode_session_id": record.opencode_session_id,
            "user_id": record.user_id,
            "title": record.title,
        },
    }


@router.get("/session-link")
def list_session_links(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """列出当前用户绑定过的 opencode session."""
    rows = (
        db.query(OpencodeSession)
        .filter_by(user_id=user_id)
        .order_by(OpencodeSession.updated_at.desc().nullslast(),
                  OpencodeSession.created_at.desc())
        .limit(200)
        .all()
    )
    return {
        "code": "SUCCESS",
        "message": "查询成功",
        "data": [
            {
                "id": r.id,
                "opencode_session_id": r.opencode_session_id,
                "title": r.title,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ],
    }