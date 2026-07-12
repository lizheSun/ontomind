"""受约束的节点连接器契约与安全值对象。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol, Sequence


class ConnectorSecurityError(ValueError):
    """连接器输入违反安全策略。"""


class HostKeyVerificationError(ConnectorSecurityError):
    """SSH 服务端密钥与已确认指纹不一致。"""


@dataclass(frozen=True)
class ManagedPath:
    value: str


@dataclass(frozen=True)
class CommandSpec:
    """由受信发现器创建的 argv 命令，不接受 shell 字符串。"""

    program: str
    args: tuple[str, ...] = ()
    cwd: ManagedPath | None = None
    timeout_seconds: float = 10.0
    output_limit: int = 64 * 1024

    def validate(
        self,
        allowed_programs: frozenset[str],
        managed_roots: Sequence[str],
        max_timeout_seconds: float,
        max_output_limit: int,
        *,
        remote: bool = False,
    ) -> None:
        if self.program not in allowed_programs:
            raise ConnectorSecurityError(f"program is not allowlisted: {self.program}")
        if not self.program or "/" in self.program or "\x00" in self.program:
            raise ConnectorSecurityError("program must be an allowlisted executable name")
        forbidden = (";", "|", "&&", "||", ">", "<", "`", "$(", "\n", "\r", "\x00")
        for arg in self.args:
            if not isinstance(arg, str) or any(token in arg for token in forbidden):
                raise ConnectorSecurityError("argv contains forbidden shell syntax")
        if not 0 < self.timeout_seconds <= max_timeout_seconds:
            raise ConnectorSecurityError("command timeout exceeds policy")
        if not 0 < self.output_limit <= max_output_limit:
            raise ConnectorSecurityError("output limit exceeds policy")
        if remote and self.cwd is not None:
            raise ConnectorSecurityError("remote cwd is unsupported without a shell")
        if self.cwd is not None:
            ensure_managed_local_path(self.cwd.value, managed_roots)


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str
    truncated: bool = False


@dataclass(frozen=True)
class ConnectionReport:
    ok: bool
    message: str
    host_key_fingerprint: str | None = None


def ensure_managed_local_path(path: str, managed_roots: Sequence[str]) -> Path:
    candidate = Path(path).expanduser().resolve()
    roots = [Path(root).expanduser().resolve() for root in managed_roots]
    if not roots or not any(candidate == root or root in candidate.parents for root in roots):
        raise ConnectorSecurityError(f"path is outside managed roots: {path}")
    return candidate


def ensure_managed_remote_path(path: str, managed_roots: Sequence[str]) -> str:
    candidate = PurePosixPath(path)
    if not candidate.is_absolute() or ".." in candidate.parts:
        raise ConnectorSecurityError("remote path must be absolute and normalized")
    roots = [PurePosixPath(root) for root in managed_roots]
    if not roots or not any(candidate == root or root in candidate.parents for root in roots):
        raise ConnectorSecurityError(f"path is outside managed roots: {path}")
    return str(candidate)


class NodeConnector(Protocol):
    async def test_connection(self) -> ConnectionReport: ...
    async def run(self, command: CommandSpec) -> CommandResult: ...
    async def read_file(self, path: ManagedPath) -> bytes: ...
    async def list_files(self, root: ManagedPath, pattern: str) -> list[str]: ...
