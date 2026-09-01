"""DSH 插件：JSON-RPC 驱动 agent，不是 `dsh --profile web`。

正确入口：
1. 源码检出里的 `tsx packages/examples/jsonrpc-demo/src/bin.ts`（设 DSH_REPO）
2. 已安装的 `deepseek-harness-sdk`（内置 dsh-jsonrpc-agent）

`dsh --profile web` 是给人用的浏览器，和 AIDE 一样不能给 OntoMind 会话当 runner。
也不存在 `dsh --profile sdk`。
"""
from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from app.harness.process import LineProcess
from app.harness.protocol import PluginInfo, RunRequest, StreamEvent

# DeepSeek 官方 API 只认这些名字。JSON-RPC server 的默认 model 是 provider 名
# `deepseek-official`，不能原样传给 API。
DSH_MODELS = (
    "deepseek-v4-pro",
    "deepseek-v4-flash",
    "deepseek-v4-flash-vision-exp",
)
DSH_DEFAULT_MODEL = "deepseek-v4-flash"


def resolve_dsh_model(raw: str) -> str:
    name = (raw or "").strip()
    if name in DSH_MODELS:
        return name
    lower = name.lower().replace("_", "-")
    if "vision" in lower:
        return "deepseek-v4-flash-vision-exp"
    if "pro" in lower and "flash" not in lower:
        return "deepseek-v4-pro"
    return DSH_DEFAULT_MODEL


class DshParser:
    """把 DSH JSON-RPC NDJSON 译成 StreamEvent。"""

    def __init__(self, session_id: str = "") -> None:
        self.session_id = session_id
        self.completed = False
        self._tools: dict[str, dict[str, str]] = {}

    def feed(self, msg: dict[str, Any]) -> list[StreamEvent]:
        if msg.get("id") is not None and "method" not in msg:
            err = msg.get("error")
            if isinstance(err, dict):
                text = _rpc_error_text(err)
                if text:
                    self.completed = True
                    return [StreamEvent(kind="error", text=text, delta=False)]
            return []
        method = msg.get("method")
        params = msg.get("params") if isinstance(msg.get("params"), dict) else {}
        if method == "session.status":
            return self._status(params)
        if method == "session.event":
            return self._event(params)
        return []

    def _status(self, params: dict[str, Any]) -> list[StreamEvent]:
        sid = str(params.get("sessionId") or "")
        if self.session_id and sid and sid != self.session_id:
            return []
        if params.get("status") == "idle":
            self.completed = True
        return []

    def _event(self, params: dict[str, Any]) -> list[StreamEvent]:
        sid = str(params.get("sessionId") or "")
        if self.session_id and sid and sid != self.session_id:
            return []
        event = params.get("event") if isinstance(params.get("event"), dict) else {}
        et = event.get("type")
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        if et == "assistant/chunk":
            return self._chunk(data)
        if et == "tool/call":
            return self._tool_call(data)
        if et == "tool/result":
            return self._tool_result(data)
        if et == "turn/end":
            return self._turn_end(data)
        return []

    def _chunk(self, data: dict[str, Any]) -> list[StreamEvent]:
        raw = data.get("chunk")
        chunk: dict[str, Any]
        if isinstance(raw, dict):
            chunk = raw
        elif isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                chunk = parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                chunk = {}
        else:
            chunk = {}
        ctype = chunk.get("type")
        if ctype == "text-delta" and chunk.get("text"):
            return [StreamEvent(kind="text", text=str(chunk["text"]), delta=True)]
        if ctype == "reasoning-delta":
            return [StreamEvent(kind="thinking", text=str(chunk.get("text") or ""), delta=True)]
        if ctype == "block-start" and chunk.get("blockType") in ("reasoning", "think"):
            return [StreamEvent(kind="thinking", text="", delta=True)]
        if ctype == "block-start" and chunk.get("blockType") == "tool-call":
            tool_id = str(chunk.get("id") or "")
            name = str(chunk.get("name") or "tool")
            if tool_id:
                self._tools[tool_id] = {"name": name}
            return [
                StreamEvent(
                    kind="execute",
                    tool_id=tool_id,
                    tool_name=name,
                    tool_status="running",
                    delta=False,
                )
            ]
        return []

    def _tool_call(self, data: dict[str, Any]) -> list[StreamEvent]:
        tool_id = str(data.get("callId") or "")
        name = str(data.get("name") or "tool")
        args = data.get("arguments") or ""
        summary = _tool_summary(name, args)
        self._tools[tool_id] = {"name": name, "summary": summary}
        return [
            StreamEvent(
                kind="execute",
                tool_id=tool_id,
                tool_name=name,
                tool_status="running",
                summary=summary,
                delta=False,
            )
        ]

    def _tool_result(self, data: dict[str, Any]) -> list[StreamEvent]:
        message = data.get("message") if isinstance(data.get("message"), dict) else {}
        source = message.get("source") if isinstance(message.get("source"), dict) else {}
        call_id = str(source.get("callId") or "")
        content = message.get("content") if isinstance(message.get("content"), list) else []
        is_error = False
        texts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("isError"):
                is_error = True
            inner = item.get("content")
            if isinstance(inner, list):
                for ci in inner:
                    if isinstance(ci, dict) and ci.get("text"):
                        texts.append(str(ci["text"]))
            elif item.get("text"):
                texts.append(str(item["text"]))
        known = self._tools.get(call_id, {})
        return [
            StreamEvent(
                kind="execute",
                tool_id=call_id,
                tool_name=known.get("name", ""),
                tool_status="error" if is_error else "completed",
                summary=known.get("summary", ""),
                output="\n".join(texts),
                delta=False,
            )
        ]

    def _turn_end(self, data: dict[str, Any]) -> list[StreamEvent]:
        reason = data.get("reason") if isinstance(data.get("reason"), dict) else {}
        kind = str(reason.get("kind") or "")
        if kind and kind not in ("completed", "stop"):
            msg = str(reason.get("message") or reason.get("error") or f"DSH turn ended: {kind}")
            return [StreamEvent(kind="error", text=msg, delta=False)]
        return []


def _rpc_error_text(err: dict[str, Any]) -> str:
    data = err.get("data")
    if isinstance(data, dict) and data.get("message"):
        return str(data["message"])
    if isinstance(data, str) and data.strip():
        return data.strip()
    msg = err.get("message")
    return str(msg) if msg else ""


def _tool_summary(name: str, raw: Any) -> str:
    obj: Any = raw
    if isinstance(raw, str):
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            return str(raw)[:80]
    if not isinstance(obj, dict):
        return ""
    for k in ("command", "file_path", "path", "url", "query", "name", "prompt"):
        if isinstance(obj.get(k), str):
            s = " ".join(str(obj[k]).split())
            return s if len(s) <= 80 else s[:79] + "…"
    return ""


def build_initialize(cwd: str, model: str) -> str:
    return json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "cwd": cwd,
                "provider": "deepseek-official",
                "model": resolve_dsh_model(model),
            },
        },
        ensure_ascii=False,
    )


def build_prompt(session_id: str, text: str) -> str:
    return json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "session/prompt",
            "params": {
                "sessionId": session_id,
                "contentBlocks": [{"type": "text", "text": text}],
            },
        },
        ensure_ascii=False,
    )


def _repo_ready(root: Path) -> bool:
    return (
        root.is_dir()
        and (root / "node_modules/.bin/tsx").is_file()
        and (root / "packages/examples/jsonrpc-demo/src/bin.ts").is_file()
        and (root / "examples/jsonrpc-agent/cordis.yml").is_file()
    )


def find_dsh_repo() -> Path | None:
    from app.core.config import settings

    candidates: list[Path] = []
    if settings.DSH_REPO:
        candidates.append(Path(settings.DSH_REPO).expanduser())
    env = (os.environ.get("DSH_REPO") or "").strip()
    if env:
        candidates.append(Path(env).expanduser())
    sibling = Path(__file__).resolve().parents[4].parent / "deepseek-harness"
    candidates.append(sibling)
    seen: set[str] = set()
    for raw in candidates:
        try:
            path = raw.expanduser().resolve()
        except OSError:
            continue
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        if _repo_ready(path):
            return path
    return None


class DshPlugin:
    id = "dsh"
    label = "DeepSeek Harness"

    def probe(self) -> PluginInfo:
        repo = find_dsh_repo()
        if repo is not None:
            return PluginInfo(
                id=self.id,
                label=self.label,
                available=True,
                binary=str(repo / "node_modules/.bin/tsx"),
                detail=f"JSON-RPC 源码运行时 · {repo}",
            )
        return PluginInfo(
            id=self.id,
            label=self.label,
            available=False,
            detail=(
                "DeepSeek Harness Web（dsh --profile web）不能给 OntoMind 会话用。"
                "请把源码检出放在同级目录并 pnpm install，或设置 DSH_REPO；"
                "也可以 pip install deepseek-harness-sdk。"
            ),
        )

    async def stream(self, req: RunRequest) -> AsyncIterator[StreamEvent]:
        info = self.probe()
        if not info.available:
            yield StreamEvent(kind="error", text=info.detail, delta=False)
            return
        model = resolve_dsh_model(req.model or req.env.get("DEEPSEEK_MODEL") or "")
        session_id = req.plugin_session_id or req.session_key
        repo = find_dsh_repo()
        if repo is None:
            yield StreamEvent(kind="error", text=info.detail, delta=False)
            return
        tsx = repo / "node_modules/.bin/tsx"
        agent = repo / "packages/examples/jsonrpc-demo/src/bin.ts"
        cordis = repo / "examples/jsonrpc-agent/cordis.yml"
        env = {
            "NODE_NO_WARNINGS": "1",
            **req.env,
            "DSH_CWD": str(req.workspace),
            "DSH_CORDIS_CONFIG": str(cordis),
            "DEEPSEEK_MODEL": model,
        }
        yield StreamEvent(kind="status", text="DSH 正在启动…", delta=False)
        parser = DshParser(session_id)
        proc = await LineProcess.spawn(
            [str(tsx), str(agent), str(cordis)],
            cwd=repo,
            env=env,
            cancel=req.cancel,
        )
        initialized = False
        try:
            await proc.write_line(build_initialize(str(req.workspace), model))
            async for line in proc.lines():
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(msg, dict):
                    continue
                if not initialized and msg.get("id") == 1:
                    err = msg.get("error")
                    if isinstance(err, dict):
                        text = _rpc_error_text(err) or "DSH initialize 失败"
                        yield StreamEvent(kind="error", text=text, delta=False)
                        parser.completed = True
                        break
                    initialized = True
                    yield StreamEvent(kind="status", text="DSH 正在思考…", delta=False)
                    await proc.write_line(build_prompt(session_id, req.prompt))
                    continue
                for ev in parser.feed(msg):
                    yield ev
                if parser.completed:
                    break
            if not initialized and not parser.completed:
                err = proc.stderr_text()
                yield StreamEvent(
                    kind="error",
                    text=err or "DSH 未能完成 initialize（进程已退出）",
                    delta=False,
                )
        finally:
            await proc.aclose()
        yield StreamEvent(
            kind="meta",
            delta=False,
            meta={"plugin_session_id": session_id},
        )
