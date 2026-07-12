"""Agent 资源平台认证与可扩展 RBAC 依赖。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from fastapi import Depends, HTTPException, Query, WebSocket, WebSocketException, status
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.core.security import decode_access_token
from app.db.models.user_model import User
from app.db.session import get_db
from app.services.role_service import RoleService


class PlatformRole(str, Enum):
    PLATFORM_ADMIN = "platform_admin"
    AGENT_BUILDER = "agent_builder"
    AGENT_USER = "agent_user"
    AUDITOR = "auditor"


class PlatformPermission(str, Enum):
    RESOURCE_READ = "resource:read"
    RESOURCE_WRITE = "resource:write"
    CREDENTIAL_READ = "credential:read"
    CREDENTIAL_WRITE = "credential:write"
    AUDIT_READ = "audit:read"
    USER_MANAGE = "user:manage"
    LLM_MANAGE = "llm:manage"


ROLE_PERMISSIONS: dict[PlatformRole, frozenset[PlatformPermission]] = {
    PlatformRole.PLATFORM_ADMIN: frozenset(PlatformPermission),
    PlatformRole.AGENT_BUILDER: frozenset(
        {
            PlatformPermission.RESOURCE_READ,
            PlatformPermission.RESOURCE_WRITE,
            PlatformPermission.CREDENTIAL_READ,
            PlatformPermission.CREDENTIAL_WRITE,
        }
    ),
    PlatformRole.AGENT_USER: frozenset({PlatformPermission.RESOURCE_READ}),
    PlatformRole.AUDITOR: frozenset(
        {PlatformPermission.RESOURCE_READ, PlatformPermission.AUDIT_READ}
    ),
}


@dataclass(frozen=True)
class PlatformPrincipal:
    user_id: int
    username: str
    roles: frozenset[PlatformRole]
    is_superuser: bool

    @property
    def role(self) -> PlatformRole:
        priority = (
            PlatformRole.PLATFORM_ADMIN,
            PlatformRole.AGENT_BUILDER,
            PlatformRole.AUDITOR,
            PlatformRole.AGENT_USER,
        )
        return next(role for role in priority if role in self.roles)

    def has_permission(self, permission: PlatformPermission) -> bool:
        return any(permission in ROLE_PERMISSIONS[role] for role in self.roles)


def _principal_from_user(user: User, db: Session) -> PlatformPrincipal:
    if user.is_superuser:
        roles = frozenset({PlatformRole.PLATFORM_ADMIN})
    else:
        table_names = set(inspect(db.get_bind()).get_table_names())
        persisted = (
            RoleService(db).role_names_for_user(user.id)
            if {"roles", "user_roles"}.issubset(table_names)
            else frozenset()
        )
        roles = frozenset(
            PlatformRole(name)
            for name in persisted
            if name in PlatformRole._value2member_map_
        ) or frozenset({PlatformRole.AGENT_USER})
    return PlatformPrincipal(
        user_id=user.id,
        username=user.username,
        roles=roles,
        is_superuser=bool(user.is_superuser),
    )


def _load_active_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "用户不存在或已禁用"},
        )
    return user


def get_current_principal(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PlatformPrincipal:
    """Authenticate an HTTP request and resolve its platform principal."""
    return _principal_from_user(_load_active_user(db, user_id), db)


def require_permission(
    permission: PlatformPermission,
) -> Callable[..., PlatformPrincipal]:
    """Build an explicit permission dependency for privileged endpoints."""

    def dependency(
        principal: PlatformPrincipal = Depends(get_current_principal),
    ) -> PlatformPrincipal:
        if not principal.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "PERMISSION_DENIED",
                    "message": f"缺少权限: {permission.value}",
                },
            )
        return principal

    return dependency


def get_websocket_principal(
    websocket: WebSocket,
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> PlatformPrincipal:
    """Prefer header/subprotocol auth while retaining legacy query tokens."""
    resolved_token = _websocket_token(websocket, token)
    if not resolved_token:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="缺少 token")
    payload = decode_access_token(resolved_token)
    user_id = payload.get("user_id") if payload else None
    if user_id is None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="token 无效")
    try:
        user = _load_active_user(db, int(user_id))
    except HTTPException as exc:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION, reason="用户不存在或已禁用"
        ) from exc
    return _principal_from_user(user, db)


def _websocket_token(websocket: WebSocket, query_token: str | None) -> str | None:
    authorization = websocket.headers.get("authorization")
    if authorization:
        scheme, _, header_token = authorization.partition(" ")
        if scheme.lower() == "bearer" and header_token:
            return header_token

    protocols = [
        item.strip()
        for item in websocket.headers.get("sec-websocket-protocol", "").split(",")
        if item.strip()
    ]
    for index, protocol in enumerate(protocols):
        lower = protocol.lower()
        if lower == "bearer" and index + 1 < len(protocols):
            return protocols[index + 1]
        if lower.startswith(("bearer.", "jwt.")):
            return protocol.split(".", 1)[1]
    return query_token


__all__ = [
    "PlatformPermission",
    "PlatformPrincipal",
    "PlatformRole",
    "get_current_principal",
    "get_websocket_principal",
    "require_permission",
]
