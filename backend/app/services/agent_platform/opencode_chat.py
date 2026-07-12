"""通过本机 OpenCode CLI 流式执行对话，并映射为平台 Run 事件。"""
from __future__ import annotations

import asyncio
import json
import os
import re
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.connectors import CommandSpec
from app.db.models.agent_platform_model import AgentVersion
from app.db.repositories.agent_platform_repo import AgentPlatformRepository
from app.services.agent_platform.node_service import NodeService

_ANSI = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
EventSink = Callable[[str, dict[str, Any]], None]


def parse_opencode_output(stdout: str) -> str:
    """解析完整 stdout 为可读文本（非流式兜底）。"""
    parts: list[str] = []
    for line in (stdout or "").splitlines():
        line = _ANSI.sub("", line).strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = extract_text(evt)
        if text:
            parts.append(text)
    if parts:
        return "\n".join(parts).strip()
    return _ANSI.sub("", stdout or "").strip()


def extract_text(data: Any) -> str:
    if not isinstance(data, dict):
        return ""
    part = data.get("part")
    if isinstance(part, dict):
        for key in ("text", "content", "message", "output", "thinking", "reasoning"):
            value = part.get(key)
            if isinstance(value, str) and value.strip():
                return value
    for key in ("content", "text", "message", "output"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def map_opencode_event(
    raw: dict[str, Any],
    *,
    assistant_message_id: str,
    text_state: dict[str, str],
    started: dict[str, bool],
) -> list[tuple[str, dict[str, Any]]]:
    """将单行 OpenCode JSONL 映射为平台事件列表。"""
    events: list[tuple[str, dict[str, Any]]] = []
    evt_type = str(raw.get("type") or "")
    part = raw.get("part") if isinstance(raw.get("part"), dict) else {}
    part_type = str(part.get("type") or evt_type)
    part_id = str(part.get("id") or raw.get("id") or evt_type)

    # ---- thinking / reasoning ----
    if evt_type in {"reasoning", "thinking", "thought"} or part_type in {
        "reasoning",
        "thinking",
        "thought",
    }:
        summary = extract_text(raw) or str(part.get("text") or "")
        if summary:
            events.append(
                (
                    "thinking_summary",
                    {
                        "summary_id": part_id,
                        "summary": summary,
                        "title": "Thinking",
                    },
                )
            )
        return events

    # ---- steps ----
    if evt_type in {"step_start", "step-start"} or part_type in {"step-start", "step_start"}:
        events.append(
            (
                "step.started",
                {
                    "step_id": part_id,
                    "step_sequence": part_id,
                    "step_name": str(part.get("name") or "OpenCode step"),
                    "role": "opencode",
                },
            )
        )
        return events

    if evt_type in {"step_finish", "step-finish"} or part_type in {"step-finish", "step_finish"}:
        events.append(
            (
                "step.completed",
                {
                    "step_id": part_id,
                    "step_sequence": part_id,
                    "step_name": str(part.get("name") or "OpenCode step"),
                    "role": "opencode",
                    "reason": part.get("reason"),
                    "tokens": part.get("tokens"),
                    "cost": part.get("cost"),
                },
            )
        )
        return events

    # ---- tools ----
    toolish = evt_type in {
        "tool",
        "tool_use",
        "tool_call",
        "tool-call",
        "tool_result",
        "tool-result",
    } or part_type in {
        "tool",
        "tool_use",
        "tool_call",
        "tool-call",
        "tool_result",
        "tool-result",
    }
    if toolish:
        tool_name = str(
            part.get("tool")
            or part.get("name")
            or part.get("toolName")
            or raw.get("tool")
            or "tool"
        )
        tool_call_id = str(part.get("callID") or part.get("call_id") or part_id)
        is_result = "result" in evt_type or "result" in part_type or part.get("result") is not None
        if is_result:
            events.append(
                (
                    "tool.completed",
                    {
                        "message_id": assistant_message_id,
                        "tool_call_id": tool_call_id,
                        "tool_name": tool_name,
                        "result": part.get("result") or part.get("output") or part.get("content"),
                        "status": "success",
                    },
                )
            )
        else:
            events.append(
                (
                    "tool.started",
                    {
                        "message_id": assistant_message_id,
                        "tool_call_id": tool_call_id,
                        "tool_name": tool_name,
                        "arguments": part.get("input")
                        or part.get("arguments")
                        or part.get("args")
                        or {},
                    },
                )
            )
        return events

    # ---- assistant text ----
    if evt_type in {"text", "message"} or part_type in {"text", "message"}:
        full = extract_text(raw)
        if not full:
            return events
        if not started.get("message"):
            events.append(
                (
                    "message.started",
                    {
                        "message_id": assistant_message_id,
                        "role": "assistant",
                        "content_type": "markdown",
                    },
                )
            )
            started["message"] = True
        prev = text_state.get(part_id, "")
        if full.startswith(prev):
            delta = full[len(prev) :]
        else:
            delta = full
        text_state[part_id] = full
        if delta:
            events.append(
                (
                    "message.delta",
                    {
                        "message_id": assistant_message_id,
                        "role": "assistant",
                        "delta": delta,
                        "part_id": f"{assistant_message_id}-text",
                    },
                )
            )
        return events

    # ---- errors ----
    if evt_type == "error" or part_type == "error":
        events.append(
            (
                "step.completed",
                {
                    "step_id": part_id,
                    "step_name": "OpenCode error",
                    "role": "opencode",
                    "output": extract_text(raw) or json.dumps(raw, ensure_ascii=False)[:500],
                    "status": "error",
                },
            )
        )
    return events


class OpenCodeChatService:
    """按 AgentVersion.runtime 绑定的节点调用 OpenCode。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.nodes = NodeService(db)
        self.repo = AgentPlatformRepository(db)

    async def prepare(self, version_id: int) -> dict[str, Any]:
        version = self.db.get(AgentVersion, version_id)
        if not version:
            raise LookupError(f"AgentVersion 不存在: {version_id}")
        config = version.config if isinstance(version.config, dict) else {}
        runtime = config.get("runtime") if isinstance(config.get("runtime"), dict) else {}
        node_id = runtime.get("node_id")
        managed_root = runtime.get("managed_root")
        config_path = runtime.get("config_path")
        if not node_id:
            local = self.repo.find_local_node()
            if local is None:
                raise RuntimeError("未绑定运行节点，且本机节点不存在；请先在资源管理注册本机")
            node_id = local.id
            connection = self.repo.get_connection(local.id)
            roots = (connection.managed_roots if connection else []) or []
            managed_root = managed_root or (roots[0] if roots else None)
        cli_path = await self._resolve_cli(int(node_id))
        cwd = self._pick_cwd(managed_root, config_path)
        return {
            "cli_path": cli_path,
            "cwd": cwd,
            "node_id": int(node_id),
            "version_id": version_id,
        }

    async def stream_prompt(
        self,
        *,
        version_id: int,
        prompt: str,
        timeout_seconds: float = 180.0,
    ) -> AsyncIterator[dict[str, Any]]:
        """逐行产出 OpenCode JSONL 事件。"""
        prepared = await self.prepare(version_id)
        async for item in self._stream_invoke(
            cli_path=prepared["cli_path"],
            prompt=prompt,
            cwd=prepared["cwd"],
            timeout_seconds=timeout_seconds,
        ):
            yield {**item, "meta": prepared}

    async def run_prompt(
        self,
        *,
        version_id: int,
        prompt: str,
        timeout_seconds: float = 120.0,
    ) -> dict[str, Any]:
        prepared = await self.prepare(version_id)
        chunks: list[str] = []
        stderr_parts: list[str] = []
        exit_code = 0
        async for item in self._stream_invoke(
            cli_path=prepared["cli_path"],
            prompt=prompt,
            cwd=prepared["cwd"],
            timeout_seconds=timeout_seconds,
        ):
            if item.get("kind") == "line":
                chunks.append(str(item.get("line") or ""))
            elif item.get("kind") == "stderr":
                stderr_parts.append(str(item.get("text") or ""))
            elif item.get("kind") == "exit":
                exit_code = int(item.get("code") or 0)
        stdout = "\n".join(chunks)
        reply = parse_opencode_output(stdout)
        if not reply:
            err = "".join(stderr_parts).strip() or f"OpenCode 无输出 (exit={exit_code})"
            raise RuntimeError(err[:2000])
        return {
            "provider": "opencode",
            "cli_path": prepared["cli_path"],
            "cwd": prepared["cwd"],
            "exit_code": exit_code,
            "reply": reply,
            "stderr": "".join(stderr_parts)[:1000],
            "node_id": prepared["node_id"],
        }

    async def _resolve_cli(self, node_id: int) -> str:
        connector = self.nodes.connector_for(node_id)
        which = await connector.run(
            CommandSpec(program="which", args=("opencode",), timeout_seconds=10)
        )
        if which.exit_code == 0 and which.stdout.strip():
            return which.stdout.strip().splitlines()[0]
        candidates = [
            Path.home() / ".opencode" / "bin" / "opencode",
            Path("/usr/local/bin/opencode"),
            Path("/opt/homebrew/bin/opencode"),
        ]
        for path in candidates:
            if path.is_file() and os.access(path, os.X_OK):
                return str(path)
        raise RuntimeError("未找到 opencode CLI，请确认已安装并在 PATH 中")

    @staticmethod
    def _pick_cwd(managed_root: str | None, config_path: str | None) -> str | None:
        if managed_root:
            path = Path(managed_root).expanduser()
            if path.is_dir():
                return str(path)
        if config_path:
            parent = Path(config_path).expanduser().parent
            if parent.is_dir():
                return str(parent)
        default = Path.home() / ".config" / "opencode"
        return str(default) if default.is_dir() else None

    async def _stream_invoke(
        self,
        *,
        cli_path: str,
        prompt: str,
        cwd: str | None,
        timeout_seconds: float,
    ) -> AsyncIterator[dict[str, Any]]:
        env = {
            **os.environ,
            "NO_COLOR": "1",
            "TERM": "dumb",
            "OPENCODE_PERMISSION": '{"*":"allow"}',
        }
        opencode_bin = str(Path.home() / ".opencode" / "bin")
        path_parts = env.get("PATH", "").split(os.pathsep)
        if opencode_bin not in path_parts:
            env["PATH"] = os.pathsep.join([opencode_bin, env.get("PATH", "")])

        proc = await asyncio.create_subprocess_exec(
            cli_path,
            "run",
            "--format",
            "json",
            prompt,
            cwd=cwd,
            env=env,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert proc.stdout is not None
        assert proc.stderr is not None

        async def read_stderr() -> str:
            data = await proc.stderr.read()
            return data.decode("utf-8", errors="replace")

        stderr_task = asyncio.create_task(read_stderr())
        buffer = ""
        timed_out = False
        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        proc.stdout.read(1024), timeout=timeout_seconds
                    )
                except TimeoutError:
                    timed_out = True
                    proc.kill()
                    await proc.wait()
                    break
                if not chunk:
                    break
                buffer += chunk.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = _ANSI.sub("", line).strip()
                    if line:
                        yield {"kind": "line", "line": line}
            if buffer.strip():
                yield {"kind": "line", "line": _ANSI.sub("", buffer).strip()}
            if not timed_out:
                await asyncio.wait_for(proc.wait(), timeout=timeout_seconds)
        except TimeoutError:
            timed_out = True
            proc.kill()
            await proc.wait()
        stderr_text = await stderr_task
        if stderr_text:
            yield {"kind": "stderr", "text": stderr_text}
        yield {"kind": "exit", "code": proc.returncode or 0}
        if timed_out:
            raise TimeoutError(f"OpenCode 执行超时（>{timeout_seconds:.0f}s）")


def run_coroutine(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()
