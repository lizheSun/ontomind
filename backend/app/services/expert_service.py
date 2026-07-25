"""Expert service — CRUD + agent 文件生成 + Docker 生命周期（优先 mock 模式）.

核心流程：
1. 创建 Expert → 同步生成 ``~/.config/opencode/agent/{slug}.md``
2. opencode 启动时自动 discover 该 agent
3. 前端对话工作台的 ExpertPicker 选中后，切到该 agent
4. 删除 Expert → 删除对应的 agent.md 文件
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
from app.db.repositories.expert_repo import ExpertRepository
from app.schemas.expert_schema import ExpertCreate, ExpertUpdate


def _agent_dir() -> Path:
    """opencode agent 配置目录."""
    path = os.environ.get("OPENCODE_AGENT_DIR", "")
    if path:
        return Path(path)
    return Path.home() / ".config" / "opencode" / "agent"


def _build_agent_md(expert: Expert) -> str:
    """根据 Expert 配置生成 opencode agent Markdown 文件内容."""
    yaml = {}
    if expert.description:
        yaml["description"] = expert.description
    # 默认 subagent，除非是 build/plan 这类 primary
    mode = "subagent"
    if expert.slug in ("build", "plan", "compaction", "summary", "title"):
        mode = "primary"
    yaml["mode"] = mode
    if expert.tools:
        yaml["tools"] = expert.tools
    if expert.model:
        yaml["model"] = expert.model
    if expert.provider:
        yaml["provider"] = expert.provider
    if expert.temperature:
        yaml["temperature"] = expert.temperature

    lines = ["---"]
    for k, v in yaml.items():
        if isinstance(v, dict):
            lines.append(f"{k}:")
            for sk, sv in v.items():
                lines.append(f"  {sk}: {sv}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")

    if expert.role:
        lines.append(expert.role)
        lines.append("")
    if expert.sop:
        lines.append("## 工作流程 (SOP)")
        lines.append("")
        lines.append(expert.sop)
        lines.append("")

    return "\n".join(lines)


def _write_agent_md(expert: Expert) -> Path:
    """把 agent 定义写入磁盘."""
    d = _agent_dir()
    d.mkdir(parents=True, exist_ok=True)
    content = _build_agent_md(expert)
    path = d / f"{expert.slug}.md"
    path.write_text(content, encoding="utf-8")
    return path


def _remove_agent_md(expert: Expert) -> None:
    """删除 agent.md 文件."""
    path = _agent_dir() / f"{expert.slug}.md"
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass


def _docker_available() -> bool:
    if not shutil.which("docker"): return False
    try:
        r = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"],
                           capture_output=True, text=True, timeout=2)
        return r.returncode == 0
    except Exception:
        return False


def _port_open(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout): return True
    except OSError: return False


def _serialize(e: Expert) -> dict[str, Any]:
    return {
        "id": e.id, "name": e.name, "slug": e.slug,
        "avatar": e.avatar, "description": e.description,
        "role": e.role, "sop": e.sop,
        "provider": e.provider, "model": e.model, "temperature": e.temperature,
        "skills": e.skills or [], "mcps": e.mcps or [], "tools": e.tools or {},
        "image": e.image, "container_name": e.container_name, "container_id": e.container_id,
        "host_port": e.host_port, "host": e.host, "port": e.port,
        "status": e.status, "agent_file_path": e.agent_file_path,
        "started_at": e.started_at.isoformat() if e.started_at else None,
        "stopped_at": e.stopped_at.isoformat() if e.stopped_at else None,
        "error_message": e.error_message,
        "sort_order": e.sort_order,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
    }


class ExpertService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ExpertRepository(db)

    def list(self, skip: int = 0, limit: int = 200) -> list[dict[str, Any]]:
        rows = self.repo.list_ordered(skip, limit)
        for e in rows:
            self._refresh_status(e, commit=False)
        self.db.commit()
        return [_serialize(e) for e in rows]

    def get(self, expert_id: int) -> dict[str, Any]:
        e = self.repo.get_by_id(expert_id)
        if not e: raise NotFoundException(f"专家不存在: {expert_id}")
        self._refresh_status(e, commit=True)
        return _serialize(e)

    def create(self, payload: ExpertCreate, user_id: Optional[int] = None) -> dict[str, Any]:
        if self.repo.get_by_slug(payload.slug):
            raise BusinessException(f"slug 已存在: {payload.slug}", code="EXPERT_SLUG_DUP")
        e = Expert(
            name=payload.name, slug=payload.slug,
            avatar=payload.avatar, description=payload.description,
            role=payload.role, sop=payload.sop,
            provider=payload.provider, model=payload.model,
            temperature=payload.temperature,
            skills=payload.skills or [], mcps=payload.mcps or [],
            tools=payload.tools or {},
            image=payload.image,
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
        self.db.commit()
        self.db.refresh(e)
        return _serialize(e)

    def update(self, expert_id: int, payload: ExpertUpdate) -> dict[str, Any]:
        e = self.repo.get_by_id(expert_id)
        if not e: raise NotFoundException(f"专家不存在: {expert_id}")
        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(e, k, v)
        self.db.flush()
        try:
            path = _write_agent_md(e)
            e.agent_file_path = str(path)
        except Exception as exc:
            self.db.rollback()
            raise BusinessException(f"写入 agent 文件失败: {exc}", code="EXPERT_AGENT_WRITE_FAILED")
        self.db.commit()
        self.db.refresh(e)
        return _serialize(e)

    def delete(self, expert_id: int) -> None:
        e = self.repo.get_by_id(expert_id)
        if not e: raise NotFoundException(f"专家不存在: {expert_id}")
        _remove_agent_md(e)
        self.db.delete(e)
        self.db.commit()

    def start(self, expert_id: int) -> dict[str, Any]:
        e = self.repo.get_by_id(expert_id)
        if not e: raise NotFoundException(f"专家不存在: {expert_id}")
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
        if not e: raise NotFoundException(f"专家不存在: {expert_id}")
        _remove_agent_md(e)
        e.status = "offline"
        e.stopped_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(e)
        return _serialize(e)

    def _refresh_status(self, e: Expert, commit: bool = False) -> None:
        if e.status == "error": return
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


# -------- 预置专家 seed --------
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
        "sort_order": 40,
    },
]


def seed_default_experts(db: Session) -> int:
    added = 0
    repo = ExpertRepository(db)
    for d in DEFAULT_EXPERTS:
        if repo.get_by_slug(d["slug"]):
            continue
        e = Expert(**{**d, "host": "127.0.0.1", "port": 4096, "status": "offline"})
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
    return added