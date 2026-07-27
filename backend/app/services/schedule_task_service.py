"""调度任务 & 运行记录服务（v2 — 日志落盘 + subprocess 执行）.

日志落盘规则：
  {log_dir}/{task_id}/{yyyyMMdd}/{task_id}-{HHmmss}-{random_4digits}.log
"""
import logging
import os
import random
import signal
import subprocess
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException, NotFoundException, ValidationException
from app.db.models.schedule_task_model import ScheduleTask, TaskRun
from app.db.repositories.schedule_task_repo import (
    ScheduleTaskRepository, TaskRunRepository,
)
from app.schemas.schedule_task_schema import (
    ScheduleTaskCreate, ScheduleTaskResponse, ScheduleTaskUpdate,
    TaskRunResponse,
)

logger = logging.getLogger(__name__)

# ======================================================================
# helpers
# ======================================================================

def build_log_path(log_dir: str, task_id: int) -> str:
    """生成日志文件完整路径（遵循落盘规则）."""
    now = datetime.now()
    date_dir = now.strftime("%Y%m%d")
    ts = now.strftime("%H%M%S")
    seed = random.randint(1000, 9999)
    dir_path = os.path.join(log_dir, str(task_id), date_dir)
    os.makedirs(dir_path, exist_ok=True)
    filename = f"{task_id}-{ts}-{seed}.log"
    return os.path.join(dir_path, filename)


def preview_log_path(log_dir: str, task_id: int) -> str:
    """预览日志路径模版（用于 UI 实时预览）."""
    now_s = datetime.now().strftime("%H%M%S")
    return os.path.join(log_dir, str(task_id), "{yyyyMMdd}", f"{{task_id}}-{now_s}-{{seed}}.log")


def compute_next_run(schedule_type: str, schedule_expr: Optional[str]) -> Optional[datetime]:
    """计算下次运行时间（UTC），手动任务返回 None."""
    if schedule_type == "manual":
        return None
    now = datetime.now(timezone.utc)
    if schedule_type == "interval" and schedule_expr:
        try:
            seconds = int(schedule_expr)
            return now + __import__("datetime").timedelta(seconds=seconds)
        except (ValueError, TypeError):
            pass
    elif schedule_type == "cron" and schedule_expr:
        # 简单 cron（分 时 日 月 周），仅计算下一次匹配，不处理复杂表达式
        try:
            from croniter import croniter
            return croniter(schedule_expr, now).get_next(datetime)
        except ImportError:
            logger.warning("croniter 未安装，无法计算 cron 下次执行时间")
            return None
        except Exception:
            return None
    elif schedule_type == "once" and schedule_expr:
        try:
            target = datetime.fromisoformat(schedule_expr)
            if target.tzinfo is None:
                target = target.replace(tzinfo=timezone.utc)
            return target
        except (ValueError, TypeError):
            return None
    return None


# ======================================================================
# Service
# ======================================================================

class ScheduleTaskService:
    # 运行中的进程映射: {run_id: subprocess.Popen}
    _running: Dict[int, subprocess.Popen] = {}
    _lock = threading.Lock()

    def __init__(self, db: Session):
        self.db = db
        self.task_repo = ScheduleTaskRepository(db)
        self.run_repo = TaskRunRepository(db)

    # ---- 任务 CRUD ----

    def list_tasks(self,
                   schedule_type: Optional[str] = None,
                   enabled: Optional[bool] = None,
                   search: str = "",
                   skip: int = 0, limit: int = 200) -> List[ScheduleTaskResponse]:
        q = self.db.query(ScheduleTask)
        if schedule_type:
            q = q.filter(ScheduleTask.schedule_type == schedule_type)
        if enabled is not None:
            q = q.filter(ScheduleTask.enabled == enabled)
        if search:
            q = q.filter(
                (ScheduleTask.name.ilike(f"%{search}%")) |
                (ScheduleTask.command.ilike(f"%{search}%"))
            )
        tasks = q.order_by(ScheduleTask.id.desc()).offset(skip).limit(limit).all()
        return [ScheduleTaskResponse.model_validate(t) for t in tasks]

    def get_task(self, task_id: int) -> ScheduleTaskResponse:
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise NotFoundException(f"任务 ID={task_id} 不存在")
        return ScheduleTaskResponse.model_validate(task)

    def create_task(self, payload: ScheduleTaskCreate) -> ScheduleTaskResponse:
        data = payload.model_dump()
        data["next_run_at"] = compute_next_run(data["schedule_type"], data.get("schedule_expr"))
        task = ScheduleTask(**data)
        self.db.add(task)
        self.db.flush()
        self.db.commit()
        logger.info(f"创建调度任务: {task.name} (ID={task.id})")
        return ScheduleTaskResponse.model_validate(task)

    def update_task(self, task_id: int, payload: ScheduleTaskUpdate) -> ScheduleTaskResponse:
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise NotFoundException(f"任务 ID={task_id} 不存在")
        updates = payload.model_dump(exclude_unset=True)
        for k, v in updates.items():
            setattr(task, k, v)
        # 重新计算 next_run
        if "schedule_type" in updates or "schedule_expr" in updates:
            task.next_run_at = compute_next_run(task.schedule_type, task.schedule_expr)
        self.db.flush()
        self.db.commit()
        logger.info(f"更新调度任务: {task.name} (ID={task.id})")
        return ScheduleTaskResponse.model_validate(task)

    def delete_task(self, task_id: int) -> None:
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise NotFoundException(f"任务 ID={task_id} 不存在")
        # 杀掉可能还在运行的进程
        self._kill_running(task_id)
        self.db.delete(task)
        self.db.flush()
        self.db.commit()
        logger.info(f"删除调度任务: {task.name} (ID={task_id})")

    def toggle_enabled(self, task_id: int) -> ScheduleTaskResponse:
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise NotFoundException(f"任务 ID={task_id} 不存在")
        task.enabled = not task.enabled
        if task.enabled:
            task.next_run_at = compute_next_run(task.schedule_type, task.schedule_expr)
        else:
            task.next_run_at = None
        self.db.flush()
        self.db.commit()
        return ScheduleTaskResponse.model_validate(task)

    # ---- 触发执行 ----

    def trigger(self, task_id: int, trigger: str = "manual") -> TaskRunResponse:
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise NotFoundException(f"任务 ID={task_id} 不存在")
        if task.status == "running":
            raise BusinessException("任务已在运行中", code="TASK_ALREADY_RUNNING")

        # 创建运行记录
        log_file = build_log_path(task.log_dir, task.id)
        now = datetime.now(timezone.utc)
        run = TaskRun(
            task_id=task.id,
            trigger=trigger,
            status="running",
            started_at=now,
            log_file=log_file,
        )
        self.db.add(run)
        task.status = "running"
        self.db.flush()
        # 先提交以持久运行记录 ID
        self.db.commit()
        run_id = run.id

        # 后台线程执行
        t = threading.Thread(
            target=self._run_worker, args=(task.id, run_id, task.command, log_file),
            daemon=True,
        )
        t.start()
        logger.info(f"触发任务 '{task.name}' (run={run_id})")
        return TaskRunResponse.model_validate(run)

    def _run_worker(self, task_id: int, run_id: int, command: str, log_file: str):
        """在独立线程中执行命令，写日志文件."""
        # 使用独立的 DB session
        from app.db.session import SessionLocal
        sub_db: Session = SessionLocal()
        try:
            # 启动进程
            with open(log_file, "a") as f:
                f.write(f"# 任务 ID={task_id} run={run_id} 启动 {datetime.now().isoformat()}\n")
                f.write(f"# 命令: {command}\n")
                f.write("# " + "-" * 60 + "\n")
                f.flush()
                proc = subprocess.Popen(
                    command,
                    shell=True, executable="/bin/bash",
                    stdout=f, stderr=subprocess.STDOUT,
                    preexec_fn=os.setsid,  # 进程组，便于 kill
                )
            with self._lock:
                self._running[run_id] = proc

            proc.wait()

            # 更新运行记录
            run = sub_db.query(TaskRun).filter(TaskRun.id == run_id).first()
            if run:
                now = datetime.now(timezone.utc)
                run.finished_at = now
                run.exit_code = proc.returncode
                run.status = "success" if proc.returncode == 0 else "failed"
                run.duration_ms = int(
                    (run.finished_at - run.started_at).total_seconds() * 1000
                )
                # 追加日志尾部
                with open(log_file, "a") as f:
                    f.write("# " + "-" * 60 + "\n")
                    f.write(f"# 退出码: {proc.returncode}  状态: {run.status}\n")
                sub_db.flush()

            # 更新任务统计
            task = sub_db.query(ScheduleTask).filter(ScheduleTask.id == task_id).first()
            if task:
                task.total_runs = (task.total_runs or 0) + 1
                if proc.returncode == 0:
                    task.success_runs = (task.success_runs or 0) + 1
                else:
                    task.failed_runs = (task.failed_runs or 0) + 1
                task.last_run_at = datetime.now(timezone.utc)
                task.status = "idle"
                task.next_run_at = compute_next_run(task.schedule_type, task.schedule_expr)
                sub_db.flush()
            sub_db.commit()
        except Exception as e:
            logger.exception(f"任务执行异常 task={task_id} run={run_id}")
            run = sub_db.query(TaskRun).filter(TaskRun.id == run_id).first()
            if run:
                run.status = "failed"
                run.error_message = str(e)
                run.finished_at = datetime.now(timezone.utc)
                sub_db.flush()
            task = sub_db.query(ScheduleTask).filter(ScheduleTask.id == task_id).first()
            if task:
                task.status = "idle"
                task.failed_runs = (task.failed_runs or 0) + 1
                task.total_runs = (task.total_runs or 0) + 1
                sub_db.flush()
            sub_db.commit()
        finally:
            with self._lock:
                self._running.pop(run_id, None)
            sub_db.close()

    # ---- 取消运行 ----

    def cancel_run(self, run_id: int) -> TaskRunResponse:
        """取消正在运行的进程."""
        with self._lock:
            proc = self._running.get(run_id)
        if not proc:
            raise BusinessException("运行不存在或已结束", code="RUN_NOT_FOUND")
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass  # 已退出
        # 更新记录
        run = self.run_repo.get_by_id(run_id)
        if run:
            run.status = "canceled"
            run.finished_at = datetime.now(timezone.utc)
            if run.started_at:
                run.duration_ms = int(
                    (run.finished_at - run.started_at).total_seconds() * 1000
                )
            self.db.flush()
            self.db.commit()
        with self._lock:
            self._running.pop(run_id, None)
        if not run:
            raise NotFoundException(f"运行记录 ID={run_id} 不存在")
        return TaskRunResponse.model_validate(run)

    def _kill_running(self, task_id: int):
        """杀死某个任务所有运行中的进程."""
        runs = (
            self.db.query(TaskRun)
            .filter(TaskRun.task_id == task_id, TaskRun.status == "running")
            .all()
        )
        for run in runs:
            with self._lock:
                proc = self._running.pop(run.id, None)
            if proc:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except (ProcessLookupError, OSError):
                    pass

    # ---- 运行记录 ----

    def list_runs(self, task_id: Optional[int] = None,
                  status: Optional[str] = None,
                  trigger: Optional[str] = None,
                  skip: int = 0, limit: int = 50) -> List[TaskRunResponse]:
        query = self.db.query(TaskRun)
        if task_id is not None:
            query = query.filter(TaskRun.task_id == task_id)
        if status:
            query = query.filter(TaskRun.status == status)
        if trigger:
            query = query.filter(TaskRun.trigger == trigger)
        runs = query.order_by(TaskRun.id.desc()).offset(skip).limit(limit).all()
        return [TaskRunResponse.model_validate(r) for r in runs]

    def get_run(self, run_id: int) -> TaskRunResponse:
        run = self.run_repo.get_by_id(run_id)
        if not run:
            raise NotFoundException(f"运行记录 ID={run_id} 不存在")
        return TaskRunResponse.model_validate(run)

    # ---- 日志读取 ----

    def read_logs(self, log_file: str, since_line: int = 0, tail: int = 500) -> List[Dict]:
        """从日志文件读取行（since_line 为已读行数，tail 作为回退读最后 N 行）."""
        lines: List[Dict] = []
        if not os.path.isfile(log_file):
            return lines
        try:
            with open(log_file, "r") as f:
                all_lines = f.readlines()
        except Exception:
            return lines
        total = len(all_lines)
        # since_line == 0 且日志过大时走 tail
        if since_line == 0 and total > tail:
            start = total - tail
        else:
            start = max(since_line, 0)
        for i in range(start, total):
            raw = all_lines[i].rstrip("\n").rstrip("\r")
            # 简易级别推断
            level = "info"
            if raw.startswith("#"):
                level = "event"
            elif "ERROR" in raw or "error" in raw[:20]:
                level = "error"
            elif "WARN" in raw or "warn" in raw[:20]:
                level = "warn"
            lines.append({"seq": i + 1, "level": level, "text": raw})
        return lines


# ======================================================================
# 调度器（后台轮询线程）
# ======================================================================

class _Scheduler:
    """全局调度器，每 15s 扫描到期任务并触发."""
    _instance: Optional["_Scheduler"] = None
    _thread: Optional[threading.Thread] = None
    _stop: bool = False

    @classmethod
    def start(cls):
        if cls._thread and cls._thread.is_alive():
            return
        cls._stop = False
        cls._thread = threading.Thread(target=cls._loop, daemon=True)
        cls._thread.start()
        logger.info("调度轮询器已启动")

    @classmethod
    def stop(cls):
        cls._stop = True
        if cls._thread:
            cls._thread.join(timeout=5)
        logger.info("调度轮询器已停止")

    @classmethod
    def _loop(cls):
        from app.db.session import SessionLocal
        while not cls._stop:
            time.sleep(15)
            db: Session = SessionLocal()
            try:
                repo = ScheduleTaskRepository(db)
                svc = ScheduleTaskService(db)
                tasks = repo.list_due()
                for task in tasks:
                    try:
                        svc.trigger(task.id, trigger="schedule")
                        logger.info(f"调度触发任务: {task.name} (ID={task.id})")
                    except Exception as e:
                        logger.warning(f"调度触发失败 {task.name}: {e}")
            except Exception as e:
                logger.exception(f"调度轮询异常: {e}")
            finally:
                db.close()
