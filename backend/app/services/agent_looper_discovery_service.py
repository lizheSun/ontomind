"""AgentLooperDiscoveryService — 扫描 opencode 原生 agent 配置目录，解析 YAML frontmatter，
upsert 进 agent_looper_configs（type='opencode_native'）。

设计要点：
- 服务层与 T34 模型 **解耦**（本任务在并行分支，T34 的 ORM 尚未合入）。因此 upsert 直接使用
  SQL text() 走 `agent_looper_configs` 表；无需 import 模型。
- discover() 是纯函数，只依赖文件系统 + PyYAML；tests 用 tmp_path 隔离。
- 缺失/损坏文件不抛异常，静默跳过（robust discovery）。
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml
from loguru import logger
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings


def _parse_frontmatter(path: Path) -> Optional[dict[str, Any]]:
    """解析单个 .md 文件的 YAML frontmatter。失败返回 None。

    结构：
        ---\n<yaml>\n---\n<body>
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning(f"[agent-looper-discovery] read failed {path}: {exc}")
        return None

    if not raw.startswith("---"):
        return None

    # 用 split("---", 2) 拿到 [before, yaml, body]
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return None

    yaml_block = parts[1]
    body = parts[2]

    try:
        meta = yaml.safe_load(yaml_block)
    except yaml.YAMLError as exc:
        logger.warning(f"[agent-looper-discovery] invalid YAML in {path}: {exc}")
        return None

    if not isinstance(meta, dict):
        return None

    # body 前若有 \n 保留原始换行仅剥离首个换行
    body_text = body[1:] if body.startswith("\n") else body

    return {
        "name": path.stem,
        "description": meta.get("description"),
        "mode": meta.get("mode"),
        "model": meta.get("model"),
        "temperature": meta.get("temperature"),
        "steps": meta.get("steps"),
        "permission": meta.get("permission"),
        "system_prompt": body_text,
    }


class AgentLooperDiscoveryService:
    """opencode 原生 agent 发现服务。"""

    def __init__(self, db: Optional[Session] = None) -> None:
        self.db = db

    # ---- discover -----------------------------------------------------

    @staticmethod
    def discover(config_path: Optional[str] = None) -> list[dict[str, Any]]:
        """扫描 opencode agent 目录，返回解析后的 dict 列表。目录不存在返回 []。"""
        raw_path = config_path or settings.AGENT_CONFIG_PATH
        path = Path(os.path.expanduser(raw_path))
        if not path.exists() or not path.is_dir():
            logger.info(f"[agent-looper-discovery] path missing, skip: {path}")
            return []

        out: list[dict[str, Any]] = []
        for md_file in sorted(path.glob("*.md")):
            parsed = _parse_frontmatter(md_file)
            if parsed is None:
                continue
            out.append(parsed)
        return out

    # ---- upsert -------------------------------------------------------

    def upsert_discovered(
        self,
        configs: list[dict[str, Any]],
        user_id: int,
    ) -> int:
        """按 name+type='opencode_native' 匹配；存在则 UPDATE，缺失则 INSERT。返回处理条数。

        注：直接走 SQL text() —— T34 的 ORM 尚未合入本分支。合入后仍兼容（列名一致）。
        """
        if self.db is None:
            raise RuntimeError("upsert_discovered requires a Session")

        n = 0
        now = datetime.utcnow()
        for cfg in configs:
            name = cfg.get("name")
            if not name:
                continue

            body_json = json.dumps(cfg, ensure_ascii=False)

            existing = self.db.execute(
                text(
                    "SELECT id FROM agent_looper_configs "
                    "WHERE name = :name AND type = 'opencode_native'"
                ),
                {"name": name},
            ).first()

            if existing is not None:
                self.db.execute(
                    text(
                        "UPDATE agent_looper_configs SET "
                        "description = :description, "
                        "active_config_json = :cfg, "
                        "is_active = 1, "
                        "is_published = 1, "
                        "updated_at = :now "
                        "WHERE id = :id"
                    ),
                    {
                        "description": cfg.get("description"),
                        "cfg": body_json,
                        "now": now,
                        "id": existing.id,
                    },
                )
            else:
                self.db.execute(
                    text(
                        "INSERT INTO agent_looper_configs "
                        "(name, type, description, active_config_json, "
                        " owner_user_id, is_active, is_published, "
                        " created_at, updated_at) "
                        "VALUES (:name, 'opencode_native', :description, :cfg, "
                        " :owner, 1, 1, :now, :now)"
                    ),
                    {
                        "name": name,
                        "description": cfg.get("description"),
                        "cfg": body_json,
                        "owner": user_id,
                        "now": now,
                    },
                )
            n += 1
        self.db.commit()
        return n
