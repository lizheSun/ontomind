"""OALP v1.0 schema 补丁 — 启动时检查缺列并 ALTER 添加.

create_all 只对完全不存在的新表生效；已有表的加列必须 ALTER。
本模块提供幂等的「加列」helper：列已存在则跳过（catch 1060 Duplicate column name）。
"""
from __future__ import annotations

from typing import Iterable

from loguru import logger
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session


def _column_exists(db: Session, table: str, column: str) -> bool:
    try:
        insp = inspect(db.bind)
        return column in {c["name"] for c in insp.get_columns(table)}
    except Exception:
        return False


def add_column_if_missing(
    db: Session, table: str, column: str, ddl_fragment: str,
) -> bool:
    """列不存在则 ALTER TABLE ADD COLUMN.

    ddl_fragment 是列定义（不含列名），如：
      "VARCHAR(16) NULL DEFAULT 'subagent'"
      "JSON NOT NULL"
    """
    if _column_exists(db, table, column):
        return False
    sql = f"ALTER TABLE `{table}` ADD COLUMN `{column}` {ddl_fragment}"
    try:
        db.execute(text(sql))
        db.commit()
        logger.info(f"[schema-patch] {table}.{column} ADD OK  → {ddl_fragment}")
        return True
    except Exception as e:
        # 1060 = Duplicate column name（并发竞态）
        msg = str(e)
        if "1060" in msg or "Duplicate column" in msg:
            logger.info(f"[schema-patch] {table}.{column} 已被并发添加，跳过")
            return False
        logger.warning(f"[schema-patch] {table}.{column} ADD 失败: {e}")
        db.rollback()
        return False


def add_index_if_missing(
    db: Session, table: str, index_name: str, columns: Iterable[str], unique: bool = False,
) -> bool:
    """缺索引则 CREATE INDEX."""
    try:
        insp = inspect(db.bind)
        existing = {ix["name"] for ix in insp.get_indexes(table)}
        if index_name in existing:
            return False
        cols = ", ".join(f"`{c}`" for c in columns)
        kind = "UNIQUE INDEX" if unique else "INDEX"
        db.execute(text(f"CREATE {kind} `{index_name}` ON `{table}` ({cols})"))
        db.commit()
        logger.info(f"[schema-patch] {table}.{index_name} 创建成功")
        return True
    except Exception as e:
        msg = str(e)
        if "1061" in msg or "Duplicate key name" in msg:
            return False
        logger.warning(f"[schema-patch] {table}.{index_name} 创建失败: {e}")
        db.rollback()
        return False


def apply_oalp_patches(db: Session) -> list[str]:
    """应用 OALP v1.0 的所有列/索引补丁，返回变更描述列表."""
    changes: list[str] = []

    # ---- experts 表 ----
    expert_cols: list[tuple[str, str]] = [
        ("top_p", "VARCHAR(16) NULL"),
        ("mode", "VARCHAR(16) NOT NULL DEFAULT 'subagent'"),
        ("subagent_depth", "INT NOT NULL DEFAULT 1"),
        ("max_steps", "INT NULL"),
        ("system_prompt", "TEXT NULL"),
        ("permission_json", "JSON NOT NULL"),
        ("hooks_json", "JSON NOT NULL"),
        ("evals_json", "JSON NOT NULL"),
        ("version", "INT NOT NULL DEFAULT 1"),
        ("container_template_id", "INT NULL"),
        ("bind_skills_to_container", "TINYINT(1) NOT NULL DEFAULT 1"),
    ]
    for col, ddl in expert_cols:
        if add_column_if_missing(db, "experts", col, ddl):
            changes.append(f"experts.{col}")

    # ---- skills 表 ----
    skill_cols: list[tuple[str, str]] = [
        ("folder_path", "VARCHAR(512) NULL"),
        ("is_loaded", "TINYINT(1) NOT NULL DEFAULT 0"),
        ("auto_description", "TEXT NULL"),
    ]
    for col, ddl in skill_cols:
        if add_column_if_missing(db, "skills", col, ddl):
            changes.append(f"skills.{col}")

    # ---- mcps 表 ----
    mcp_cols: list[tuple[str, str]] = [
        ("auto_description", "TEXT NULL"),
        ("tools_manifest_json", "JSON NULL"),
        ("last_synced_at", "DATETIME NULL"),
    ]
    for col, ddl in mcp_cols:
        if add_column_if_missing(db, "mcps", col, ddl):
            changes.append(f"mcps.{col}")

    # ---- agent_relations 表（全新表，create_all 已建）----
    # 若缺（首次启动），让 create_all 兜底；这里只加 unique 索引（已通过 model 声明）

    return changes
