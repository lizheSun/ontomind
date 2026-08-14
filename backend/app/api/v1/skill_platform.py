"""Skill 平台 API — 元数据 / 参数契约 / 执行配置 / 治理策略 / 版本 / 导出."""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.services.skill_platform_service import SkillPlatformService
from app.schemas.skill_platform_schema import (
    SkillCreateRequest,
    SkillFullResponse,
    SkillListItem,
    SkillMetaPayload,
    SkillParamResponse,
    SkillParamsUpdate,
    SkillValidation,
    SkillVersionCreate,
    SkillVersionResponse,
    SkillAuditResponse,
    SkillExportRequest,
    SkillExportResponse,
    ParamDebugRequest,
    ParamDebugResult,
    LifecycleChangeRequest,
    ExecPromptPayload,
    ExecApiPayload,
    ExecFlowPayload,
    SkillPolicyPayload,
    LIFECYCLES,
    SKILL_KINDS,
    RISK_LEVELS,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/skill-platform", tags=["Skill 平台"])


def get_svc(db: Session = Depends(get_db)) -> SkillPlatformService:
    return SkillPlatformService(db)


# ==================== 元数据 ====================

@router.get("/meta/kinds")
def list_kinds():
    """三形态说明。"""
    from app.schemas.skill_platform_schema import SKILL_KIND_META
    return {"data": SKILL_KIND_META}


@router.get("/meta/lifecycles")
def list_lifecycles():
    """生命周期流转说明。"""
    from app.schemas.skill_platform_schema import LIFECYCLE_META
    return {"data": LIFECYCLE_META}


# ==================== Skill CRUD ====================

@router.get("/skills", response_model=List[SkillListItem])
def list_skills(
    keyword: Optional[str] = Query(None),
    kind: Optional[str] = Query(None),
    lifecycle: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    biz_line: Optional[str] = Query(None),
    svc: SkillPlatformService = Depends(get_svc),
):
    """Skill 列表。"""
    return svc.list_skills(
        keyword=keyword, kind=kind, lifecycle=lifecycle,
        risk_level=risk_level, biz_line=biz_line,
    )


@router.post("/skills", response_model=SkillFullResponse)
def create_skill(
    data: SkillCreateRequest,
    svc: SkillPlatformService = Depends(get_svc),
    user_id: int = Depends(get_current_user_id),
):
    """新建 Skill（定义 + 元数据一步到位）。"""
    return svc.create_skill(data, user_id=user_id)


@router.get("/skills/{skill_id}", response_model=SkillFullResponse)
def get_skill(
    skill_id: int,
    svc: SkillPlatformService = Depends(get_svc),
):
    """Skill 全量配置。"""
    return svc.get_skill(skill_id)


@router.put("/skills/{skill_id}", response_model=SkillFullResponse)
def update_skill(
    skill_id: int,
    data: Dict[str, Any] = Body(...),
    svc: SkillPlatformService = Depends(get_svc),
):
    """更新 Skill（各段独立可选）。"""
    return svc.update_skill(skill_id, data)


@router.delete("/skills/{skill_id}")
def delete_skill(
    skill_id: int,
    svc: SkillPlatformService = Depends(get_svc),
):
    """删除 Skill（内置预设禁删）。"""
    svc.delete_skill(skill_id)
    return {"code": "SUCCESS", "message": "Skill 已删除", "data": None}


# ==================== 生命周期 ====================

@router.post("/skills/{skill_id}/lifecycle", response_model=SkillMetaPayload)
def change_lifecycle(
    skill_id: int,
    data: LifecycleChangeRequest,
    svc: SkillPlatformService = Depends(get_svc),
    user_id: int = Depends(get_current_user_id),
):
    """生命周期流转。"""
    return svc.change_lifecycle(skill_id, data.to, data.note, user_id=user_id)


# ==================== 参数契约 ====================

@router.put("/skills/{skill_id}/params", response_model=List[SkillParamResponse])
def update_params(
    skill_id: int,
    data: SkillParamsUpdate,
    svc: SkillPlatformService = Depends(get_svc),
):
    """整批替换某个方向的参数。"""
    return svc.update_params(skill_id, data.direction, [p.model_dump() for p in data.params])


@router.post("/skills/{skill_id}/params/debug", response_model=ParamDebugResult)
def debug_params(
    skill_id: int,
    data: ParamDebugRequest,
    svc: SkillPlatformService = Depends(get_svc),
):
    """在线调试入参（只做 Schema 校验，不真正调用）。"""
    return svc.debug_params(skill_id, data.sample_json)


# ==================== 生命周期校验 ====================

@router.post("/skills/validate/lifecycle", response_model=SkillValidation)
def validate_lifecycle_transition(
    current: str = Body(..., embed=True),
    target: str = Body(..., embed=True),
):
    """校验生命周期迁移是否合法（不落库）。"""
    from app.services.skill_validate_service import validate_lifecycle_transition
    issues = validate_lifecycle_transition(current, target)
    return SkillValidation(ok=not any(i.level == "error" for i in issues), issues=issues)


# ==================== 导出 ====================

@router.post("/skills/{skill_id}/export", response_model=SkillExportResponse)
def export_skill(
    skill_id: int,
    data: SkillExportRequest = Body(default_factory=SkillExportRequest),
    svc: SkillPlatformService = Depends(get_svc),
):
    """一键导出合规 OpenCode 目录包（约束 1）。"""
    return svc.export_skill(skill_id, data.scope, data.include_manifest)


# ==================== 版本 ====================

@router.post("/skills/{skill_id}/versions", response_model=SkillVersionResponse)
def create_version(
    skill_id: int,
    data: SkillVersionCreate = Body(default_factory=SkillVersionCreate),
    svc: SkillPlatformService = Depends(get_svc),
    user_id: int = Depends(get_current_user_id),
):
    """存版本快照。"""
    return svc.create_version(skill_id, data.change_note, data.canary, user_id=user_id)


@router.get("/skills/{skill_id}/versions", response_model=List[SkillVersionResponse])
def list_versions(
    skill_id: int,
    svc: SkillPlatformService = Depends(get_svc),
):
    """版本列表。"""
    return svc.list_versions(skill_id)


@router.post("/skills/{skill_id}/rollback", response_model=SkillFullResponse)
def rollback_skill(
    skill_id: int,
    version: int = Body(..., embed=True),
    svc: SkillPlatformService = Depends(get_svc),
):
    """回滚到指定版本。"""
    return svc.rollback_skill(skill_id, version)


# ==================== 克隆 ====================

@router.post("/skills/{skill_id}/clone", response_model=SkillFullResponse)
def clone_skill(
    skill_id: int,
    new_name: str = Body(..., embed=True),
    svc: SkillPlatformService = Depends(get_svc),
    user_id: int = Depends(get_current_user_id),
):
    """克隆 Skill（名称追加 -copy，生命周期回草稿）。"""
    return svc.clone_skill(skill_id, new_name, user_id=user_id)


# ==================== 审计 ====================

@router.get("/skills/{skill_id}/audit", response_model=List[SkillAuditResponse])
def list_audit(
    skill_id: int,
    svc: SkillPlatformService = Depends(get_svc),
):
    """变更审计日志。"""
    return svc.list_audit(skill_id)


# ==================== 校验 ====================

@router.post("/skills/validate", response_model=SkillValidation)
def validate_skill_payload(
    payload: Dict[str, Any] = Body(...),
):
    """纯校验，不落库。"""
    from app.services.skill_validate_service import validate_skill
    return validate_skill(payload)