"""POST /agent-looper/discover — 扫描本机 opencode agent 目录并 upsert。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.services.agent_looper_discovery_service import AgentLooperDiscoveryService

router = APIRouter()


@router.post("/discover", response_model=dict)
async def discover_agents(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """扫描 settings.AGENT_CONFIG_PATH 下的 opencode .md agent，upsert 进 agent_looper_configs。"""
    svc = AgentLooperDiscoveryService(db)
    configs = svc.discover()
    upserted = svc.upsert_discovered(configs, user_id=user_id)
    return {
        "code": "SUCCESS",
        "message": "发现完成",
        "data": {
            "discovered": len(configs),
            "upserted": upserted,
        },
    }
