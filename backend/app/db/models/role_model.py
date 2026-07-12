"""Persistent Agent platform roles and user-role assignments.

Migration is intentionally owned by the integration agent because the current
Alembic head is being advanced in parallel.
"""
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, UniqueConstraint

from app.db.models.base import BaseModel


class Role(BaseModel):
    __tablename__ = "roles"
    __table_args__ = {"comment": "Agent 平台角色"}

    name = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(String(256), nullable=True)
    is_system = Column(Boolean, nullable=False, default=True)


class UserRole(BaseModel):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
        {"comment": "用户角色关联"},
    )

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id = Column(
        Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


__all__ = ["Role", "UserRole"]
