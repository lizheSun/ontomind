"""add node connections and discovery previews

Revision ID: 2026071204
Revises: 2026071203
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "2026071204"
down_revision: Union[str, None] = "2026071203"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _base_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    with op.batch_alter_table("compute_nodes") as batch:
        batch.add_column(sa.Column("address", sa.String(255), nullable=True))
        batch.add_column(sa.Column("architecture", sa.String(64), nullable=True))
        batch.add_column(
            sa.Column(
                "environment",
                sa.String(64),
                nullable=False,
                server_default="default",
            )
        )
        batch.add_column(sa.Column("status_reason", sa.String(512), nullable=True))
        batch.add_column(
            sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(sa.Column("last_scan_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("created_by_user_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_compute_nodes_created_by",
            "users",
            ["created_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.execute("UPDATE compute_nodes SET address = ip WHERE address IS NULL")
    with op.batch_alter_table("compute_nodes") as batch:
        batch.create_unique_constraint(
            "uq_compute_nodes_address_environment", ["address", "environment"]
        )

    op.create_table(
        "node_connections",
        *_base_columns(),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("connector_type", sa.String(16), nullable=False),
        sa.Column("address", sa.String(255), nullable=True),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("username", sa.String(128), nullable=True),
        sa.Column("credential_id", sa.Integer(), nullable=True),
        sa.Column("host_key_algorithm", sa.String(64), nullable=True),
        sa.Column("host_key_fingerprint", sa.String(255), nullable=True),
        sa.Column(
            "host_key_status", sa.String(16), nullable=False, server_default="pending"
        ),
        sa.Column("host_key_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "connect_timeout_seconds", sa.Integer(), nullable=False, server_default="10"
        ),
        sa.Column(
            "command_timeout_seconds", sa.Integer(), nullable=False, server_default="30"
        ),
        sa.Column("max_concurrency", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("managed_roots", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["node_id"], ["compute_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["credential_id"], ["credentials.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("node_id", name="uq_node_connections_node"),
    )
    op.create_index("ix_node_connections_id", "node_connections", ["id"])
    op.create_index(
        "ix_node_connections_credential_id", "node_connections", ["credential_id"]
    )

    op.create_table(
        "discovery_runs",
        *_base_columns(),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column(
            "provider_type", sa.String(32), nullable=False, server_default="opencode"
        ),
        sa.Column("status", sa.String(24), nullable=False, server_default="queued"),
        sa.Column("started_by_user_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["node_id"], ["compute_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["started_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_discovery_runs_id", "discovery_runs", ["id"])
    op.create_index("ix_discovery_runs_node_id", "discovery_runs", ["node_id"])

    op.create_table(
        "discovery_items",
        *_base_columns(),
        sa.Column("discovery_run_id", sa.Integer(), nullable=False),
        sa.Column("resource_type", sa.String(24), nullable=False),
        sa.Column("external_key", sa.String(512), nullable=False),
        sa.Column("source_path", sa.String(1024), nullable=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="new"),
        sa.Column("remote_snapshot", sa.JSON(), nullable=False),
        sa.Column("platform_resource_id", sa.Integer(), nullable=True),
        sa.Column("platform_snapshot", sa.JSON(), nullable=True),
        sa.Column("diff", sa.JSON(), nullable=True),
        sa.Column("decision", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("decided_by_user_id", sa.Integer(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["discovery_run_id"], ["discovery_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["decided_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "discovery_run_id",
            "resource_type",
            "external_key",
            name="uq_discovery_item_external_key",
        ),
    )
    op.create_index("ix_discovery_items_id", "discovery_items", ["id"])
    op.create_index(
        "ix_discovery_items_run_id", "discovery_items", ["discovery_run_id"]
    )


def downgrade() -> None:
    op.drop_table("discovery_items")
    op.drop_table("discovery_runs")
    op.drop_table("node_connections")
    with op.batch_alter_table("compute_nodes") as batch:
        batch.drop_constraint("uq_compute_nodes_address_environment", type_="unique")
        batch.drop_constraint("fk_compute_nodes_created_by", type_="foreignkey")
        for column in (
            "created_by_user_id",
            "last_scan_at",
            "last_heartbeat_at",
            "status_reason",
            "environment",
            "architecture",
            "address",
        ):
            batch.drop_column(column)
