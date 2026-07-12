"""Agent identity and immutable version routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.agent_platform_schema import (
    AgentCreateRequest,
    AgentUpdateRequest,
    VersionCreateRequest,
    VersionLoadRequest,
)
from app.services.agent_platform.agent import AgentService
from app.services.agent_platform.migration import LegacyAgentMigrationService
from app.services.agent_platform.version import VersionService, _row

router = APIRouter()


def _ok(data, message: str = "操作成功"):
    return {"code": "SUCCESS", "message": message, "data": data}


@router.post("/legacy/{legacy_config_id}/migrate")
def migrate_legacy_agent(
    legacy_config_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return _ok(LegacyAgentMigrationService(db).migrate(legacy_config_id, user_id))


@router.post("")
def create_agent(
    payload: AgentCreateRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return _ok(
        AgentService(db).create(
            name=payload.name,
            agent_type=payload.type,
            description=payload.description,
            config=payload.config,
            user_id=user_id,
            version_note=payload.version_note,
        ),
        message="Agent 创建成功",
    )


@router.get("")
def list_agents(
    user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)
):
    return _ok(AgentService(db).list(user_id))


@router.get("/{agent_id}")
def get_agent(
    agent_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return _ok(AgentService(db).get(agent_id, user_id))


@router.patch("/{agent_id}")
def update_agent(
    agent_id: int,
    payload: AgentUpdateRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return _ok(
        AgentService(db).update(
            agent_id, payload.model_dump(exclude_unset=True), user_id
        )
    )


@router.post("/{agent_id}/versions")
def create_version(
    agent_id: int,
    payload: VersionCreateRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return _ok(
        VersionService(db).create(agent_id, payload.config, user_id, payload.note),
        message="版本创建成功",
    )


@router.get("/{agent_id}/versions")
def list_versions(
    agent_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    AgentService(db).get_model(agent_id, user_id)
    return _ok(VersionService(db).list(agent_id))


@router.get("/{agent_id}/versions/{version_id}")
def get_version(
    agent_id: int,
    version_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    AgentService(db).get_model(agent_id, user_id)
    version = VersionService(db).get(version_id)
    if version.agent_id != agent_id:
        from app.core.exceptions import NotFoundException

        raise NotFoundException("版本不存在")
    return _ok(_row(version))


@router.post("/{agent_id}/versions/{version_id}/publish")
def publish_version(
    agent_id: int,
    version_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return _ok(
        VersionService(db).publish(agent_id, version_id, user_id),
        message="版本发布成功",
    )


@router.post("/{agent_id}/versions/{version_id}/validate")
def validate_version(
    agent_id: int,
    version_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    AgentService(db).get_model(agent_id, user_id)
    return _ok(VersionService(db).validate(agent_id, version_id))


@router.post("/{agent_id}/versions/{version_id}/load")
def load_version(
    agent_id: int,
    version_id: int,
    payload: VersionLoadRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    AgentService(db).get_model(agent_id, user_id)
    return _ok(
        VersionService(db).load(
            agent_id,
            version_id,
            payload.environment,
            payload.runtime_config,
            user_id,
        )
    )


