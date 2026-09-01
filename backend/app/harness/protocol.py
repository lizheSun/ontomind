"""统一交互协议 —— 前端与插件都不直连对方。

插件把 OpenCode JSONL / DSH JSON-RPC 翻译成本文件的 StreamEvent；
API 再把 StreamEvent 写成 SSE。以后加 runner 只实现 RunnerPlugin。
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Literal, Optional, Protocol

EventKind = Literal["text", "thinking", "execute", "error", "status", "meta"]
ToolStatus = Literal["running", "completed", "error"]


@dataclass
class StreamEvent:
    kind: EventKind
    text: str = ""
    delta: bool = True
    tool_id: str = ""
    tool_name: str = ""
    tool_status: str = ""
    summary: str = ""
    output: str = ""
    part_id: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def to_sse_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"kind": self.kind}
        if self.text:
            d["text"] = self.text
        if self.kind in ("text", "thinking"):
            d["delta"] = self.delta
        if self.tool_id:
            d["tool_id"] = self.tool_id
        if self.tool_name:
            d["tool_name"] = self.tool_name
        if self.tool_status:
            d["tool_status"] = self.tool_status
        if self.summary:
            d["summary"] = self.summary
        if self.output:
            d["output"] = self.output
        if self.part_id:
            d["part_id"] = self.part_id
        if self.meta:
            d["meta"] = self.meta
        return d


@dataclass
class PluginInfo:
    id: str
    label: str
    available: bool
    detail: str = ""
    binary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "available": self.available,
            "detail": self.detail,
            "binary": self.binary,
        }


@dataclass
class RunRequest:
    """一次用户回合。session_key 给 DSH 当 sessionId，也给 OpenCode 续聊。"""

    session_key: str
    workspace: Path
    prompt: str
    plugin_session_id: Optional[str] = None
    env: dict[str, str] = field(default_factory=dict)
    model: str = ""
    cancel: Optional[asyncio.Event] = None


class RunnerPlugin(Protocol):
    id: str
    label: str

    def probe(self) -> PluginInfo: ...

    def stream(self, req: RunRequest) -> AsyncIterator[StreamEvent]: ...
