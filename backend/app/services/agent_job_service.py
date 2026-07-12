"""AgentJobService — Agent 长任务 Job 管理（T55）.

围绕 `agent_run_jobs` 表提供 CRUD + 显式生命周期状态机，用于前端 ETL 风格仪表盘。

状态机（`pending → running → paused → completed | failed | cancelled`）：

    pending ─────► running ◄────► paused
      │              │              │
      │              ├─► completed  │
      │              ├─► failed ◄───┘
      └─────────────►┴─► cancelled

- `create`  → status=pending, progress=0, current_step=0
- `start`   pending → running（set started_at）
- `pause`   running → paused
- `resume`  paused → running
- `complete` running → completed（set finished_at, progress=100, current_step=total_steps）
- `fail`    running|paused|pending → failed（可选 error_message）
- `cancel`  pending|running|paused → cancelled
- `advance_step` running 时把 current_step += 1，并按 total_steps 重算 progress
- `update_step_output` 更新 steps[idx] 的 output/status 元数据

Owner 语义：只有 `created_by_user_id == user_id` 或 superuser 可写；读默认按 owner 过滤。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import (
    BusinessException,
    NotFoundException,
    PermissionException,
    ValidationException,
)
from app.db.models.agent_model import Agent
from app.db.models.agent_run_job_model import AgentRunJob


TERMINAL_STATES: frozenset[str] = frozenset({"completed", "failed", "cancelled"})
ALL_STATES: frozenset[str] = frozenset(
    {"pending", "running", "paused", "completed", "failed", "cancelled"}
)

# Allowed forward transitions (source → set of legal targets).
_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"running", "cancelled", "failed"}),
    "running": frozenset({"paused", "completed", "failed", "cancelled"}),
    "paused": frozenset({"running", "cancelled", "failed"}),
    # Terminal states have no legal outgoing transitions.
    "completed": frozenset(),
    "failed": frozenset(),
    "cancelled": frozenset(),
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentJobService:
    """AgentRunJob CRUD + lifecycle."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------- helpers -------------------------------------------------

    def _require_job(self, job_id: int) -> AgentRunJob:
        row = self.db.query(AgentRunJob).filter(AgentRunJob.id == job_id).first()
        if row is None:
            raise NotFoundException(
                message=f"AgentJob id={job_id} 不存在", code="AGENT_JOB_NOT_FOUND"
            )
        return row

    def _require_agent(self, agent_id: int) -> Agent:
        row = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if row is None:
            raise NotFoundException(
                message=f"Agent id={agent_id} 不存在", code="AGENT_NOT_FOUND"
            )
        return row

    @staticmethod
    def _check_owner(job: AgentRunJob, user_id: int) -> None:
        if job.created_by_user_id != user_id:
            raise PermissionException(
                message="仅 Job 创建者可操作", code="AGENT_JOB_FORBIDDEN"
            )

    @staticmethod
    def _validate_status_transition(current: str, target: str) -> None:
        if current == target:
            return
        allowed = _TRANSITIONS.get(current, frozenset())
        if target not in allowed:
            raise ValidationException(
                message=f"非法状态迁移: {current} → {target}",
                code="AGENT_JOB_INVALID_TRANSITION",
            )

    @staticmethod
    def _sanitize_steps(steps: Any) -> list[dict[str, Any]]:
        """Normalize `steps` payload → list of {name, status, output?} dicts."""
        if steps is None:
            return []
        if not isinstance(steps, list):
            raise ValidationException(
                message="steps 必须是列表", code="AGENT_JOB_STEPS_INVALID"
            )
        out: list[dict[str, Any]] = []
        for i, s in enumerate(steps):
            if isinstance(s, str):
                out.append({"name": s, "status": "pending"})
            elif isinstance(s, dict):
                name = s.get("name")
                if not isinstance(name, str) or not name.strip():
                    raise ValidationException(
                        message=f"steps[{i}].name 必填",
                        code="AGENT_JOB_STEPS_INVALID",
                    )
                out.append(
                    {
                        "name": name,
                        "status": str(s.get("status", "pending")),
                        **(
                            {"output": s.get("output")}
                            if "output" in s
                            else {}
                        ),
                    }
                )
            else:
                raise ValidationException(
                    message=f"steps[{i}] 必须是 str 或 dict",
                    code="AGENT_JOB_STEPS_INVALID",
                )
        return out

    @staticmethod
    def _progress_for(current_step: int, total_steps: int) -> int:
        if total_steps <= 0:
            return 0
        pct = int(round(100.0 * current_step / total_steps))
        return max(0, min(100, pct))

    @staticmethod
    def _to_dict(job: AgentRunJob) -> dict[str, Any]:
        def _iso(dt: Any) -> Optional[str]:
            if dt is None:
                return None
            if isinstance(dt, datetime):
                return dt.isoformat()
            return str(dt)

        return {
            "id": job.id,
            "agent_id": job.agent_id,
            "name": job.name,
            "status": job.status,
            "steps": job.steps or [],
            "current_step": int(job.current_step or 0),
            "total_steps": int(job.total_steps or 1),
            "progress": int(job.progress or 0),
            "input_data": job.input_data,
            "output_data": job.output_data,
            "error_message": job.error_message,
            "started_at": _iso(job.started_at),
            "finished_at": _iso(job.finished_at),
            "created_by_user_id": job.created_by_user_id,
            "created_at": _iso(job.created_at),
            "updated_at": _iso(job.updated_at),
        }

    # ---------- CRUD ----------------------------------------------------

    def create(
        self,
        *,
        agent_id: int,
        name: str,
        user_id: int,
        steps: Optional[Iterable[Any]] = None,
        input_data: Any = None,
        total_steps: Optional[int] = None,
    ) -> dict[str, Any]:
        if not name or not name.strip():
            raise ValidationException(
                message="Job name 不能为空", code="AGENT_JOB_NAME_REQUIRED"
            )
        self._require_agent(agent_id)

        step_list = self._sanitize_steps(steps)
        if total_steps is None:
            total = len(step_list) if step_list else 1
        else:
            if total_steps <= 0:
                raise ValidationException(
                    message="total_steps 必须 > 0",
                    code="AGENT_JOB_TOTAL_STEPS_INVALID",
                )
            total = int(total_steps)

        job = AgentRunJob(
            agent_id=agent_id,
            name=name.strip(),
            status="pending",
            steps=step_list,
            current_step=0,
            total_steps=total,
            progress=0,
            input_data=input_data,
            output_data=None,
            error_message=None,
            started_at=None,
            finished_at=None,
            created_by_user_id=user_id,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return self._to_dict(job)

    def get(self, job_id: int) -> dict[str, Any]:
        return self._to_dict(self._require_job(job_id))

    def list(
        self,
        *,
        user_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        q = self.db.query(AgentRunJob)
        if user_id is not None:
            q = q.filter(AgentRunJob.created_by_user_id == user_id)
        if agent_id is not None:
            q = q.filter(AgentRunJob.agent_id == agent_id)
        if status is not None:
            if status not in ALL_STATES:
                raise ValidationException(
                    message=f"未知 status: {status}",
                    code="AGENT_JOB_UNKNOWN_STATUS",
                )
            q = q.filter(AgentRunJob.status == status)
        rows = (
            q.order_by(AgentRunJob.id.desc())
            .offset(max(0, int(skip)))
            .limit(max(1, min(int(limit), 500)))
            .all()
        )
        return [self._to_dict(r) for r in rows]

    def update(
        self,
        job_id: int,
        user_id: int,
        *,
        name: Optional[str] = None,
        steps: Optional[Iterable[Any]] = None,
        total_steps: Optional[int] = None,
        input_data: Any = None,
        _input_data_set: bool = False,
    ) -> dict[str, Any]:
        """Metadata-only update: name/steps/total_steps/input_data.

        状态、进度、时间戳请走 lifecycle 方法。当前处于终态时禁止元数据修改。
        """
        job = self._require_job(job_id)
        self._check_owner(job, user_id)
        if job.status in TERMINAL_STATES:
            raise BusinessException(
                message=f"Job 已处于终态 {job.status}，不可修改元数据",
                code="AGENT_JOB_TERMINAL",
                status_code=409,
            )

        if name is not None:
            if not name.strip():
                raise ValidationException(
                    message="name 不能为空", code="AGENT_JOB_NAME_REQUIRED"
                )
            job.name = name.strip()
        if steps is not None:
            job.steps = self._sanitize_steps(steps)
        if total_steps is not None:
            if total_steps <= 0:
                raise ValidationException(
                    message="total_steps 必须 > 0",
                    code="AGENT_JOB_TOTAL_STEPS_INVALID",
                )
            job.total_steps = int(total_steps)
            job.progress = self._progress_for(
                int(job.current_step or 0), int(job.total_steps)
            )
        if _input_data_set:
            job.input_data = input_data

        self.db.commit()
        self.db.refresh(job)
        return self._to_dict(job)

    def delete(self, job_id: int, user_id: int) -> None:
        job = self._require_job(job_id)
        self._check_owner(job, user_id)
        if job.status == "running":
            raise BusinessException(
                message="running 状态下不可删除，请先 pause/cancel",
                code="AGENT_JOB_RUNNING",
                status_code=409,
            )
        self.db.delete(job)
        self.db.commit()

    # ---------- lifecycle ----------------------------------------------

    def transition(
        self,
        job_id: int,
        user_id: int,
        target_status: str,
        *,
        error_message: Optional[str] = None,
        output_data: Any = None,
        _output_data_set: bool = False,
    ) -> dict[str, Any]:
        """Generic state transition guard."""
        if target_status not in ALL_STATES:
            raise ValidationException(
                message=f"未知 target status: {target_status}",
                code="AGENT_JOB_UNKNOWN_STATUS",
            )
        job = self._require_job(job_id)
        self._check_owner(job, user_id)
        self._validate_status_transition(job.status, target_status)

        now = _utcnow()
        job.status = target_status

        if target_status == "running":
            if job.started_at is None:
                job.started_at = now
            job.error_message = None
        elif target_status == "completed":
            job.finished_at = now
            job.progress = 100
            job.current_step = int(job.total_steps or 1)
            if _output_data_set:
                job.output_data = output_data
        elif target_status == "failed":
            job.finished_at = now
            if error_message is not None:
                job.error_message = str(error_message)[:2000]
        elif target_status == "cancelled":
            job.finished_at = now

        self.db.commit()
        self.db.refresh(job)
        return self._to_dict(job)

    def start(self, job_id: int, user_id: int) -> dict[str, Any]:
        return self.transition(job_id, user_id, "running")

    def pause(self, job_id: int, user_id: int) -> dict[str, Any]:
        return self.transition(job_id, user_id, "paused")

    def resume(self, job_id: int, user_id: int) -> dict[str, Any]:
        return self.transition(job_id, user_id, "running")

    def complete(
        self,
        job_id: int,
        user_id: int,
        output_data: Any = None,
    ) -> dict[str, Any]:
        return self.transition(
            job_id,
            user_id,
            "completed",
            output_data=output_data,
            _output_data_set=True,
        )

    def fail(
        self,
        job_id: int,
        user_id: int,
        error_message: Optional[str] = None,
    ) -> dict[str, Any]:
        return self.transition(
            job_id, user_id, "failed", error_message=error_message
        )

    def cancel(self, job_id: int, user_id: int) -> dict[str, Any]:
        return self.transition(job_id, user_id, "cancelled")

    # ---------- progress / step output ---------------------------------

    def advance_step(self, job_id: int, user_id: int) -> dict[str, Any]:
        """Increment `current_step` by 1 and recompute `progress`.

        Only legal while status == 'running'. Completing the final step does
        NOT auto-transition to completed — call `complete` explicitly to keep
        the state machine intent-driven.
        """
        job = self._require_job(job_id)
        self._check_owner(job, user_id)
        if job.status != "running":
            raise BusinessException(
                message=f"advance_step 仅在 running 状态可用，当前 {job.status}",
                code="AGENT_JOB_NOT_RUNNING",
                status_code=409,
            )
        total = int(job.total_steps or 1)
        current = int(job.current_step or 0)
        if current >= total:
            raise BusinessException(
                message="已达到 total_steps，无法继续 advance",
                code="AGENT_JOB_STEPS_EXHAUSTED",
                status_code=409,
            )
        job.current_step = current + 1
        job.progress = self._progress_for(job.current_step, total)
        self.db.commit()
        self.db.refresh(job)
        return self._to_dict(job)

    def update_step_output(
        self,
        job_id: int,
        user_id: int,
        step_index: int,
        *,
        status: Optional[str] = None,
        output: Any = None,
        _output_set: bool = False,
    ) -> dict[str, Any]:
        job = self._require_job(job_id)
        self._check_owner(job, user_id)
        steps = list(job.steps or [])
        if step_index < 0 or step_index >= len(steps):
            raise ValidationException(
                message=f"step_index {step_index} 越界（0..{len(steps) - 1}）",
                code="AGENT_JOB_STEP_INDEX_OOB",
            )
        entry = dict(steps[step_index]) if isinstance(steps[step_index], dict) else {
            "name": str(steps[step_index]),
            "status": "pending",
        }
        if status is not None:
            entry["status"] = str(status)
        if _output_set:
            entry["output"] = output
        steps[step_index] = entry
        job.steps = steps
        self.db.commit()
        self.db.refresh(job)
        return self._to_dict(job)


__all__ = [
    "AgentJobService",
    "TERMINAL_STATES",
    "ALL_STATES",
]
