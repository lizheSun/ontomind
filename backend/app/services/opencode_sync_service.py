"""OpencodeSyncService (T48).

双向同步 opencode 配置文件与 DB：
- ``sync_from_opencode`` : 读取 ``opencode.json`` / ``skills/**/SKILL.md`` -> upsert 到 DB
  （复用 T46 的 :class:`OpencodeConfigDiscoveryService`）。
- ``sync_to_opencode``  : 把 DB 中的 skills / mcp_configs 写回配置文件。写入采用
  「临时文件 + os.replace」的原子操作，并在覆盖前生成 ``opencode.json.bak.<ts>`` 备份。

设计要点：
- 全部通过 ``settings.OPENCODE_CONFIG_PATH`` 可配置；测试用 ``config_path=`` 覆盖。
- 不会破坏 opencode.json 里除 ``mcp`` 之外的其它字段（读回原文件、只覆写 ``mcp`` 节）。
- ``dry_run`` 支持：只返回 diff / 待写入内容，不落盘、不改库。
- 冲突处理：``sync_from_opencode`` / ``sync_to_opencode`` 均是幂等的，同名资源
  会覆盖对方；单向调用清晰。
"""
from __future__ import annotations

import difflib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

import yaml
from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.mcp_model import MCPConfig, MCPType
from app.db.models.skill_model import Skill
from app.services.opencode_config_discovery_service import (
    OpencodeConfigDiscoveryService,
)


def _mcp_type_to_opencode(mcp_type: Any) -> str:
    """DB 的 MCPType -> opencode.json 的 type 字符串。"""
    if isinstance(mcp_type, MCPType):
        value = mcp_type.value
    else:
        value = str(mcp_type or "").lower()
    # opencode 只识别 local / remote；stdio -> local, http/sse -> remote
    if value in ("stdio", "local"):
        return "local"
    return "remote"


def _mcp_row_to_opencode(row: MCPConfig) -> dict[str, Any]:
    """把一个 MCPConfig ORM 行转成 opencode.json['mcp'][name] 的 payload。"""
    payload: dict[str, Any] = {
        "type": _mcp_type_to_opencode(row.mcp_type),
        "enabled": bool(row.is_active),
    }
    # command：DB 存字符串，opencode 期望 list 或字符串；stdio 通常给 list
    if row.command:
        parts = str(row.command).split()
        if len(parts) > 1:
            payload["command"] = parts
        else:
            payload["command"] = row.command
    if row.url:
        payload["url"] = row.url
    if row.env_vars:
        payload["environment"] = row.env_vars
    if row.headers:
        payload["headers"] = row.headers
    if row.description:
        payload["description"] = row.description
    return payload


def _skill_to_markdown(row: Skill) -> str:
    """把 Skill ORM 行序列化为 SKILL.md 文本。"""
    meta: dict[str, Any] = {"name": row.name}
    if row.description:
        meta["description"] = row.description
    if row.tags:
        meta["tags"] = row.tags
    frontmatter = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip()
    body = (row.description or "").strip()
    return f"---\n{frontmatter}\n---\n{body}\n"


def _unified_diff(old: str, new: str, path: str) -> str:
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"{path} (current)",
            tofile=f"{path} (new)",
            n=3,
        )
    )


def _atomic_write(target: Path, content: str) -> None:
    """临时文件 + rename 原子写。"""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=target.name + ".", suffix=".tmp", dir=str(target.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, target)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


class OpencodeSyncService:
    """双向同步 opencode 配置文件 <-> DB。"""

    def __init__(
        self,
        db: Session,
        config_path: Optional[str] = None,
    ) -> None:
        if db is None:
            raise ValueError("OpencodeSyncService requires a Session")
        raw_path = config_path or settings.OPENCODE_CONFIG_PATH
        self.config_path = Path(os.path.expanduser(raw_path))
        self.opencode_json_path = self.config_path / "opencode.json"
        self.skills_dir = self.config_path / "skills"
        self.db = db
        self._discovery = OpencodeConfigDiscoveryService(
            config_path=str(self.config_path), db=db
        )

    # ---------------- FILE -> DB ----------------

    def sync_from_opencode(
        self, dry_run: bool = False, target: str = "all"
    ) -> dict[str, Any]:
        """opencode.json / SKILL.md 中的资源导入到 DB。

        ``target`` 可选 ``mcps`` / ``skills`` / ``all``；默认全部。
        """
        result: dict[str, Any] = {
            "direction": "from_opencode",
            "dry_run": dry_run,
            "target": target,
            "mcps_found": 0,
            "skills_found": 0,
            "mcp_created": 0,
            "mcp_updated": 0,
            "skill_created": 0,
            "skill_updated": 0,
            "errors": [],
        }

        do_mcps = target in ("all", "mcps")
        do_skills = target in ("all", "skills")

        if do_mcps:
            mcps, mcp_errors = self._discovery.discover_mcps()
            result["mcps_found"] = len(mcps)
            result["errors"].extend(mcp_errors)
            result["mcps"] = mcps
            if not dry_run:
                created, updated = self._discovery.upsert_mcps(mcps)
                result["mcp_created"] = created
                result["mcp_updated"] = updated

        if do_skills:
            skills, skill_errors = self._discovery.discover_skills()
            result["skills_found"] = len(skills)
            result["errors"].extend(skill_errors)
            result["skills"] = skills
            if not dry_run:
                created, updated = self._discovery.upsert_skills(skills)
                result["skill_created"] = created
                result["skill_updated"] = updated

        logger.info(
            f"[opencode-sync-in] target={target} dry_run={dry_run} "
            f"mcps={result['mcps_found']} skills={result['skills_found']}"
        )
        return result

    # ---------------- DB -> FILE ----------------

    def _load_existing_opencode_json(self) -> tuple[dict[str, Any], list[str]]:
        errors: list[str] = []
        if not self.opencode_json_path.is_file():
            return {}, errors
        try:
            text = self.opencode_json_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"read opencode.json failed: {exc}")
            return {}, errors
        if not text.strip():
            return {}, errors
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON in opencode.json: {exc}")
            return {}, errors
        if not isinstance(data, dict):
            errors.append("opencode.json root is not an object")
            return {}, errors
        return data, errors

    def _backup_opencode_json(self) -> Optional[str]:
        """写覆盖前生成 ``opencode.json.bak.<ts>`` 备份。文件不存在则跳过。"""
        if not self.opencode_json_path.is_file():
            return None
        ts = int(time.time() * 1000)
        backup = self.opencode_json_path.with_suffix(
            self.opencode_json_path.suffix + f".bak.{ts}"
        )
        backup.write_bytes(self.opencode_json_path.read_bytes())
        return str(backup)

    def sync_to_opencode(
        self, dry_run: bool = False, target: str = "all"
    ) -> dict[str, Any]:
        """把 DB 中的 skills / mcp_configs 写回配置文件。"""
        result: dict[str, Any] = {
            "direction": "to_opencode",
            "dry_run": dry_run,
            "target": target,
            "mcps_written": 0,
            "skills_written": 0,
            "backup_path": None,
            "diffs": {},
            "errors": [],
        }
        do_mcps = target in ("all", "mcps")
        do_skills = target in ("all", "skills")

        # ---- MCP: 覆写 opencode.json 的 mcp 节 ----
        if do_mcps:
            existing, load_errors = self._load_existing_opencode_json()
            result["errors"].extend(load_errors)
            new_data = dict(existing)  # 浅拷贝，保留其它顶层字段
            mcp_rows = (
                self.db.query(MCPConfig)
                .filter(MCPConfig.is_active.is_(True))
                .all()
            )
            new_mcp: dict[str, Any] = {}
            for row in mcp_rows:
                if not row.name:
                    continue
                new_mcp[row.name] = _mcp_row_to_opencode(row)
            new_data["mcp"] = new_mcp

            new_text = json.dumps(new_data, ensure_ascii=False, indent=2) + "\n"
            old_text = (
                self.opencode_json_path.read_text(encoding="utf-8")
                if self.opencode_json_path.is_file()
                else ""
            )
            result["diffs"]["opencode.json"] = _unified_diff(
                old_text, new_text, str(self.opencode_json_path)
            )
            result["mcps_written"] = len(new_mcp)
            if not dry_run:
                if self.opencode_json_path.is_file():
                    result["backup_path"] = self._backup_opencode_json()
                _atomic_write(self.opencode_json_path, new_text)

        # ---- Skills: 逐个写 skills/<name>/SKILL.md ----
        if do_skills:
            skill_rows = self.db.query(Skill).all()
            for row in skill_rows:
                if not row.name:
                    continue
                target_path = self.skills_dir / row.name / "SKILL.md"
                new_text = _skill_to_markdown(row)
                old_text = (
                    target_path.read_text(encoding="utf-8")
                    if target_path.is_file()
                    else ""
                )
                result["diffs"][str(target_path)] = _unified_diff(
                    old_text, new_text, str(target_path)
                )
                if not dry_run:
                    try:
                        _atomic_write(target_path, new_text)
                    except OSError as exc:
                        result["errors"].append(
                            f"write {target_path} failed: {exc}"
                        )
                        continue
                result["skills_written"] += 1

        logger.info(
            f"[opencode-sync-out] target={target} dry_run={dry_run} "
            f"mcps_written={result['mcps_written']} "
            f"skills_written={result['skills_written']}"
        )
        return result

    # ---------------- Convenience ----------------

    def sync_skills(self, direction: str, dry_run: bool = False) -> dict[str, Any]:
        """便捷入口：只同步 skills。``direction`` ∈ {in, out}"""
        if direction == "in":
            return self.sync_from_opencode(dry_run=dry_run, target="skills")
        if direction == "out":
            return self.sync_to_opencode(dry_run=dry_run, target="skills")
        raise ValueError(f"invalid direction: {direction!r}")

    def sync_mcps(self, direction: str, dry_run: bool = False) -> dict[str, Any]:
        """便捷入口：只同步 mcps。``direction`` ∈ {in, out}"""
        if direction == "in":
            return self.sync_from_opencode(dry_run=dry_run, target="mcps")
        if direction == "out":
            return self.sync_to_opencode(dry_run=dry_run, target="mcps")
        raise ValueError(f"invalid direction: {direction!r}")
