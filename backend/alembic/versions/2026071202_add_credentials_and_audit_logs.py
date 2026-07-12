"""add credentials and audit logs

Revision ID: 2026071202
Revises: 2026071201
Create Date: 2026-07-12 18:45:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "2026071202"
down_revision: Union[str, None] = "2026071201"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "credentials",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("credential_type", sa.String(length=64), nullable=False),
        sa.Column("encrypted_payload", sa.Text(), nullable=False),
        sa.Column("payload_keys", sa.JSON(), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.UniqueConstraint("name", name="uq_credentials_name"),
        comment="Agent 平台凭据",
    )
    op.create_index("ix_credentials_id", "credentials", ["id"])
    op.create_index("ix_credentials_name", "credentials", ["name"])
    op.create_index(
        "ix_credentials_credential_type", "credentials", ["credential_type"]
    )
    op.create_index(
        "ix_credentials_owner_user_id", "credentials", ["owner_user_id"]
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=True),
        sa.Column(
            "outcome", sa.String(length=32), nullable=False, server_default="success"
        ),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("source_ip", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        comment="Agent 平台安全审计日志",
    )
    for column in (
        "id",
        "actor_user_id",
        "action",
        "resource_type",
        "resource_id",
        "outcome",
        "request_id",
    ):
        op.create_index(f"ix_audit_logs_{column}", "audit_logs", [column])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("credentials")
