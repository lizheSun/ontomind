"""子进程 JSONL 读取。插件只关心行，不自己管 pipe。"""
from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Optional


def _merge_env(env: Optional[dict[str, str]]) -> dict[str, str]:
    merged = os.environ.copy()
    if env:
        merged.update({k: v for k, v in env.items() if v is not None})
    return merged


class LineProcess:
    """stdin 可分多次写的 JSONL 子进程。DSH JSON-RPC 必须先 initialize 再 prompt。"""

    def __init__(
        self,
        proc: asyncio.subprocess.Process,
        err_task: asyncio.Task[None],
        stderr_buf: bytearray,
        cancel: Optional[asyncio.Event],
    ) -> None:
        self.proc = proc
        self._err_task = err_task
        self._stderr_buf = stderr_buf
        self._cancel = cancel

    @classmethod
    async def spawn(
        cls,
        argv: list[str],
        *,
        cwd: Path,
        env: Optional[dict[str, str]] = None,
        cancel: Optional[asyncio.Event] = None,
    ) -> LineProcess:
        cwd.mkdir(parents=True, exist_ok=True)
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
            env=_merge_env(env),
            limit=8 * 1024 * 1024,
        )
        stderr_buf = bytearray()

        async def _drain_stderr() -> None:
            assert proc.stderr is not None
            while True:
                chunk = await proc.stderr.read(4096)
                if not chunk:
                    break
                stderr_buf.extend(chunk)

        return cls(proc, asyncio.create_task(_drain_stderr()), stderr_buf, cancel)

    async def write_line(self, text: str) -> None:
        if self.proc.stdin is None:
            raise RuntimeError("process stdin is closed")
        payload = text if text.endswith("\n") else f"{text}\n"
        self.proc.stdin.write(payload.encode("utf-8"))
        await self.proc.stdin.drain()

    def close_stdin(self) -> None:
        if self.proc.stdin is not None and not self.proc.stdin.is_closing():
            self.proc.stdin.close()

    async def lines(self) -> AsyncIterator[str]:
        assert self.proc.stdout is not None
        while True:
            if self._cancel is not None and self._cancel.is_set():
                _kill(self.proc)
                break
            try:
                line = await asyncio.wait_for(self.proc.stdout.readline(), timeout=0.4)
            except asyncio.TimeoutError:
                if self.proc.returncode is not None:
                    break
                continue
            if not line:
                break
            yield line.decode("utf-8", errors="replace").rstrip("\r\n")

    def stderr_text(self) -> str:
        return self._stderr_buf.decode("utf-8", errors="replace").strip()

    async def aclose(self) -> str:
        self.close_stdin()
        if self.proc.returncode is None:
            try:
                await asyncio.wait_for(self.proc.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                _kill(self.proc)
                await self.proc.wait()
        if not self._err_task.done():
            try:
                await asyncio.wait_for(self._err_task, timeout=1.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._err_task.cancel()
        return self.stderr_text()


async def iter_process_lines(
    argv: list[str],
    *,
    cwd: Path,
    env: Optional[dict[str, str]] = None,
    stdin: Optional[bytes] = None,
    cancel: Optional[asyncio.Event] = None,
    close_stdin: bool = True,
) -> AsyncIterator[str]:
    proc = await LineProcess.spawn(argv, cwd=cwd, env=env, cancel=cancel)
    try:
        if stdin is not None:
            await proc.write_line(stdin.decode("utf-8", errors="replace"))
            if close_stdin:
                proc.close_stdin()
        async for line in proc.lines():
            yield line
        err = await proc.aclose()
        if proc.proc.returncode not in (0, None) and err:
            yield f"__STDERR__:{err}"
    finally:
        if proc.proc.returncode is None:
            _kill(proc.proc)
        if not proc._err_task.done():
            proc._err_task.cancel()


def _kill(proc: asyncio.subprocess.Process) -> None:
    try:
        proc.kill()
    except ProcessLookupError:
        pass
