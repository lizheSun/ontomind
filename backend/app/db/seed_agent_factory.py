"""Agent 工厂内置预设播种.

幂等：以 name 为准 upsert。
- 内置预设的**结构性字段**（description/permission/prompt 等）每次启动都刷新，
  保证平台升级后预设跟着更新
- 用户自建的模板（is_builtin_preset=False）绝不触碰

在 app/main.py 的 lifespan 里调用，紧跟 create_all 之后。
"""
import logging
from typing import Dict, List

from sqlalchemy.orm import Session

from app.db.models.agent_bundle_model import (
    AgentBundle,
    BundleMember,
    MemberRole,
    MemberType,
)
from app.db.models.agent_template_model import AgentTemplate, TemplateSource
from app.db.models.skill_template_model import SkillFile, SkillTemplate
from app.schemas.agent_factory_schema import (
    AGENT_PRESETS,
    BUNDLE_PRESETS,
    SKILL_PRESETS,
)

logger = logging.getLogger(__name__)


def _seed_agents(db: Session) -> Dict[str, int]:
    """播种 agent 预设，返回 {name: id}。"""
    name_to_id: Dict[str, int] = {}

    for p in AGENT_PRESETS:
        name = p["name"]
        row = db.query(AgentTemplate).filter(AgentTemplate.name == name).first()
        payload = {
            "display_name": p.get("display_name"),
            "description": p["description"],
            "mode": p.get("mode", "subagent"),
            "prompt": p.get("prompt"),
            "temperature": p.get("temperature"),
            "steps": p.get("steps"),
            "permission_json": p.get("permission"),
            "color": p.get("color"),
            "category": p.get("category"),
            "is_builtin_preset": True,
            "source": TemplateSource.PRESET.value,
        }
        if row is None:
            row = AgentTemplate(name=name, current_version=1, **payload)
            db.add(row)
            db.flush()
            logger.info(f"[seed] agent 预设新增: {name}")
        elif row.is_builtin_preset:
            # 只刷新内置预设；用户改过的自建模板不动
            changed = False
            for k, v in payload.items():
                if getattr(row, k, None) != v:
                    setattr(row, k, v)
                    changed = True
            if changed:
                db.flush()
                logger.info(f"[seed] agent 预设更新: {name}")
        name_to_id[name] = row.id

    return name_to_id


def _seed_skills(db: Session) -> Dict[str, int]:
    """播种 skill 预设（含附属文件），返回 {name: id}。"""
    name_to_id: Dict[str, int] = {}

    for p in SKILL_PRESETS:
        name = p["name"]
        row = db.query(SkillTemplate).filter(SkillTemplate.name == name).first()
        payload = {
            "display_name": p.get("display_name"),
            "description": p["description"],
            "license": p.get("license"),
            "compatibility": p.get("compatibility"),
            "metadata_json": p.get("metadata_json"),
            "body": p.get("body"),
            "category": p.get("category"),
            "is_builtin_preset": True,
            "source": TemplateSource.PRESET.value,
        }
        if row is None:
            row = SkillTemplate(name=name, current_version=1, **payload)
            db.add(row)
            db.flush()
            logger.info(f"[seed] skill 预设新增: {name}")
        elif row.is_builtin_preset:
            changed = False
            for k, v in payload.items():
                if getattr(row, k, None) != v:
                    setattr(row, k, v)
                    changed = True
            if changed:
                db.flush()
                logger.info(f"[seed] skill 预设更新: {name}")

        # 附属文件：内置预设整批重建（保证与代码里的定义一致）
        if row.is_builtin_preset:
            want = {f["rel_path"]: f for f in (p.get("files") or [])}
            existing = (
                db.query(SkillFile)
                .filter(SkillFile.skill_template_id == row.id)
                .all()
            )
            exist_map = {f.rel_path: f for f in existing}

            # 删除已移除的
            for rel, f in exist_map.items():
                if rel not in want:
                    db.delete(f)
            # 增改
            for rel, spec in want.items():
                cur = exist_map.get(rel)
                if cur is None:
                    db.add(SkillFile(
                        skill_template_id=row.id,
                        rel_path=rel,
                        content=spec.get("content") or "",
                        is_executable=bool(spec.get("is_executable")),
                    ))
                else:
                    cur.content = spec.get("content") or ""
                    cur.is_executable = bool(spec.get("is_executable"))
            db.flush()

        name_to_id[name] = row.id

    return name_to_id


def _seed_bundles(
    db: Session, agent_ids: Dict[str, int], skill_ids: Dict[str, int]
) -> None:
    """播种 bundle 预设（含成员）。"""
    for p in BUNDLE_PRESETS:
        name = p["name"]
        row = db.query(AgentBundle).filter(AgentBundle.name == name).first()
        payload = {
            "description": p.get("description"),
            "pattern": p.get("pattern", "custom"),
            "default_agent": p.get("default_agent"),
            "subagent_depth": p.get("subagent_depth"),
            "global_permission_json": p.get("global_permission_json"),
            "topology_json": p.get("topology_json"),
            "is_builtin_preset": True,
        }
        if row is None:
            row = AgentBundle(name=name, current_version=1, **payload)
            db.add(row)
            db.flush()
            logger.info(f"[seed] bundle 预设新增: {name}")
        elif row.is_builtin_preset:
            changed = False
            for k, v in payload.items():
                if getattr(row, k, None) != v:
                    setattr(row, k, v)
                    changed = True
            if changed:
                db.flush()

        if not row.is_builtin_preset:
            continue

        # 成员整批重建（内置预设以代码定义为准）
        db.query(BundleMember).filter(BundleMember.bundle_id == row.id).delete(
            synchronize_session=False
        )
        db.flush()

        order = 0
        for agent_name, role in p.get("agents") or []:
            aid = agent_ids.get(agent_name)
            if aid is None:
                logger.warning(f"[seed] bundle {name} 引用了不存在的 agent {agent_name}，跳过")
                continue
            db.add(BundleMember(
                bundle_id=row.id,
                member_type=MemberType.AGENT.value,
                agent_template_id=aid,
                role=role,
                sort_order=order,
            ))
            order += 1

        for skill_name, perm in p.get("skills") or []:
            sid = skill_ids.get(skill_name)
            if sid is None:
                logger.warning(f"[seed] bundle {name} 引用了不存在的 skill {skill_name}，跳过")
                continue
            db.add(BundleMember(
                bundle_id=row.id,
                member_type=MemberType.SKILL.value,
                skill_template_id=sid,
                role=MemberRole.SKILL.value,
                skill_permission=perm,
                sort_order=order,
            ))
            order += 1

        db.flush()


def seed_agent_factory(db: Session) -> None:
    """播种全部 Agent 工厂预设（幂等）。"""
    try:
        agent_ids = _seed_agents(db)
        skill_ids = _seed_skills(db)
        _seed_bundles(db, agent_ids, skill_ids)
        db.commit()
        logger.info(
            f"[seed] Agent 工厂预设就绪: "
            f"{len(agent_ids)} agents / {len(skill_ids)} skills / {len(BUNDLE_PRESETS)} bundles"
        )
    except Exception as e:
        db.rollback()
        # 播种失败不能阻塞应用启动
        logger.error(f"[seed] Agent 工厂预设播种失败（不影响启动）: {e}")


__all__ = ["seed_agent_factory"]
