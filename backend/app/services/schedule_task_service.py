"""Schedule task + task run + log service.

功能：
1. CRUD schedule_tasks
2. 手动/调度触发 run（后台线程执行 opencode 调用）
3. 实时日志：追加到 task_log_entries；前端可增量拉取
4. 简单调度器：每 5s 扫描一次到期的 enabled task 触发（interval / cron 支持）
"""
from __future__ import annotations

import asyncio
import json
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException, NotFoundException
from app.db.models.docker_service_model import DockerService
from app.db.models.schedule_task_model import ScheduleTask, TaskLogEntry, TaskRun
from app.db.repositories.schedule_task_repo import (
    ScheduleTaskRepository, TaskLogEntryRepository, TaskRunRepository,
)
from app.db.session import SessionLocal
from app.schemas.schedule_task_schema import ScheduleTaskCreate, ScheduleTaskUpdate


# ---- 辅助 ----
def _serialize_task(t: ScheduleTask) -> dict[str, Any]:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "task_type": t.task_type,
        "schedule_type": t.schedule_type,
        "schedule_expr": t.schedule_expr,
        "docker_service_id": t.docker_service_id,
        "opencode_config": t.opencode_config or {},
        "env": t.env or {},
        "timeout_seconds": t.timeout_seconds,
        "enabled": t.enabled,
        "status": t.status,
        "last_run_at": t.last_run_at.isoformat() if t.last_run_at else None,
        "next_run_at": t.next_run_at.isoformat() if t.next_run_at else None,
        "total_runs": t.total_runs,
        "success_runs": t.success_runs,
        "failed_runs": t.failed_runs,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


def _serialize_run(r: TaskRun) -> dict[str, Any]:
    return {
        "id": r.id,
        "task_id": r.task_id,
        "trigger": r.trigger,
        "status": r.status,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        "duration_ms": r.duration_ms,
        "snapshot": r.snapshot or {},
        "exit_code": r.exit_code,
        "output_summary": r.output_summary,
        "error_message": r.error_message,
        "opencode_session_id": r.opencode_session_id,
        "triggered_by_user_id": r.triggered_by_user_id,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _serialize_log(l: TaskLogEntry) -> dict[str, Any]:
    return {
        "id": l.id,
        "run_id": l.run_id,
        "sequence": l.sequence,
        "level": l.level,
        "message": l.message,
        "created_at": l.created_at.isoformat() if l.created_at else None,
    }


def _compute_next_run(schedule_type: str, expr: Optional[str],
                      last: Optional[datetime] = None) -> Optional[datetime]:
    """极简版本：interval 支持秒；cron 只支持 'every_N_minutes' / 'every_N_hours' 简化格式.

    生产可换 croniter；这里保持零依赖.
    """
    now = datetime.now(timezone.utc)
    base = last or now
    if schedule_type == "interval":
        try:
            secs = int(expr or "60")
            return base + timedelta(seconds=max(1, secs))
        except (ValueError, TypeError):
            return None
    if schedule_type == "cron":
        # 简化：接受 "*/5 * * * *"（5 分钟）或 "0 * * * *"（每小时）等
        if not expr:
            return None
        m = re.match(r"^\*/(\d+) \* \* \* \*$", expr.strip())
        if m:
            return base + timedelta(minutes=int(m.group(1)))
        m = re.match(r"^0 \*/(\d+) \* \* \*$", expr.strip())
        if m:
            return base + timedelta(hours=int(m.group(1)))
        # fallback: 每小时
        return base + timedelta(hours=1)
    if schedule_type == "once":
        try:
            dt = datetime.fromisoformat(expr) if expr else None
            if dt and dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None
    return None  # manual


class LogAppender:
    """向 task_log_entries 追加日志的辅助类（跨 session 使用）."""

    def __init__(self, run_id: int):
        self.run_id = run_id
        self._seq = 0

    def add(self, message: str, level: str = "info") -> None:
        db = SessionLocal()
        try:
            self._seq += 1
            entry = TaskLogEntry(
                run_id=self.run_id,
                sequence=self._seq,
                level=level,
                message=message[:8000],
            )
            db.add(entry)
            db.commit()
        finally:
            db.close()


class ScheduleTaskService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ScheduleTaskRepository(db)
        self.run_repo = TaskRunRepository(db)
        self.log_repo = TaskLogEntryRepository(db)

    # ---- CRUD ----
    def list(self, skip: int = 0, limit: int = 200) -> list[dict[str, Any]]:
        return [_serialize_task(t) for t in self.repo.list_ordered(skip, limit)]

    def get(self, task_id: int) -> dict[str, Any]:
        t = self.repo.get_by_id(task_id)
        if not t:
            raise NotFoundException(f"任务不存在: {task_id}")
        return _serialize_task(t)

    def create(self, payload: ScheduleTaskCreate, user_id: Optional[int] = None) -> dict[str, Any]:
        t = ScheduleTask(
            name=payload.name,
            description=payload.description,
            task_type=payload.task_type,
            schedule_type=payload.schedule_type,
            schedule_expr=payload.schedule_expr,
            docker_service_id=payload.docker_service_id,
            opencode_config=payload.opencode_config or {},
            env=payload.env or {},
            timeout_seconds=payload.timeout_seconds,
            enabled=payload.enabled,
            status="idle",
            created_by_user_id=user_id,
        )
        t.next_run_at = _compute_next_run(t.schedule_type, t.schedule_expr)
        self.db.add(t)
        self.db.commit()
        self.db.refresh(t)
        return _serialize_task(t)

    def update(self, task_id: int, payload: ScheduleTaskUpdate) -> dict[str, Any]:
        t = self.repo.get_by_id(task_id)
        if not t:
            raise NotFoundException(f"任务不存在: {task_id}")
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(t, k, v)
        # 调度参数变化 → 重新计算 next_run_at
        t.next_run_at = _compute_next_run(t.schedule_type, t.schedule_expr, t.last_run_at)
        self.db.commit()
        self.db.refresh(t)
        return _serialize_task(t)

    def delete(self, task_id: int) -> None:
        t = self.repo.get_by_id(task_id)
        if not t:
            raise NotFoundException(f"任务不存在: {task_id}")
        self.db.delete(t)
        self.db.commit()

    def toggle(self, task_id: int, enabled: bool) -> dict[str, Any]:
        t = self.repo.get_by_id(task_id)
        if not t:
            raise NotFoundException(f"任务不存在: {task_id}")
        t.enabled = enabled
        if enabled and not t.next_run_at:
            t.next_run_at = _compute_next_run(t.schedule_type, t.schedule_expr, t.last_run_at)
        self.db.commit()
        self.db.refresh(t)
        return _serialize_task(t)

    # ---- 触发 ----
    def trigger(self, task_id: int, trigger: str = "manual",
                user_id: Optional[int] = None) -> dict[str, Any]:
        """立即触发一次任务运行（异步）."""
        t = self.repo.get_by_id(task_id)
        if not t:
            raise NotFoundException(f"任务不存在: {task_id}")
        run = TaskRun(
            task_id=t.id,
            trigger=trigger,
            status="pending",
            snapshot={
                "name": t.name,
                "task_type": t.task_type,
                "docker_service_id": t.docker_service_id,
                "opencode_config": t.opencode_config,
                "timeout_seconds": t.timeout_seconds,
            },
            triggered_by_user_id=user_id,
        )
        self.db.add(run)
        t.status = "running"
        t.total_runs += 1
        self.db.commit()
        self.db.refresh(run)

        # 后台线程执行
        threading.Thread(
            target=_run_task_worker,
            args=(t.id, run.id),
            daemon=True,
        ).start()

        return _serialize_run(run)

    def cancel_run(self, run_id: int) -> dict[str, Any]:
        r = self.run_repo.get_by_id(run_id)
        if not r:
            raise NotFoundException(f"运行不存在: {run_id}")
        if r.status not in ("pending", "running"):
            raise BusinessException("运行已结束，无法取消", code="RUN_ALREADY_DONE")
        r.status = "cancelled"
        r.finished_at = datetime.now(timezone.utc)
        # 同步 task 状态
        t = self.repo.get_by_id(r.task_id)
        if t:
            t.status = "idle"
            t.failed_runs += 1
        self.db.commit()
        self.db.refresh(r)
        return _serialize_run(r)

    # ---- 运行记录查询 ----
    def list_runs(self, task_id: int, skip: int = 0, limit: int = 50) -> list[dict[str, Any]]:
        return [_serialize_run(r) for r in self.run_repo.list_by_task(task_id, skip, limit)]

    def get_run(self, run_id: int) -> dict[str, Any]:
        r = self.run_repo.get_by_id(run_id)
        if not r:
            raise NotFoundException(f"运行不存在: {run_id}")
        return _serialize_run(r)

    def get_logs(self, run_id: int, since_seq: int = 0, limit: int = 500) -> list[dict[str, Any]]:
        r = self.run_repo.get_by_id(run_id)
        if not r:
            raise NotFoundException(f"运行不存在: {run_id}")
        rows = (
            self.db.query(TaskLogEntry)
            .filter(TaskLogEntry.run_id == run_id, TaskLogEntry.sequence > since_seq)
            .order_by(TaskLogEntry.sequence.asc())
            .limit(limit)
            .all()
        )
        return [_serialize_log(l) for l in rows]


# ============================================================
# 后台 worker：真正执行 opencode 调用
# ============================================================
def _run_task_worker(task_id: int, run_id: int) -> None:
    """在独立线程 + 独立 DB session 里跑."""
    log = LogAppender(run_id)
    start_ts = time.time()
    db = SessionLocal()
    try:
        t = db.query(ScheduleTask).get(task_id)
        r = db.query(TaskRun).get(run_id)
        if not t or not r:
            return
        r.status = "running"
        r.started_at = datetime.now(timezone.utc)
        db.commit()

        log.add(f"任务开始 · {t.name}", "event")
        log.add(f"trigger={r.trigger} timeout={t.timeout_seconds}s", "info")

        # 目标 opencode base URL
        ds: Optional[DockerService] = None
        if t.docker_service_id:
            ds = db.query(DockerService).get(t.docker_service_id)

        if ds:
            base_url = f"http://{ds.host}:{ds.host_port or ds.container_port}"
            log.add(f"目标 docker 服务: {ds.name} @ {base_url}", "info")
        else:
            base_url = "http://127.0.0.1:4096"
            log.add(f"未指定 docker 服务，回退本机 {base_url}", "warn")

        # 调用 opencode
        cfg = t.opencode_config or {}
        prompt = str(cfg.get("prompt") or cfg.get("message") or "").strip()
        agent = cfg.get("agent") or "build"
        model = cfg.get("model")
        provider = cfg.get("provider")
        system = cfg.get("system")

        if not prompt:
            raise ValueError("opencode_config.prompt 为空")

        exit_code = 0
        output_text = ""
        oc_session_id = None

        try:
            with httpx.Client(base_url=base_url, timeout=t.timeout_seconds) as cli:
                log.add("创建 opencode session…", "info")
                s = cli.post("/session", json={"title": f"[Task] {t.name}"})
                s.raise_for_status()
                session = s.json()
                oc_session_id = session.get("id")
                log.add(f"session_id = {oc_session_id}", "info")

                body: dict[str, Any] = {
                    "parts": [{"type": "text", "text": prompt}],
                    "agent": agent,
                }
                if model and provider:
                    body["model"] = {"providerID": provider, "modelID": model}
                if system:
                    body["system"] = system

                log.add(f"发送消息 → agent={agent}", "info")
                m = cli.post(f"/session/{oc_session_id}/message", json=body)
                m.raise_for_status()
                data = m.json()

                for p in data.get("parts", []):
                    if p.get("type") == "text":
                        txt = p.get("text") or ""
                        if txt:
                            output_text += txt
                            for line in txt.splitlines():
                                if line.strip():
                                    log.add(line, "stdout")
                    elif p.get("type") == "tool":
                        state = p.get("state", {})
                        log.add(
                            f"工具调用: {p.get('tool')} [{state.get('status')}]",
                            "event",
                        )
                        if state.get("error"):
                            log.add(f"工具错误: {state['error']}", "stderr")
        except httpx.TimeoutException:
            log.add(f"超时 (> {t.timeout_seconds}s)", "error")
            r.status = "timeout"
            r.error_message = f"timeout after {t.timeout_seconds}s"
            exit_code = 124
        except Exception as exc:
            log.add(f"运行异常: {exc}", "error")
            r.status = "failed"
            r.error_message = str(exc)[:2000]
            exit_code = 1

        # 结束
        r.finished_at = datetime.now(timezone.utc)
        r.duration_ms = int((time.time() - start_ts) * 1000)
        r.exit_code = exit_code
        r.output_summary = (output_text[-1000:] or "").strip()
        if oc_session_id:
            r.opencode_session_id = oc_session_id

        if r.status == "running":  # 未被上面异常改过
            r.status = "success" if exit_code == 0 else "failed"

        # 同步 task 状态
        t = db.query(ScheduleTask).get(task_id)
        if t:
            t.status = "idle"
            t.last_run_at = r.finished_at
            if r.status == "success":
                t.success_runs += 1
            else:
                t.failed_runs += 1
            # 计算下次触发（若是循环调度）
            t.next_run_at = _compute_next_run(t.schedule_type, t.schedule_expr, t.last_run_at)
        db.commit()

        log.add(f"任务完成 · status={r.status} · duration={r.duration_ms}ms", "event")
    except Exception as exc:
        log.add(f"worker 崩溃: {exc}", "error")
        try:
            r = db.query(TaskRun).get(run_id)
            if r:
                r.status = "failed"
                r.finished_at = datetime.now(timezone.utc)
                r.error_message = str(exc)[:2000]
            t = db.query(ScheduleTask).get(task_id)
            if t:
                t.status = "idle"
                t.failed_runs += 1
            db.commit()
        except Exception:
            pass
    finally:
        db.close()


# ============================================================
# 全局调度器（后台协程）
# ============================================================
class _Scheduler:
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._stop = False

    async def _loop(self):
        while not self._stop:
            try:
                self._tick()
            except Exception:
                pass
            await asyncio.sleep(5)

    def _tick(self):
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            due = (
                db.query(ScheduleTask)
                .filter(ScheduleTask.enabled == True)
                .filter(ScheduleTask.status != "running")
                .filter(ScheduleTask.schedule_type.in_(("interval", "cron", "once")))
                .filter(ScheduleTask.next_run_at != None)  # noqa: E711
                .filter(ScheduleTask.next_run_at <= now)
                .all()
            )
            for t in due:
                # once 只跑一次
                if t.schedule_type == "once":
                    t.enabled = False
                # 立即触发
                run = TaskRun(
                    task_id=t.id,
                    trigger="schedule",
                    status="pending",
                    snapshot={
                        "name": t.name,
                        "task_type": t.task_type,
                        "docker_service_id": t.docker_service_id,
                        "opencode_config": t.opencode_config,
                        "timeout_seconds": t.timeout_seconds,
                    },
                )
                db.add(run)
                t.status = "running"
                t.total_runs += 1
                db.commit()
                threading.Thread(
                    target=_run_task_worker,
                    args=(t.id, run.id),
                    daemon=True,
                ).start()
        finally:
            db.close()

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        if self._task and not self._task.done():
            return
        self._stop = False
        self._task = loop.create_task(self._loop())

    def stop(self) -> None:
        self._stop = True


scheduler = _Scheduler()
