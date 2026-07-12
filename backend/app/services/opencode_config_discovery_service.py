"""OpencodeConfigDiscoveryService (T46).

扫描本地 opencode 配置目录（默认 `~/.config/opencode`），发现：
1. `opencode.json` 中的 `mcp:` 字段 -> upsert 进 `mcp_configs` 表
2. `skills/*/SKILL.md` -> upsert 进 `skills` 表

设计要点：
- 全部通过 `settings.OPENCODE_CONFIG_PATH` 可配置；测试用 `config_path=` 覆盖。
- 目录/文件缺失、YAML 损坏都不抛异常，收集到 `errors` 里静默跳过。
- 幂等：按 `name` 匹配，存在则 UPDATE，缺失则 INSERT。
- dry-run：`discover_all(dry_run=True)` 不写库，只返回将要 upsert 的数据。
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml
from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.mcp_model import MCPConfig, MCPType
from app.db.models.skill_model import Skill, SkillType


_MCP_TYPE_MAP = {
    "local": MCPType.stdio,
    "stdio": MCPType.stdio,
    "remote": MCPType.sse,
    "sse": MCPType.sse,
    "http": MCPType.http,
    "https": MCPType.http,
}


def _normalize_mcp_type(raw: Any) -> MCPType:
    if not raw:
        return MCPType.stdio
    key = str(raw).lower().strip()
    return _MCP_TYPE_MAP.get(key, MCPType.stdio)


def _split_frontmatter(text: str) -> tuple[Optional[dict[str, Any]], str]:
    """解析 `---\\n<yaml>\\n---\\n<body>` 结构。失败返回 (None, "")。"""
    if not text.startswith("---"):
        return None, ""
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, ""
    try:
        meta = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None, ""
    if not isinstance(meta, dict):
        return None, ""
    body = parts[2]
    if body.startswith("\n"):
        body = body[1:]
    return meta, body


class OpencodeConfigDiscoveryService:
    """opencode 本地配置发现（MCP + Skill）。"""

    def __init__(
        self,
        config_path: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> None:
        raw_path = config_path or settings.OPENCODE_CONFIG_PATH
        self.config_path = Path(os.path.expanduser(raw_path))
        self.opencode_json_path = self.config_path / "opencode.json"
        self.skills_dir = self.config_path / "skills"
        self.db = db

    # ---------------- MCP discovery ----------------

    def discover_mcps(self) -> tuple[list[dict[str, Any]], list[str]]:
        errors: list[str] = []
        if not self.opencode_json_path.is_file():
            return [], errors
        try:
            raw = self.opencode_json_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"read opencode.json failed: {exc}")
            return [], errors
        try:
            config = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON in opencode.json: {exc}")
            return [], errors

        mcp_section = config.get("mcp", {})
        if not isinstance(mcp_section, dict):
            errors.append("opencode.json 'mcp' field is not an object")
            return [], errors

        results: list[dict[str, Any]] = []
        for name, mcp in mcp_section.items():
            if not isinstance(mcp, dict):
                errors.append(f"mcp[{name}] is not an object")
                continue
            mcp_type = _normalize_mcp_type(mcp.get("type"))
            command_raw = mcp.get("command")
            if isinstance(command_raw, list):
                command_str = " ".join(str(x) for x in command_raw)
                args = command_raw[1:] if len(command_raw) > 1 else []
            elif isinstance(command_raw, str):
                command_str = command_raw
                args = []
            else:
                command_str = None
                args = []
            results.append({
                "name": name,
                "mcp_type": mcp_type,
                "url": mcp.get("url") or None,
                "command": command_str,
                "args": args or None,
                "env_vars": mcp.get("environment") or mcp.get("env") or None,
                "headers": mcp.get("headers") or None,
                "description": mcp.get("description") or f"opencode MCP: {name}",
                "is_active": bool(mcp.get("enabled", True)),
            })
        return results, errors

    # ---------------- Skill discovery ----------------

    def discover_skills(self) -> tuple[list[dict[str, Any]], list[str]]:
        errors: list[str] = []
        if not self.skills_dir.is_dir():
            return [], errors
        results: list[dict[str, Any]] = []
        for skill_dir in sorted(self.skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                continue
            try:
                content = skill_md.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                errors.append(f"read {skill_md} failed: {exc}")
                continue
            meta, body = _split_frontmatter(content)
            if meta is None:
                errors.append(f"invalid frontmatter in {skill_md}")
                continue
            name = str(meta.get("name") or skill_dir.name)
            tags = meta.get("tags") or meta.get("triggers")
            if tags is not None and not isinstance(tags, list):
                tags = [str(tags)]
            results.append({
                "name": name,
                "skill_type": SkillType.script,
                "entrypoint": str(skill_md),
                "install_cmd": None,
                "parameters_schema": None,
                "output_schema": None,
                "env_vars": None,
                "description": meta.get("description") or (body.strip()[:200] if body else None),
                "tags": tags,
                "icon": None,
                "is_installed": True,
                "is_active": True,
            })
        return results, errors

    # ---------------- Upsert ----------------

    def upsert_mcps(self, mcps: list[dict[str, Any]]) -> tuple[int, int]:
        """返回 (created, updated)."""
        if self.db is None:
            raise RuntimeError("upsert_mcps requires a Session")
        created = 0
        updated = 0
        for data in mcps:
            name = data.get("name")
            if not name:
                continue
            existing = self.db.query(MCPConfig).filter(MCPConfig.name == name).first()
            if existing is not None:
                for key, value in data.items():
                    if key == "name":
                        continue
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                updated += 1
            else:
                self.db.add(MCPConfig(**data))
                created += 1
        self.db.commit()
        return created, updated

    def upsert_skills(self, skills: list[dict[str, Any]]) -> tuple[int, int]:
        if self.db is None:
            raise RuntimeError("upsert_skills requires a Session")
        created = 0
        updated = 0
        now = datetime.now(timezone.utc)
        for data in skills:
            name = data.get("name")
            if not name:
                continue
            payload = dict(data)
            if payload.get("is_installed") and "installed_at" not in payload:
                payload["installed_at"] = now
            existing = self.db.query(Skill).filter(Skill.name == name).first()
            if existing is not None:
                for key, value in payload.items():
                    if key == "name":
                        continue
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                updated += 1
            else:
                self.db.add(Skill(**payload))
                created += 1
        self.db.commit()
        return created, updated

    # ---------------- Combined ----------------

    def discover_all(self, dry_run: bool = False) -> dict[str, Any]:
        mcps, mcp_errors = self.discover_mcps()
        skills, skill_errors = self.discover_skills()
        errors = mcp_errors + skill_errors

        result: dict[str, Any] = {
            "mcps_found": len(mcps),
            "skills_found": len(skills),
            "mcps": mcps,
            "skills": skills,
            "errors": errors,
            "dry_run": dry_run,
        }
        if dry_run or self.db is None:
            result["created"] = 0
            result["updated"] = 0
            return result

        mcp_created, mcp_updated = self.upsert_mcps(mcps)
        skill_created, skill_updated = self.upsert_skills(skills)
        result["created"] = mcp_created + skill_created
        result["updated"] = mcp_updated + skill_updated
        result["mcp_created"] = mcp_created
        result["mcp_updated"] = mcp_updated
        result["skill_created"] = skill_created
        result["skill_updated"] = skill_updated
        logger.info(
            f"[opencode-discovery] mcps={len(mcps)} skills={len(skills)} "
            f"created={result['created']} updated={result['updated']} errors={len(errors)}"
        )
        return result
