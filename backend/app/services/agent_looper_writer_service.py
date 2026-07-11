"""AgentLooperWriterService — 把库里的 agent 配置序列化成 opencode 原生 `.md` frontmatter，
用原子 rename 落盘到 `AGENT_CONFIG_PATH/<name>.md`。

关键约束（spec）：
- 仅 emit opencode 支持的字段：name / description / mode / model / temperature / steps / permission
- 绝不 emit loop_strategy / custom_tools / memory_window / resource_bindings / credential_ref / tools
- Body = config_json.system_prompt
- 写入必须 `os.replace(tmp, dst)`，不允许 shutil.move / open("w") 直写。
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


# opencode 白名单 —— 除此之外的字段一律 **不** 写进 .md
_OPENCODE_FIELDS = ("description", "mode", "model", "temperature", "steps", "permission")


class AgentLooperWriterError(Exception):
    """Writer 服务的业务错误。"""


class AgentLooperWriterService:
    """把 AgentLooperConfig 写盘为 opencode `.md`。"""

    def __init__(self, db: Optional[Session] = None) -> None:
        self.db = db

    # ---- 主接口 -------------------------------------------------------

    def publish(
        self,
        config_id: int,
        db: Optional[Session] = None,
        config_path: Optional[str] = None,
    ) -> str:
        """加载 config → 拼 frontmatter → 原子写 <name>.md → 更新 is_published。返回写入路径。"""
        sess = db if db is not None else self.db
        if sess is None:
            raise AgentLooperWriterError("publish() requires a Session")

        row = self._load_config(sess, config_id)
        if row is None:
            raise AgentLooperWriterError(f"agent_looper_configs id={config_id} not found")

        cfg_dict = self._parse_config_json(row["active_config_json"])

        name = row["name"]
        # 序列化
        content = self._render(name, cfg_dict)

        # 目录解析
        base = Path(os.path.expanduser(config_path or settings.AGENT_CONFIG_PATH))
        try:
            base.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise AgentLooperWriterError(f"cannot create target dir {base}: {exc}") from exc

        dst = base / f"{name}.md"
        tmp = base / f"{name}.md.tmp"

        # 写 tmp → 原子 rename
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, dst)  # atomic on POSIX
        except OSError as exc:
            # 清理 tmp
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
            raise AgentLooperWriterError(f"failed to write {dst}: {exc}") from exc

        # 更新 is_published
        try:
            sess.execute(
                text(
                    "UPDATE agent_looper_configs SET is_published = 1, updated_at = :now "
                    "WHERE id = :id"
                ),
                {"now": datetime.utcnow(), "id": config_id},
            )
            sess.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[agent-looper-writer] mark is_published failed id={config_id}: {exc}")
            sess.rollback()

        return str(dst)

    # ---- 内部 helpers -------------------------------------------------

    @staticmethod
    def _load_config(sess: Session, config_id: int) -> Optional[dict[str, Any]]:
        row = sess.execute(
            text(
                "SELECT id, name, description, active_config_json "
                "FROM agent_looper_configs WHERE id = :id"
            ),
            {"id": config_id},
        ).first()
        if row is None:
            return None
        return {
            "id": row.id,
            "name": row.name,
            "description": row.description,
            "active_config_json": row.active_config_json,
        }

    @staticmethod
    def _parse_config_json(raw: Optional[str]) -> dict[str, Any]:
        if not raw:
            return {}
        if isinstance(raw, dict):
            return raw
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    @staticmethod
    def _render(name: str, cfg: dict[str, Any]) -> str:
        """产出 `---\\n<yaml>\\n---\\n\\n<body>\\n` 格式字符串。"""
        frontmatter: dict[str, Any] = {"name": name}
        for k in _OPENCODE_FIELDS:
            if k in cfg and cfg[k] is not None:
                frontmatter[k] = cfg[k]

        yaml_block = yaml.safe_dump(
            frontmatter,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )

        body = cfg.get("system_prompt", "") or ""
        # 确保 body 以换行结尾
        if body and not body.endswith("\n"):
            body = body + "\n"

        return f"---\n{yaml_block}---\n\n{body}"
