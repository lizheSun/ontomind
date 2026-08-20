"""后台长任务：独立线程 + 独立 Session。"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Optional

from app.db.session import get_session_factory

logger = logging.getLogger(__name__)


def run_in_background(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    def _wrapper() -> None:
        try:
            fn(*args, **kwargs)
        except Exception:
            logger.exception("background job crashed: %s", getattr(fn, "__name__", fn))

    t = threading.Thread(target=_wrapper, daemon=True, name=f"job-{getattr(fn, '__name__', 'fn')}")
    t.start()


def guard_job(
    db: Any,
    job: Any,
    fn: Callable[[], Any],
    *,
    running_status: str = "running",
    success_status: str = "succeeded",
    failed_status: str = "failed",
) -> None:
    started = time.perf_counter()
    try:
        if hasattr(job, "status"):
            job.status = running_status
        db.add(job)
        db.commit()
        fn()
        if hasattr(job, "status"):
            job.status = success_status
        if hasattr(job, "duration_ms"):
            job.duration_ms = int((time.perf_counter() - started) * 1000)
        if hasattr(job, "error_detail"):
            job.error_detail = None
        db.add(job)
        db.commit()
    except Exception as exc:
        logger.exception("guard_job failed")
        try:
            if hasattr(job, "status"):
                job.status = failed_status
            if hasattr(job, "error_detail"):
                job.error_detail = str(exc)[:2000]
            if hasattr(job, "duration_ms"):
                job.duration_ms = int((time.perf_counter() - started) * 1000)
            db.add(job)
            db.commit()
        except Exception:
            logger.exception("guard_job failed to persist error")
            db.rollback()


def open_job_session():
    factory = get_session_factory()
    return factory()
