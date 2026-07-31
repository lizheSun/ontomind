"""Expert service — CRUD + agent 文件生成 + 关系/容器编排（OALP v1.0）.

OALP = OntoMind Agent Loop Protocol，对齐 opencode 1.17+ agent 协议。

核心流程：
1. 创建/更新 Expert → 同步生成 ``~/.config/opencode/agent/{slug}.md``
2. 关系（AgentRelation）变化 → 同步生成 ``~/.config/opencode/opencode.json`` 中
   对应 agent 的 ``permission.task`` 节
3. opencode serve 启动时自动 discover 这些文件
4. 前端对话工作台的 ExpertPicker 选中后切到该 agent
5. 容器部署：调 ``POST /experts/{id}/deploy-container`` 走 DockerNodeService
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessException, NotFoundException
from app.db.models.expert_model import Expert
from app.db.models.agent_relation_model import AgentRelation
from app.db.models.skill_model import Skill
from app.db.models.mcp_model import MCP
from app.db.repositories.expert_repo import ExpertRepository
from app.schemas.expert_schema import ExpertCreate, ExpertUpdate


# ---------------------------------------------------------------------------
# opencode agent 文件路径与生成
# ---------------------------------------------------------------------------

def _agent_dir() -> Path:
    """opencode agent 配置目录（markdown 单文件格式）."""
    path = os.environ.get("OPENCODE_AGENT_DIR", "")
    if path:
        return Path(path)
    return Path.home() / ".config" / "opencode" / "agent"


def _opencode_config_path() -> Path:
    """opencode.json 所在目录（用于关系同步时写入 permission.task）."""
    raw = settings.OPENCODE_CONFIG_PATH
    return Path(os.path.expanduser(raw))


_PRIMARY_SLUGS = {"build", "plan", "compaction", "summary", "title"}


def _resolve_mode(expert: Expert) -> str:
    """根据 slug 决定 mode：内置 primary 名强制 primary，其他看字段."""
    if expert.slug in _PRIMARY_SLUGS:
        return "primary"
    return expert.mode or "subagent"


def _build_frontmatter(expert: Expert) -> dict[str, Any]:
    """按 OALP v1.0 生成 opencode agent frontmatter.

    注意：permission.task 由 sync_expert_relations_to_opencode() 统一合并到
    opencode.json 的 agent 节点，不在 .md 文件里写（避免每次保存 agent.md 都
    反查关系导致循环依赖与脏写）。
    """
    fm: dict[str, Any] = {}
    if expert.description:
        fm["description"] = expert.description
    fm["mode"] = _resolve_mode(expert)
    if expert.tools:
        fm["tools"] = expert.tools
    if expert.model:
        fm["model"] = expert.model
    if expert.provider:
        fm["provider"] = expert.provider
    if expert.temperature:
        try:
            fm["temperature"] = float(expert.temperature)
        except (TypeError, ValueError):
            pass
    if expert.top_p:
        try:
            fm["top_p"] = float(expert.top_p)
        except (TypeError, ValueError):
            pass
    if expert.max_steps:
        fm["steps"] = expert.max_steps

    # permission：只写用户自定义的部分（不含 task，那是 opencode.json 的事）
    perm: dict[str, Any] = dict(expert.permission_json or {})
    if perm:
        fm["permission"] = perm

    return fm


def _render_frontmatter_yaml(fm: dict[str, Any]) -> str:
    """把 frontmatter dict 渲染为 YAML（保留 key 顺序，支持嵌套）."""
    lines = ["---"]

    def _emit(key: str, value: Any, indent: int = 0) -> None:
        prefix = "  " * indent
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            for sk, sv in value.items():
                _emit(sk, sv, indent + 1)
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                if isinstance(item, dict):
                    first = True
                    for ik, iv in item.items():
                        bullet = f"{prefix}  -" if first else f"{prefix}   "
                        first = False
                        if isinstance(iv, dict):
                            lines.append(f"{bullet} {ik}:")
                            for iik, iiv in iv.items():
                                lines.append(f"{prefix}     {iik}: {iiv}")
                        else:
                            lines.append(f"{bullet} {ik}: {iv}")
                else:
                    lines.append(f"{prefix}  - {item}")
        elif isinstance(value, bool):
            lines.append(f"{prefix}{key}: {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            lines.append(f"{prefix}{key}: {value}")
        elif value is None:
            lines.append(f"{prefix}{key}: null")
        else:
            escaped = str(value).replace('"', '\\"')
            lines.append(f'{prefix}{key}: "{escaped}"')

    for k, v in fm.items():
        _emit(k, v, 0)
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _build_agent_md(expert: Expert) -> str:
    """根据 Expert 配置生成 opencode agent Markdown 文件内容（OALP v1.0）.

    结构：
      ---
      <YAML frontmatter，含 description/mode/model/tools/permission/...>
      ---

      <role 段，若有>
      <sop 段，若有>
      <system_prompt 段，若有>
    """
    fm = _build_frontmatter(expert)
    yaml_text = _render_frontmatter_yaml(fm)

    body_parts: list[str] = []
    if expert.role:
        body_parts.append(expert.role.strip())
        body_parts.append("")
    if expert.system_prompt:
        body_parts.append(expert.system_prompt.strip())
        body_parts.append("")
    if expert.sop:
        body_parts.append("## 工作流程 (SOP)")
        body_parts.append("")
        body_parts.append(expert.sop.strip())
        body_parts.append("")

    if not body_parts:
        body_parts.append(f"# {expert.name}")
        body_parts.append("")

    return yaml_text + "\n".join(body_parts)


def _write_agent_md(expert: Expert) -> Path:
    """把 agent 定义写入磁盘."""
    d = _agent_dir()
    d.mkdir(parents=True, exist_ok=True)
    content = _build_agent_md(expert)
    path = d / f"{expert.slug}.md"
    path.write_text(content, encoding="utf-8")
    return path


def _remove_agent_md(expert: Expert) -> None:
    path = _agent_dir() / f"{expert.slug}.md"
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# opencode.json 中 permission 节同步（用于 task 关系）
# ---------------------------------------------------------------------------

def _read_opencode_json() -> dict[str, Any]:
    """读 opencode.json，没有则返回空 dict。失败时也不抛异常。"""
    p = _opencode_config_path() / "opencode.json"
    if not p.exists():
        return {}
    try:
        import json
        return json.loads(p.read_text(encoding="utf-8") or "{}")
    except Exception:
        return {}


def _atomic_write_json(target: Path, data: dict[str, Any]) -> None:
    """临时文件 + rename 原子写（与 opencode_sync_service 一致策略）."""
    import json
    import tempfile
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".opencode.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, target)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def sync_expert_relations_to_opencode(db: Session) -> int:
    """把所有 AgentRelation 派生出的 permission.task 合并写入 opencode.json.

    返回被更新的 expert 数。
    """
    import json
    rels = db.query(AgentRelation).all()
    if not rels:
        return 0

    # parent_expert_id -> {child_slug: "allow"}
    by_parent: dict[int, dict[str, str]] = {}
    child_ids: set[int] = set()
    for r in rels:
        by_parent.setdefault(r.parent_expert_id, {})  # 留位
        child_ids.add(r.child_expert_id)

    children = {
        e.id: e for e in db.query(Expert).filter(Expert.id.in_(child_ids)).all()
    } if child_ids else {}
    for r in rels:
        child = children.get(r.child_expert_id)
        if not child or not child.slug:
            continue
        by_parent[r.parent_expert_id][child.slug] = "allow"

    cfg = _read_opencode_json()
    agents = cfg.setdefault("agent", {})
    for parent_id, child_rules in by_parent.items():
        parent = db.query(Expert).get(parent_id)
        if not parent or not parent.slug:
            continue
        node = agents.setdefault(parent.slug, {})
        perm = node.setdefault("permission", {})
        if not isinstance(perm, dict):
            perm = {}
            node["permission"] = perm
        # 合并 task 规则：用户已有规则不覆盖
        existing = perm.get("task") or {}
        if not isinstance(existing, dict):
            existing = {}
        for k, v in child_rules.items():
            existing.setdefault(k, v)
        existing.setdefault("*", existing.get("*", "deny"))
        perm["task"] = existing
        agents[parent.slug] = node

    _atomic_write_json(_opencode_config_path() / "opencode.json", cfg)
    return len(by_parent)


# ---------------------------------------------------------------------------
# docker 探测
# ---------------------------------------------------------------------------

def _docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        r = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True, text=True, timeout=2,
        )
        return r.returncode == 0
    except Exception:
        return False


def _port_open(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# 序列化
# ---------------------------------------------------------------------------

def _serialize(e: Expert) -> dict[str, Any]:
    return {
        "id": e.id, "name": e.name, "slug": e.slug,
        "avatar": e.avatar, "description": e.description,
        "role": e.role, "sop": e.sop,
        "provider": e.provider, "model": e.model,
        "temperature": e.temperature, "top_p": e.top_p,
        "mode": e.mode or "subagent",
        "subagent_depth": e.subagent_depth or 1,
        "max_steps": e.max_steps,
        "system_prompt": e.system_prompt,
        "permission": e.permission_json or {},
        "hooks": e.hooks_json or [],
        "evals": e.evals_json or [],
        "version": e.version or 1,
        "skills": e.skills or [],
        "mcps": e.mcps or [],
        "tools": e.tools or {},
        "image": e.image,
        "container_template_id": e.container_template_id,
        "container_name": e.container_name,
        "container_id": e.container_id,
        "host_port": e.host_port,
        "host": e.host, "port": e.port,
        "bind_skills_to_container": bool(e.bind_skills_to_container),
        "status": e.status, "agent_file_path": e.agent_file_path,
        "started_at": e.started_at.isoformat() if e.started_at else None,
        "stopped_at": e.stopped_at.isoformat() if e.stopped_at else None,
        "error_message": e.error_message,
        "sort_order": e.sort_order,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ExpertService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ExpertRepository(db)

    # ---- list / get ----

    def list(self, skip: int = 0, limit: int = 200) -> list[dict[str, Any]]:
        rows = self.repo.list_ordered(skip, limit)
        for e in rows:
            self._refresh_status(e, commit=False)
        self.db.commit()
        return [_serialize(e) for e in rows]

    def get(self, expert_id: int) -> dict[str, Any]:
        e = self.repo.get_by_id(expert_id)
        if not e:
            raise NotFoundException(f"专家不存在: {expert_id}")
        self._refresh_status(e, commit=True)
        return _serialize(e)

    # ---- create / update / delete ----

    def create(self, payload: ExpertCreate, user_id: Optional[int] = None) -> dict[str, Any]:
        if self.repo.get_by_slug(payload.slug):
            raise BusinessException(f"slug 已存在: {payload.slug}", code="EXPERT_SLUG_DUP")
        e = Expert(
            name=payload.name, slug=payload.slug,
            avatar=payload.avatar, description=payload.description,
            role=payload.role, sop=payload.sop,
            provider=payload.provider, model=payload.model,
            temperature=payload.temperature, top_p=payload.top_p,
            mode=payload.mode or "subagent",
            subagent_depth=payload.subagent_depth or 1,
            max_steps=payload.max_steps,
            system_prompt=payload.system_prompt,
            permission_json=payload.permission or {},
            hooks_json=payload.hooks or [],
            evals_json=payload.evals or [],
            skills=payload.skills or [], mcps=payload.mcps or [],
            tools=payload.tools or {},
            image=payload.image,
            container_template_id=payload.container_template_id,
            bind_skills_to_container=(
                payload.bind_skills_to_container
                if payload.bind_skills_to_container is not None
                else True
            ),
            host=payload.host or "127.0.0.1", port=payload.port or 4096,
            sort_order=payload.sort_order or 0,
            created_by_user_id=user_id, status="offline",
        )
        self.db.add(e)
        self.db.flush()
        try:
            path = _write_agent_md(e)
            e.agent_file_path = str(path)
        except Exception as exc:
            self.db.rollback()
            raise BusinessException(f"写入 agent 文件失败: {exc}", code="EXPERT_AGENT_WRITE_FAILED")
        # 关系同步（让 permission.task 进 opencode.json）
        try:
            sync_expert_relations_to_opencode(self.db)
        except Exception as exc:
            # 关系同步失败不阻塞专家创建
            from loguru import logger
            logger.warning(f"[expert-service] 关系同步失败: {exc}")
        self.db.commit()
        self.db.refresh(e)
        return _serialize(e)

    def update(self, expert_id: int, payload: ExpertUpdate) -> dict[str, Any]:
        e = self.repo.get_by_id(expert_id)
        if not e:
            raise NotFoundException(f"专家不存在: {expert_id}")
        data = payload.model_dump(exclude_unset=True)
        # 嵌套字典/列表的字段需要显式赋值
        nested_keys = {"permission", "hooks", "evals"}
        for k, v in data.items():
            if k in nested_keys:
                setattr(e, f"{k}_json", v)
            else:
                setattr(e, k, v)
        e.version = (e.version or 1) + 1
        self.db.flush()
        try:
            path = _write_agent_md(e)
            e.agent_file_path = str(path)
        except Exception as exc:
            self.db.rollback()
            raise BusinessException(f"写入 agent 文件失败: {exc}", code="EXPERT_AGENT_WRITE_FAILED")
        try:
            sync_expert_relations_to_opencode(self.db)
        except Exception as exc:
            from loguru import logger
            logger.warning(f"[expert-service] 关系同步失败: {exc}")
        self.db.commit()
        self.db.refresh(e)
        return _serialize(e)

    def delete(self, expert_id: int) -> None:
        e = self.repo.get_by_id(expert_id)
        if not e:
            raise NotFoundException(f"专家不存在: {expert_id}")
        # 先清掉以我为 parent/child 的关系
        self.db.query(AgentRelation).filter(
            (AgentRelation.parent_expert_id == expert_id)
            | (AgentRelation.child_expert_id == expert_id)
        ).delete(synchronize_session=False)
        _remove_agent_md(e)
        self.db.delete(e)
        self.db.commit()
        try:
            sync_expert_relations_to_opencode(self.db)
        except Exception:
            pass

    # ---- 启停 ----

    def start(self, expert_id: int) -> dict[str, Any]:
        e = self.repo.get_by_id(expert_id)
        if not e:
            raise NotFoundException(f"专家不存在: {expert_id}")
        try:
            path = _write_agent_md(e)
            e.agent_file_path = str(path)
        except Exception:
            pass
        e.status = "online"
        e.started_at = datetime.now(timezone.utc)
        e.error_message = None
        self.db.commit()
        self.db.refresh(e)
        return _serialize(e)

    def stop(self, expert_id: int) -> dict[str, Any]:
        e = self.repo.get_by_id(expert_id)
        if not e:
            raise NotFoundException(f"专家不存在: {expert_id}")
        _remove_agent_md(e)
        e.status = "offline"
        e.stopped_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(e)
        return _serialize(e)

    def _refresh_status(self, e: Expert, commit: bool = False) -> None:
        if e.status == "error":
            return
        # 在线 = agent.md 文件存在
        path = _agent_dir() / f"{e.slug}.md"
        online = path.exists()
        new_status = "online" if online else "offline"
        if e.status != new_status:
            e.status = new_status
            if not online and not e.stopped_at:
                e.stopped_at = datetime.now(timezone.utc)
        if commit:
            self.db.commit()


# ---------------------------------------------------------------------------
# 关系 service（独立类，避免与 ExpertService 互相依赖）
# ---------------------------------------------------------------------------

class AgentRelationService:
    def __init__(self, db: Session):
        self.db = db

    def list_for_parent(self, parent_id: int) -> list[dict[str, Any]]:
        rows = (
            self.db.query(AgentRelation)
            .filter(AgentRelation.parent_expert_id == parent_id)
            .order_by(AgentRelation.sort_order.asc(), AgentRelation.id.asc())
            .all()
        )
        return [self._serialize(r) for r in rows]

    def list_all(self) -> list[dict[str, Any]]:
        rows = (
            self.db.query(AgentRelation)
            .order_by(AgentRelation.parent_expert_id.asc(), AgentRelation.sort_order.asc())
            .all()
        )
        return [self._serialize(r) for r in rows]

    def create(
        self, parent_id: int, child_id: int,
        relation: str = "delegate", condition: Optional[str] = None,
        sort_order: int = 0,
    ) -> dict[str, Any]:
        from app.db.models.agent_relation_model import assert_no_cycle
        if parent_id == child_id:
            raise BusinessException("父与子不能相同", code="AGENT_RELATION_SELF")
        # 校验两端 expert 存在
        if not self.db.query(Expert).get(parent_id):
            raise NotFoundException(f"父 expert 不存在: {parent_id}")
        if not self.db.query(Expert).get(child_id):
            raise NotFoundException(f"子 expert 不存在: {child_id}")
        # 重复校验
        existing = (
            self.db.query(AgentRelation)
            .filter(
                AgentRelation.parent_expert_id == parent_id,
                AgentRelation.child_expert_id == child_id,
            )
            .first()
        )
        if existing:
            raise BusinessException(
                f"关系已存在 parent={parent_id} → child={child_id}",
                code="AGENT_RELATION_DUP",
            )
        assert_no_cycle(self.db, parent_id, child_id)
        r = AgentRelation(
            parent_expert_id=parent_id,
            child_expert_id=child_id,
            relation=relation,
            condition=condition,
            sort_order=sort_order,
        )
        self.db.add(r)
        self.db.flush()
        # 同步 opencode.json
        try:
            sync_expert_relations_to_opencode(self.db)
        except Exception as exc:
            from loguru import logger
            logger.warning(f"[agent-relation] 同步失败: {exc}")
        self.db.commit()
        self.db.refresh(r)
        return self._serialize(r)

    def delete(self, relation_id: int) -> None:
        r = self.db.query(AgentRelation).get(relation_id)
        if not r:
            raise NotFoundException(f"关系不存在: {relation_id}")
        self.db.delete(r)
        self.db.commit()
        try:
            sync_expert_relations_to_opencode(self.db)
        except Exception:
            pass

    def _serialize(self, r: AgentRelation) -> dict[str, Any]:
        parent = self.db.query(Expert).get(r.parent_expert_id)
        child = self.db.query(Expert).get(r.child_expert_id)
        return {
            "id": r.id,
            "parent_expert_id": r.parent_expert_id,
            "parent_slug": parent.slug if parent else None,
            "parent_name": parent.name if parent else None,
            "child_expert_id": r.child_expert_id,
            "child_slug": child.slug if child else None,
            "child_name": child.name if child else None,
            "relation": r.relation,
            "condition": r.condition,
            "sort_order": r.sort_order,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }


# ---------------------------------------------------------------------------
# 预置专家 seed
# ---------------------------------------------------------------------------

DEFAULT_EXPERTS: list[dict[str, Any]] = [
    {
        "name": "数据分析专家",
        "slug": "data-analyst",
        "avatar": "📊",
        "description": "擅长 SQL、数据建模、指标定义与数据可视化",
        "role": "# 角色定位\n\n你是一位资深数据分析师，精通 SQL、Python 数据科学栈和 BI 工具。",
        "sop": "1. 理解需求 → 2. 探查数据源 → 3. 编写 SQL → 4. 验证结果 → 5. 输出图表",
        "provider": "agent-plan",
        "model": "ark-code-latest",
        "skills": ["byted-web-search", "arkcli-usage"],
        "mcps": [],
        "tools": {"read": True, "write": True, "bash": True, "todo": True},
        "mode": "subagent",
        "permission": {
            "edit": "allow",
            "bash": "allow",
            "webfetch": "allow",
            "websearch": "allow",
        },
        "sort_order": 10,
    },
    {
        "name": "前端专家",
        "slug": "frontend",
        "avatar": "🎨",
        "description": "React / TypeScript / antd / Vite / 视觉设计",
        "role": "# 角色定位\n\n你是一位前端架构师，精通 React 21、TypeScript、antd v6 和 Vite 8。",
        "sop": "1. 理解设计 → 2. 组件拆分 → 3. 实现 → 4. 视觉打磨 → 5. 测试",
        "provider": "agent-plan",
        "model": "ark-code-latest",
        "skills": ["frontend-design", "web-artifacts-builder"],
        "mcps": [],
        "tools": {"read": True, "write": True, "bash": True, "todo": True},
        "mode": "subagent",
        "permission": {
            "edit": "allow",
            "bash": "allow",
        },
        "sort_order": 20,
    },
    {
        "name": "后端专家",
        "slug": "backend",
        "avatar": "⚙️",
        "description": "FastAPI / SQLAlchemy / MySQL / 系统设计",
        "role": "# 角色定位\n\n你是一位后端架构师，精通 FastAPI、SQLAlchemy 2.0、MySQL 8 和 Docker。",
        "sop": "1. 设计 API → 2. 建表 → 3. 实现 service → 4. 写测试 → 5. 部署",
        "provider": "agent-plan",
        "model": "ark-code-latest",
        "skills": ["mcp-builder", "byted-supabase"],
        "mcps": [],
        "tools": {"read": True, "write": True, "bash": True, "todo": True},
        "mode": "subagent",
        "permission": {
            "edit": "allow",
            "bash": "allow",
        },
        "sort_order": 30,
    },
    {
        "name": "产品经理",
        "slug": "product-manager",
        "avatar": "📝",
        "description": "需求分析 / PRD / 用户研究 / 优先级",
        "role": "# 角色定位\n\n你是一位经验丰富的产品经理。",
        "sop": "1. 需求澄清 → 2. 用户研究 → 3. PRD 撰写 → 4. 评审 → 5. 验收",
        "provider": "agent-plan",
        "model": "ark-code-latest",
        "skills": ["doc-coauthoring"],
        "mcps": [],
        "tools": {"read": True, "write": True, "todo": True},
        "mode": "subagent",
        "permission": {
            "edit": "ask",
            "bash": "ask",
        },
        "sort_order": 40,
    },
]


def seed_default_experts(db: Session) -> int:
    added = 0
    repo = ExpertRepository(db)
    for d in DEFAULT_EXPERTS:
        if repo.get_by_slug(d["slug"]):
            continue
        e = Expert(
            **{k: v for k, v in d.items() if k != "permission"},
            permission_json=d.get("permission", {}),
            host="127.0.0.1", port=4096, status="offline",
        )
        db.add(e)
        db.flush()
        try:
            path = _write_agent_md(e)
            e.agent_file_path = str(path)
        except Exception:
            pass
        added += 1
    if added:
        db.commit()
        # 给内置的"产品经理"自动建一条 review 关系到"前端/后端"作为演示
        try:
            rel_svc = AgentRelationService(db)
            pm = repo.get_by_slug("product-manager")
            fe = repo.get_by_slug("frontend")
            be = repo.get_by_slug("backend")
            da = repo.get_by_slug("data-analyst")
            if pm and fe:
                rel_svc.create(pm.id, fe.id, relation="review",
                               condition="涉及前端实现细节时拉前端专家评审", sort_order=10)
            if pm and be:
                rel_svc.create(pm.id, be.id, relation="review",
                               condition="涉及后端实现细节时拉后端专家评审", sort_order=20)
            if pm and da:
                rel_svc.create(pm.id, da.id, relation="delegate",
                               condition="需要数据支撑的决策时让数据分析师提供指标", sort_order=30)
        except Exception:
            pass
    return added


# ---------------------------------------------------------------------------
# 一句话 LLM 生成专家草稿（核心需求 #3）
# ---------------------------------------------------------------------------

def _collect_skill_pool(db: Session) -> list[str]:
    """从 skills 表 + opencode 预置取一个池子."""
    pool: list[str] = []
    try:
        rows = db.query(Skill).filter(Skill.is_active.is_(True)).limit(200).all()
        pool.extend([r.name for r in rows if r.name])
    except Exception:
        pass
    # 加 opencode 官方常见 skill 兜底
    pool.extend([
        "byted-web-search", "byted-supabase", "doc-coauthoring",
        "frontend-design", "web-artifacts-builder", "canvas-design",
        "mcp-builder", "skill-creator", "xlsx", "docx", "pdf", "pptx",
        "algorithmic-art", "internal-comms", "brand-guidelines",
        "slack-gif-creator", "theme-factory", "webapp-testing",
        "arkcli-shared", "arkcli-chat", "arkcli-usage",
    ])
    # 去重保序
    seen: set[str] = set()
    out: list[str] = []
    for s in pool:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _collect_mcp_pool(db: Session) -> list[str]:
    pool: list[str] = []
    try:
        rows = db.query(MCP).filter(MCP.is_active.is_(True)).limit(100).all()
        pool.extend([r.name for r in rows if r.name])
    except Exception:
        pass
    return pool


def _parse_llm_json(content: str) -> dict[str, Any]:
    """从 LLM 输出中抠 JSON（容忍 ```json``` 包裹 / 前置废话）."""
    import json
    import re
    if not content:
        return {}
    s = content.strip()
    # 去 markdown 围栏
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, re.DOTALL)
    if m:
        s = m.group(1)
    # 找第一个 { 到最后一个 }
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        s = s[start:end + 1]
    try:
        return json.loads(s)
    except Exception:
        return {}


def _slugify(text: str) -> str:
    import re
    s = (text or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:48] or "expert"


def auto_draft_expert(db: Session, description: str) -> dict[str, Any]:
    """调用 LLMConfigService.chat_completion 生成专家草稿.

    失败回退：基于 description 做一个最小可用的草稿。
    """
    skill_pool = _collect_skill_pool(db)
    mcp_pool = _collect_mcp_pool(db)

    sys_prompt = (
        "你是 OntoMind 平台上的「专家团设计师」。\n"
        "请根据用户的一段自然语言描述，输出一份 JSON（不要 markdown 包裹，"
        "直接 { 开头 } 结尾）。\n"
        "schema 如下：\n"
        "{\n"
        '  "name": "<中文名称，<= 8 字>",\n'
        '  "slug": "<英文 kebab-case，<= 48 字>",\n'
        '  "avatar": "<单个 emoji>",\n'
        '  "description": "<一句话中文描述，<= 60 字>",\n'
        '  "role": "<# 角色定位\\n\\n...，3-5 行 Markdown>",\n'
        '  "sop": "<## 工作流程\\n\\n1. ... 2. ... 3. ...>",\n'
        '  "skills": ["<从预置池挑 0-5 个>"],\n'
        '  "mcps": ["<从预置池挑 0-3 个>"],\n'
        '  "tools": {"read": true, "write": true, "bash": true, "todo": true},\n'
        '  "temperature": "0.3",\n'
        '  "permission": {"edit": "allow", "bash": "ask", "websearch": "allow"}\n'
        "}\n"
        f"可用 skills 池（最多列 60 个）：{', '.join(skill_pool[:60])}\n"
        f"可用 mcps 池：{', '.join(mcp_pool) or '（当前系统没有 MCP，可返回空数组）'}\n"
    )
    user_prompt = f"用户描述：{description}"

    draft: dict[str, Any] = {}
    try:
        from app.services.llm_config_service import LLMConfigService
        llm = LLMConfigService(db)
        # chat_completion 是 async，这里走 asyncio
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            resp = loop.run_until_complete(llm.chat_completion(
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=1200,
            ))
        finally:
            loop.close()
        draft = _parse_llm_json(resp.get("content", ""))
    except Exception as exc:
        from loguru import logger
        logger.warning(f"[auto-draft] LLM 调用失败: {exc}")

    # 字段兜底
    if not draft.get("name"):
        draft["name"] = (description or "新专家")[:8] or "新专家"
    if not draft.get("slug"):
        draft["slug"] = _slugify(draft.get("name", ""))
    if not draft.get("avatar"):
        draft["avatar"] = "🤖"
    if not draft.get("description"):
        draft["description"] = (description or "")[:60]
    if not draft.get("role"):
        draft["role"] = f"# 角色定位\n\n你是一位 {draft['name']}。"
    if not draft.get("sop"):
        draft["sop"] = (
            "## 工作流程\n\n"
            "1. 理解用户需求\n"
            "2. 制定执行计划\n"
            "3. 实施并验证\n"
            "4. 输出结果并复盘"
        )
    draft.setdefault("provider", "agent-plan")
    draft.setdefault("model", "ark-code-latest")
    draft.setdefault("temperature", "0.3")
    draft.setdefault("skills", [])
    draft.setdefault("mcps", [])
    draft.setdefault("tools", {
        "read": True, "write": True, "bash": True, "todo": True,
    })
    draft.setdefault("permission", {"edit": "allow", "bash": "ask"})
    # 强制 tools 字段为 bool
    for k, v in list(draft["tools"].items()):
        draft["tools"][k] = bool(v)
    return draft


# ---------------------------------------------------------------------------
# 复制专家
# ---------------------------------------------------------------------------

def clone_expert(
    db: Session, src_id: int, new_slug: str,
    new_name: Optional[str] = None, user_id: Optional[int] = None,
) -> int:
    src = db.query(Expert).get(src_id)
    if not src:
        raise NotFoundException(f"源专家不存在: {src_id}")
    if db.query(Expert).filter(Expert.slug == new_slug).first():
        raise BusinessException(f"目标 slug 已存在: {new_slug}", code="EXPERT_SLUG_DUP")
    new_e = Expert(
        name=new_name or f"{src.name} 副本",
        slug=new_slug,
        avatar=src.avatar,
        description=src.description,
        role=src.role, sop=src.sop,
        provider=src.provider, model=src.model,
        temperature=src.temperature, top_p=src.top_p,
        mode=src.mode, subagent_depth=src.subagent_depth,
        max_steps=src.max_steps, system_prompt=src.system_prompt,
        permission_json=dict(src.permission_json or {}),
        hooks_json=list(src.hooks_json or []),
        evals_json=list(src.evals_json or []),
        skills=list(src.skills or []),
        mcps=list(src.mcps or []),
        tools=dict(src.tools or {}),
        image=src.image,
        container_template_id=src.container_template_id,
        bind_skills_to_container=src.bind_skills_to_container,
        host=src.host, port=src.port,
        sort_order=(src.sort_order or 0) + 1,
        version=1,
        created_by_user_id=user_id,
        status="offline",
    )
    db.add(new_e)
    db.flush()
    try:
        path = _write_agent_md(new_e)
        new_e.agent_file_path = str(path)
    except Exception:
        pass
    db.commit()
    db.refresh(new_e)
    return new_e.id


# ---------------------------------------------------------------------------
# 容器化部署（核心需求 #1）
# ---------------------------------------------------------------------------

def _render_template_env(template) -> list[str]:
    import json as _json
    try:
        return _json.loads(template.env_vars or "[]")
    except Exception:
        return []


def _render_template_volumes(template) -> list[str]:
    import json as _json
    try:
        return _json.loads(template.volumes or "[]")
    except Exception:
        return []


def _render_template_ports(template) -> list[str]:
    import json as _json
    try:
        return _json.loads(template.ports or "[]")
    except Exception:
        return []


def _next_free_port(host: str, start: int = 14100, end: int = 15100) -> int:
    import socket as _sock
    for p in range(start, end):
        with _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM) as s:
            try:
                s.bind((host, p))
                return p
            except OSError:
                continue
    raise BusinessException(f"在 {start}-{end} 区间找不到空闲端口", code="PORT_EXHAUSTED")


def deploy_expert_container(
    db: Session, expert_id: int, node_id: int,
    container_template_id: Optional[int] = None,
    host_port: Optional[int] = None,
    extra_env: Optional[dict[str, str]] = None,
    auto_start: bool = True,
) -> dict[str, Any]:
    """在指定 Docker 节点上拉起 opencode 容器，自动注入 expert md + skills.

    步骤：
    1. 查 expert / node / template
    2. 重新写 agent md 到磁盘（确保最新）
    3. 构造 ContainerCreate：把 expert md / skills / opencode.json 精确 mount
    4. docker run → 容器起来
    5. 等 health（/global/health）→ 把 container_id/host_port/status 写回 expert
    """
    from app.db.models.container_template_model import ContainerTemplate
    from app.schemas.docker_node_schema import ContainerCreate
    from app.services.docker_node_service import DockerNodeService

    expert = db.query(Expert).get(expert_id)
    if not expert:
        raise NotFoundException(f"专家不存在: {expert_id}")

    node_svc = DockerNodeService(db)
    node = node_svc.repo.get_by_id(node_id)
    if not node:
        raise NotFoundException(f"Docker 节点不存在: {node_id}")

    # 1) 选模板
    if container_template_id:
        template = db.query(ContainerTemplate).get(container_template_id)
        if not template:
            raise NotFoundException(f"容器模板不存在: {container_template_id}")
    else:
        # 找内置 opencode 模板；没有就用任意 image=opencode 的
        template = (
            db.query(ContainerTemplate)
            .filter(ContainerTemplate.name.in_(["opencode-agent", "OpenCode"]))
            .order_by(ContainerTemplate.sort_order.asc())
            .first()
        )
        if not template:
            raise NotFoundException("未找到内置 opencode 容器模板，请先在容器模板页创建")

    # 2) 写最新 agent md 到磁盘（保证容器 mount 到的是最新）
    try:
        path = _write_agent_md(expert)
        expert.agent_file_path = str(path)
        db.commit()
    except Exception as exc:
        from loguru import logger
        logger.warning(f"[deploy-container] 写 agent md 失败: {exc}")

    # 3) 构造 volumes
    agent_dir = _agent_dir()                # ~/.config/opencode/agent
    cfg_dir = _opencode_config_path()        # ~/.config/opencode
    skill_dir = cfg_dir / "skills"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    agent_dir.mkdir(parents=True, exist_ok=True)
    skill_dir.mkdir(parents=True, exist_ok=True)

    base_volumes = _render_template_volumes(template)
    # 把 bind-mount 容器配置目录保留，其他 named volume 也保留
    # 关键：精确挂载本机的 agent/{slug}.md → 容器内 /root/.config/opencode/agent/{slug}.md
    base_volumes = [
        v for v in base_volumes
        if not v.startswith("opencode-config:") and not v.startswith("opencode-data:")
    ]
    base_volumes.extend([
        f"{agent_dir}:/root/.config/opencode/agent:ro",
        f"{skill_dir}:/root/.config/opencode/skills:ro",
        f"{cfg_dir}/opencode.json:/root/.config/opencode/opencode.json:ro",
    ])

    # 4) 选 host_port
    if not host_port:
        try:
            host_port = _next_free_port("127.0.0.1")
        except BusinessException:
            host_port = 14100
    ports = [f"{host_port}:4096"] if not _render_template_ports(template) else _render_template_ports(template)
    # 替换模板里的 4096:4096 为实际端口
    ports = [p.replace("4096:4096", f"{host_port}:4096") for p in ports]

    # 5) env
    env_vars = _render_template_env(template)
    # 把 OPENCODE_PORT 同步成我们映射出来的端口
    env_vars = [e for e in env_vars if not e.startswith("OPENCODE_PORT=")]
    env_vars.append(f"OPENCODE_PORT=4096")
    env_vars.append(f"OPENCODE_HOSTNAME=0.0.0.0")
    env_vars.append("OPENCODE_CORS=http://localhost:5173,http://127.0.0.1:5173")
    if extra_env:
        for k, v in extra_env.items():
            env_vars.append(f"{k}={v}")

    # 6) container name：ontomind-{slug}-{短 id}
    short = expert.slug.replace("_", "-")[:32]
    container_name = f"ontomind-{short}-{expert.id}"

    # 7) 构造 payload 调 create_container
    payload = ContainerCreate(
        name=container_name,
        image=template.image,
        ports=ports,
        env_vars=env_vars,
        volumes=base_volumes,
        expert_slug=expert.slug,
        restart_policy=template.restart_policy or "unless-stopped",
        network=template.network,
        extra_args=template.extra_args,
        command=template.command or "opencode serve --port 4096 --hostname 0.0.0.0",
    )
    info = node_svc.create_container(node_id, payload)

    # 8) auto_start
    if auto_start:
        try:
            node_svc.start_container(node_id, info.id)
            info.status = "running"
        except Exception as exc:
            from loguru import logger
            logger.warning(f"[deploy-container] 启动失败: {exc}")

    # 9) 等 health（最多 15s）
    healthy = False
    if info.status == "running":
        import time
        import httpx
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                r = httpx.get(
                    f"http://{node.address}:{host_port}/global/health",
                    timeout=1.5,
                )
                if r.status_code == 200:
                    healthy = True
                    break
            except Exception:
                pass
            time.sleep(0.5)

    # 10) 回写 expert
    expert.container_id = info.id
    expert.container_name = info.name
    expert.host = node.address or "127.0.0.1"
    expert.host_port = host_port
    expert.port = 4096
    if healthy:
        expert.status = "online"
        expert.started_at = datetime.now(timezone.utc)
    else:
        expert.status = "error"
        expert.error_message = "容器已启动但 /global/health 15s 内未通过"
    expert.image = template.image
    expert.container_template_id = template.id
    db.commit()
    db.refresh(expert)

    return {
        "expert": _serialize(expert),
        "container": {
            "id": info.id,
            "name": info.name,
            "node_id": node_id,
            "node_name": node.name,
            "image": template.image,
            "host_port": host_port,
            "container_port": 4096,
            "url": f"http://{expert.host}:{host_port}",
            "healthy": healthy,
            "status": info.status,
        },
    }

