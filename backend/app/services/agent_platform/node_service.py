"""计算节点与安全连接配置服务。"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.connectors import HostKeyVerificationError, LocalConnector, NodeConnector, SSHConnector
from app.db.models.compute_node_model import ComputeNode
from app.db.repositories.agent_platform_repo import AgentPlatformRepository
from app.schemas.agent_platform_schema import HostKeyConfirmation, NodeCreate, NodeConnectionCreate
from app.schemas.audit_log_schema import AuditLogCreate
from app.schemas.credential_schema import CredentialCreate
from app.services.agent_platform.host_detection import detect_local_host_info
from app.services.audit_log_service import AuditLogService
from app.services.credential_service import CredentialService


def node_to_dict(node, connection=None) -> dict:
    data = node.to_dict()
    if connection is not None:
        data["connection"] = {
            "id": connection.id,
            "connector_type": connection.connector_type,
            "address": connection.address,
            "port": connection.port,
            "username": connection.username,
            "credential_id": connection.credential_id,
            "host_key_algorithm": connection.host_key_algorithm,
            "host_key_fingerprint": connection.host_key_fingerprint,
            "host_key_status": connection.host_key_status,
            "host_key_confirmed_at": (
                connection.host_key_confirmed_at.isoformat()
                if connection.host_key_confirmed_at
                else None
            ),
            "managed_roots": connection.managed_roots,
            "enabled": connection.enabled,
            "has_credential": connection.credential_id is not None,
        }
    return data


class NodeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AgentPlatformRepository(db)
        self.audit = AuditLogService(db)

    def list(self, skip: int = 0, limit: int = 100) -> list[dict]:
        return [
            node_to_dict(node, self.repo.get_connection(node.id))
            for node in self.repo.list_nodes(skip, limit)
        ]

    def get(self, node_id: int) -> dict | None:
        node = self.repo.get_node(node_id)
        return node_to_dict(node, self.repo.get_connection(node_id)) if node else None

    def create(self, data: NodeCreate, actor_user_id: int) -> dict:
        if self.db.query(ComputeNode).filter(ComputeNode.name == data.name).first():
            raise ValueError("node name already exists")
        connection = data.connection
        credential_id = connection.credential_id
        credential_service = CredentialService(self.db)
        if credential_id is not None:
            credential = credential_service.get(credential_id)
            if not credential["is_active"]:
                raise ValueError("credential is disabled")
        if connection.password or connection.private_key:
            payload = {
                key: value
                for key, value in {
                    "password": connection.password,
                    "private_key": connection.private_key,
                }.items()
                if value is not None
            }
            credential = credential_service.create(
                CredentialCreate(
                    name=f"node-{data.name}-{uuid4().hex[:12]}",
                    credential_type=(
                        "ssh_private_key" if connection.private_key else "ssh_password"
                    ),
                    payload=payload,
                    description=f"SSH credential for node {data.name}",
                ),
                actor_user_id,
            )
            credential_id = credential["id"]
        confirmed_at = (
            datetime.now(timezone.utc)
            if connection.host_key_algorithm and connection.host_key_fingerprint
            else None
        )
        node = self.repo.create_node(
            {
                "name": data.name,
                "hostname": data.hostname or connection.address,
                "address": connection.address,
                "ip": connection.address,
                "platform": data.platform,
                "environment": "default",
                "status": "online" if connection.connector_type == "local" else "offline",
                "labels": data.labels,
                "created_by_user_id": actor_user_id,
            },
            {
                "connector_type": connection.connector_type,
                "address": connection.address,
                "port": connection.port or (22 if connection.connector_type == "ssh" else None),
                "username": connection.username,
                "credential_id": credential_id,
                "host_key_algorithm": connection.host_key_algorithm,
                "host_key_fingerprint": connection.host_key_fingerprint,
                "host_key_status": "confirmed" if confirmed_at else "pending",
                "host_key_confirmed_at": confirmed_at,
                "connect_timeout_seconds": connection.connect_timeout_seconds,
                "command_timeout_seconds": connection.command_timeout_seconds,
                "max_concurrency": connection.max_concurrency,
                "managed_roots": connection.managed_roots,
            },
        )
        self.audit.record(
            AuditLogCreate(
                actor_user_id=actor_user_id,
                action="node.create",
                resource_type="compute_node",
                resource_id=str(node.id),
                details={
                    "name": node.name,
                    "connector_type": connection.connector_type,
                    "credential_id": credential_id,
                    "host_key_status": "confirmed" if confirmed_at else "pending",
                },
            )
        )
        self.db.commit()
        return node_to_dict(node, self.repo.get_connection(node.id))

    def confirm_host_key(
        self, node_id: int, data: HostKeyConfirmation, actor_user_id: int
    ) -> dict:
        connection = self.repo.get_connection(node_id)
        if not connection:
            raise LookupError("node connection not found or disabled")
        if connection.connector_type != "ssh":
            raise ValueError("host key confirmation only applies to SSH nodes")
        previous = connection.host_key_fingerprint
        connection.host_key_algorithm = data.host_key_algorithm
        connection.host_key_fingerprint = data.host_key_fingerprint
        connection.host_key_status = "confirmed"
        connection.host_key_confirmed_at = datetime.now(timezone.utc)
        self.audit.record(
            AuditLogCreate(
                actor_user_id=actor_user_id,
                action="node.host_key.confirm",
                resource_type="compute_node",
                resource_id=str(node_id),
                details={
                    "previous_fingerprint": previous,
                    "host_key_algorithm": data.host_key_algorithm,
                    "host_key_fingerprint": data.host_key_fingerprint,
                    "reason": data.reason,
                },
            )
        )
        self.db.commit()
        return node_to_dict(self.repo.get_node(node_id), connection)

    def register_local(self, actor_user_id: int) -> dict:
        """注册或返回本机计算节点，并设置 OpenCode 受管目录。"""
        from pathlib import Path

        existing = self.repo.find_local_node()
        if existing:
            return node_to_dict(existing, self.repo.get_connection(existing.id))

        host = detect_local_host_info()
        default_root = str(Path.home() / ".config" / "opencode")
        payload = NodeCreate(
            name=f"local-{host['hostname']}",
            hostname=host["hostname"],
            platform=(host.get("platform_raw") or "linux").lower(),
            labels={"source": "auto-register", "environment": "local"},
            connection=NodeConnectionCreate(
                connector_type="local",
                address=host.get("ip") or "127.0.0.1",
                managed_roots=[default_root],
            ),
        )
        return self.create(payload, actor_user_id)

    def connector_for(self, node_id: int) -> NodeConnector:
        connection = self.repo.get_connection(node_id)
        if not connection:
            raise LookupError("node connection not found or disabled")
        if connection.connector_type == "local":
            return LocalConnector(
                managed_roots=connection.managed_roots,
                max_timeout_seconds=connection.command_timeout_seconds,
            )
        if connection.host_key_status != "confirmed":
            raise HostKeyVerificationError("SSH host key is not confirmed")
        credential = (
            CredentialService(self.db).decrypt_payload_for_use(connection.credential_id)
            if connection.credential_id
            else {}
        )
        return SSHConnector(
            host=connection.address,
            port=connection.port or 22,
            username=connection.username,
            password=credential.get("password"),
            private_key=credential.get("private_key"),
            host_key_algorithm=connection.host_key_algorithm,
            host_key_fingerprint=connection.host_key_fingerprint,
            managed_roots=connection.managed_roots,
            connect_timeout_seconds=connection.connect_timeout_seconds,
            max_timeout_seconds=connection.command_timeout_seconds,
        )
