"""Harness 解析器单测：不启 CLI。"""
from __future__ import annotations

import json

from app.harness.plugins.dsh import DshParser, build_initialize, build_prompt, resolve_dsh_model
from app.harness.plugins.opencode import OpenCodeParser
from app.services.harness_service import apply_event
from app.harness.protocol import StreamEvent


def test_opencode_text_reasoning_tool():
    p = OpenCodeParser()
    p.feed({"type": "step_start", "sessionID": "ses_1", "part": {"id": "p1"}})
    assert p.session_id == "ses_1"
    think = p.feed({"type": "reasoning", "part": {"text": "先看目录"}})
    assert think[0].kind == "thinking" and "目录" in think[0].text
    text = p.feed({"type": "text", "part": {"text": "你好"}})
    assert text[0].kind == "text" and text[0].text == "你好"
    tool = p.feed(
        {
            "type": "tool_use",
            "part": {
                "toolName": "bash",
                "toolCallId": "t1",
                "state": {"status": "completed", "input": {"command": "ls -la"}, "output": "a.txt"},
            },
        }
    )
    assert tool[0].kind == "execute"
    assert tool[0].tool_name == "bash"
    assert tool[0].summary == "ls -la"
    assert tool[0].output == "a.txt"
    err = p.feed({"type": "error", "error": {"message": "boom"}})
    assert err[0].kind == "error" and "boom" in err[0].text


def test_dsh_text_delta_and_idle():
    p = DshParser("s1")
    evs = p.feed(
        {
            "jsonrpc": "2.0",
            "method": "session.event",
            "params": {
                "sessionId": "s1",
                "event": {"type": "assistant/chunk", "data": {"chunk": {"type": "text-delta", "text": "Hi"}}},
            },
        }
    )
    assert evs[0].kind == "text" and evs[0].text == "Hi" and evs[0].delta
    p.feed({"jsonrpc": "2.0", "method": "session.status", "params": {"sessionId": "s1", "status": "idle"}})
    assert p.completed


def test_dsh_tool_lifecycle_and_rpc_error():
    p = DshParser("s1")
    start = p.feed(
        {
            "jsonrpc": "2.0",
            "method": "session.event",
            "params": {
                "sessionId": "s1",
                "event": {
                    "type": "assistant/chunk",
                    "data": {"chunk": {"type": "block-start", "blockType": "tool-call", "id": "c1", "name": "bash"}},
                },
            },
        }
    )
    assert start[0].tool_status == "running"
    done = p.feed(
        {
            "jsonrpc": "2.0",
            "method": "session.event",
            "params": {
                "sessionId": "s1",
                "event": {
                    "type": "tool/result",
                    "data": {
                        "message": {
                            "source": {"callId": "c1"},
                            "content": [{"content": [{"text": "ok"}], "isError": False}],
                        }
                    },
                },
            },
        }
    )
    assert done[0].tool_status == "completed" and done[0].output == "ok"
    err = p.feed({"jsonrpc": "2.0", "id": 2, "error": {"code": -1, "message": "no key"}})
    assert err[0].kind == "error" and "no key" in err[0].text


def test_dsh_rpc_builders():
    init = json.loads(build_initialize("/tmp/ws", "deepseek-chat"))
    assert init["method"] == "initialize"
    assert init["params"]["provider"] == "deepseek-official"
    assert init["params"]["model"] == "deepseek-v4-flash"
    prompt = build_prompt("om-1", "hello")
    assert "session/prompt" in prompt and "hello" in prompt


def test_resolve_dsh_model_aliases():
    assert resolve_dsh_model("deepseek-official") == "deepseek-v4-flash"
    assert resolve_dsh_model("deepseek-chat") == "deepseek-v4-flash"
    assert resolve_dsh_model("deepseek-v4-pro") == "deepseek-v4-pro"
    assert resolve_dsh_model("deepseek-v4-flash-vision-exp") == "deepseek-v4-flash-vision-exp"
    assert resolve_dsh_model("") == "deepseek-v4-flash"


def test_dsh_reasoning_delta_without_text():
    p = DshParser("s1")
    start = p.feed(
        {
            "jsonrpc": "2.0",
            "method": "session.event",
            "params": {
                "sessionId": "s1",
                "event": {"type": "assistant/chunk", "data": {"chunk": {"type": "reasoning-delta", "text": ""}}},
            },
        }
    )
    assert start[0].kind == "thinking"
    delta = p.feed(
        {
            "jsonrpc": "2.0",
            "method": "session.event",
            "params": {
                "sessionId": "s1",
                "event": {"type": "assistant/chunk", "data": {"chunk": {"type": "reasoning-delta", "text": "先列目录"}}},
            },
        }
    )
    assert delta[0].text == "先列目录" and delta[0].delta


def test_apply_event_upserts_part_id():
    parts: list = []
    apply_event(parts, StreamEvent(kind="thinking", text="一", delta=False, part_id="r1"))
    apply_event(parts, StreamEvent(kind="thinking", text="一二", delta=False, part_id="r1"))
    apply_event(
        parts,
        StreamEvent(kind="execute", part_id="t1", tool_id="c1", tool_name="bash", tool_status="running", delta=False),
    )
    apply_event(
        parts,
        StreamEvent(kind="execute", part_id="t1", tool_id="c1", tool_status="completed", output="ok", delta=False),
    )
    assert len(parts) == 2
    assert parts[0]["text"] == "一二"
    assert parts[1]["tool_status"] == "completed"


def test_opencode_serve_reasoning_and_tool():
    from app.harness.plugins.opencode import OpenCodeServeParser

    p = OpenCodeServeParser("ses_1")
    p.feed({"type": "message.updated", "properties": {"info": {"id": "msg_a", "role": "assistant", "sessionID": "ses_1"}}})
    think = p.feed(
        {
            "type": "message.part.updated",
            "properties": {
                "sessionID": "ses_1",
                "part": {"id": "prt_r", "type": "reasoning", "messageID": "msg_a", "text": "先看文件"},
            },
        }
    )
    assert think[0].kind == "thinking" and think[0].part_id == "prt_r"
    tool = p.feed(
        {
            "type": "message.part.updated",
            "properties": {
                "sessionID": "ses_1",
                "part": {
                    "id": "prt_t",
                    "type": "tool",
                    "tool": "bash",
                    "callID": "call_1",
                    "messageID": "msg_a",
                    "state": {"status": "completed", "input": {"command": "ls"}, "output": "a.txt"},
                },
            },
        }
    )
    assert tool[0].kind == "execute" and tool[0].tool_name == "bash" and tool[0].output == "a.txt"
    p.feed({"type": "session.idle", "properties": {"sessionID": "ses_1"}})
    assert p.idle


def test_opencode_serve_ignores_idle_before_start():
    from app.harness.plugins.opencode import OpenCodeServeParser

    p = OpenCodeServeParser("ses_1")
    p.feed({"type": "session.idle", "properties": {"sessionID": "ses_1"}})
    assert not p.idle
    p.feed({"type": "server.connected", "properties": {}})
    assert not p.idle
    p.feed({"type": "message.updated", "properties": {"info": {"id": "msg_a", "role": "assistant", "sessionID": "ses_1"}}})
    assert p.started
    p.feed({"type": "session.idle", "properties": {"sessionID": "ses_1"}})
    assert p.idle


def test_apply_event_merges_deltas_and_tools():
    parts: list = []
    apply_event(parts, StreamEvent(kind="text", text="a", delta=True))
    apply_event(parts, StreamEvent(kind="text", text="b", delta=True))
    apply_event(
        parts,
        StreamEvent(kind="execute", tool_id="t", tool_name="bash", tool_status="running", delta=False),
    )
    apply_event(
        parts,
        StreamEvent(kind="execute", tool_id="t", tool_status="completed", output="done", delta=False),
    )
    apply_event(parts, StreamEvent(kind="status", text="ignore"))
    assert parts[0]["text"] == "ab"
    assert parts[1]["tool_status"] == "completed"
    assert parts[1]["output"] == "done"
    assert len(parts) == 2
