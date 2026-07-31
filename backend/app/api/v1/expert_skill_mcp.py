"""专家团 — Skill / MCP / Agent 资源管理子路由（OALP v1.0）.

端点（统一挂在 /api/v1/experts/skill-mcp/* 下）：

  GET  /skills/discover              扫描 opencode + claude + .agents 的 SKILL.md
  POST /skills/load-from-opencode    把扫描结果 upsert 到 skills 表
  POST /skills/upload-folder         上传 zip / 目录，扫 SKILL.md 入库
  POST /skills/{id}/summarize        LLM 解读 SKILL.md（写入 auto_description）

  GET  /mcps/discover                从 opencode.json 读 mcp 节
  POST /mcps/load-from-opencode      upsert 到 mcps 表
  POST /mcps/{id}/summarize          LLM 解读（拉 /mcp 拿 tool manifest + 解析）

  GET  /agents/list-local            列出 ~/.config/opencode/agent/*.md

所有写操作都会更新 ~ / .config/opencode/{skills,opencode.json,agent}，并
把 is_loaded 标记好，确保容器化部署时能 mount 最新内容。
"""
from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Optional

import yaml
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.core.config import settings
from app.core.exceptions import BusinessException, NotFoundException
from app.db.models.mcp_model import MCP
from app.db.models.skill_model import Skill
from app.db.session import get_db
from app.services.expert_service import _agent_dir, _opencode_config_path

router = APIRouter()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_SKILL_SEARCH_DIRS: list[Path] = []


def _skill_search_dirs() -> list[Path]:
    """opencode + claude + agents 兼容目录（按 opencode 官方文档）."""
    if _SKILL_SEARCH_DIRS:
        return _SKILL_SEARCH_DIRS
    home = Path.home()
    base = _opencode_config_path()
    _SKILL_SEARCH_DIRS.extend([
        base / "skills",                              # ~/.config/opencode/skills
        home / ".claude" / "skills",                  # ~/.claude/skills
        home / ".agents" / "skills",                  # ~/.agents/skills
    ])
    return _SKILL_SEARCH_DIRS


def _split_frontmatter(text: str) -> tuple[Optional[dict[str, Any]], str]:
    if not text or not text.startswith("---"):
        return None, text or ""
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, ""
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        meta = {}
    body = parts[2]
    if body.startswith("\n"):
        body = body[1:]
    return meta if isinstance(meta, dict) else {}, body


def _ensure_skill_dir() -> Path:
    """确保目标 skills 目录存在."""
    d = _opencode_config_path() / "skills"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Skill discover / load
# ---------------------------------------------------------------------------

@router.get("/skills/discover")
def discover_skills(
    _user_id: int = Depends(get_current_user_id),
):
    """扫描所有兼容目录的 SKILL.md，返回未入库的清单（preview）."""
    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    for d in _skill_search_dirs():
        if not d.exists():
            continue
        for skill_md in d.glob("*/SKILL.md"):
            try:
                meta, body = _split_frontmatter(skill_md.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not meta:
                continue
            name = (meta.get("name") or skill_md.parent.name).strip()
            if not name or name in seen:
                continue
            seen.add(name)
            items.append({
                "name": name,
                "source_path": str(skill_md),
                "source_dir": str(d),
                "description": meta.get("description", ""),
                "frontmatter": meta,
                "body_length": len(body),
                "is_loaded": (d / skill_md.parent.name).exists() and d == _ensure_skill_dir(),
            })
    return {"code": "SUCCESS", "message": "ok", "data": items}


@router.post("/skills/load-from-opencode")
def load_skills(
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    """把扫描结果 upsert 到 skills 表；同时 copy 到 ~/.config/opencode/skills."""
    target = _ensure_skill_dir()
    added = updated = 0
    for d in _skill_search_dirs():
        if not d.exists():
            continue
        for skill_md in d.glob("*/SKILL.md"):
            try:
                meta, body = _split_frontmatter(skill_md.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not meta:
                continue
            name = (meta.get("name") or skill_md.parent.name).strip()
            if not name:
                continue
            # 复制到目标目录
            dst = target / name
            if dst.resolve() != skill_md.parent.resolve():
                dst.mkdir(parents=True, exist_ok=True)
                shutil.copy2(skill_md, dst / "SKILL.md")
            row = db.query(Skill).filter(Skill.name == name).first()
            if row:
                row.source_path = str(skill_md)
                row.body_markdown = body
                row.auto_description = meta.get("description") or row.auto_description
                if isinstance(meta.get("license"), str):
                    row.version = meta.get("version") or row.version
                row.is_loaded = True
                updated += 1
            else:
                row = Skill(
                    name=name,
                    type="opencode_prompt",
                    source_path=str(skill_md),
                    body_markdown=body,
                    description=meta.get("description"),
                    is_active=True,
                    is_loaded=True,
                    folder_path=str(dst),
                )
                db.add(row)
                added += 1
    db.commit()
    return {
        "code": "SUCCESS",
        "message": f"已加载 {added} 个新 skill，更新 {updated} 个",
        "data": {"added": added, "updated": updated},
    }


@router.post("/skills/upload-folder")
async def upload_skill_folder(
    file: UploadFile = File(..., description="zip 压缩包"),
    overwrite: bool = Form(False),
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    """上传 zip（多 skill 目录），解压后扫 SKILL.md 全部入库."""
    if not (file.filename or "").lower().endswith(".zip"):
        raise BusinessException("仅支持 zip 文件", code="SKILL_UPLOAD_NOT_ZIP")

    target = _ensure_skill_dir()
    content = await file.read()
    added = updated = skipped = 0
    errors: list[str] = []

    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            tmp = Path(tempfile.mkdtemp(prefix="skill_upload_"))
            try:
                zf.extractall(tmp)
                # 扫所有 SKILL.md
                for skill_md in tmp.rglob("SKILL.md"):
                    try:
                        meta, body = _split_frontmatter(skill_md.read_text(encoding="utf-8"))
                    except Exception as e:
                        errors.append(f"{skill_md}: 解析失败 {e}")
                        continue
                    if not meta:
                        errors.append(f"{skill_md}: frontmatter 缺失")
                        continue
                    name = (meta.get("name") or skill_md.parent.name).strip()
                    if not name:
                        errors.append(f"{skill_md}: name 缺失")
                        continue
                    # copy 到目标
                    dst = target / name
                    if dst.exists() and not overwrite:
                        skipped += 1
                        continue
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(skill_md.parent, dst)
                    # 入库
                    row = db.query(Skill).filter(Skill.name == name).first()
                    if row:
                        row.source_path = str(skill_md)
                        row.body_markdown = body
                        row.auto_description = meta.get("description") or row.auto_description
                        row.folder_path = str(dst)
                        row.is_loaded = True
                        updated += 1
                    else:
                        row = Skill(
                            name=name,
                            type="opencode_prompt",
                            source_path=str(skill_md),
                            body_markdown=body,
                            description=meta.get("description"),
                            is_active=True,
                            is_loaded=True,
                            folder_path=str(dst),
                        )
                        db.add(row)
                        added += 1
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
    except zipfile.BadZipFile:
        raise BusinessException("zip 文件损坏", code="SKILL_UPLOAD_BAD_ZIP")

    db.commit()
    return {
        "code": "SUCCESS",
        "message": f"上传完成：新增 {added} / 更新 {updated} / 跳过 {skipped}",
        "data": {
            "added": added,
            "updated": updated,
            "skipped": skipped,
            "errors": errors[:20],
        },
    }


# ---------------------------------------------------------------------------
# MCP discover / load
# ---------------------------------------------------------------------------

@router.get("/mcps/discover")
def discover_mcps(
    _user_id: int = Depends(get_current_user_id),
):
    """从 opencode.json 读 mcp 节，preview."""
    cfg_path = _opencode_config_path() / "opencode.json"
    if not cfg_path.exists():
        return {"code": "SUCCESS", "message": "ok", "data": []}
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8") or "{}")
    except Exception:
        return {"code": "SUCCESS", "message": "opencode.json 解析失败", "data": []}
    mcps = cfg.get("mcp", {}) or {}
    items: list[dict[str, Any]] = []
    for name, conf in mcps.items():
        if not isinstance(conf, dict):
            continue
        items.append({
            "name": name,
            "type": conf.get("type", "local"),
            "enabled": conf.get("enabled", True),
            "command": conf.get("command"),
            "url": conf.get("url"),
            "description": conf.get("description", ""),
        })
    return {"code": "SUCCESS", "message": "ok", "data": items}


@router.post("/mcps/load-from-opencode")
def load_mcps(
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    """把 opencode.json 里的 mcp 全部 upsert 到 mcps 表."""
    cfg_path = _opencode_config_path() / "opencode.json"
    if not cfg_path.exists():
        return {"code": "SUCCESS", "message": "opencode.json 不存在", "data": {"added": 0, "updated": 0}}
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8") or "{}")
    except Exception as e:
        raise BusinessException(f"opencode.json 解析失败: {e}", code="MCP_CFG_INVALID")
    added = updated = 0
    for name, conf in (cfg.get("mcp") or {}).items():
        if not isinstance(conf, dict):
            continue
        t = conf.get("type") or "local"
        transport_type = "stdio" if t in ("local", "stdio") else (
            "http" if t in ("http", "https") else "sse"
        )
        row = db.query(MCP).filter(MCP.name == name).first()
        if row:
            row.transport_type = transport_type
            row.command = conf.get("command")
            row.url = conf.get("url")
            row.env_vars = conf.get("environment")
            row.headers = conf.get("headers")
            row.is_active = bool(conf.get("enabled", True))
            row.source = "opencode_config"
            updated += 1
        else:
            row = MCP(
                name=name,
                transport_type=transport_type,
                command=conf.get("command"),
                url=conf.get("url"),
                env_vars=conf.get("environment"),
                headers=conf.get("headers"),
                is_active=bool(conf.get("enabled", True)),
                source="opencode_config",
            )
            db.add(row)
            added += 1
    db.commit()
    return {
        "code": "SUCCESS",
        "message": f"已加载 {added} 个新 MCP，更新 {updated} 个",
        "data": {"added": added, "updated": updated},
    }


# ---------------------------------------------------------------------------
# Agent (opencode agent/*.md) discover
# ---------------------------------------------------------------------------

@router.get("/agents/list-local")
def list_local_agents(
    _user_id: int = Depends(get_current_user_id),
):
    """列出 ~/.config/opencode/agent/*.md（opencode 自动 discover）."""
    d = _agent_dir()
    if not d.exists():
        return {"code": "SUCCESS", "message": "ok", "data": []}
    items: list[dict[str, Any]] = []
    for p in sorted(d.glob("*.md")):
        try:
            text = p.read_text(encoding="utf-8")
            meta, body = _split_frontmatter(text)
        except Exception:
            continue
        if not meta:
            continue
        items.append({
            "slug": p.stem,
            "path": str(p),
            "description": meta.get("description", ""),
            "mode": meta.get("mode", "subagent"),
            "model": meta.get("model"),
            "permission": meta.get("permission", {}),
            "body_length": len(body),
        })
    return {"code": "SUCCESS", "message": "ok", "data": items}


# ---------------------------------------------------------------------------
# LLM 解读 skill / mcp
# ---------------------------------------------------------------------------

async def _llm_summarize(
    db: Session, *, system: str, user: str,
) -> dict[str, Any]:
    """调 LLMConfigService.chat_completion，返回解析后的 dict（fallback 友好）."""
    from app.services.llm_config_service import LLMConfigService
    import re

    try:
        llm = LLMConfigService(db)
        resp = await llm.chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=800,
        )
    except Exception as exc:
        return {"summary": f"(LLM 调用失败: {exc})", "tags": [], "use_when": ""}

    content = (resp.get("content") or "").strip()
    # 抠 JSON
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if m:
        s = m.group(1)
    else:
        start = content.find("{")
        end = content.rfind("}")
        s = content[start:end + 1] if start >= 0 and end > start else ""
    try:
        return json.loads(s)
    except Exception:
        return {"summary": content[:500], "tags": [], "use_when": ""}


@router.post("/skills/{skill_id}/summarize")
async def summarize_skill(
    skill_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    row = db.query(Skill).get(skill_id)
    if not row:
        raise NotFoundException(f"Skill 不存在: {skill_id}")
    body = (row.body_markdown or row.auto_description or "").strip()
    if not body:
        return {"code": "SUCCESS", "message": "SKILL 内容为空，跳过", "data": {
            "summary": "", "tags": [], "use_when": "",
        }}

    sys_prompt = (
        "你是 OntoMind 的「Skill 解读员」。阅读下面的 SKILL.md 内容，"
        "返回 JSON（不要 markdown 包裹）：\n"
        '{"summary": "<2-3 句中文人话，说明这个 skill 干什么>",'
        ' "use_when": "<1-2 句中文，说明在什么场景下应该调用>",'
        ' "input_output": "<1-2 句中文，说明输入和输出是什么>",'
        ' "tags": ["<标签1>", "<标签2>"]}\n'
        "全部用中文，简短直接。"
    )
    user = f"Skill 名: {row.name}\n\nSKILL.md 内容（前 4000 字）:\n{body[:4000]}"
    out = await _llm_summarize(db, system=sys_prompt, user=user)
    # 写回
    row.auto_description = (
        f"**功能**：{out.get('summary','')}\n\n"
        f"**何时用**：{out.get('use_when','')}\n\n"
        f"**输入输出**：{out.get('input_output','')}\n\n"
        f"**标签**：{', '.join(out.get('tags', []) or [])}"
    ).strip()
    db.commit()
    return {"code": "SUCCESS", "message": "已生成解读", "data": out}


@router.post("/mcps/{mcp_id}/summarize")
async def summarize_mcp(
    mcp_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    row = db.query(MCP).get(mcp_id)
    if not row:
        raise NotFoundException(f"MCP 不存在: {mcp_id}")
    info = {
        "name": row.name,
        "transport_type": row.transport_type,
        "url": row.url,
        "command": row.command,
        "headers": row.headers,
        "env_vars": row.env_vars,
        "existing_description": row.auto_description,
        "tools_manifest": row.tools_manifest_json,
    }
    sys_prompt = (
        "你是 OntoMind 的「MCP 解读员」。根据下面的 MCP 配置信息，"
        "返回 JSON（不要 markdown 包裹）：\n"
        '{"summary": "<2-3 句中文人话，说明这个 MCP 提供什么能力>",'
        ' "use_when": "<1-2 句中文，说明在什么场景下应该用>",'
        ' "tags": ["<标签1>", "<标签2>"]}\n'
        "全部用中文，简短直接。"
    )
    user = json.dumps(info, ensure_ascii=False, indent=2)
    out = await _llm_summarize(db, system=sys_prompt, user=user)
    row.auto_description = (
        f"**功能**：{out.get('summary','')}\n\n"
        f"**何时用**：{out.get('use_when','')}\n\n"
        f"**标签**：{', '.join(out.get('tags', []) or [])}"
    ).strip()
    db.commit()
    return {"code": "SUCCESS", "message": "已生成解读", "data": out}
