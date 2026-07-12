"""Persistent Run service and AgentLoopEngine adapter."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.db.models.agent_platform_model import (
    AgentDeployment,
    AgentRunEvent,
    AgentRunStep,
    AgentSession,
    AgentVersion,
)
from app.db.models.agent_run_model import AgentRun
from app.schemas.agent_loop_schema import EvalResult, LoopRequest, LoopStep
from app.services.agent_loop_service import AgentLoopEngine


class RunService:
    TERMINAL = {"completed", "failed", "cancelled", "needs_review"}

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        version_id: int,
        deployment_id: int | None,
        session_id: int | None,
        strategy: str,
        input_data: dict[str, Any],
        user_id: int,
        kind: str = "chat",
        parent_run_id: int | None = None,
        attempt: int = 1,
        auto_commit: bool = True,
    ) -> dict[str, Any]:
        version = self.db.get(AgentVersion, version_id)
        if not version:
            raise NotFoundException(f"AgentVersion 不存在: {version_id}")
        if deployment_id:
            deployment = self.db.get(AgentDeployment, deployment_id)
            if not deployment or deployment.agent_version_id != version_id:
                raise ConflictException("部署与版本不匹配", code="RUN_DEPLOYMENT_MISMATCH")
        if session_id:
            session = self.db.get(AgentSession, session_id)
            if not session or session.agent_id != version.agent_id:
                raise ConflictException("Session 与 Agent 不匹配", code="RUN_SESSION_MISMATCH")
        run = AgentRun(
            agent_id=version.agent_id,
            agent_version_id=version.id,
            deployment_id=deployment_id,
            session_id=session_id,
            owner_user_id=user_id,
            run_name=f"agent-{version.agent_id}-run",
            status="queued",
            strategy=strategy,
            kind=kind,
            parent_run_id=parent_run_id,
            attempt=attempt,
            goal=str(input_data.get("goal") or input_data.get("prompt") or ""),
            input=input_data,
            state_version=1,
        )
        self.db.add(run)
        self.db.flush()
        self._append_event(run.id, "run.queued", {"status": "queued"})
        if auto_commit:
            self.db.commit()
            self.db.refresh(run)
        else:
            self.db.flush()
        return self._run_dict(run)

    def get_model(self, run_id: int) -> AgentRun:
        run = self.db.get(AgentRun, run_id)
        if not run:
            raise NotFoundException(f"Run 不存在: {run_id}")
        return run

    def get(self, run_id: int) -> dict[str, Any]:
        return self._run_dict(self.get_model(run_id))

    def list(self, user_id: int | None = None) -> list[dict[str, Any]]:
        query = self.db.query(AgentRun)
        if user_id is not None:
            query = query.filter(AgentRun.owner_user_id == user_id)
        return [self._run_dict(row) for row in query.order_by(AgentRun.id.desc()).all()]

    def control(
        self, run_id: int, action: str, expected_version: int | None = None
    ) -> dict[str, Any]:
        if action == "start":
            return self.execute(run_id, expected_version)
        if action == "pause":
            run = self.get_model(run_id)
            if run.kind != "job":
                raise ConflictException(
                    "仅 checkpoint-safe Job Run 支持暂停",
                    code="RUN_PAUSE_NOT_SUPPORTED",
                )
            return self._transition(
                run_id,
                {"running"},
                "paused",
                expected_version,
                "run.paused",
            )
        if action == "resume":
            return self._transition(
                run_id,
                {"paused"},
                "running",
                expected_version,
                "run.resumed",
            )
        if action == "cancel":
            return self._transition(
                run_id,
                {"queued", "pending", "running", "paused", "awaiting_approval"},
                "cancelled",
                expected_version,
                "run.cancelled",
                terminal=True,
            )
        if action == "retry":
            source = self.get_model(run_id)
            self._check_expected(source, expected_version)
            if source.status not in {"failed", "cancelled", "needs_review"}:
                raise ConflictException(
                    f"Run 当前状态不能重试: {source.status}",
                    code="INVALID_RUN_TRANSITION",
                )
            return self.create(
                version_id=source.agent_version_id,
                deployment_id=source.deployment_id,
                session_id=source.session_id,
                strategy=source.strategy or "single_shot",
                kind=source.kind or "chat",
                input_data=source.input or {},
                user_id=source.owner_user_id,
                parent_run_id=source.parent_run_id or source.id,
                attempt=(source.attempt or 1) + 1,
            )
        raise ConflictException(f"未知 Run 控制动作: {action}", code="UNKNOWN_RUN_ACTION")

    def execute(
        self, run_id: int, expected_version: int | None = None
    ) -> dict[str, Any]:
        """优先走 OpenCode 流式执行；测试 / Loop 策略走 stub。"""
        run = self.get_model(run_id)
        if run.status not in {"queued", "pending"}:
            raise ConflictException(
                f"Run 当前状态不能启动: {run.status}", code="INVALID_RUN_TRANSITION"
            )
        prompt = str((run.input or {}).get("prompt") or (run.input or {}).get("goal") or "")
        force_stub = bool((run.input or {}).get("force_stub")) or prompt.startswith("__stub__")
        if (
            force_stub
            or not run.agent_version_id
            or (run.strategy or "") == "evaluator_optimizer"
            or (run.kind or "chat") != "chat"
        ):
            return self.execute_stub(run_id, expected_version)

        from app.services.agent_platform.opencode_chat import run_coroutine

        return run_coroutine(self.execute_opencode_streaming(run_id, expected_version))

    async def execute_opencode_streaming(
        self, run_id: int, expected_version: int | None = None
    ) -> dict[str, Any]:
        """按行消费 OpenCode JSONL，实时落库 Run 事件供 SSE 推送。"""
        from app.services.agent_platform.opencode_chat import (
            OpenCodeChatService,
            map_opencode_event,
            parse_opencode_output,
        )

        run = self.get_model(run_id)
        if run.status not in {"queued", "pending"}:
            raise ConflictException(
                f"Run 当前状态不能启动: {run.status}", code="INVALID_RUN_TRANSITION"
            )
        self._check_expected(run, expected_version)
        prompt = str((run.input or {}).get("prompt") or (run.input or {}).get("goal") or "")
        version_id = run.agent_version_id
        if not version_id:
            raise ConflictException("Run 缺少 agent_version_id", code="RUN_VERSION_REQUIRED")

        updated = (
            self.db.query(AgentRun)
            .filter(
                AgentRun.id == run_id,
                AgentRun.status.in_(("queued", "pending")),
                AgentRun.state_version == run.state_version,
            )
            .update(
                {
                    AgentRun.status: "running",
                    AgentRun.started_at: datetime.now(timezone.utc),
                    AgentRun.state_version: run.state_version + 1,
                },
                synchronize_session=False,
            )
        )
        if updated != 1:
            self.db.rollback()
            raise ConflictException("Run 状态已变化", code="RUN_VERSION_CONFLICT")
        self.db.expire_all()
        run = self.get_model(run_id)
        self._append_event(
            run.id,
            "run.started",
            {"strategy": run.strategy, "provider": "opencode", "streaming": True},
            commit=True,
        )

        assistant_message_id = f"assistant-{run_id}"
        text_state: dict[str, str] = {}
        started = {"message": False}
        stderr = ""
        exit_code = 0
        meta: dict[str, Any] = {"provider": "opencode"}
        raw_lines: list[str] = []

        try:
            chat = OpenCodeChatService(self.db)
            async for item in chat.stream_prompt(
                version_id=version_id,
                prompt=prompt,
                timeout_seconds=180.0,
            ):
                kind = item.get("kind")
                if kind == "line":
                    line = str(item.get("line") or "")
                    raw_lines.append(line)
                    try:
                        raw = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(raw, dict):
                        continue
                    mapped = map_opencode_event(
                        raw,
                        assistant_message_id=assistant_message_id,
                        text_state=text_state,
                        started=started,
                    )
                    for event_type, payload in mapped:
                        self._append_event(run_id, event_type, payload, commit=True)
                    if item.get("meta"):
                        meta.update(
                            {
                                "cli_path": item["meta"].get("cli_path"),
                                "cwd": item["meta"].get("cwd"),
                                "node_id": item["meta"].get("node_id"),
                            }
                        )
                elif kind == "stderr":
                    stderr = str(item.get("text") or "")
                elif kind == "exit":
                    exit_code = int(item.get("code") or 0)

            reply = "\n".join(v for v in text_state.values() if v).strip()
            if not reply:
                reply = parse_opencode_output("\n".join(raw_lines))
            if not reply:
                raise RuntimeError(
                    (stderr.strip() or f"OpenCode 无输出 (exit={exit_code})")[:2000]
                )

            run = self.get_model(run_id)
            if started["message"]:
                self._persist_assistant_message(run, reply, source="opencode")
                self._append_event(
                    run_id,
                    "message.completed",
                    {
                        "message_id": assistant_message_id,
                        "role": "assistant",
                    },
                    commit=False,
                )
            else:
                self._emit_assistant_reply(run, reply, source="opencode")

            run = self.get_model(run_id)
            run.status = "completed"
            run.output = {
                "final_output": reply,
                "exit_code": exit_code,
                "stderr": stderr[:1000],
                **meta,
            }
            run.error_message = None
            run.state_version += 1
            run.completed_at = datetime.now(timezone.utc)
            self._append_event(
                run.id,
                "run.completed",
                {"status": "completed", "output": run.output, "error": None},
                commit=False,
            )
            self.db.commit()
            self.db.refresh(run)
            return self._run_dict(run)
        except Exception as exc:
            run = self.get_model(run_id)
            error_reply = (
                "❌ 调用本机 OpenCode 失败。\n\n"
                f"原因：{exc}\n\n"
                "请确认：\n"
                "1. 已安装 opencode（`which opencode`）\n"
                "2. 资源管理中本机节点在线，且 Agent 已绑定 OpenCode 容器\n"
                "3. `~/.config/opencode` 可读写\n"
            )
            if run.status == "running":
                if not started["message"]:
                    self._emit_assistant_reply(run, error_reply, source="opencode_error")
                else:
                    self._append_event(
                        run_id,
                        "message.delta",
                        {
                            "message_id": assistant_message_id,
                            "role": "assistant",
                            "delta": f"\n\n{error_reply}",
                        },
                        commit=False,
                    )
                    self._persist_assistant_message(
                        run,
                        ("\n".join(text_state.values()) + f"\n\n{error_reply}").strip(),
                        source="opencode_error",
                    )
                    self._append_event(
                        run_id,
                        "message.completed",
                        {"message_id": assistant_message_id, "role": "assistant"},
                        commit=False,
                    )
                run = self.get_model(run_id)
                run.status = "failed"
                run.output = {
                    "final_output": error_reply,
                    "provider": "opencode_error",
                    "error": str(exc)[:1000],
                }
                run.error_message = str(exc)[:1000]
                run.state_version += 1
                run.completed_at = datetime.now(timezone.utc)
                self._append_event(
                    run.id,
                    "run.failed",
                    {
                        "status": "failed",
                        "output": run.output,
                        "error": run.error_message,
                    },
                    commit=False,
                )
                self.db.commit()
                self.db.refresh(run)
            return self._run_dict(run)

    def execute_stub(
        self, run_id: int, expected_version: int | None = None
    ) -> dict[str, Any]:
        """Minimal deterministic adapter for single_shot/evaluator_optimizer tests."""
        run = self.get_model(run_id)
        if run.status not in {"queued", "pending"}:
            raise ConflictException(
                f"Run 当前状态不能启动: {run.status}", code="INVALID_RUN_TRANSITION"
            )
        self._check_expected(run, expected_version)
        updated = (
            self.db.query(AgentRun)
            .filter(
                AgentRun.id == run_id,
                AgentRun.status.in_(("queued", "pending")),
                AgentRun.state_version == run.state_version,
            )
            .update(
                {
                    AgentRun.status: "running",
                    AgentRun.started_at: datetime.now(timezone.utc),
                    AgentRun.state_version: run.state_version + 1,
                },
                synchronize_session=False,
            )
        )
        if updated != 1:
            self.db.rollback()
            raise ConflictException("Run 状态已变化", code="RUN_VERSION_CONFLICT")
        self.db.expire_all()
        run = self.get_model(run_id)
        self._append_event(run.id, "run.started", {"strategy": run.strategy})
        self.db.flush()

        eval_count = 0

        def step_fn(request: LoopRequest, prior: list[LoopStep], iteration: int, role: str) -> LoopStep:
            prompt = request.context.get("prompt") or request.goal
            output = f"{role}:{prompt}"
            return LoopStep(iteration=iteration, role=role, output=output)

        def eval_fn(_request: LoopRequest, _steps: list[LoopStep]) -> EvalResult:
            nonlocal eval_count
            eval_count += 1
            if eval_count == 1:
                return EvalResult(verdict="REVISE", score=0.5, feedback="stub revision")
            return EvalResult(verdict="PASS", score=1.0, feedback="stub pass")

        strategy = run.strategy or "single_shot"
        request = LoopRequest(
            strategy=strategy,
            goal=str((run.input or {}).get("prompt") or (run.input or {}).get("goal") or "run"),
            enable_eval=strategy == "evaluator_optimizer",
            max_revisions=1,
            context=run.input or {},
        )
        try:
            engine = AgentLoopEngine(
                step_fn,
                eval_fn if strategy == "evaluator_optimizer" else None,
            )
            result = engine.run(request)
            for index, step in enumerate(result.steps, start=1):
                row = AgentRunStep(
                    run_id=run.id,
                    sequence=index,
                    role=step.role,
                    status="completed",
                    output={"text": step.output},
                    started_at=step.timestamp,
                    completed_at=step.timestamp,
                )
                self.db.add(row)
                self._append_event(
                    run.id,
                    "step.completed",
                    {"step_sequence": index, "role": step.role, "output": step.output},
                )
            for verdict in result.eval_history:
                self._append_event(
                    run.id,
                    "eval.result",
                    verdict.model_dump(),
                )
            final_output = self._format_reply(run, result.final_output or "")
            run.status = result.state
            run.output = {
                "final_output": final_output,
                "iterations_used": result.iterations_used,
                "revisions_used": result.revisions_used,
            }
            run.error_message = result.error
            if run.status == "completed" and final_output:
                self._emit_assistant_reply(run, final_output)
        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)
        run.state_version += 1
        run.completed_at = datetime.now(timezone.utc)
        self._append_event(
            run.id,
            f"run.{run.status}",
            {"status": run.status, "output": run.output, "error": run.error_message},
        )
        self.db.commit()
        self.db.refresh(run)
        return self._run_dict(run)

    def _format_reply(self, run: AgentRun, raw_output: str) -> str:
        prompt = str((run.input or {}).get("prompt") or (run.input or {}).get("goal") or "")
        version = self.db.get(AgentVersion, run.agent_version_id) if run.agent_version_id else None
        config = (version.config or {}) if version else {}
        role = config.get("role") if isinstance(config.get("role"), dict) else {}
        objective = config.get("objective") if isinstance(config.get("objective"), dict) else {}
        agent_name = objective.get("name") or "Agent"
        system_hint = str(role.get("system_prompt") or "").strip()
        # Stub 执行器：产出可读回复，接入真实模型后替换为 LLM 流式输出
        lines = [
            f"【{agent_name}】",
            "",
            f"已收到请求：{prompt}" if prompt else "已收到请求。",
            "",
        ]
        if system_hint:
            lines.append(f"角色设定：{system_hint[:180]}{'…' if len(system_hint) > 180 else ''}")
            lines.append("")
        cleaned = raw_output.strip()
        if cleaned and not cleaned.startswith("worker:") and not cleaned.startswith("assistant:"):
            lines.append(cleaned)
        else:
            lines.append(
                "当前为平台 stub 执行器，已完成 Loop 步骤并返回本条回复。"
                "接入真实模型 / OpenCode 后，这里将变为流式生成内容。"
            )
        return "\n".join(lines).strip()

    def _persist_assistant_message(
        self, run: AgentRun, content: str, *, source: str = "opencode"
    ) -> str | None:
        """将会话助手消息落库（不重复发 message.delta）。"""
        if run.session_id is None:
            return None
        from app.services.agent_platform.session import SessionService

        session = self.db.get(AgentSession, run.session_id)
        actor_id = run.owner_user_id or (session.owner_user_id if session else None)
        saved = SessionService(self.db).add_message(
            run.session_id,
            "assistant",
            content,
            {"source": source},
            actor_id if actor_id is not None else 0,
            content_type="markdown",
            run_id=run.id,
            auto_commit=False,
        )
        return str(saved["id"])

    def _emit_assistant_reply(
        self, run: AgentRun, content: str, *, source: str = "run_stub"
    ) -> None:
        message_id = f"assistant-{run.id}"
        saved_id = self._persist_assistant_message(run, content, source=source)
        if saved_id:
            message_id = saved_id
        self._append_event(
            run.id,
            "message.started",
            {"message_id": message_id, "role": "assistant", "content_type": "markdown"},
        )
        # 分块 delta，便于前端流式渲染（stub / 非流式路径）
        chunk_size = 48
        for index in range(0, len(content), chunk_size):
            self._append_event(
                run.id,
                "message.delta",
                {
                    "message_id": message_id,
                    "role": "assistant",
                    "delta": content[index : index + chunk_size],
                },
            )
        self._append_event(
            run.id,
            "message.completed",
            {"message_id": message_id, "role": "assistant"},
        )

    def _check_expected(
        self, run: AgentRun, expected_version: int | None
    ) -> None:
        if expected_version is not None and run.state_version != expected_version:
            raise ConflictException("Run 状态已变化", code="RUN_VERSION_CONFLICT")

    def _transition(
        self,
        run_id: int,
        allowed: set[str],
        target: str,
        expected_version: int | None,
        event_type: str,
        *,
        terminal: bool = False,
    ) -> dict[str, Any]:
        run = self.get_model(run_id)
        self._check_expected(run, expected_version)
        if run.status not in allowed:
            raise ConflictException(
                f"非法 Run 状态转换: {run.status} -> {target}",
                code="INVALID_RUN_TRANSITION",
            )
        values: dict[Any, Any] = {
            AgentRun.status: target,
            AgentRun.state_version: run.state_version + 1,
        }
        if terminal:
            values[AgentRun.completed_at] = datetime.now(timezone.utc)
        updated = (
            self.db.query(AgentRun)
            .filter(
                AgentRun.id == run_id,
                AgentRun.status == run.status,
                AgentRun.state_version == run.state_version,
            )
            .update(values, synchronize_session=False)
        )
        if updated != 1:
            self.db.rollback()
            raise ConflictException("Run 状态已变化", code="RUN_VERSION_CONFLICT")
        self.db.expire_all()
        run = self.get_model(run_id)
        self._append_event(run.id, event_type, {"status": target})
        self.db.commit()
        self.db.refresh(run)
        return self._run_dict(run)

    def events_after(self, run_id: int, last_event_id: int = 0) -> list[dict[str, Any]]:
        self.get_model(run_id)
        rows = (
            self.db.query(AgentRunEvent)
            .filter(
                AgentRunEvent.run_id == run_id,
                AgentRunEvent.sequence > last_event_id,
            )
            .order_by(AgentRunEvent.sequence)
            .all()
        )
        return [self._event_envelope(event) for event in rows]

    def _append_event(
        self,
        run_id: int,
        event_type: str,
        data: dict[str, Any],
        *,
        commit: bool = False,
    ) -> AgentRunEvent:
        sequence = (
            self.db.query(func.max(AgentRunEvent.sequence))
            .filter(AgentRunEvent.run_id == run_id)
            .scalar()
            or 0
        ) + 1
        event = AgentRunEvent(
            run_id=run_id,
            sequence=sequence,
            event_type=event_type,
            data=data,
            visibility="user",
        )
        self.db.add(event)
        self.db.flush()
        if commit:
            self.db.commit()
        return event

    @staticmethod
    def _run_dict(run: AgentRun) -> dict[str, Any]:
        return run.to_response_dict()

    @staticmethod
    def _event_envelope(event: AgentRunEvent) -> dict[str, Any]:
        timestamp = event.created_at.isoformat() if event.created_at else None
        if timestamp and timestamp.endswith("+00:00"):
            timestamp = f"{timestamp[:-6]}Z"
        return {
            "run_id": event.run_id,
            "sequence": event.sequence,
            "type": event.event_type,
            "timestamp": timestamp,
            "visibility": event.visibility,
            "payload": event.data or {},
        }
