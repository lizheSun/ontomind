"""不经 shell 的本机节点连接器。"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Iterable

from app.connectors.base import (
    CommandResult,
    CommandSpec,
    ConnectionReport,
    ManagedPath,
    ensure_managed_local_path,
)


DEFAULT_PROGRAMS = frozenset({"which", "opencode", "uname", "hostname"})


class LocalConnector:
    def __init__(
        self,
        managed_roots: Iterable[str],
        allowed_programs: frozenset[str] = DEFAULT_PROGRAMS,
        max_timeout_seconds: float = 30.0,
        max_output_limit: int = 1024 * 1024,
    ) -> None:
        self.managed_roots = tuple(managed_roots)
        self.allowed_programs = allowed_programs
        self.max_timeout_seconds = max_timeout_seconds
        self.max_output_limit = max_output_limit

    async def test_connection(self) -> ConnectionReport:
        return ConnectionReport(ok=True, message="local connector ready")

    async def run(self, command: CommandSpec) -> CommandResult:
        command.validate(
            self.allowed_programs,
            self.managed_roots,
            self.max_timeout_seconds,
            self.max_output_limit,
        )
        cwd = (
            str(ensure_managed_local_path(command.cwd.value, self.managed_roots))
            if command.cwd
            else None
        )
        proc = await asyncio.create_subprocess_exec(
            command.program,
            *command.args,
            cwd=cwd,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_task = asyncio.create_task(
            self._read_limited(proc.stdout, command.output_limit)
        )
        stderr_task = asyncio.create_task(
            self._read_limited(proc.stderr, command.output_limit)
        )
        try:
            await asyncio.wait_for(proc.wait(), timeout=command.timeout_seconds)
        except TimeoutError:
            proc.kill()
            await proc.wait()
            raise
        finally:
            stdout, stdout_truncated = await stdout_task
            stderr, stderr_truncated = await stderr_task
        return CommandResult(
            exit_code=proc.returncode or 0,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
            truncated=stdout_truncated or stderr_truncated,
        )

    @staticmethod
    async def _read_limited(
        stream: asyncio.StreamReader | None, limit: int
    ) -> tuple[bytes, bool]:
        if stream is None:
            return b"", False
        output = bytearray()
        truncated = False
        while True:
            chunk = await stream.read(8192)
            if not chunk:
                break
            remaining = limit - len(output)
            if remaining > 0:
                output.extend(chunk[:remaining])
            if len(chunk) > remaining:
                truncated = True
        return bytes(output), truncated

    async def read_file(self, path: ManagedPath) -> bytes:
        resolved = ensure_managed_local_path(path.value, self.managed_roots)
        return await asyncio.to_thread(resolved.read_bytes)

    async def list_files(self, root: ManagedPath, pattern: str) -> list[str]:
        resolved = ensure_managed_local_path(root.value, self.managed_roots)
        if ".." in Path(pattern).parts or Path(pattern).is_absolute():
            raise ValueError("glob pattern must stay below managed root")
        paths = await asyncio.to_thread(lambda: list(resolved.glob(pattern)))
        return [
            str(ensure_managed_local_path(str(path), self.managed_roots))
            for path in paths
            if path.is_file()
        ]
