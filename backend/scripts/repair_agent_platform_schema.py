"""Repair agent-platform schema drift when create_all and Alembic are out of sync."""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.db.session import engine


def column_names(table: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table)}


def add_column_if_missing(table: str, column: str, ddl: str) -> None:
    if column in column_names(table):
        print(f"skip {table}.{column}")
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
    print(f"add {table}.{column}")


def main() -> None:
    compute_columns = {
        "address": "address VARCHAR(255) NULL",
        "architecture": "architecture VARCHAR(64) NULL",
        "environment": "environment VARCHAR(64) NOT NULL DEFAULT 'default'",
        "status_reason": "status_reason VARCHAR(512) NULL",
        "last_heartbeat_at": "last_heartbeat_at DATETIME NULL",
        "last_scan_at": "last_scan_at DATETIME NULL",
        "created_by_user_id": "created_by_user_id INT NULL",
    }
    for name, ddl in compute_columns.items():
        add_column_if_missing("compute_nodes", name, ddl)

    with engine.begin() as conn:
        conn.execute(text("UPDATE compute_nodes SET address = ip WHERE address IS NULL AND ip IS NOT NULL"))
        conn.execute(text("UPDATE compute_nodes SET environment = 'default' WHERE environment IS NULL OR environment = ''"))

    agent_columns = {
        "owner_user_id": "owner_user_id INT NULL",
        "current_version_id": "current_version_id INT NULL",
    }
    for name, ddl in agent_columns.items():
        add_column_if_missing("agents", name, ddl)

    run_columns = {
        "agent_version_id": "agent_version_id INT NULL",
        "deployment_id": "deployment_id INT NULL",
        "session_id": "session_id INT NULL",
        "owner_user_id": "owner_user_id INT NULL",
        "strategy": "strategy VARCHAR(32) NULL",
        "kind": "kind VARCHAR(32) NOT NULL DEFAULT 'chat'",
        "parent_run_id": "parent_run_id INT NULL",
        "attempt": "attempt INT NOT NULL DEFAULT 1",
        "goal": "goal TEXT NULL",
        "checkpoint": "checkpoint JSON NULL",
        "input": "input JSON NULL",
        "output": "output JSON NULL",
        "state_version": "state_version INT NOT NULL DEFAULT 1",
        "completed_at": "completed_at DATETIME NULL",
    }
    for name, ddl in run_columns.items():
        add_column_if_missing("agent_runs", name, ddl)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO alembic_version (version_num)
                SELECT '2026071204'
                WHERE NOT EXISTS (SELECT 1 FROM alembic_version)
                """
            )
        )
        conn.execute(text("UPDATE alembic_version SET version_num = '2026071204'"))

    print("schema repair complete; alembic stamped to 2026071204")


if __name__ == "__main__":
    main()
