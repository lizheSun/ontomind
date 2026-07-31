"""专家团 API — /api/v1/experts.

OALP v1.0：
- 一个 expert = 一份 opencode agent markdown + 可选 Docker 容器
- 一个 AgentRelation 决定两个 expert 间的 `permission.task` 规则
- 部署容器时把 expert md + skills + opencode.json 精确 mount 到容器内
"""
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.expert_schema import (
    AgentRelationCreate,
    ExpertAutoDraftRequest,
    ExpertAutoDraftResponse,
    ExpertCloneRequest,
    ExpertCreate,
    ExpertDeployContainerRequest,
    ExpertUpdate,
)
from app.services.expert_service import (
    AgentRelationService,
    ExpertService,
    auto_draft_expert,
    clone_expert,
    deploy_expert_container,
    seed_default_experts,
)

router = APIRouter()


def _ok(data, message: str = "操作成功"):
    return {"code": "SUCCESS", "message": message, "data": data}


# ---------------------------------------------------------------------------
# Expert CRUD
# ---------------------------------------------------------------------------

@router.get("")
def list_experts(
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    svc = ExpertService(db)
    return _ok(svc.list(skip, limit))


@router.post("/seed")
def seed_experts(
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    """幂等：为空库注入 4 个内置专家 + 演示关系."""
    added = seed_default_experts(db)
    return _ok({"added": added}, message=f"已 seed {added} 个专家")


@router.post("/auto-draft", response_model=ExpertAutoDraftResponse)
def auto_draft(
    payload: ExpertAutoDraftRequest,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    """一句话 LLM 生成专家草稿（不落库，前端二次微调后 POST /experts）.

    直接返回 ExpertAutoDraftResponse（不走 _ok 包装），便于前端用 form.setFieldsValue。
    """
    return auto_draft_expert(db, payload.description)


@router.post("")
def create_expert(
    payload: ExpertCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    svc = ExpertService(db)
    return _ok(svc.create(payload, user_id), message="专家已创建")


@router.get("/{expert_id}")
def get_expert(
    expert_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    svc = ExpertService(db)
    return _ok(svc.get(expert_id))


@router.patch("/{expert_id}")
def update_expert(
    expert_id: int,
    payload: ExpertUpdate,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    svc = ExpertService(db)
    return _ok(svc.update(expert_id, payload), message="专家已更新")


@router.delete("/{expert_id}")
def delete_expert(
    expert_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    svc = ExpertService(db)
    svc.delete(expert_id)
    return _ok(None, message="专家已删除")


@router.post("/{expert_id}/clone")
def clone_expert_endpoint(
    expert_id: int,
    payload: ExpertCloneRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """复制专家（含 skills / mcps / permission 等所有字段，version=1）."""
    new_id = clone_expert(db, expert_id, payload.new_slug, payload.new_name, user_id)
    svc = ExpertService(db)
    return _ok(svc.get(new_id), message="专家已克隆")


@router.post("/{expert_id}/start")
def start_expert(
    expert_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    svc = ExpertService(db)
    return _ok(svc.start(expert_id), message="专家已启动")


@router.post("/{expert_id}/stop")
def stop_expert(
    expert_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    svc = ExpertService(db)
    return _ok(svc.stop(expert_id), message="专家已关闭")


# ---------------------------------------------------------------------------
# 容器部署 — 核心需求 #1
# ---------------------------------------------------------------------------

@router.post("/{expert_id}/deploy-container")
def deploy_container(
    expert_id: int,
    payload: ExpertDeployContainerRequest,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    """拉起 opencode 容器，自动注入 agent md + skills + opencode.json."""
    result = deploy_expert_container(
        db=db,
        expert_id=expert_id,
        node_id=payload.node_id,
        container_template_id=payload.container_template_id,
        host_port=payload.host_port,
        extra_env=payload.extra_env,
        auto_start=payload.auto_start,
    )
    return _ok(result, message="容器已部署")


# ---------------------------------------------------------------------------
# 多 Agent 关系 — OALP 主调子协同
# ---------------------------------------------------------------------------

@router.get("/relations/all")
def list_all_relations(
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    svc = AgentRelationService(db)
    return _ok(svc.list_all())


@router.get("/{expert_id}/relations")
def list_expert_relations(
    expert_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    svc = AgentRelationService(db)
    return _ok(svc.list_for_parent(expert_id))


@router.post("/relations")
def create_relation(
    payload: AgentRelationCreate,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    svc = AgentRelationService(db)
    return _ok(svc.create(
        parent_id=payload.parent_expert_id,
        child_id=payload.child_expert_id,
        relation=payload.relation,
        condition=payload.condition,
        sort_order=payload.sort_order,
    ), message="关系已创建")


@router.delete("/relations/{relation_id}")
def delete_relation(
    relation_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    svc = AgentRelationService(db)
    svc.delete(relation_id)
    return _ok(None, message="关系已删除")
