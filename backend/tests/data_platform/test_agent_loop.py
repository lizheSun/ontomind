"""Tests for AgentLoopEngine (T53) — state machine + 5 strategies + eval hooks."""
from __future__ import annotations

from typing import Optional

import pytest

from app.core.exceptions import BusinessException
from app.schemas.agent_loop_schema import (
    EvalResult,
    LoopRequest,
    LoopStep,
    can_transition,
)
from app.services.agent_loop_service import AgentLoopEngine


# --- helpers ---------------------------------------------------------------
def _make_step_fn(sequence: Optional[list[dict]] = None):
    """Return a step_fn that yields scripted steps or a default execute step."""
    scripted = list(sequence or [])
    calls: list[dict] = []

    def step_fn(request, prior_steps, iteration, role):
        calls.append({"iteration": iteration, "role": role})
        if scripted:
            spec = scripted.pop(0)
        else:
            spec = {}
        return LoopStep(
            iteration=iteration,
            role=spec.get("role", role),
            thought=spec.get("thought", f"thought-{iteration}"),
            action=spec.get("action"),
            observation=spec.get("observation"),
            output=spec.get("output", f"out-{iteration}"),
        )

    step_fn.calls = calls  # type: ignore[attr-defined]
    return step_fn


def _eval_fn_seq(verdicts: list[EvalResult]):
    q = list(verdicts)

    def eval_fn(request, steps):
        return q.pop(0)

    return eval_fn


def _pass(score: float = 1.0) -> EvalResult:
    return EvalResult(verdict="PASS", score=score, feedback="ok")


def _revise(score: float = 0.5) -> EvalResult:
    return EvalResult(verdict="REVISE", score=score, feedback="improve")


def _fail(score: float = 0.0) -> EvalResult:
    return EvalResult(verdict="FAIL", score=score, feedback="bad")


# --- schema / state machine ------------------------------------------------
def test_can_transition_matrix():
    assert can_transition("pending", "running") is True
    assert can_transition("running", "evaluating") is True
    assert can_transition("evaluating", "completed") is True
    assert can_transition("evaluating", "needs_review") is True
    assert can_transition("completed", "running") is False
    assert can_transition("failed", "running") is False
    assert can_transition("pending", "completed") is False


def test_eval_result_score_bounds():
    with pytest.raises(Exception):
        EvalResult(verdict="PASS", score=1.5, feedback="nope")
    with pytest.raises(Exception):
        EvalResult(verdict="PASS", score=-0.1, feedback="nope")
    r = EvalResult(verdict="PASS", score=0.5)
    assert r.feedback == ""  # None → ""


# --- single_shot -----------------------------------------------------------
def test_single_shot_completes_without_eval():
    engine = AgentLoopEngine(step_fn=_make_step_fn())
    req = LoopRequest(strategy="single_shot", goal="say hi", enable_eval=False)
    result = engine.run(req)
    assert result.state == "completed"
    assert result.iterations_used == 1
    assert result.eval_history == []
    assert result.final_output == "out-0"
    assert result.is_terminal is True


def test_single_shot_with_pass_eval():
    engine = AgentLoopEngine(
        step_fn=_make_step_fn(), eval_fn=_eval_fn_seq([_pass(0.9)])
    )
    req = LoopRequest(strategy="single_shot", goal="say hi")
    result = engine.run(req)
    assert result.state == "completed"
    assert len(result.eval_history) == 1
    assert result.eval_history[0].verdict == "PASS"


def test_single_shot_with_fail_eval_marks_failed():
    engine = AgentLoopEngine(step_fn=_make_step_fn(), eval_fn=_eval_fn_seq([_fail()]))
    req = LoopRequest(strategy="single_shot", goal="say hi")
    result = engine.run(req)
    assert result.state == "failed"


def test_single_shot_revise_without_optimizer_yields_needs_review():
    engine = AgentLoopEngine(step_fn=_make_step_fn(), eval_fn=_eval_fn_seq([_revise()]))
    req = LoopRequest(strategy="single_shot", goal="say hi")
    result = engine.run(req)
    assert result.state == "needs_review"


# --- react -----------------------------------------------------------------
def test_react_short_circuits_on_done_marker():
    fn = _make_step_fn(
        [
            {"action": "search", "observation": "found candidate"},
            {"action": "DONE", "output": "answer=42"},
        ]
    )
    engine = AgentLoopEngine(step_fn=fn)
    req = LoopRequest(strategy="react", goal="q", max_iterations=5, enable_eval=False)
    result = engine.run(req)
    assert result.state == "completed"
    assert result.iterations_used == 2
    assert result.final_output == "answer=42"


def test_react_hits_max_iterations_without_done():
    engine = AgentLoopEngine(step_fn=_make_step_fn())
    req = LoopRequest(strategy="react", goal="q", max_iterations=3, enable_eval=False)
    result = engine.run(req)
    assert result.state == "completed"
    assert result.iterations_used == 3


# --- plan_execute ----------------------------------------------------------
def test_plan_execute_emits_plan_then_execute_steps():
    fn = _make_step_fn()
    engine = AgentLoopEngine(step_fn=fn)
    req = LoopRequest(
        strategy="plan_execute", goal="q", max_iterations=4, enable_eval=False
    )
    result = engine.run(req)
    assert result.state == "completed"
    roles = [s.role for s in result.steps]
    assert roles[0] == "plan"
    assert roles[1:] == ["execute", "execute", "execute"]
    assert result.iterations_used == 4


# --- evaluator_optimizer ---------------------------------------------------
def test_evaluator_optimizer_passes_on_first_try():
    engine = AgentLoopEngine(
        step_fn=_make_step_fn(), eval_fn=_eval_fn_seq([_pass()])
    )
    req = LoopRequest(strategy="evaluator_optimizer", goal="q", max_revisions=2)
    result = engine.run(req)
    assert result.state == "completed"
    assert result.revisions_used == 0
    assert len(result.eval_history) == 1


def test_evaluator_optimizer_revises_then_passes():
    engine = AgentLoopEngine(
        step_fn=_make_step_fn(), eval_fn=_eval_fn_seq([_revise(), _pass()])
    )
    req = LoopRequest(strategy="evaluator_optimizer", goal="q", max_revisions=2)
    result = engine.run(req)
    assert result.state == "completed"
    assert result.revisions_used == 1
    assert result.iterations_used == 2
    assert [s.role for s in result.steps] == ["execute", "revise"]
    assert [e.verdict for e in result.eval_history] == ["REVISE", "PASS"]


def test_evaluator_optimizer_exhausts_revisions_needs_review():
    engine = AgentLoopEngine(
        step_fn=_make_step_fn(),
        eval_fn=_eval_fn_seq([_revise(), _revise(), _revise()]),
    )
    req = LoopRequest(strategy="evaluator_optimizer", goal="q", max_revisions=2)
    result = engine.run(req)
    assert result.state == "needs_review"
    assert result.revisions_used == 2
    assert len(result.eval_history) == 3


def test_evaluator_optimizer_fail_verdict_marks_failed():
    engine = AgentLoopEngine(
        step_fn=_make_step_fn(), eval_fn=_eval_fn_seq([_fail()])
    )
    req = LoopRequest(strategy="evaluator_optimizer", goal="q", max_revisions=3)
    result = engine.run(req)
    assert result.state == "failed"


def test_evaluator_optimizer_requires_eval_fn():
    engine = AgentLoopEngine(step_fn=_make_step_fn())  # no eval
    req = LoopRequest(strategy="evaluator_optimizer", goal="q")
    with pytest.raises(BusinessException):
        engine.run(req)


# --- reflect ---------------------------------------------------------------
def test_reflect_pairs_execute_and_reflect():
    engine = AgentLoopEngine(step_fn=_make_step_fn())
    req = LoopRequest(strategy="reflect", goal="q", max_iterations=4, enable_eval=False)
    result = engine.run(req)
    assert result.state == "completed"
    roles = [s.role for s in result.steps]
    # max_iterations=4 → 2 pairs of (execute, reflect)
    assert roles == ["execute", "reflect", "execute", "reflect"]


def test_reflect_stops_when_reflection_says_done():
    fn = _make_step_fn(
        [
            {"role": "execute", "output": "attempt-1"},
            {"role": "reflect", "observation": "looks good — DONE"},
            {"role": "execute", "output": "should-not-run"},
        ]
    )
    engine = AgentLoopEngine(step_fn=fn)
    req = LoopRequest(strategy="reflect", goal="q", max_iterations=6, enable_eval=False)
    result = engine.run(req)
    assert result.state == "completed"
    assert result.iterations_used == 2  # stopped after first reflect


# --- misc / error paths ----------------------------------------------------
def test_unknown_strategy_rejected():
    engine = AgentLoopEngine(step_fn=_make_step_fn())
    with pytest.raises(Exception):
        # Bypass Literal by casting through Pydantic-agnostic dict.
        LoopRequest.model_validate({"strategy": "bogus", "goal": "q"})


def test_step_fn_exception_transitions_to_failed():
    def bad_step(*args, **kwargs):
        raise RuntimeError("boom")

    engine = AgentLoopEngine(step_fn=bad_step)
    req = LoopRequest(strategy="single_shot", goal="q", enable_eval=False)
    result = engine.run(req)
    assert result.state == "failed"
    assert result.error is not None and "boom" in result.error


def test_engine_forces_iteration_number():
    # step_fn returns wrong iteration; engine must overwrite.
    def bad_iter(request, prior_steps, iteration, role):
        return LoopStep(iteration=999, role=role, output="x")

    engine = AgentLoopEngine(step_fn=bad_iter)
    req = LoopRequest(strategy="single_shot", goal="q", enable_eval=False)
    result = engine.run(req)
    assert result.state == "completed"
    assert result.steps[0].iteration == 0
