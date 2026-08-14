"""Agent 工厂 API — Agent / Skill / 编排方案（Loop）/ 发布.

端点分四组 + 元数据，共 26 个。
统一响应由全局异常处理器 + response_model 保证。

设计依据见 docs/PRD-agent-skill-platform.md。
关键实测结论（决定了发布必须重启）：
- `PATCH /config` 返回 200 但不生效、不落盘
- 写 opencode.jsonc 后不热感知
- `GET /api/skill` 在 skill 可用时仍返回空，不可作校验依据
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.agent_factory_schema import (
    AGENT_PRESETS,
    BUNDLE_PRESETS,
    GLOB_CAPABLE_KEYS,
    PERMISSION_ACTIONS,
    PERMISSION_KEY_META,
    PERMISSION_KEYS,
    SKILL_PRESETS,
    AgentBundleCreate,
    AgentBundleResponse,
    AgentBundleUpdate,
    AgentImportRequest,
    AgentTemplateCreate,
    AgentTemplateResponse,
    AgentTemplateUpdate,
    AgentVersionResponse,
    DeploymentResponse,
    DeployRequest,
    PreviewResponse,
    RollbackRequest,
    SkillTemplateCreate,
    SkillTemplateResponse,
    SkillTemplateUpdate,
    ValidationResult,
    VersionCreateRequest,
)
from app.services.agent_deploy_service import AgentDeployService
from app.services.agent_factory_service import AgentFactoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent-factory", tags=["Agent 工厂"])


def get_factory(db: Session = Depends(get_db)) -> AgentFactoryService:
    return AgentFactoryService(db)


def get_deployer(db: Session = Depends(get_db)) -> AgentDeployService:
    return AgentDeployService(db)


# ==================== 元数据 ====================

@router.get("/permission-keys")
def list_permission_keys():
    """OpenCode 的 15 个合法权限键及元数据。

    前端据此渲染权限矩阵；也是「为什么写 write 不生效」的答案来源。
    """
    return {
        "keys": PERMISSION_KEYS,
        "glob_capable": GLOB_CAPABLE_KEYS,
        "actions": PERMISSION_ACTIONS,
        "meta": PERMISSION_KEY_META,
        "notes": [
            "OpenCode 对未列出的权限键**静默忽略**（不报错也不生效），所以平台在保存前会拦截。",
            "支持 glob 的键可配 {\"*\": \"ask\", \"git diff\": \"allow\"}；其余键只能给简写动作。",
            "规则按顺序匹配且**最后匹配的胜出**，所以 \"*\" 必须写在第一个。",
        ],
    }


@router.get("/presets")
def list_presets():
    """内置预设清单（6 个 Loop 模式 / 8 个 Agent / 4 个 Skill）。"""
    return {
        "bundles": [
            {
                "name": b["name"],
                "pattern": b["pattern"],
                "description": b.get("description"),
                "default_agent": b.get("default_agent"),
                "subagent_depth": b.get("subagent_depth"),
                "agents": [n for n, _ in (b.get("agents") or [])],
                "skills": [n for n, _ in (b.get("skills") or [])],
            }
            for b in BUNDLE_PRESETS
        ],
        "agents": [
            {
                "name": a["name"],
                "display_name": a.get("display_name"),
                "description": a["description"],
                "mode": a.get("mode"),
                "category": a.get("category"),
            }
            for a in AGENT_PRESETS
        ],
        "skills": [
            {
                "name": s["name"],
                "display_name": s.get("display_name"),
                "description": s["description"],
                "category": s.get("category"),
                "files": [f["rel_path"] for f in (s.get("files") or [])],
            }
            for s in SKILL_PRESETS
        ],
    }


# ==================== Agent ====================

@router.get("/agents", response_model=List[AgentTemplateResponse])
def list_agents(
    category: Optional[str] = Query(None, description="按分类筛选"),
    mode: Optional[str] = Query(None, description="按模式筛选: subagent/primary/all"),
    keyword: Optional[str] = Query(None, description="名称或描述关键词"),
    svc: AgentFactoryService = Depends(get_factory),
):
    """Agent 模板列表。"""
    return svc.list_agents(category=category, mode=mode, keyword=keyword)


@router.post("/agents", response_model=AgentTemplateResponse)
def create_agent(
    data: AgentTemplateCreate,
    svc: AgentFactoryService = Depends(get_factory),
    user_id: int = Depends(get_current_user_id),
):
    """创建 Agent 模板（保存前强制校验权限键等）。"""
    return svc.create_agent(data, user_id=user_id)


@router.post("/agents/validate", response_model=ValidationResult)
def validate_agent(
    payload: Dict[str, Any] = Body(..., description="agent 字段（不落库，纯校验）"),
    svc: AgentFactoryService = Depends(get_factory),
):
    """纯校验，不落库 —— 前端边编辑边提示用。"""
    return svc.validate_agent_payload(payload)


@router.post("/agents/import", response_model=AgentTemplateResponse)
def import_agent(
    data: AgentImportRequest,
    svc: AgentFactoryService = Depends(get_factory),
    user_id: int = Depends(get_current_user_id),
):
    """从 agent .md 文本反向导入（把手写的 agent 收进平台管理）。"""
    return svc.import_agent(data, user_id=user_id)


@router.get("/agents/{agent_id}", response_model=AgentTemplateResponse)
def get_agent(agent_id: int, svc: AgentFactoryService = Depends(get_factory)):
    """Agent 模板详情。"""
    return svc.get_agent(agent_id)


@router.put("/agents/{agent_id}", response_model=AgentTemplateResponse)
def update_agent(
    agent_id: int,
    data: AgentTemplateUpdate,
    svc: AgentFactoryService = Depends(get_factory),
):
    """更新 Agent 模板（name 不可改 —— 它是落盘文件名）。"""
    return svc.update_agent(agent_id, data)


@router.delete("/agents/{agent_id}")
def delete_agent(agent_id: int, svc: AgentFactoryService = Depends(get_factory)):
    """删除 Agent 模板（内置预设禁删；被方案引用时禁删）。"""
    svc.delete_agent(agent_id)
    return {"code": "SUCCESS", "message": "Agent 模板已删除", "data": None}


@router.post("/agents/{agent_id}/preview", response_model=PreviewResponse)
def preview_agent(agent_id: int, svc: AgentFactoryService = Depends(get_factory)):
    """渲染 .md 预览（不落盘）—— 所见即所得。"""
    return svc.preview_agent(agent_id)


@router.get("/agents/{agent_id}/versions", response_model=List[AgentVersionResponse])
def list_agent_versions(agent_id: int, svc: AgentFactoryService = Depends(get_factory)):
    """版本列表。"""
    return svc.list_agent_versions(agent_id)


@router.post("/agents/{agent_id}/versions", response_model=AgentVersionResponse)
def create_agent_version(
    agent_id: int,
    data: VersionCreateRequest,
    svc: AgentFactoryService = Depends(get_factory),
    user_id: int = Depends(get_current_user_id),
):
    """存一个版本快照（整份配置留存，可回滚）。"""
    return svc.create_agent_version(agent_id, data.change_note, user_id=user_id)


@router.post("/agents/{agent_id}/rollback", response_model=AgentTemplateResponse)
def rollback_agent(
    agent_id: int,
    data: RollbackRequest,
    svc: AgentFactoryService = Depends(get_factory),
):
    """回滚到指定版本（name 不回滚）。"""
    return svc.rollback_agent(agent_id, data.version)


# ==================== Skill ====================

@router.get("/skills", response_model=List[SkillTemplateResponse])
def list_skills(
    category: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    svc: AgentFactoryService = Depends(get_factory),
):
    """Skill 模板列表（含附属文件）。"""
    return svc.list_skills(category=category, keyword=keyword)


@router.post("/skills", response_model=SkillTemplateResponse)
def create_skill(
    data: SkillTemplateCreate,
    svc: AgentFactoryService = Depends(get_factory),
    user_id: int = Depends(get_current_user_id),
):
    """创建 Skill 模板（支持 references/scripts 多文件）。"""
    return svc.create_skill(data, user_id=user_id)


@router.get("/skills/{skill_id}", response_model=SkillTemplateResponse)
def get_skill(skill_id: int, svc: AgentFactoryService = Depends(get_factory)):
    """Skill 模板详情。"""
    return svc.get_skill(skill_id)


@router.put("/skills/{skill_id}", response_model=SkillTemplateResponse)
def update_skill(
    skill_id: int,
    data: SkillTemplateUpdate,
    svc: AgentFactoryService = Depends(get_factory),
):
    """更新 Skill 模板（传 files 即整批替换附属文件）。"""
    return svc.update_skill(skill_id, data)


@router.delete("/skills/{skill_id}")
def delete_skill(skill_id: int, svc: AgentFactoryService = Depends(get_factory)):
    """删除 Skill 模板（内置预设禁删；被方案引用时禁删）。"""
    svc.delete_skill(skill_id)
    return {"code": "SUCCESS", "message": "Skill 模板已删除", "data": None}


@router.post("/skills/{skill_id}/preview", response_model=PreviewResponse)
def preview_skill(skill_id: int, svc: AgentFactoryService = Depends(get_factory)):
    """渲染 skill 目录预览（SKILL.md + 附属文件）。"""
    return svc.preview_skill(skill_id)


# ==================== 编排方案（Bundle / Loop） ====================

@router.get("/bundles", response_model=List[AgentBundleResponse])
def list_bundles(
    pattern: Optional[str] = Query(None, description="按 Loop 模式筛选"),
    keyword: Optional[str] = Query(None),
    svc: AgentFactoryService = Depends(get_factory),
):
    """编排方案列表（含成员）。"""
    return svc.list_bundles(pattern=pattern, keyword=keyword)


@router.post("/bundles", response_model=AgentBundleResponse)
def create_bundle(
    data: AgentBundleCreate,
    svc: AgentFactoryService = Depends(get_factory),
    user_id: int = Depends(get_current_user_id),
):
    """创建编排方案（会做拓扑一致性校验）。"""
    return svc.create_bundle(data, user_id=user_id)


@router.get("/bundles/{bundle_id}", response_model=AgentBundleResponse)
def get_bundle(bundle_id: int, svc: AgentFactoryService = Depends(get_factory)):
    """编排方案详情。"""
    return svc.get_bundle(bundle_id)


@router.put("/bundles/{bundle_id}", response_model=AgentBundleResponse)
def update_bundle(
    bundle_id: int,
    data: AgentBundleUpdate,
    svc: AgentFactoryService = Depends(get_factory),
):
    """更新编排方案（传 members 即整批替换成员）。"""
    return svc.update_bundle(bundle_id, data)


@router.delete("/bundles/{bundle_id}")
def delete_bundle(bundle_id: int, svc: AgentFactoryService = Depends(get_factory)):
    """删除编排方案（内置预设禁删）。"""
    svc.delete_bundle(bundle_id)
    return {"code": "SUCCESS", "message": "编排方案已删除", "data": None}


@router.post("/bundles/{bundle_id}/validate", response_model=ValidationResult)
def validate_bundle(bundle_id: int, svc: AgentFactoryService = Depends(get_factory)):
    """校验编排方案（含 Loop 拓扑一致性：死引用、无 primary、depth 冲突等）。"""
    return svc.validate_bundle(bundle_id)


@router.post("/bundles/{bundle_id}/preview", response_model=PreviewResponse)
def preview_bundle(bundle_id: int, svc: AgentFactoryService = Depends(get_factory)):
    """全量产物预览 —— 发布前确认到底会写哪些文件。"""
    return svc.preview_bundle(bundle_id)


# ==================== 发布 ====================

@router.post("/bundles/{bundle_id}/deploy", response_model=DeploymentResponse)
async def deploy_bundle(
    bundle_id: int,
    data: DeployRequest,
    svc: AgentDeployService = Depends(get_deployer),
    user_id: int = Depends(get_current_user_id),
):
    """发布编排方案到 Docker 容器（五阶段：解析→校验→写入→重启→回读校验）。

    ⚠️ 必须传 restart_confirmed=true：发布需重启容器内 opencode 服务才能生效，
       会中断进行中的会话。
    """
    return await svc.deploy(bundle_id, data, user_id=user_id)


@router.get("/deployments", response_model=List[DeploymentResponse])
def list_deployments(
    bundle_id: Optional[int] = Query(None),
    node_id: Optional[int] = Query(None),
    container_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    svc: AgentDeployService = Depends(get_deployer),
):
    """发布历史。"""
    return svc.list_deployments(
        bundle_id=bundle_id, node_id=node_id,
        container_id=container_id, status=status,
    )


@router.get("/deployments/{deployment_id}", response_model=DeploymentResponse)
def get_deployment(
    deployment_id: int, svc: AgentDeployService = Depends(get_deployer)
):
    """发布详情（含产物清单与回读校验结果）。"""
    return svc.get_deployment(deployment_id)


@router.post("/deployments/{deployment_id}/verify", response_model=DeploymentResponse)
async def reverify_deployment(
    deployment_id: int, svc: AgentDeployService = Depends(get_deployer)
):
    """重新回读校验（不重写文件、不重启）—— 用于检测产物漂移。"""
    return await svc.reverify(deployment_id)
