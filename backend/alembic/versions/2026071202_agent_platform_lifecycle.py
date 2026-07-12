"""add unified agent platform lifecycle and run domain

Revision ID: 2026071203
Revises: 2026071202
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "2026071203"
down_revision: Union[str, None] = "2026071202"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _base_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "agent_versions",
        *_base_columns(),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("config_hash", sa.String(64), nullable=False),
        sa.Column("note", sa.String(256), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column(
            "config_schema_version", sa.String(32), nullable=False, server_default="1"
        ),
        sa.Column("source", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.UniqueConstraint("agent_id", "version_number", name="uq_agent_version_number"),
    )
    with op.batch_alter_table("agents") as batch:
        batch.add_column(sa.Column("owner_user_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("current_version_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_agents_owner_user", "users", ["owner_user_id"], ["id"])
        batch.create_foreign_key(
            "fk_agents_current_version",
            "agent_versions",
            ["current_version_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_table(
        "agent_deployments",
        *_base_columns(),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("agent_version_id", sa.Integer(), nullable=False),
        sa.Column("environment", sa.String(64), nullable=False, server_default="default"),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("runtime_config", sa.JSON(), nullable=False),
        sa.Column("status_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("previous_deployment_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(64), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_version_id"], ["agent_versions.id"]),
        sa.ForeignKeyConstraint(
            ["previous_deployment_id"],
            ["agent_deployments.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
    )
    op.create_table(
        "agent_sessions",
        *_base_columns(),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("agent_version_id", sa.Integer(), nullable=False),
        sa.Column("deployment_id", sa.Integer(), nullable=True),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(256), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("session_metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_version_id"], ["agent_versions.id"]),
        sa.ForeignKeyConstraint(
            ["deployment_id"], ["agent_deployments.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
    )
    op.create_table(
        "agent_messages",
        *_base_columns(),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(32), nullable=False, server_default="text"),
        sa.Column("run_id", sa.Integer(), nullable=True),
        sa.Column("message_metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["agent_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["run_id"], ["agent_runs.id"], name="fk_agent_messages_run"
        ),
        sa.UniqueConstraint("session_id", "sequence", name="uq_agent_message_sequence"),
    )
    with op.batch_alter_table("agent_runs") as batch:
        batch.alter_column(
            "status",
            existing_type=sa.Enum(
                "initializing", "running", "error", "stopped", name="run_status_enum"
            ),
            type_=sa.String(32),
            existing_nullable=True,
        )
        batch.add_column(sa.Column("agent_version_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("deployment_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("session_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("owner_user_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("strategy", sa.String(32), nullable=True))
        batch.add_column(
            sa.Column("kind", sa.String(32), nullable=False, server_default="chat")
        )
        batch.add_column(sa.Column("parent_run_id", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column("attempt", sa.Integer(), nullable=False, server_default="1")
        )
        batch.add_column(sa.Column("goal", sa.Text(), nullable=True))
        batch.add_column(sa.Column("checkpoint", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("input", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("output", sa.JSON(), nullable=True))
        batch.add_column(
            sa.Column("state_version", sa.Integer(), nullable=False, server_default="1")
        )
        batch.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_foreign_key(
            "fk_runs_agent_version", "agent_versions", ["agent_version_id"], ["id"]
        )
        batch.create_foreign_key(
            "fk_runs_deployment", "agent_deployments", ["deployment_id"], ["id"]
        )
        batch.create_foreign_key(
            "fk_runs_session", "agent_sessions", ["session_id"], ["id"]
        )
        batch.create_foreign_key("fk_runs_owner", "users", ["owner_user_id"], ["id"])
        batch.create_foreign_key(
            "fk_runs_parent", "agent_runs", ["parent_run_id"], ["id"], ondelete="SET NULL"
        )

    op.create_table(
        "agent_run_steps",
        *_base_columns(),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="completed"),
        sa.Column("input", sa.JSON(), nullable=True),
        sa.Column("output", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("run_id", "sequence", name="uq_agent_run_step_sequence"),
    )
    op.create_table(
        "agent_run_events",
        *_base_columns(),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("visibility", sa.String(32), nullable=False, server_default="user"),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("run_id", "sequence", name="uq_agent_run_event_sequence"),
    )
    op.create_index(
        "ix_agent_run_events_replay", "agent_run_events", ["run_id", "sequence"]
    )
    op.create_table(
        "agent_tool_approvals",
        *_base_columns(),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("step_id", sa.Integer(), nullable=True),
        sa.Column("tool_name", sa.String(128), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("lock_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column("decided_by_user_id", sa.Integer(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["step_id"], ["agent_run_steps.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"]),
    )
    op.create_table(
        "eval_suites",
        *_base_columns(),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
    )
    op.create_table(
        "eval_cases",
        *_base_columns(),
        sa.Column("suite_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("input", sa.JSON(), nullable=False),
        sa.Column("expected", sa.JSON(), nullable=True),
        sa.Column("evaluator_config", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["suite_id"], ["eval_suites.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("suite_id", "name", name="uq_eval_case_suite_name"),
    )


def downgrade() -> None:
    op.drop_table("eval_cases")
    op.drop_table("eval_suites")
    op.drop_table("agent_tool_approvals")
    op.drop_index("ix_agent_run_events_replay", table_name="agent_run_events")
    op.drop_table("agent_run_events")
    op.drop_table("agent_run_steps")
    with op.batch_alter_table("agent_runs") as batch:
        for constraint in (
            "fk_runs_agent_version",
            "fk_runs_deployment",
            "fk_runs_session",
            "fk_runs_owner",
            "fk_runs_parent",
        ):
            batch.drop_constraint(constraint, type_="foreignkey")
        for name in (
            "completed_at",
            "state_version",
            "output",
            "input",
            "strategy",
            "checkpoint",
            "goal",
            "attempt",
            "parent_run_id",
            "kind",
            "owner_user_id",
            "session_id",
            "deployment_id",
            "agent_version_id",
        ):
            batch.drop_column(name)
        batch.alter_column(
            "status",
            existing_type=sa.String(32),
            type_=sa.Enum(
                "initializing", "running", "error", "stopped", name="run_status_enum"
            ),
            existing_nullable=True,
        )
    op.drop_table("agent_messages")
    op.drop_table("agent_sessions")
    op.drop_table("agent_deployments")
    with op.batch_alter_table("agents") as batch:
        batch.drop_constraint("fk_agents_current_version", type_="foreignkey")
        batch.drop_constraint("fk_agents_owner_user", type_="foreignkey")
        batch.drop_column("current_version_id")
        batch.drop_column("owner_user_id")
    op.drop_table("agent_versions")
