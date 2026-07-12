"""计算节点资源清单 — 计算节点 / OpenCode 容器 / Agent·Skill·MCP 层级视图。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.connectors import CommandSpec
from app.db.models.agent_model import Agent
from app.db.models.mcp_model import MCP
from app.db.models.skill_model import Skill
from app.services.agent_platform.discovery_service import DiscoveryService, _row_dict
from app.services.agent_platform.node_service import NodeService
from app.services.agent_platform.serialization import json_safe_row


def _expand_home(path: str) -> str:
    return str(Path(path).expanduser())


class InventoryService:
    def __init__(self, db: Session) -> None:
        self.db = db

    async def get(self, node_id: int, *, refresh: bool = False, user_id: int | None = None) -> dict:
        node = NodeService(self.db).get(node_id)
        if node is None:
            raise LookupError("node not found")

        latest_run = None
        discovery_items: list[dict] = []
        repo = NodeService(self.db).repo
        run = repo.get_latest_run(node_id)
        if refresh and user_id is not None:
            run = await DiscoveryService(self.db).start(node_id=node_id, user_id=user_id)
        if run:
            latest_run = _row_dict(run)
            run_id = run["id"] if isinstance(run, dict) else run.id
            discovery_items = DiscoveryService(self.db).items(run_id)

        runtime_items = [item for item in discovery_items if item.get("resource_type") == "runtime"]
        container = await self._build_opencode_container(node, runtime_items)

        platform_agents = [
            self._platform_resource_row(row, "agent")
            for row in self.db.query(Agent).order_by(Agent.id).all()
        ]
        platform_skills = [
            self._platform_resource_row(row, "skill")
            for row in self.db.query(Skill).order_by(Skill.id).all()
        ]
        platform_mcps = [
            self._platform_resource_row(row, "mcp")
            for row in self.db.query(MCP).order_by(MCP.id).all()
        ]

        discovered = {
            "agents": self._merge_resources(
                [item for item in discovery_items if item.get("resource_type") == "agent"],
                platform_agents,
            ),
            "skills": self._merge_resources(
                [item for item in discovery_items if item.get("resource_type") == "skill"],
                platform_skills,
            ),
            "mcps": self._merge_resources(
                [item for item in discovery_items if item.get("resource_type") == "mcp"],
                platform_mcps,
            ),
        }

        return {
            "node": node,
            "latest_discovery": latest_run,
            "containers": [container] if container else [],
            "resources": discovered,
            "hierarchy_label": "计算节点 → OpenCode 容器 → Agent / Skill / MCP",
        }

    async def _build_opencode_container(
        self, node: dict[str, Any], runtime_items: list[dict]
    ) -> dict[str, Any] | None:
        managed_roots = [
            _expand_home(root) for root in node.get("connection", {}).get("managed_roots", [])
        ]
        runtime = runtime_items[0]["remote_snapshot"] if runtime_items else {}
        cli_path = runtime.get("cli_path")
        version = runtime.get("version")
        status = "running" if cli_path else "not_installed"

        if not cli_path:
            try:
                connector = NodeService(self.db).connector_for(node["id"])
                which = await connector.run(CommandSpec(program="which", args=("opencode",)))
                if which.exit_code == 0 and which.stdout.strip():
                    cli_path = which.stdout.strip().splitlines()[0]
                    version_result = await connector.run(
                        CommandSpec(program="opencode", args=("--version",), timeout_seconds=10)
                    )
                    version = version_result.stdout.strip() or version
                    status = "running"
            except Exception:
                status = "not_installed"

        config_path = None
        config_preview: dict[str, Any] | None = None
        for root in managed_roots:
            candidate = str(Path(root) / "opencode.json")
            try:
                connector = NodeService(self.db).connector_for(node["id"])
                from app.connectors.base import ManagedPath

                raw = await connector.read_file(ManagedPath(candidate))
                config_preview = json.loads(raw.decode("utf-8"))
                config_path = candidate
                break
            except Exception:
                continue

        return {
            "id": f"opencode-{node['id']}",
            "container_type": "opencode",
            "name": "OpenCode Runtime",
            "status": status,
            "cli_path": cli_path,
            "version": version,
            "managed_roots": managed_roots,
            "config_path": config_path,
            "config_preview": config_preview,
            "node_id": node["id"],
            "node_name": node["name"],
            "hostname": node.get("hostname"),
        }

    @staticmethod
    def _platform_resource_row(row, resource_type: str) -> dict[str, Any]:
        return {
            "resource_type": resource_type,
            "external_key": row.name,
            "source_path": getattr(row, "published_path", None) or getattr(row, "source_path", None),
            "status": "platform",
            "decision": "platform",
            "platform_resource_id": row.id,
            "remote_snapshot": {"name": row.name},
            "platform_snapshot": json_safe_row(row),
        }

    @staticmethod
    def _merge_resources(discovered: list[dict], platform: list[dict]) -> list[dict]:
        merged: dict[str, dict] = {}
        for item in discovered:
            key = str(item.get("external_key") or item.get("id"))
            merged[key] = {
                **item,
                "origin": "discovered",
                "location": item.get("source_path") or "OpenCode 配置",
            }
        for item in platform:
            key = str(item.get("external_key"))
            if key in merged:
                merged[key]["platform_resource_id"] = item.get("platform_resource_id")
                merged[key]["origin"] = "both"
            else:
                merged[key] = {
                    **item,
                    "origin": "platform",
                    "location": item.get("source_path") or "平台数据库",
                }
        return list(merged.values())
