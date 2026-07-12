"""POST /agent-looper/discover — 扫描本机 opencode agent 目录并 upsert。

T46 追加：POST /agent-looper/discover-opencode — 扫描 opencode.json + skills/。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.services.agent_looper_discovery_service import AgentLooperDiscoveryService
from app.services.opencode_config_discovery_service import OpencodeConfigDiscoveryService

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


@router.post("/discover-opencode", response_model=dict)
async def discover_opencode_config(
    dry_run: bool = Query(False, description="仅返回将要 upsert 的数据，不写库"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """扫描本地 opencode 配置（opencode.json 的 mcp + skills/*/SKILL.md），upsert 进 mcp_configs 与 skills 表。"""
    svc = OpencodeConfigDiscoveryService(db=db)
    result = svc.discover_all(dry_run=dry_run)
    return {
        "code": "SUCCESS",
        "message": (
            f"发现 {result['mcps_found']} 个 MCP，{result['skills_found']} 个 Skill；"
            f"created={result.get('created', 0)} updated={result.get('updated', 0)}"
        ),
        "data": result,
    }
