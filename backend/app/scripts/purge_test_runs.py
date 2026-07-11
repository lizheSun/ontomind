"""剧本：清理超过 TTL 天数的 AgentLooperTestRun 记录（配合 cron 调度）。

用法：
    PYTHONPATH=. python -m app.scripts.purge_test_runs [--days N] [--dry-run]

默认使用 `settings.AGENT_LOOPER_TEST_RUNS_TTL_DAYS`（30 天）。
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.agent_looper_test_run_model import AgentLooperTestRun


def purge_old_test_runs(
    db: Session,
    *,
    days: Optional[int] = None,
    dry_run: bool = False,
) -> int:
    """删除 created_at < now - days 的 test_run 行；返回删除条数。"""
    days_val = int(days if days is not None else settings.AGENT_LOOPER_TEST_RUNS_TTL_DAYS)
    cutoff = datetime.utcnow() - timedelta(days=days_val)
    q = db.query(AgentLooperTestRun).filter(AgentLooperTestRun.created_at < cutoff)
    if dry_run:
        return q.count()
    deleted = q.delete(synchronize_session=False)
    db.commit()
    return int(deleted)


def _cli() -> None:  # pragma: no cover - CLI 入口
    parser = argparse.ArgumentParser(description="Purge old AgentLooperTestRun rows")
    parser.add_argument("--days", type=int, default=None, help="TTL 天数（缺省从 settings）")
    parser.add_argument("--dry-run", action="store_true", help="仅统计不删除")
    args = parser.parse_args()

    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        n = purge_old_test_runs(db, days=args.days, dry_run=args.dry_run)
        action = "would-delete" if args.dry_run else "deleted"
        print(f"{action} {n} test runs")
    finally:
        db.close()


if __name__ == "__main__":  # pragma: no cover
    _cli()
