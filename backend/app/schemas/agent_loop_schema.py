"""Agent Loop state machine engine — Pydantic schemas (T53).

Provides a pure in-process state machine for orchestrating agent loops.
The engine is decoupled from any DB / LLM binding: callers supply a
`step_fn` and (optionally) an `eval_fn`; the engine drives transitions.

Strategies:
    - single_shot        : one step, evaluate once
    - react              : Thought/Action/Observation until DONE or max_iter
    - plan_execute       : one plan step then sequential execute steps
    - evaluator_optimizer: run → eval → revise until PASS / budget out
    - reflect            : execute → self-reflection → refine

Eval hook contract:
    verdict ∈ {PASS, REVISE, FAIL}, score ∈ [0, 1], feedback: str.

State machine:
    pending → running → evaluating → completed | failed | needs_review
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


LoopStrategy = Literal[
    "single_shot",
    "react",
    "plan_execute",
    "evaluator_optimizer",
    "reflect",
]

LoopState = Literal[
    "pending",
    "running",
    "evaluating",
    "completed",
    "failed",
    "needs_review",
]

EvalVerdict = Literal["PASS", "REVISE", "FAIL"]


# --- allowed transitions (defensive; enforced in engine) --------------------
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"running", "failed"},
    "running": {"evaluating", "completed", "failed"},
    "evaluating": {"running", "completed", "failed", "needs_review"},
    "completed": set(),
    "failed": set(),
    "needs_review": set(),
}


def can_transition(src: str, dst: str) -> bool:
    """Return True iff `src → dst` is an allowed state transition."""
    return dst in _ALLOWED_TRANSITIONS.get(src, set())


# --- eval hook contract -----------------------------------------------------
class EvalResult(BaseModel):
    """Verdict from an eval hook run."""

    verdict: EvalVerdict
    score: float = Field(..., ge=0.0, le=1.0)
    feedback: str = ""

    @field_validator("feedback", mode="before")
    @classmethod
    def _feedback_none_to_empty(cls, v: Any) -> Any:
        return "" if v is None else v


# --- step trace record ------------------------------------------------------
class LoopStep(BaseModel):
    """One iteration of the loop — thought/action/observation trace."""

    iteration: int = Field(..., ge=0)
    role: Literal["plan", "execute", "reflect", "revise", "final"] = "execute"
    thought: Optional[str] = None
    action: Optional[str] = None
    observation: Optional[str] = None
    output: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --- request / result -------------------------------------------------------
class LoopRequest(BaseModel):
    """Input to `AgentLoopEngine.run`."""

    strategy: LoopStrategy
    goal: str = Field(..., min_length=1)
    max_iterations: int = Field(default=5, ge=1, le=50)
    enable_eval: bool = True
    max_revisions: int = Field(default=2, ge=0, le=10)
    context: dict[str, Any] = Field(default_factory=dict)


class LoopRunResult(BaseModel):
    """Terminal snapshot returned by the engine."""

    strategy: LoopStrategy
    state: LoopState
    goal: str
    steps: list[LoopStep] = Field(default_factory=list)
    eval_history: list[EvalResult] = Field(default_factory=list)
    final_output: Optional[str] = None
    error: Optional[str] = None
    iterations_used: int = 0
    revisions_used: int = 0

    @property
    def is_terminal(self) -> bool:
        return self.state in ("completed", "failed", "needs_review")
