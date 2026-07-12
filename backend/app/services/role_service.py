"""Persistent role assignment service."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.db.models.role_model import Role, UserRole
from app.db.models.user_model import User
from app.schemas.audit_log_schema import AuditLogCreate
from app.services.audit_log_service import AuditLogService

SYSTEM_ROLES: dict[str, str] = {
    "platform_admin": "平台管理员",
    "agent_builder": "Agent 构建者",
    "agent_user": "Agent 使用者",
    "auditor": "只读审计员",
}


class RoleService:
    def __init__(self, db: Session):
        self.db = db

    def ensure_system_roles(self) -> dict[str, Role]:
        existing = {
            role.name: role
            for role in self.db.query(Role).filter(Role.name.in_(SYSTEM_ROLES)).all()
        }
        for name, description in SYSTEM_ROLES.items():
            if name not in existing:
                role = Role(name=name, description=description, is_system=True)
                self.db.add(role)
                existing[name] = role
        self.db.flush()
        return existing

    def role_names_for_user(self, user_id: int) -> frozenset[str]:
        rows = (
            self.db.query(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .filter(UserRole.user_id == user_id)
            .all()
        )
        return frozenset(row[0] for row in rows)

    def assign_role(
        self, user_id: int, role_name: str, assigned_by_user_id: int
    ) -> dict:
        if not self.db.get(User, user_id):
            raise NotFoundException(f"用户不存在: {user_id}")
        roles = self.ensure_system_roles()
        role = roles.get(role_name)
        if role is None:
            raise NotFoundException(f"角色不存在: {role_name}", code="ROLE_NOT_FOUND")
        assignment = (
            self.db.query(UserRole)
            .filter(UserRole.user_id == user_id, UserRole.role_id == role.id)
            .first()
        )
        if assignment is None:
            assignment = UserRole(
                user_id=user_id,
                role_id=role.id,
                assigned_by_user_id=assigned_by_user_id,
            )
            self.db.add(assignment)
            self.db.flush()
            AuditLogService(self.db).record(
                AuditLogCreate(
                    actor_user_id=assigned_by_user_id,
                    action="role.assign",
                    resource_type="user_role",
                    resource_id=str(assignment.id),
                    details={"user_id": user_id, "role": role_name},
                )
            )
        self.db.commit()
        self.db.refresh(assignment)
        return {
            "id": assignment.id,
            "user_id": assignment.user_id,
            "role_id": assignment.role_id,
            "role": role.name,
            "assigned_by_user_id": assignment.assigned_by_user_id,
        }

    def revoke_role(
        self, user_id: int, role_name: str, revoked_by_user_id: int
    ) -> bool:
        assignment = (
            self.db.query(UserRole)
            .join(Role, Role.id == UserRole.role_id)
            .filter(UserRole.user_id == user_id, Role.name == role_name)
            .first()
        )
        if assignment is None:
            return False
        assignment_id = assignment.id
        self.db.delete(assignment)
        AuditLogService(self.db).record(
            AuditLogCreate(
                actor_user_id=revoked_by_user_id,
                action="role.revoke",
                resource_type="user_role",
                resource_id=str(assignment_id),
                details={"user_id": user_id, "role": role_name},
            )
        )
        self.db.commit()
        return True


__all__ = ["RoleService", "SYSTEM_ROLES"]
