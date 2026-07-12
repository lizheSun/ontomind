"""T55 tests: AgentJobService lifecycle + agent-looper /jobs API endpoints.

Covers:
- Service CRUD (create/get/list/update/delete).
- State machine transitions (pending → running → paused → running → completed).
- Terminal state guards (can't restart cancelled/failed).
- Owner permission enforcement.
- advance_step + progress recomputation.
- update_step_output metadata.
- API endpoints: POST /jobs, GET /jobs, GET/PUT/DELETE /jobs/{id},
  POST /jobs/{id}/transition.

Uses a MINIMAL FastAPI app that mounts only the agent-looper test router, so
unrelated pre-existing broken imports in the rest of `app.main` do not block
T55 verification.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.api.v1.agent_looper import test as agent_looper_test_router
from app.api.v1.auth import get_current_user_id
from app.core.exceptions import (
    BusinessException,
    NotFoundException,
    PermissionException,
    ValidationException,
    add_exception_handlers,
)
from app.db.models.agent_model import Agent
from app.db.models.agent_run_job_model import AgentRunJob
from app.db.models.user_model import User
from app.db.session import get_db
from app.services.agent_job_service import ALL_STATES, AgentJobService, TERMINAL_STATES


# ---------- helpers -----------------------------------------------------


def _mk_user(session, username: str = "t55u") -> User:
    u = User(
        username=username,
        email=f"{username}@ex.io",
        password_hash="x",
        is_active=True,
        is_superuser=False,
    )
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


def _mk_agent(session, name: str = "t55-agent") -> Agent:
    a = Agent(name=name, type="custom_looper")
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def _build_app(isolated_engine, user_id: int) -> FastAPI:
    """Minimal FastAPI wiring the agent-looper test router with fake auth."""
    app = FastAPI()
    add_exception_handlers(app)
    app.include_router(
        agent_looper_test_router.router, prefix="/api/v1/agent-looper"
    )
    SessionLocal = sessionmaker(
        bind=isolated_engine, autoflush=False, expire_on_commit=False, future=True
    )

    def _override_db():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    def _override_user():
        return user_id

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user_id] = _override_user
    return app


# ---------- service-level: create + lifecycle --------------------------


def test_create_defaults_and_infer_total_steps(db_session):
    user = _mk_user(db_session, "s1")
    agent = _mk_agent(db_session, "s1-agent")
    svc = AgentJobService(db_session)

    job = svc.create(
        agent_id=agent.id,
        name="etl-1",
        user_id=user.id,
        steps=[{"name": "extract"}, "transform", {"name": "load"}],
        input_data={"source": "mysql://x"},
    )
    assert job["status"] == "pending"
    assert job["progress"] == 0
    assert job["current_step"] == 0
    assert job["total_steps"] == 3
    assert [s["name"] for s in job["steps"]] == ["extract", "transform", "load"]
    assert job["input_data"] == {"source": "mysql://x"}
    assert job["created_by_user_id"] == user.id
    assert job["started_at"] is None and job["finished_at"] is None


def test_create_requires_valid_name_and_agent(db_session):
    user = _mk_user(db_session, "s2")
    agent = _mk_agent(db_session, "s2-agent")
    svc = AgentJobService(db_session)

    with pytest.raises(ValidationException):
        svc.create(agent_id=agent.id, name=" ", user_id=user.id)

    with pytest.raises(NotFoundException):
        svc.create(agent_id=99999, name="no-agent", user_id=user.id)


def test_full_lifecycle_pending_running_paused_completed(db_session):
    user = _mk_user(db_session, "s3")
    agent = _mk_agent(db_session, "s3-agent")
    svc = AgentJobService(db_session)

    job = svc.create(
        agent_id=agent.id,
        name="lc",
        user_id=user.id,
        steps=["a", "b", "c", "d"],
    )
    jid = job["id"]

    started = svc.start(jid, user.id)
    assert started["status"] == "running"
    assert started["started_at"] is not None

    paused = svc.pause(jid, user.id)
    assert paused["status"] == "paused"

    resumed = svc.resume(jid, user.id)
    assert resumed["status"] == "running"

    stepped = svc.advance_step(jid, user.id)
    assert stepped["current_step"] == 1
    assert stepped["progress"] == 25
    stepped = svc.advance_step(jid, user.id)
    assert stepped["current_step"] == 2
    assert stepped["progress"] == 50

    completed = svc.complete(jid, user.id, output_data={"rows": 42})
    assert completed["status"] == "completed"
    assert completed["progress"] == 100
    assert completed["current_step"] == completed["total_steps"]
    assert completed["output_data"] == {"rows": 42}
    assert completed["finished_at"] is not None


def test_illegal_transition_and_terminal_guard(db_session):
    user = _mk_user(db_session, "s4")
    agent = _mk_agent(db_session, "s4-agent")
    svc = AgentJobService(db_session)

    job = svc.create(agent_id=agent.id, name="illegal", user_id=user.id)
    jid = job["id"]

    with pytest.raises(ValidationException):
        svc.transition(jid, user.id, "completed")

    with pytest.raises(ValidationException):
        svc.pause(jid, user.id)

    svc.start(jid, user.id)
    svc.complete(jid, user.id)

    with pytest.raises(ValidationException):
        svc.start(jid, user.id)
    with pytest.raises(ValidationException):
        svc.cancel(jid, user.id)


def test_fail_and_cancel_paths(db_session):
    user = _mk_user(db_session, "s5")
    agent = _mk_agent(db_session, "s5-agent")
    svc = AgentJobService(db_session)

    j_fail = svc.create(agent_id=agent.id, name="f", user_id=user.id)
    svc.start(j_fail["id"], user.id)
    failed = svc.fail(j_fail["id"], user.id, error_message="upstream boom")
    assert failed["status"] == "failed"
    assert failed["error_message"] == "upstream boom"
    assert failed["finished_at"] is not None

    j_cancel = svc.create(agent_id=agent.id, name="c", user_id=user.id)
    cancelled = svc.cancel(j_cancel["id"], user.id)
    assert cancelled["status"] == "cancelled"
    assert cancelled["finished_at"] is not None


def test_owner_permission_and_metadata_update(db_session):
    owner = _mk_user(db_session, "s6owner")
    other = _mk_user(db_session, "s6other")
    agent = _mk_agent(db_session, "s6-agent")
    svc = AgentJobService(db_session)

    job = svc.create(
        agent_id=agent.id,
        name="perm",
        user_id=owner.id,
        steps=["a", "b"],
    )
    jid = job["id"]

    with pytest.raises(PermissionException):
        svc.start(jid, other.id)
    with pytest.raises(PermissionException):
        svc.update(jid, other.id, name="hack")
    with pytest.raises(PermissionException):
        svc.delete(jid, other.id)

    updated = svc.update(
        jid,
        owner.id,
        name="renamed",
        steps=["x", "y", "z"],
        total_steps=3,
    )
    assert updated["name"] == "renamed"
    assert updated["total_steps"] == 3
    assert [s["name"] for s in updated["steps"]] == ["x", "y", "z"]


def test_update_step_output_and_running_delete_guard(db_session):
    user = _mk_user(db_session, "s7")
    agent = _mk_agent(db_session, "s7-agent")
    svc = AgentJobService(db_session)

    job = svc.create(
        agent_id=agent.id,
        name="upd",
        user_id=user.id,
        steps=["read", "write"],
    )
    jid = job["id"]
    updated = svc.update_step_output(
        jid, user.id, 0, status="success", output={"rows": 100}, _output_set=True
    )
    assert updated["steps"][0]["status"] == "success"
    assert updated["steps"][0]["output"] == {"rows": 100}

    with pytest.raises(ValidationException):
        svc.update_step_output(jid, user.id, 5, status="success")

    svc.start(jid, user.id)
    with pytest.raises(BusinessException):
        svc.delete(jid, user.id)

    svc.pause(jid, user.id)
    svc.delete(jid, user.id)
    assert db_session.query(AgentRunJob).filter_by(id=jid).first() is None


def test_advance_step_bounds_and_state_guards(db_session):
    user = _mk_user(db_session, "s8")
    agent = _mk_agent(db_session, "s8-agent")
    svc = AgentJobService(db_session)

    job = svc.create(
        agent_id=agent.id, name="adv", user_id=user.id, total_steps=2
    )
    jid = job["id"]
    with pytest.raises(BusinessException):
        svc.advance_step(jid, user.id)

    svc.start(jid, user.id)
    svc.advance_step(jid, user.id)
    svc.advance_step(jid, user.id)
    with pytest.raises(BusinessException):
        svc.advance_step(jid, user.id)


def test_list_filters(db_session):
    user = _mk_user(db_session, "s9")
    other = _mk_user(db_session, "s9other")
    agent1 = _mk_agent(db_session, "s9-a1")
    agent2 = _mk_agent(db_session, "s9-a2")
    svc = AgentJobService(db_session)

    a = svc.create(agent_id=agent1.id, name="a", user_id=user.id)
    b = svc.create(agent_id=agent1.id, name="b", user_id=user.id)
    c = svc.create(agent_id=agent2.id, name="c", user_id=user.id)
    d = svc.create(agent_id=agent1.id, name="d", user_id=other.id)

    svc.start(a["id"], user.id)
    svc.cancel(b["id"], user.id)

    mine = svc.list(user_id=user.id)
    assert {j["id"] for j in mine} == {a["id"], b["id"], c["id"]}

    only_a1 = svc.list(user_id=user.id, agent_id=agent1.id)
    assert {j["id"] for j in only_a1} == {a["id"], b["id"]}

    cancelled = svc.list(user_id=user.id, status="cancelled")
    assert {j["id"] for j in cancelled} == {b["id"]}

    all_including_others = svc.list(user_id=None)
    assert {j["id"] for j in all_including_others} == {
        a["id"], b["id"], c["id"], d["id"],
    }

    with pytest.raises(ValidationException):
        svc.list(user_id=user.id, status="bogus")


# ---------- API endpoints ---------------------------------------------


def test_api_jobs_crud_and_transition(isolated_engine, db_session):
    user = _mk_user(db_session, "api1")
    agent = _mk_agent(db_session, "api1-agent")
    app = _build_app(isolated_engine, user.id)

    with TestClient(app) as c:
        r = c.post(
            "/api/v1/agent-looper/jobs",
            json={
                "agent_id": agent.id,
                "name": "job-api",
                "steps": ["read", "write"],
                "input_data": {"table": "orders"},
            },
        )
        assert r.status_code == 200, r.text
        job = r.json()["data"]
        jid = job["id"]
        assert job["status"] == "pending"
        assert job["total_steps"] == 2

        r = c.get("/api/v1/agent-looper/jobs")
        assert r.status_code == 200
        assert any(j["id"] == jid for j in r.json()["data"])

        r = c.get(f"/api/v1/agent-looper/jobs/{jid}")
        assert r.status_code == 200
        assert r.json()["data"]["name"] == "job-api"

        r = c.put(
            f"/api/v1/agent-looper/jobs/{jid}",
            json={"name": "job-api-renamed"},
        )
        assert r.status_code == 200
        assert r.json()["data"]["name"] == "job-api-renamed"

        r = c.post(
            f"/api/v1/agent-looper/jobs/{jid}/transition",
            json={"action": "start"},
        )
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "running"

        r = c.post(
            f"/api/v1/agent-looper/jobs/{jid}/transition",
            json={"action": "advance_step"},
        )
        assert r.status_code == 200
        assert r.json()["data"]["current_step"] == 1
        assert r.json()["data"]["progress"] == 50

        r = c.post(
            f"/api/v1/agent-looper/jobs/{jid}/transition",
            json={"action": "complete", "output_data": {"rows": 7}},
        )
        assert r.status_code == 200
        done = r.json()["data"]
        assert done["status"] == "completed"
        assert done["progress"] == 100
        assert done["output_data"] == {"rows": 7}

        r = c.post(
            f"/api/v1/agent-looper/jobs/{jid}/transition",
            json={"action": "start"},
        )
        assert r.status_code == 422
        assert r.json()["detail"]["code"] == "AGENT_JOB_INVALID_TRANSITION"

        r = c.delete(f"/api/v1/agent-looper/jobs/{jid}")
        assert r.status_code == 200

        r = c.get(f"/api/v1/agent-looper/jobs/{jid}")
        assert r.status_code == 404


def test_api_jobs_owner_scope_and_unknown_action(isolated_engine, db_session):
    owner = _mk_user(db_session, "own")
    intruder = _mk_user(db_session, "intr")
    agent = _mk_agent(db_session, "scope-agent")

    app_owner = _build_app(isolated_engine, owner.id)
    with TestClient(app_owner) as c:
        r = c.post(
            "/api/v1/agent-looper/jobs",
            json={"agent_id": agent.id, "name": "owned"},
        )
        assert r.status_code == 200
        jid = r.json()["data"]["id"]

        r = c.post(
            f"/api/v1/agent-looper/jobs/{jid}/transition",
            json={"action": "warp"},
        )
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "AGENT_JOB_UNKNOWN_ACTION"

    app_intruder = _build_app(isolated_engine, intruder.id)
    with TestClient(app_intruder) as c:
        r = c.get("/api/v1/agent-looper/jobs")
        assert r.status_code == 200
        assert all(j["id"] != jid for j in r.json()["data"])

        r = c.post(
            f"/api/v1/agent-looper/jobs/{jid}/transition",
            json={"action": "start"},
        )
        assert r.status_code == 403
        assert r.json()["detail"]["code"] == "AGENT_JOB_FORBIDDEN"


def test_state_constants_are_consistent():
    assert TERMINAL_STATES <= ALL_STATES
    assert "pending" in ALL_STATES and "pending" not in TERMINAL_STATES
    assert TERMINAL_STATES == frozenset({"completed", "failed", "cancelled"})
