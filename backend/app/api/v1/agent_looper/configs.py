"""Agent Looper 配置路由（T45: 已归口 `/api/v1/resources/agents`）。

T45 naming migration:
    `/api/v1/agent-looper/configs`            → `/api/v1/resources/agents`
    `/api/v1/agent-looper/configs/{id}/publish`
                                              → `/api/v1/resources/agents/{id}/publish`

All old routes return **HTTP 308 Permanent Redirect** to preserve request
method + body, so existing POST/PUT callers keep working while they migrate.
The `publish` handler still lives here because the canonical `/resources/agents`
namespace currently serves the *Agent definition* CRUD, not the config
publish action — see `.blueprint/tasks/45-naming-migration.md` for the
follow-up unification plan.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.services.agent_looper_writer_service import (
    AgentLooperWriterError,
    AgentLooperWriterService,
)

router = APIRouter()


def _redirect_308(new_path: str, request: Request) -> RedirectResponse:
    qs = request.url.query
    target = f"{new_path}?{qs}" if qs else new_path
    return RedirectResponse(url=target, status_code=308)


@router.get("/configs")
async def list_configs(request: Request):
    return _redirect_308("/api/v1/resources/agents", request)


@router.post("/configs")
async def create_config(request: Request):
    return _redirect_308("/api/v1/resources/agents", request)


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
