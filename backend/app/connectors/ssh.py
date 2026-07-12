"""AsyncSSH 节点连接器，强制校验已确认的 host key 指纹。"""
from __future__ import annotations

import asyncio
import shlex
from typing import Any, Iterable

import asyncssh

from app.connectors.base import (
    CommandResult,
    CommandSpec,
    ConnectionReport,
    HostKeyVerificationError,
    ManagedPath,
    ensure_managed_remote_path,
)
from app.connectors.local import DEFAULT_PROGRAMS


class _FingerprintClient(asyncssh.SSHClient):
    def __init__(self, algorithm: str, fingerprint: str) -> None:
        self.algorithm = algorithm
        self.fingerprint = fingerprint

    def validate_host_public_key(self, host: str, addr: str, port: int, key: Any) -> bool:
        if self.algorithm and key.get_algorithm() != self.algorithm:
            return False
        actual = key.get_fingerprint("sha256")
        return actual == self.fingerprint


class SSHConnector:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        host_key_algorithm: str,
        host_key_fingerprint: str,
        managed_roots: Iterable[str],
        password: str | None = None,
        private_key: str | None = None,
        connect_timeout_seconds: float = 10.0,
        max_timeout_seconds: float = 30.0,
        max_output_limit: int = 1024 * 1024,
        allowed_programs: frozenset[str] = DEFAULT_PROGRAMS,
    ) -> None:
        if not host_key_algorithm or not host_key_fingerprint:
            raise HostKeyVerificationError("confirmed host key algorithm and fingerprint required")
        self.host = host
        self.port = port
        self.username = username
        self.host_key_algorithm = host_key_algorithm
        self.host_key_fingerprint = host_key_fingerprint
        self.managed_roots = tuple(managed_roots)
        self.password = password
        self.private_key = private_key
        self.connect_timeout_seconds = connect_timeout_seconds
        self.max_timeout_seconds = max_timeout_seconds
        self.max_output_limit = max_output_limit
        self.allowed_programs = allowed_programs

    async def _connect(self):
        client = _FingerprintClient(self.host_key_algorithm, self.host_key_fingerprint)
        kwargs: dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            # Empty trust tuple keeps AsyncSSH verification enabled; our client
            # accepts only the exact, administrator-confirmed SHA256 fingerprint.
            "known_hosts": ([], [], []),
            "client_factory": lambda: client,
            "connect_timeout": self.connect_timeout_seconds,
        }
        if self.password:
            kwargs["password"] = self.password
        if self.private_key:
            kwargs["client_keys"] = [asyncssh.import_private_key(self.private_key)]
        try:
            return await asyncssh.connect(**kwargs)
        except asyncssh.HostKeyNotVerifiable as exc:
            raise HostKeyVerificationError("SSH host key fingerprint rejected") from exc

    async def test_connection(self) -> ConnectionReport:
        try:
            conn = await self._connect()
            conn.close()
            await conn.wait_closed()
            return ConnectionReport(
                ok=True,
                message="ssh connection verified",
                host_key_fingerprint=self.host_key_fingerprint,
            )
        except HostKeyVerificationError:
            raise
        except (asyncssh.Error, OSError, TimeoutError) as exc:
            return ConnectionReport(ok=False, message=str(exc))

    async def run(self, command: CommandSpec) -> CommandResult:
        command.validate(
            self.allowed_programs,
            self.managed_roots,
            self.max_timeout_seconds,
            self.max_output_limit,
            remote=True,
        )
        # SSH exec carries one protocol string, but every token originated from
        # validated argv and is POSIX-quoted; callers can never submit shell text.
        encoded = shlex.join([command.program, *command.args])
        conn = await self._connect()
        try:
            result = await asyncio.wait_for(
                conn.run(encoded, check=False, timeout=command.timeout_seconds),
                timeout=command.timeout_seconds + 1,
            )
        finally:
            conn.close()
            await conn.wait_closed()
        stdout = str(result.stdout)
        stderr = str(result.stderr)
        truncated = (
            len(stdout.encode()) > command.output_limit
            or len(stderr.encode()) > command.output_limit
        )
        return CommandResult(
            exit_code=result.exit_status,
            stdout=stdout.encode()[: command.output_limit].decode(errors="replace"),
            stderr=stderr.encode()[: command.output_limit].decode(errors="replace"),
            truncated=truncated,
        )

    async def read_file(self, path: ManagedPath) -> bytes:
        remote_path = ensure_managed_remote_path(path.value, self.managed_roots)
        conn = await self._connect()
        try:
            async with conn.start_sftp_client() as sftp:
                async with sftp.open(remote_path, "rb") as handle:
                    return await handle.read()
        finally:
            conn.close()
            await conn.wait_closed()

    async def list_files(self, root: ManagedPath, pattern: str) -> list[str]:
        remote_root = ensure_managed_remote_path(root.value, self.managed_roots)
        if pattern.startswith("/") or ".." in pattern.split("/") or "\x00" in pattern:
            raise ValueError("SSH glob pattern must stay below managed root")
        conn = await self._connect()
        try:
            async with conn.start_sftp_client() as sftp:
                names = await sftp.glob(f"{remote_root.rstrip('/')}/{pattern}")
                return [
                    ensure_managed_remote_path(str(name), self.managed_roots)
                    for name in names
                ]
        finally:
            conn.close()
            await conn.wait_closed()
