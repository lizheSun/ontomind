"""OpenCode 只读发现、预览决策与显式应用服务。"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any

import yaml
from sqlalchemy.orm import Session

from app.connectors import CommandSpec, ManagedPath, NodeConnector
from app.db.models.agent_model import Agent
from app.db.models.mcp_model import MCP
from app.db.models.skill_model import Skill
from app.db.repositories.agent_platform_repo import AgentPlatformRepository
from app.schemas.audit_log_schema import AuditLogCreate
from app.services.agent_platform.node_service import NodeService
from app.services.audit_log_service import AuditLogService


def _now():
    return datetime.now(timezone.utc)


def _fingerprint(snapshot: dict[str, Any]) -> str:
    raw = json.dumps(
        snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def _frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) != 3:
        return {}, text
    metadata = yaml.safe_load(parts[1]) or {}
    return (metadata if isinstance(metadata, dict) else {}), parts[2].lstrip()


def _row_dict(row) -> dict:
    if isinstance(row, dict):
        return json_safe(row)
    return json_safe_row(row)


from app.services.agent_platform.serialization import json_safe, json_safe_row


class DiscoveryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AgentPlatformRepository(db)
        self.audit = AuditLogService(db)

    async def start(
        self,
        node_id: int,
        user_id: int,
        provider_type: str = "opencode",
        connector: NodeConnector | None = None,
    ) -> dict:
        if not self.repo.get_node(node_id):
            raise LookupError("node not found")
        run = self.repo.create_run(
            node_id=node_id,
            provider_type=provider_type,
            status="running",
            started_by_user_id=user_id,
            started_at=_now(),
        )
        self.db.commit()
        errors: list[str] = []
        try:
            active_connector = connector or NodeService(self.db).connector_for(node_id)
            report = await active_connector.test_connection()
            if not report.ok:
                raise ConnectionError(report.message)
            await self._discover_opencode(run.id, active_connector, errors)
            run.status = "partial" if errors else "completed"
            run.summary = {
                "items": len(self.repo.list_items(run.id)),
                "errors": errors,
                "preview_only": True,
            }
        except Exception as exc:
            run.status = "failed"
            run.error_code = type(exc).__name__.upper()
            run.error_message = str(exc)
            run.summary = {"items": 0, "errors": [str(exc)], "preview_only": True}
        run.finished_at = _now()
        self.audit.record(
            actor_user_id=user_id,
            action="discovery.run",
            resource_type="discovery_run",
            resource_id=run.id,
            outcome="failure" if run.status == "failed" else "success",
            details={
                "node_id": node_id,
                "provider_type": provider_type,
                "status": run.status,
                "item_count": (run.summary or {}).get("items", 0),
            },
        )
        self.db.commit()
        return _row_dict(run)

    async def _discover_opencode(
        self, run_id: int, connector: NodeConnector, errors: list[str]
    ) -> None:
        which = await connector.run(CommandSpec(program="which", args=("opencode",)))
        if which.exit_code == 0 and which.stdout.strip():
            version = await connector.run(
                CommandSpec(program="opencode", args=("--version",), timeout_seconds=10)
            )
            snapshot = {
                "provider_type": "opencode",
                "cli_path": which.stdout.strip().splitlines()[0],
                "version": version.stdout.strip() or None,
            }
            self._add_item(run_id, "runtime", "opencode", None, snapshot)

        connection = self.repo.get_connection(self.repo.get_run(run_id).node_id)
        for root in connection.managed_roots:
            config_path = f"{root.rstrip('/')}/opencode.json"
            try:
                raw = await connector.read_file(ManagedPath(config_path))
                config = json.loads(raw.decode("utf-8"))
                self._add_config_items(run_id, config_path, config)
            except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
                errors.append(f"{config_path}: {exc}")
            try:
                skill_paths = await connector.list_files(
                    ManagedPath(root), "skills/*/SKILL.md"
                )
                for skill_path in skill_paths:
                    content = (await connector.read_file(ManagedPath(skill_path))).decode("utf-8")
                    metadata, body = _frontmatter(content)
                    name = str(metadata.get("name") or PurePosixPath(skill_path).parent.name)
                    self._add_item(
                        run_id,
                        "skill",
                        name,
                        skill_path,
                        {
                            "name": name,
                            "description": metadata.get("description"),
                            "tags": metadata.get("tags") or metadata.get("triggers"),
                            "body_markdown": body,
                        },
                    )
            except (OSError, UnicodeDecodeError, ValueError, yaml.YAMLError) as exc:
                errors.append(f"{root}/skills: {exc}")
            try:
                agent_paths = await connector.list_files(
                    ManagedPath(root), "agents/*.md"
                )
                for agent_path in agent_paths:
                    content = (await connector.read_file(ManagedPath(agent_path))).decode("utf-8")
                    metadata, body = _frontmatter(content)
                    name = str(metadata.get("name") or PurePosixPath(agent_path).stem)
                    self._add_item(
                        run_id,
                        "agent",
                        name,
                        agent_path,
                        {
                            "name": name,
                            "description": metadata.get("description"),
                            "model": metadata.get("model"),
                            "mode": metadata.get("mode"),
                            "body_markdown": body[:500] if body else None,
                        },
                    )
            except (OSError, UnicodeDecodeError, ValueError, yaml.YAMLError) as exc:
                errors.append(f"{root}/agents: {exc}")
        self.db.flush()

    def _add_config_items(self, run_id: int, path: str, config: dict[str, Any]) -> None:
        mcp_section = config.get("mcp", {})
        if isinstance(mcp_section, dict):
            for name, payload in mcp_section.items():
                if isinstance(payload, dict):
                    self._add_item(
                        run_id, "mcp", str(name), path,
                        {"name": str(name), **payload},
                    )
        agent_section = config.get("agent", {})
        if isinstance(agent_section, dict):
            for name, payload in agent_section.items():
                if isinstance(payload, dict):
                    self._add_item(
                        run_id, "agent", str(name), path,
                        {"name": str(name), **payload},
                    )

    def _add_item(
        self,
        run_id: int,
        resource_type: str,
        external_key: str,
        source_path: str | None,
        snapshot: dict[str, Any],
    ) -> None:
        model = {"agent": Agent, "skill": Skill, "mcp": MCP}.get(resource_type)
        existing = (
            self.db.query(model).filter(model.name == snapshot.get("name", external_key)).first()
            if model
            else None
        )
        platform_snapshot = json_safe_row(existing) if existing else None
        status = (
            "new"
            if existing is None
            else ("matched" if _fingerprint(platform_snapshot) == _fingerprint(snapshot) else "changed")
        )
        self.repo.create_item(
            discovery_run_id=run_id,
            resource_type=resource_type,
            external_key=external_key,
            source_path=source_path,
            fingerprint=_fingerprint(snapshot),
            status=status,
            remote_snapshot=snapshot,
            platform_resource_id=existing.id if existing else None,
            platform_snapshot=platform_snapshot,
            diff={"changed": sorted(snapshot.keys())} if status == "changed" else None,
        )

    def get(self, run_id: int) -> dict | None:
        run = self.repo.get_run(run_id)
        return _row_dict(run) if run else None

    def items(self, run_id: int) -> list[dict]:
        return [_row_dict(item) for item in self.repo.list_items(run_id)]

    def decide(self, run_id: int, item_id: int, decision: str, user_id: int) -> dict:
        item = self.repo.get_item(run_id, item_id)
        if not item:
            raise LookupError("discovery item not found")
        item.decision = decision
        item.decided_by_user_id = user_id
        item.decided_at = _now()
        self.audit.record(
            actor_user_id=user_id,
            action="discovery.decide",
            resource_type="discovery_item",
            resource_id=item.id,
            details={"run_id": run_id, "decision": decision},
        )
        self.db.commit()
        return _row_dict(item)

    def apply(self, run_id: int, user_id: int, item_ids: list[int] | None = None) -> dict:
        run = self.repo.get_run(run_id)
        if not run or run.status not in {"completed", "partial"}:
            raise ValueError("only completed discovery runs can be applied")
        selected = [
            item for item in self.repo.list_items(run_id)
            if item.decision != "pending" and (item_ids is None or item.id in item_ids)
        ]
        decision_summary: dict[str, int] = {}
        for item in selected:
            decision_summary[item.decision] = decision_summary.get(item.decision, 0) + 1
        self.audit.record(
            AuditLogCreate(
                actor_user_id=user_id,
                action="discovery.apply.preview",
                resource_type="discovery_run",
                resource_id=str(run_id),
                details={
                    "node_id": run.node_id,
                    "item_ids": [item.id for item in selected],
                    "decisions": decision_summary,
                    "configuration_writes": 0,
                },
            )
        )
        self.db.commit()
        return {
            "run_id": run_id,
            "selected_item_ids": [item.id for item in selected],
            "decisions": decision_summary,
            "configuration_writes": 0,
            "preview_only": True,
        }
