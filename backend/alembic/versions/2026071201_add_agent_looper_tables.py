"""add agent_looper tables

Revision ID: 2026071201
Revises: 
Create Date: 2026-07-12 00:00:00.000000

T34: 新增 3 张 agent_looper_* 表 + config/version 唯一索引 + 相互 FK。

注意：agent_looper_configs.current_version_id 不使用 CASCADE 删除 —— 该 FK 指向
      versions.id，而 versions.config_id 又反向 CASCADE 回 configs.id，两侧同时
      CASCADE 会形成循环。这里使用 use_alter + no-cascade，删除 config 时业务层
      先将 current_version_id 清 NULL 再走 versions 的 CASCADE。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "2026071201"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. agent_looper_configs（先建，但暂不加 current_version_id 的 FK；等 versions 建好后 ALTER 添加）
    op.create_table(
        "agent_looper_configs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键ID"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), comment="更新时间"),
        sa.Column("name", sa.String(length=128), nullable=False, comment="配置名称（同 owner 下唯一）"),
        sa.Column("type", sa.String(length=32), nullable=False, server_default="custom_looper",
                  comment="custom_looper/opencode_native/mcp_agent/imported"),
        sa.Column("description", sa.Text(), nullable=True, comment="描述"),
        sa.Column("current_version_id", sa.Integer(), nullable=True,
                  comment="当前生效版本 id（引用 agent_looper_versions.id）"),
        sa.Column("active_config_json", sa.Text(), nullable=True,
                  comment="LONGTEXT: 当前版本完整 JSON schema 快照"),
        sa.Column("owner_user_id", sa.Integer(), nullable=False, comment="拥有者 user_id"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1"),
                  comment="是否激活（soft-delete = False）"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("0"),
                  comment="是否已发布"),
        sa.Column("settings", sa.JSON(), nullable=True, comment="path overrides 等运行时设置"),
        sa.Column("resource_bindings", sa.JSON(), nullable=True, comment="资源绑定：LLM/数据源/知识库等"),
        sa.Column("credential_ref", sa.JSON(), nullable=True,
                  comment="{credential_type: dp_source, credential_id: int}"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], name="fk_alc_owner_user"),
        comment="AgentLooper 配置主表",
    )

    # 2. agent_looper_versions
    op.create_table(
        "agent_looper_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键ID"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), comment="更新时间"),
        sa.Column("config_id", sa.Integer(), nullable=False,
                  comment="所属 config id（删除 config 级联删除本表）"),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default=sa.text("1"),
                  comment="版本号（同 config 下自增，从 1 起）"),
        sa.Column("config_json", sa.Text(), nullable=False,
                  comment="LONGTEXT: 该版本完整 JSON schema 快照"),
        sa.Column("model_snapshot", sa.String(length=256), nullable=True, comment="使用的模型标识"),
        sa.Column("prompt_snapshot", sa.Text(), nullable=True, comment="使用的主 prompt"),
        sa.Column("note", sa.String(length=256), nullable=True, comment="版本备注"),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False, comment="创建者 user_id"),
        sa.ForeignKeyConstraint(
            ["config_id"], ["agent_looper_configs.id"],
            name="fk_alv_config", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_alv_creator"),
        comment="AgentLooper 版本快照表",
    )
    op.create_index(
        "ix_agent_looper_versions_config_id_version",
        "agent_looper_versions",
        ["config_id", "version_number"],
        unique=True,
    )

    # 3. configs.current_version_id → versions.id（延迟到 versions 表建成后再加 FK，无 CASCADE）
    op.create_foreign_key(
        "fk_alc_current_version",
        "agent_looper_configs",
        "agent_looper_versions",
        ["current_version_id"], ["id"],
        # 不指定 ondelete —— 走 MySQL 默认 RESTRICT / NO ACTION，避免循环级联
    )

    # 4. agent_looper_test_runs
    op.create_table(
        "agent_looper_test_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键ID"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), comment="更新时间"),
        sa.Column("config_id", sa.Integer(), nullable=False, comment="所属 config id"),
        sa.Column("version_id", sa.Integer(), nullable=True,
                  comment="使用的版本 id（可能已被 TTL 清理时保留 NULL）"),
        sa.Column("prompt", sa.Text(), nullable=False, comment="用户提问 prompt"),
        sa.Column("response", sa.Text(), nullable=True, comment="agent 回复"),
        sa.Column("latency_ms", sa.Integer(), nullable=True, comment="端到端耗时 ms"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="running",
                  comment="running/success/failed/timeout"),
        sa.Column("error", sa.Text(), nullable=True, comment="失败原因"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="发起试跑 user_id"),
        sa.ForeignKeyConstraint(
            ["config_id"], ["agent_looper_configs.id"],
            name="fk_altr_config", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["version_id"], ["agent_looper_versions.id"],
            name="fk_altr_version",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_altr_user"),
        comment="AgentLooper 试跑记录（TTL 清理）",
    )


def downgrade() -> None:
    op.drop_table("agent_looper_test_runs")
    op.drop_constraint("fk_alc_current_version", "agent_looper_configs", type_="foreignkey")
    op.drop_index("ix_agent_looper_versions_config_id_version", table_name="agent_looper_versions")
    op.drop_table("agent_looper_versions")
    op.drop_table("agent_looper_configs")
