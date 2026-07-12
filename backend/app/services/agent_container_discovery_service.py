"""AgentContainerDiscoveryService (T47).

扫描本地节点上运行的 agent 容器（opencode / openclaw / harness），
判断可用性并输出结构化结果，供 `register-local` 汇总。

设计要点：
- 三种判定方式（任一命中即算已发现）：
    1. `shutil.which(name)` — CLI 二进制在 PATH 中
    2. `pgrep -f name`      — 有运行中的进程
    3. `socket.connect(host, port)` — 端口正在被监听
- 每个 kind 各自独立判定，互不影响；命中就写入 `containers`。
- 全部异常静默降级，不阻断 register-local 主流程。
- 所有外部命令/网络通过 `_run_pgrep` / `_port_open` 抽出，方便 mock。
"""
from __future__ import annotations

import shutil
import socket
import subprocess
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger


# 已知 agent 容器类型 —— name 与 KNOWN_AGENTS 对齐
_CONTAINER_SPECS: dict[str, dict] = {
    "opencode": {
        "label": "OpenCode",
        "icon": "💻",
        "cli_names": ["opencode", "open-code"],
        "proc_names": ["opencode", "open-code"],
        "ports": [5173, 3000, 8080, 8787],
    },
    "openclaw": {
        "label": "OpenClaw",
        "icon": "🦞",
        "cli_names": ["openclaw", "claw", "open-claw"],
        "proc_names": ["openclaw", "claw", "open-claw"],
        "ports": [3000, 8080, 8000, 7860],
    },
    "harness": {
        "label": "Harness",
        "icon": "⚙️",
        "cli_names": ["harness", "agent-harness"],
        "proc_names": ["harness", "agent-harness"],
        "ports": [3000, 8080, 4000],
    },
}


@dataclass
class ContainerRecord:
    """单个 agent 容器的发现结果."""
    kind: str                                     # opencode / openclaw / harness
    label: str
    icon: str
    cli_path: Optional[str] = None                # shutil.which 结果
    pids: list[int] = field(default_factory=list) # pgrep 找到的进程 PID
    open_ports: list[int] = field(default_factory=list)  # 监听中的端口
    is_running: bool = False                      # cli 存在 or pid 有 or 端口开

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "label": self.label,
            "icon": self.icon,
            "cli_path": self.cli_path,
            "pids": list(self.pids),
            "open_ports": list(self.open_ports),
            "is_running": self.is_running,
        }


class AgentContainerDiscoveryService:
    """扫描本地 opencode / openclaw / harness 容器."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port_timeout: float = 0.2,
        specs: Optional[dict[str, dict]] = None,
    ) -> None:
        self.host = host
        self.port_timeout = port_timeout
        self.specs = specs if specs is not None else _CONTAINER_SPECS

    # ---------------- 底层探测（可被测试 patch） ----------------

    def _which(self, name: str) -> Optional[str]:
        try:
            return shutil.which(name)
        except Exception:  # noqa: BLE001
            return None

    def _run_pgrep(self, pattern: str) -> list[int]:
        """`pgrep -f <pattern>` → 一组 PID。失败/无结果返回 []。"""
        try:
            out = subprocess.check_output(
                ["pgrep", "-f", pattern],
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                FileNotFoundError, OSError):
            return []
        pids: list[int] = []
        for line in out.decode(errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                pids.append(int(line))
            except ValueError:
                continue
        return pids

    def _port_open(self, port: int) -> bool:
        """TCP connect_ex 判定端口是否可连接."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.port_timeout)
                return sock.connect_ex((self.host, port)) == 0
        except (OSError, socket.timeout):
            return False

    # ---------------- 单 kind 扫描 ----------------

    def scan_container(self, kind: str) -> ContainerRecord:
        spec = self.specs[kind]
        rec = ContainerRecord(kind=kind, label=spec["label"], icon=spec["icon"])

        # 1. CLI
        for cli_name in spec.get("cli_names", []):
            path = self._which(cli_name)
            if path:
                rec.cli_path = path
                break

        # 2. pgrep
        seen: set[int] = set()
        for proc_name in spec.get("proc_names", []):
            for pid in self._run_pgrep(proc_name):
                if pid not in seen:
                    seen.add(pid)
                    rec.pids.append(pid)

        # 3. ports
        for port in spec.get("ports", []):
            if self._port_open(port):
                rec.open_ports.append(port)

        rec.is_running = bool(rec.cli_path or rec.pids or rec.open_ports)
        return rec

    # ---------------- 汇总 ----------------

    def discover(self) -> list[ContainerRecord]:
        results: list[ContainerRecord] = []
        for kind in self.specs.keys():
            try:
                results.append(self.scan_container(kind))
            except Exception as exc:  # noqa: BLE001 — 单 kind 失败不影响其他
                logger.warning(f"[agent-container-discovery] scan {kind} failed: {exc}")
                results.append(ContainerRecord(
                    kind=kind,
                    label=self.specs[kind]["label"],
                    icon=self.specs[kind]["icon"],
                ))
        return results

    def discover_running(self) -> list[ContainerRecord]:
        """只返回 is_running == True 的记录."""
        return [r for r in self.discover() if r.is_running]
