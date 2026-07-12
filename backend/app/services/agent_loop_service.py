"""Agent Loop state machine engine (T53).

Pure in-process orchestrator for 5 loop strategies with pluggable
`step_fn` (produces a `LoopStep`) and optional `eval_fn` (returns an
`EvalResult`). The engine enforces the state machine:

    pending → running → evaluating → completed | failed | needs_review

and returns an immutable `LoopRunResult` snapshot.

Design notes
------------
* No DB / LLM coupling — callers inject callables. This keeps the engine
  testable and reusable by both the FastAPI service layer and future
  worker jobs.
* Transitions are validated via `agent_loop_schema.can_transition`;
  illegal transitions raise `BusinessException`.
* Eval verdicts drive the loop: PASS → completed, REVISE → run again
  (up to `max_revisions`), FAIL → failed. Once `max_iterations` or
  `max_revisions` is exhausted without a PASS the run ends in
  `needs_review` (not `failed` — the trace is preserved for humans).
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from app.core.exceptions import BusinessException
from app.schemas.agent_loop_schema import (
    EvalResult,
    LoopRequest,
    LoopRunResult,
    LoopState,
    LoopStep,
    LoopStrategy,
    can_transition,
)


StepFn = Callable[[LoopRequest, list[LoopStep], int, str], LoopStep]
"""Signature: (request, prior_steps, iteration, role) -> LoopStep."""

EvalFn = Callable[[LoopRequest, list[LoopStep]], EvalResult]
"""Signature: (request, steps_so_far) -> EvalResult."""


class AgentLoopEngine:
    """Deterministic state-machine driver for the 5 loop strategies."""

    _STRATEGIES: frozenset[str] = frozenset(
        {"single_shot", "react", "plan_execute", "evaluator_optimizer", "reflect"}
    )

    def __init__(self, step_fn: StepFn, eval_fn: Optional[EvalFn] = None) -> None:
        if step_fn is None:  # pragma: no cover - defensive
            raise BusinessException("step_fn is required")
        self._step_fn = step_fn
        self._eval_fn = eval_fn
        # mutable run state ------------------------------------------------
        self._state: LoopState = "pending"
        self._steps: list[LoopStep] = []
        self._eval_history: list[EvalResult] = []
        self._iterations_used = 0
        self._revisions_used = 0

    # ------------------------------------------------------------------ api
    @property
    def state(self) -> LoopState:
        return self._state

    def run(self, request: LoopRequest) -> LoopRunResult:
        """Execute the requested strategy and return the terminal snapshot."""
        if request.strategy not in self._STRATEGIES:
            raise BusinessException(f"unknown strategy: {request.strategy}")

        self._transition("running")
        try:
            final_output = self._dispatch(request)
        except BusinessException:
            raise
        except Exception as exc:  # noqa: BLE001 - engine boundary
            self._transition("failed")
            return self._snapshot(request, error=str(exc))

        if self._state not in ("completed", "failed", "needs_review"):
            # Strategy did not commit a terminal state → default to completed.
            self._transition("completed")
        return self._snapshot(request, final_output=final_output)

    # -------------------------------------------------------------- dispatch
    def _dispatch(self, request: LoopRequest) -> Optional[str]:
        strategy: LoopStrategy = request.strategy
        if strategy == "single_shot":
            return self._run_single_shot(request)
        if strategy == "react":
            return self._run_react(request)
        if strategy == "plan_execute":
            return self._run_plan_execute(request)
        if strategy == "evaluator_optimizer":
            return self._run_evaluator_optimizer(request)
        if strategy == "reflect":
            return self._run_reflect(request)
        raise BusinessException(f"unknown strategy: {strategy}")  # pragma: no cover

    # ---------------------------------------------------------- strategies
    def _run_single_shot(self, request: LoopRequest) -> Optional[str]:
        step = self._invoke_step(request, role="final")
        return self._evaluate_and_finalize(request, step.output)

    def _run_react(self, request: LoopRequest) -> Optional[str]:
        last_output: Optional[str] = None
        for _ in range(request.max_iterations):
            step = self._invoke_step(request, role="execute")
            last_output = step.output
            # A step whose action == "DONE" (or observation contains "DONE")
            # short-circuits the loop, matching the ReAct convention.
            if _is_done_marker(step):
                break
        return self._evaluate_and_finalize(request, last_output)

    def _run_plan_execute(self, request: LoopRequest) -> Optional[str]:
        # Plan once, then execute up to (max_iterations - 1) times.
        self._invoke_step(request, role="plan")
        last_output: Optional[str] = None
        remaining = max(1, request.max_iterations - 1)
        for _ in range(remaining):
            step = self._invoke_step(request, role="execute")
            last_output = step.output
            if _is_done_marker(step):
                break
        return self._evaluate_and_finalize(request, last_output)

    def _run_evaluator_optimizer(self, request: LoopRequest) -> Optional[str]:
        if not request.enable_eval or self._eval_fn is None:
            raise BusinessException(
                "evaluator_optimizer strategy requires enable_eval=True and eval_fn"
            )
        last_output: Optional[str] = None
        # Attempt 1 + up to `max_revisions` revisions.
        attempts = request.max_revisions + 1
        for attempt in range(attempts):
            role = "execute" if attempt == 0 else "revise"
            step = self._invoke_step(request, role=role)
            last_output = step.output
            if attempt > 0:
                self._revisions_used += 1

            self._transition("evaluating")
            verdict = self._eval_fn(request, list(self._steps))
            self._eval_history.append(verdict)

            if verdict.verdict == "PASS":
                self._transition("completed")
                return last_output
            if verdict.verdict == "FAIL":
                self._transition("failed")
                return last_output
            # REVISE — go back to running for another attempt (if any left).
            if attempt < attempts - 1:
                self._transition("running")

        # Ran out of revisions without a PASS/FAIL verdict.
        self._transition("needs_review")
        return last_output

    def _run_reflect(self, request: LoopRequest) -> Optional[str]:
        last_output: Optional[str] = None
        # Pair each execute with a reflect step until we hit the iteration cap.
        pairs = max(1, request.max_iterations // 2)
        for _ in range(pairs):
            exec_step = self._invoke_step(request, role="execute")
            last_output = exec_step.output
            reflect_step = self._invoke_step(request, role="reflect")
            if _is_done_marker(reflect_step):
                break
        return self._evaluate_and_finalize(request, last_output)

    # ------------------------------------------------------------ helpers
    def _invoke_step(self, request: LoopRequest, *, role: str) -> LoopStep:
        step = self._step_fn(request, list(self._steps), self._iterations_used, role)
        if step.iteration != self._iterations_used:
            # Force iteration counter to match engine truth — never trust caller.
            step = step.model_copy(update={"iteration": self._iterations_used})
        self._steps.append(step)
        self._iterations_used += 1
        return step

    def _evaluate_and_finalize(
        self, request: LoopRequest, last_output: Optional[str]
    ) -> Optional[str]:
        if not (request.enable_eval and self._eval_fn is not None):
            self._transition("completed")
            return last_output

        self._transition("evaluating")
        verdict = self._eval_fn(request, list(self._steps))
        self._eval_history.append(verdict)
        if verdict.verdict == "PASS":
            self._transition("completed")
        elif verdict.verdict == "FAIL":
            self._transition("failed")
        else:  # REVISE without an optimizer strategy → hand off to human.
            self._transition("needs_review")
        return last_output

    def _transition(self, dst: LoopState) -> None:
        if not can_transition(self._state, dst):
            raise BusinessException(
                f"illegal state transition: {self._state} → {dst}"
            )
        self._state = dst

    def _snapshot(
        self,
        request: LoopRequest,
        *,
        final_output: Optional[str] = None,
        error: Optional[str] = None,
    ) -> LoopRunResult:
        return LoopRunResult(
            strategy=request.strategy,
            state=self._state,
            goal=request.goal,
            steps=list(self._steps),
            eval_history=list(self._eval_history),
            final_output=final_output,
            error=error,
            iterations_used=self._iterations_used,
            revisions_used=self._revisions_used,
        )


def _is_done_marker(step: LoopStep) -> bool:
    """React/reflect convention: an action or observation of DONE stops the loop."""
    for field in (step.action, step.observation, step.output):
        if field and "DONE" in field.upper():
            return True
    return False


__all__ = [
    "AgentLoopEngine",
    "StepFn",
    "EvalFn",
]
