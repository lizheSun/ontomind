"""Tool approval service with optimistic locking."""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.db.models.agent_platform_model import AgentRunStep, AgentToolApproval
from app.db.models.agent_run_model import AgentRun
from app.services.agent_platform.run import RunService
from app.services.agent_platform.version import _row


class ApprovalService:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        run_id: int,
        step_id: int | None,
        tool_name: str,
        arguments: dict[str, Any],
        user_id: int,
    ) -> dict[str, Any]:
        if not self.db.get(AgentRun, run_id):
            raise NotFoundException(f"Run 不存在: {run_id}")
        if step_id:
            step = self.db.get(AgentRunStep, step_id)
            if not step or step.run_id != run_id:
                raise ConflictException("Step 与 Run 不匹配", code="APPROVAL_STEP_MISMATCH")
        approval = AgentToolApproval(
            run_id=run_id,
            step_id=step_id,
            tool_name=tool_name,
            arguments=arguments,
            status="pending",
            lock_version=1,
            requested_by_user_id=user_id,
        )
        self.db.add(approval)
        self.db.flush()
        RunService(self.db)._append_event(
            run_id,
            "approval.requested",
            {"approval_id": approval.id, "tool_name": tool_name},
        )
        self.db.commit()
        self.db.refresh(approval)
        return _row(approval)

    def get(self, approval_id: int) -> dict[str, Any]:
        approval = self.db.get(AgentToolApproval, approval_id)
        if not approval:
            raise NotFoundException(f"审批不存在: {approval_id}")
        return _row(approval)

    def list(self, status: str | None = None) -> list[dict[str, Any]]:
        query = self.db.query(AgentToolApproval)
        if status:
            query = query.filter(AgentToolApproval.status == status)
        return [_row(row) for row in query.order_by(AgentToolApproval.id.desc()).all()]

    def decide(
        self,
        approval_id: int,
        decision: str,
        expected_version: int,
        user_id: int,
        reason: str | None = None,
    ) -> dict[str, Any]:
        target = "approved" if decision == "approve" else "rejected"
        now = datetime.now(timezone.utc)
        updated = (
            self.db.query(AgentToolApproval)
            .filter(
                AgentToolApproval.id == approval_id,
                AgentToolApproval.status == "pending",
                AgentToolApproval.lock_version == expected_version,
            )
            .update(
                {
                    AgentToolApproval.status: target,
                    AgentToolApproval.lock_version: expected_version + 1,
                    AgentToolApproval.decided_by_user_id: user_id,
                    AgentToolApproval.decided_at: now,
                    AgentToolApproval.decision_reason: reason,
                },
                synchronize_session=False,
            )
        )
        if updated != 1:
            exists = self.db.get(AgentToolApproval, approval_id)
            if not exists:
                raise NotFoundException(f"审批不存在: {approval_id}")
            raise ConflictException(
                "审批已被处理或版本已变化", code="APPROVAL_VERSION_CONFLICT"
            )
        self.db.flush()
        approval = self.db.get(AgentToolApproval, approval_id)
        RunService(self.db)._append_event(
            approval.run_id,
            f"approval.{target}",
            {"approval_id": approval.id, "lock_version": expected_version + 1},
        )
        self.db.commit()
        self.db.expire_all()
        return self.get(approval_id)
