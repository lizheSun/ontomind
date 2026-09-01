"""任务看板 API 测试。"""
from __future__ import annotations


def test_default_board_and_task_move(client):
    r = client.get("/api/v1/kanban/boards")
    assert r.status_code == 200, r.text
    boards = r.json()
    assert len(boards) == 1
    board = boards[0]
    assert board["name"] == "默认看板"
    assert len(board["columns"]) == 3
    todo, doing, _done = board["columns"]
    board_id = board["id"]

    r = client.post(
        f"/api/v1/kanban/boards/{board_id}/tasks",
        json={"title": "排查登录", "plugin_id": "opencode", "column_id": todo["id"]},
    )
    assert r.status_code == 200, r.text
    task = r.json()
    assert task["title"] == "排查登录"
    assert task["session_id"]
    assert task["run_status"] == "pending"
    assert task["column_id"] == todo["id"]
    assert task["position"] == 1
    tid = task["id"]

    r = client.put(
        f"/api/v1/kanban/tasks/{tid}/move",
        json={"column_id": doing["id"], "position": 1},
    )
    assert r.status_code == 200, r.text
    assert r.json()["column_id"] == doing["id"]
    assert r.json()["position"] == 1

    r = client.get(f"/api/v1/kanban/boards/{board_id}/tasks")
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.patch(f"/api/v1/kanban/tasks/{tid}", json={"run_status": "running"})
    assert r.json()["run_status"] == "running"

    r = client.get(f"/api/v1/kanban/boards/{board_id}/tasks", params={"run_status": "pending"})
    assert r.json() == []

    r = client.post(
        f"/api/v1/kanban/boards/{board_id}/columns",
        json={"name": "阻塞", "color": "#e62965"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "阻塞"

    r = client.delete(f"/api/v1/kanban/tasks/{tid}")
    assert r.status_code == 200
    r = client.get(f"/api/v1/kanban/boards/{board_id}/tasks")
    assert r.json() == []


def test_create_second_board(client):
    client.get("/api/v1/kanban/boards")
    r = client.post("/api/v1/kanban/boards", json={"name": "发版", "from_template": True})
    assert r.status_code == 200, r.text
    assert len(r.json()["columns"]) == 3
    r = client.get("/api/v1/kanban/boards")
    assert len(r.json()) == 2
