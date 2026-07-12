"""Unified Agent lifecycle and Run domain regression tests."""
import pytest

from app.core.exceptions import ConflictException
from app.db.models.agent_platform_model import AgentMessage
from app.db.models.agent_run_model import AgentRun
from app.services.agent_platform.agent import AgentService
from app.services.agent_platform.approval import ApprovalService
from app.services.agent_platform.deployment import DeploymentService
from app.services.agent_platform.run import RunService
from app.services.agent_platform.session import SessionService
from app.services.agent_platform.version import VersionService


def _agent(db_session, user_id: int, name: str = "platform-agent"):
    return AgentService(db_session).create(
        name=name,
        agent_type="custom_looper",
        description="test",
        config={"model": "stub", "system_prompt": "v1"},
        user_id=user_id,
    )


def test_agent_version_is_append_only(db_session, test_user):
    created = _agent(db_session, test_user["id"])
    agent_id = created["id"]
    first = created["latest_version"]

    second = VersionService(db_session).create(
        agent_id,
        {"model": "stub-v2", "system_prompt": "v2"},
        test_user["id"],
    )

    assert first["version_number"] == 1
    assert second["version_number"] == 2
    assert VersionService(db_session).get(first["id"]).config["system_prompt"] == "v1"
    with pytest.raises(ConflictException) as exc:
        VersionService(db_session).update(first["id"], {"config": {}})
    assert exc.value.code == "VERSION_IMMUTABLE"

    persisted = VersionService(db_session).get(first["id"])
    persisted.note = "illegal mutation"
    with pytest.raises(ValueError, match="immutable"):
        db_session.commit()
    db_session.rollback()


def test_deployment_state_machine_and_optimistic_version(db_session, test_user):
    version = _agent(db_session, test_user["id"])["latest_version"]
    service = DeploymentService(db_session)
    deployment = service.create(version["id"], "test", {}, test_user["id"])

    deploying = service.transition(deployment["id"], "start", expected_version=1)
    active = service.transition(deployment["id"], "activate", expected_version=2)
    assert deploying["status"] == "deploying"
    assert active["status"] == "active"
    assert active["status_version"] == 3

    with pytest.raises(ConflictException) as exc:
        service.transition(deployment["id"], "stop", expected_version=2)
    assert exc.value.code == "DEPLOYMENT_VERSION_CONFLICT"


@pytest.mark.parametrize("strategy", ["single_shot", "evaluator_optimizer"])
def test_persistent_run_adapter_and_ordered_events(
    db_session, test_user, strategy
):
    version = _agent(db_session, test_user["id"], f"run-{strategy}")["latest_version"]
    service = RunService(db_session)
    run = service.create(
        version_id=version["id"],
        deployment_id=None,
        session_id=None,
        strategy=strategy,
        input_data={"prompt": "hello", "force_stub": True},
        user_id=test_user["id"],
    )
    completed = service.control(run["id"], "start")
    events = service.events_after(run["id"])

    assert completed["status"] == "completed"
    assert completed["output"]["final_output"]
    assert [event["sequence"] for event in events] == list(range(1, len(events) + 1))
    assert events[-1]["type"] == "run.completed"
    assert events[-1]["timestamp"]
    assert "payload" in events[-1]
    if strategy == "evaluator_optimizer":
        assert completed["output"]["revisions_used"] == 1
        assert len([e for e in events if e["type"] == "eval.result"]) == 2


def test_sse_replays_after_last_event_id(client, auth_headers, db_session, test_user):
    version = _agent(db_session, test_user["id"], "sse-agent")["latest_version"]
    service = RunService(db_session)
    run = service.create(
        version_id=version["id"],
        deployment_id=None,
        session_id=None,
        strategy="single_shot",
        input_data={"prompt": "replay", "force_stub": True},
        user_id=test_user["id"],
    )
    service.control(run["id"], "start")

    response = client.get(
        f"/api/v1/agent-platform/runs/{run['id']}/events",
        headers={**auth_headers, "Last-Event-ID": "1"},
    )
    assert response.status_code == 200
    assert "id: 1\r\n" not in response.text
    assert "id: 2\r\n" in response.text
    assert "event: run.completed" in response.text
    assert '"type": "run.completed"' in response.text


def test_approval_decision_uses_optimistic_lock(db_session, test_user):
    version = _agent(db_session, test_user["id"], "approval-agent")["latest_version"]
    run = RunService(db_session).create(
        version_id=version["id"],
        deployment_id=None,
        session_id=None,
        strategy="single_shot",
        input_data={},
        user_id=test_user["id"],
    )
    service = ApprovalService(db_session)
    approval = service.create(
        run["id"], None, "dangerous_tool", {"path": "/tmp/x"}, test_user["id"]
    )
    decided = service.decide(
        approval["id"], "approve", approval["lock_version"], test_user["id"]
    )
    assert decided["status"] == "approved"
    assert decided["lock_version"] == 2

    with pytest.raises(ConflictException) as exc:
        service.decide(approval["id"], "reject", 1, test_user["id"])
    assert exc.value.code == "APPROVAL_VERSION_CONFLICT"


def test_version_validate_and_load(db_session, test_user):
    created = _agent(db_session, test_user["id"], "load-agent")
    version = created["latest_version"]
    service = VersionService(db_session)

    report = service.validate(created["id"], version["id"])
    loaded = service.load(
        created["id"], version["id"], "test", {"runtime": "stub"}, test_user["id"]
    )

    assert report["valid"] is True
    assert report["config"]["missing_fields"] == []
    assert report["dependencies"]["valid"] is True
    assert report["eval"]["executed"] == 0
    assert loaded["deployment"]["status"] == "deploying"
    assert loaded["version"]["config_snapshot"]["model"] == "stub"


def test_deployment_drain_force_offline_and_rollback(db_session, test_user):
    created = _agent(db_session, test_user["id"], "deploy-lifecycle")
    agent_id = created["id"]
    v1 = created["latest_version"]
    v2 = VersionService(db_session).create(
        agent_id,
        {"model": "stub-v2", "system_prompt": "v2"},
        test_user["id"],
    )
    service = DeploymentService(db_session)
    first = service.create(v1["id"], "prod", {}, test_user["id"])
    first = service.transition(first["id"], "start", first["status_version"])
    first = service.transition(first["id"], "activate", first["status_version"])
    draining = service.drain(first["id"], first["status_version"])
    offline = service.force_offline(
        first["id"], draining["status_version"], "maintenance"
    )
    assert draining["status"] == "draining"
    assert offline["status"] == "offline"

    second = service.create(v2["id"], "prod", {}, test_user["id"])
    second = service.transition(second["id"], "start", second["status_version"])
    second = service.transition(second["id"], "activate", second["status_version"])
    rollback = service.rollback(
        second["id"], test_user["id"], second["status_version"]
    )
    assert rollback["agent_version_id"] == v1["id"]
    assert rollback["previous_deployment_id"] == second["id"]
    assert rollback["operation"] == "rollback"


def test_run_pause_resume_retry_cancel_with_optimistic_lock(db_session, test_user):
    version = _agent(db_session, test_user["id"], "run-controls")["latest_version"]
    service = RunService(db_session)
    run = service.create(
        version_id=version["id"],
        deployment_id=None,
        session_id=None,
        strategy="single_shot",
        kind="job",
        input_data={"goal": "checkpoint-safe job"},
        user_id=test_user["id"],
    )
    row = db_session.get(AgentRun, run["id"])
    row.status = "running"
    db_session.commit()

    paused = service.control(run["id"], "pause", expected_version=1)
    with pytest.raises(ConflictException) as exc:
        service.control(run["id"], "resume", expected_version=1)
    assert exc.value.code == "RUN_VERSION_CONFLICT"
    resumed = service.control(run["id"], "resume", expected_version=2)
    cancelled = service.control(run["id"], "cancel", expected_version=3)
    retry = service.control(run["id"], "retry", expected_version=4)

    assert paused["status"] == "paused"
    assert resumed["status"] == "running"
    assert cancelled["status"] == "cancelled"
    assert retry["status"] == "queued"
    assert retry["attempt"] == 2
    assert retry["parent_run_id"] == run["id"]


def test_session_user_message_creates_chat_run(db_session, test_user):
    created = _agent(db_session, test_user["id"], "chat-agent")
    sessions = SessionService(db_session)
    session = sessions.create(
        created["id"], None, "Chat", {}, test_user["id"]
    )
    result = sessions.send_message(
        session["id"], "hello", "text", {"force_stub": True}, test_user["id"]
    )

    message = db_session.get(AgentMessage, result["message_id"])
    run = db_session.get(AgentRun, result["run_id"])
    assert message.run_id == run.id
    assert message.role == "user"
    assert run.kind == "chat"
    assert run.status == "completed"
    assert result["run"]["status"] == "completed"
    assert result["run"]["output"]["final_output"]
    events = RunService(db_session).events_after(run.id)
    assert any(event["type"] == "message.delta" for event in events)
    assert any(event["type"] == "run.completed" for event in events)
    assistants = (
        db_session.query(AgentMessage)
        .filter(AgentMessage.session_id == session["id"], AgentMessage.role == "assistant")
        .all()
    )
    assert len(assistants) == 1
    assert "hello" in assistants[0].content or "已收到" in assistants[0].content
