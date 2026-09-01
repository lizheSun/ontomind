"""OpenCode 插件：优先打本机 `opencode serve` HTTP/SSE（thinking / tools 轨迹完整）。

serve 没起来时回退 `opencode run --format json`。不把 AIDE iframe 当会话层。
"""
from __future__ import annotations

import json
import shutil
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import settings
from app.harness.process import iter_process_lines
from app.harness.protocol import PluginInfo, RunRequest, StreamEvent


class OpenCodeParser:
    """把 OpenCode JSONL 译成 StreamEvent。无副作用，单测直接喂 dict。"""

    def __init__(self) -> None:
        self.session_id: str = ""

    def feed(self, msg: dict[str, Any]) -> list[StreamEvent]:
        t = msg.get("type")
        if t == "step_start":
            sid = msg.get("sessionID") or msg.get("sessionId") or ""
            if isinstance(sid, str) and sid:
                self.session_id = sid
            return []
        if t == "text":
            content = _part_text(msg)
            if not content:
                return []
            return [StreamEvent(kind="text", text=content, delta=False)]
        if t == "reasoning":
            content = _part_text(msg)
            if not content:
                return []
            return [StreamEvent(kind="thinking", text=content, delta=False)]
        if t == "tool_use":
            return self._tool(msg)
        if t == "error":
            return [StreamEvent(kind="error", text=_error_text(msg))]
        if t == "step_finish":
            return []
        return []

    def _tool(self, msg: dict[str, Any]) -> list[StreamEvent]:
        part = msg.get("part") if isinstance(msg.get("part"), dict) else {}
        state = part.get("state") if isinstance(part.get("state"), dict) else {}
        name = str(part.get("toolName") or part.get("tool") or "tool")
        tool_id = str(part.get("toolCallId") or part.get("id") or name)
        status = str(state.get("status") or "completed")
        if status == "error":
            tool_status = "error"
        elif status in ("pending", "running"):
            tool_status = "running"
        else:
            tool_status = "completed"
        input_raw = state.get("input")
        summary = _tool_summary(name, input_raw)
        output = state.get("output")
        if isinstance(output, (dict, list)):
            output_text = json.dumps(output, ensure_ascii=False)
        else:
            output_text = "" if output is None else str(output)
        return [
            StreamEvent(
                kind="execute",
                tool_id=tool_id,
                tool_name=name,
                tool_status=tool_status,
                summary=summary,
                output=output_text,
                delta=False,
            )
        ]


def _part_text(msg: dict[str, Any]) -> str:
    part = msg.get("part")
    if isinstance(part, dict):
        return str(part.get("text") or part.get("content") or "")
    return str(msg.get("text") or "")


def _error_text(msg: dict[str, Any]) -> str:
    part = msg.get("part")
    if isinstance(part, dict):
        err = part.get("error") or part.get("message")
        if err:
            return str(err)
    err = msg.get("error")
    if isinstance(err, str) and err:
        return err
    if isinstance(err, dict):
        return str(err.get("message") or err.get("name") or "OpenCode error")
    return "OpenCode 返回错误"


def _tool_summary(name: str, raw: Any) -> str:
    obj: Any = raw
    if isinstance(raw, str):
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            return raw[:80]
    if not isinstance(obj, dict):
        return ""
    key = {
        "bash": "command",
        "execute": "command",
        "write": "file_path",
        "read": "file_path",
        "edit": "file_path",
        "create": "file_path",
    }.get(name.lower(), "")
    if key and isinstance(obj.get(key), str):
        return _trunc(obj[key])
    for k in ("command", "file_path", "path", "url", "query"):
        if isinstance(obj.get(k), str):
            return _trunc(obj[k])
    return ""


def _trunc(s: str, n: int = 80) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def serve_base() -> str:
    return f"http://{settings.OPENCODE_HOST}:{settings.OPENCODE_PORT}"


def serve_alive() -> bool:
    try:
        r = httpx.get(f"{serve_base()}/global/health", timeout=1.0)
        return r.status_code == 200
    except httpx.HTTPError:
        return False
    except httpx.RequestError:
        return False


class OpenCodeServeParser:
    """把 serve `/event` 的 message.part.updated 译成 StreamEvent。"""

    def __init__(self, session_id: str = "") -> None:
        self.session_id = session_id
        self.assistant_ids: set[str] = set()
        self.idle = False
        self.started = False

    def feed(self, evt: dict[str, Any]) -> list[StreamEvent]:
        if not evt.get("type") and isinstance(evt.get("payload"), dict):
            evt = evt["payload"]
        t = str(evt.get("type") or "")
        props = evt.get("properties") if isinstance(evt.get("properties"), dict) else {}
        sid = _event_session_id(evt)
        if t == "session.idle":
            if sid and self.session_id and sid != self.session_id:
                return []
            if self.started:
                self.idle = True
            return []
        if t == "session.status":
            if sid and self.session_id and sid != self.session_id:
                return []
            raw = props.get("status")
            status = ""
            if isinstance(raw, str):
                status = raw
            elif isinstance(raw, dict):
                status = str(raw.get("type") or raw.get("status") or "")
            if status in ("busy", "running"):
                self.started = True
            elif status in ("idle", "idle_with_error") and self.started:
                self.idle = True
            return []
        if sid and self.session_id and sid != self.session_id:
            return []
        if t == "session.error":
            err = props.get("error")
            msg = err.get("message") if isinstance(err, dict) else (err or props.get("message") or "OpenCode 出错")
            return [StreamEvent(kind="error", text=str(msg), delta=False)]
        if t == "message.updated":
            info = props.get("info") if isinstance(props.get("info"), dict) else {}
            if info.get("role") == "assistant" and info.get("id"):
                self.assistant_ids.add(str(info["id"]))
                self.started = True
            return []
        if t != "message.part.updated":
            return []
        part = props.get("part") if isinstance(props.get("part"), dict) else {}
        events = self._part(part)
        if events:
            self.started = True
        return events

    def _part(self, part: dict[str, Any]) -> list[StreamEvent]:
        message_id = str(part.get("messageID") or "")
        ptype = str(part.get("type") or "")
        accept = (
            not message_id
            or message_id in self.assistant_ids
            or ptype in ("reasoning", "tool", "step-start", "step-finish")
        )
        if not accept:
            return []
        if message_id:
            self.assistant_ids.add(message_id)
        part_id = str(part.get("id") or ptype)
        if ptype == "text":
            text = str(part.get("text") or "")
            if not text:
                return []
            return [StreamEvent(kind="text", text=text, delta=False, part_id=part_id)]
        if ptype == "reasoning":
            text = str(part.get("text") or "")
            return [StreamEvent(kind="thinking", text=text, delta=False, part_id=part_id)]
        if ptype == "tool":
            state = part.get("state") if isinstance(part.get("state"), dict) else {}
            name = str(part.get("tool") or "tool")
            tool_id = str(part.get("callID") or part_id)
            status = str(state.get("status") or "pending")
            if status == "error":
                tool_status = "error"
            elif status in ("pending", "running"):
                tool_status = "running"
            else:
                tool_status = "completed"
            output = state.get("output")
            if isinstance(output, (dict, list)):
                output_text = json.dumps(output, ensure_ascii=False)
            else:
                output_text = "" if output is None else str(output)
            err = state.get("error")
            if err and not output_text:
                output_text = str(err)
            return [
                StreamEvent(
                    kind="execute",
                    part_id=part_id,
                    tool_id=tool_id,
                    tool_name=name,
                    tool_status=tool_status,
                    summary=_tool_summary(name, state.get("input")) or str(state.get("title") or ""),
                    output=output_text,
                    delta=False,
                )
            ]
        return []


def _event_session_id(evt: dict[str, Any]) -> str:
    props = evt.get("properties") if isinstance(evt.get("properties"), dict) else {}
    part = props.get("part") if isinstance(props.get("part"), dict) else {}
    info = props.get("info") if isinstance(props.get("info"), dict) else {}
    status = props.get("status") if isinstance(props.get("status"), dict) else {}
    for raw in (
        props.get("sessionID"),
        props.get("session_id"),
        part.get("sessionID"),
        info.get("sessionID"),
        status.get("sessionID"),
    ):
        if isinstance(raw, str) and raw:
            return raw
    return ""


def _parse_sse_line(line: str, data_lines: list[str]) -> dict[str, Any] | None:
    if line.startswith("data:"):
        data_lines.append(line[5:].strip())
        return None
    if line.strip():
        return None
    if not data_lines:
        return None
    raw = "\n".join(data_lines)
    data_lines.clear()
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return msg if isinstance(msg, dict) else None


class OpenCodePlugin:
    id = "opencode"
    label = "OpenCode"

    def probe(self) -> PluginInfo:
        if serve_alive():
            return PluginInfo(
                id=self.id,
                label=self.label,
                available=True,
                binary=serve_base(),
                detail=f"serve {serve_base()}（thinking / tools 走 SSE）",
            )
        binary = shutil.which("opencode") or ""
        if binary:
            return PluginInfo(
                id=self.id,
                label=self.label,
                available=True,
                binary=binary,
                detail=f"{binary} · CLI 兜底（先开 opencode serve 可看完整轨迹）",
            )
        return PluginInfo(
            id=self.id,
            label=self.label,
            available=False,
            detail="未找到 opencode。安装 CLI 后执行 opencode serve --port 4096 --cors http://localhost:5173",
        )

    async def stream(self, req: RunRequest) -> AsyncIterator[StreamEvent]:
        if serve_alive():
            async for ev in self._stream_serve(req):
                yield ev
            return
        async for ev in self._stream_cli(req):
            yield ev

    async def _stream_serve(self, req: RunRequest) -> AsyncIterator[StreamEvent]:
        base = serve_base()
        params = {"directory": str(req.workspace)}
        yield StreamEvent(kind="status", text="OpenCode 正在思考…", delta=False)
        timeout = httpx.Timeout(connect=5.0, read=None, write=30.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                sid = req.plugin_session_id or ""
                if sid:
                    existing = await client.get(f"{base}/session/{sid}", params=params)
                    if existing.status_code != 200:
                        sid = ""
                if not sid:
                    created = await client.post(
                        f"{base}/session",
                        params=params,
                        json={"title": req.session_key[:80]},
                    )
                    created.raise_for_status()
                    sid = str(created.json().get("id") or "")
                    if not sid:
                        yield StreamEvent(kind="error", text="OpenCode 未能创建会话", delta=False)
                        return
            except (httpx.HTTPError, httpx.RequestError) as exc:
                yield StreamEvent(kind="error", text=f"连接 OpenCode serve 失败：{exc}", delta=False)
                return
            yield StreamEvent(kind="meta", delta=False, meta={"plugin_session_id": sid})
            parser = OpenCodeServeParser(sid)

            async def abort() -> None:
                try:
                    await client.post(f"{base}/session/{sid}/abort", params=params)
                except httpx.HTTPError:
                    pass

            try:
                async with client.stream(
                    "GET",
                    f"{base}/event",
                    params=params,
                    headers={"Accept": "text/event-stream"},
                ) as evstream:
                    evstream.raise_for_status()
                    prompt = await client.post(
                        f"{base}/session/{sid}/prompt_async",
                        params=params,
                        json={"parts": [{"type": "text", "text": req.prompt}]},
                    )
                    if prompt.status_code >= 400:
                        yield StreamEvent(
                            kind="error",
                            text=prompt.text[:400] or f"prompt 失败 ({prompt.status_code})",
                            delta=False,
                        )
                        return
                    data_lines: list[str] = []
                    async for line in evstream.aiter_lines():
                        if req.cancel is not None and req.cancel.is_set():
                            await abort()
                            break
                        msg = _parse_sse_line(line, data_lines)
                        if not msg:
                            continue
                        for ev in parser.feed(msg):
                            yield ev
                        if parser.idle:
                            break
            except (httpx.HTTPError, httpx.RequestError) as exc:
                yield StreamEvent(kind="error", text=str(exc), delta=False)

    async def _stream_cli(self, req: RunRequest) -> AsyncIterator[StreamEvent]:
        binary = shutil.which("opencode") or ""
        if not binary:
            yield StreamEvent(kind="error", text=self.probe().detail, delta=False)
            return
        argv = [binary, "run", "--format", "json"]
        sid = req.plugin_session_id or ""
        if sid:
            argv += ["--continue", "--session", sid]
        yield StreamEvent(kind="status", text="OpenCode CLI 正在思考…", delta=False)
        parser = OpenCodeParser()
        env = {
            "OPENCODE_DISABLE_DEFAULT_PLUGINS": "true",
            "OPENCODE_CLIENT": "cli",
            **req.env,
        }
        async for line in iter_process_lines(
            argv,
            cwd=req.workspace,
            env=env,
            stdin=req.prompt.encode("utf-8"),
            cancel=req.cancel,
        ):
            if line.startswith("__STDERR__:"):
                yield StreamEvent(kind="error", text=line[len("__STDERR__:") :], delta=False)
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(msg, dict):
                continue
            for ev in parser.feed(msg):
                yield ev
        if parser.session_id:
            yield StreamEvent(
                kind="meta",
                delta=False,
                meta={"plugin_session_id": parser.session_id},
            )
