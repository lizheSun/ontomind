"""Agent 发现与可用性检测服务。

在计算节点上自动扫描已知 Agent（openclaw、opencode 等），通过进程检测和端口健康检查判断可用性。
"""
import socket
import urllib.request
import subprocess
from typing import Optional
from dataclasses import dataclass, field


# 已知 Agent 类型及其常见端口、进程名、健康检查路径
KNOWN_AGENTS: dict[str, dict] = {
    "openclaw": {
        "label": "OpenClaw",
        "ports": [3000, 8080, 8000, 7860],
        "proc_names": ["openclaw", "claw", "open-claw"],
        "health_paths": ["/health", "/api/health", "/"],
        "icon": "🦞",
    },
    "opencode": {
        "label": "OpenCode",
        "ports": [5173, 3000, 8080, 8787],
        "proc_names": ["opencode", "open-code"],
        "health_paths": ["/health", "/api/health", "/"],
        "icon": "💻",
    },
    "harness": {
        "label": "Harness",
        "ports": [3000, 8080, 4000],
        "proc_names": ["harness", "agent-harness"],
        "health_paths": ["/health", "/api/health", "/"],
        "icon": "⚙️",
    },
    "custom": {
        "label": "Custom Agent",
        "ports": [3000, 8080, 9000],
        "proc_names": [],
        "health_paths": ["/health", "/api/health", "/readyz"],
        "icon": "🔧",
    },
}


@dataclass
class DiscoveredAgent:
    agent_type: str           # openclaw / opencode / harness / custom
    label: str
    icon: str
    port: int                 # 实际监听的端口
    host: str                 # 主机地址
    health_url: Optional[str] = None
    is_healthy: bool = False
    version: Optional[str] = None
    process_name: Optional[str] = None
    error: Optional[str] = None


@dataclass
class DiscoveryResult:
    instance_id: Optional[int] = None
    host: str = ""
    agents: list[DiscoveredAgent] = field(default_factory=list)
    total_ports_scanned: int = 0
    errors: list[str] = field(default_factory=list)


def _is_localhost(host: str) -> bool:
    """判断 host 是否是本机地址"""
    return host in ("127.0.0.1", "localhost", "::1", "0.0.0.0")


def _check_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """快速检测端口是否开放"""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def _check_http_health(host: str, port: int, paths: list[str], timeout: float = 2.0) -> tuple[bool, Optional[str], Optional[str]]:
    """尝试 HTTP 健康检查，返回 (healthy?, response_text, version)"""
    for path in paths:
        for scheme in ("http",):
            url = f"{scheme}://{host}:{port}{path}"
            try:
                req = urllib.request.Request(url, method="GET")
                req.add_header("User-Agent", "OntoMind-AgentDiscovery/1.0")
                # 不跟随重定向
                resp = urllib.request.urlopen(req, timeout=timeout)
                body = resp.read().decode(errors="ignore")[:2000]
                # 尝试从响应中提取版本号
                version = None
                import json as _json
                try:
                    data = _json.loads(body)
                    version = data.get("version") or data.get("app_version") or data.get("semver")
                except Exception:
                    pass
                return True, body[:200], version
            except Exception:
                continue
    return False, None, None


def _scan_processes(agent_type: str) -> Optional[DiscoveredAgent]:
    """通过进程名扫描本地运行的 Agent"""
    proc_names = KNOWN_AGENTS.get(agent_type, {}).get("proc_names", [])
    if not proc_names:
        return None

    info = KNOWN_AGENTS[agent_type]
    for proc_name in proc_names:
        try:
            # pgrep -fl 查找匹配进程
            result = subprocess.run(
                ["pgrep", "-fl", proc_name],
                capture_output=True, text=True, timeout=3,
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split("\n")
                pid, cmdline = None, None
                for line in lines:
                    parts = line.split(" ", 1)
                    if len(parts) >= 1:
                        pid = parts[0]
                        cmdline = parts[1] if len(parts) > 1 else None
                        break
                return DiscoveredAgent(
                    agent_type=agent_type,
                    label=info["label"],
                    icon=info["icon"],
                    port=0,  # 进程存在但未确定端口
                    host="localhost",
                    process_name=f"{proc_name}[{pid}]" if pid else proc_name,
                    is_healthy=True,  # 进程在运行即算健康
                )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def discover_agents(host: str, instance_id: Optional[int] = None, scan_processes: bool = True) -> DiscoveryResult:
    """扫描指定主机上运行的 Agent。

    Args:
        host: 目标主机 IP/域名
        instance_id: 关联的计算节点 ID
        scan_processes: 是否同时扫描进程（仅本地有效）

    Returns:
        DiscoveryResult 包含发现的 Agent 列表
    """
    result = DiscoveryResult(instance_id=instance_id, host=host)

    is_local = _is_localhost(host)
    scan_host = "127.0.0.1" if is_local else host

    # 1. 进程扫描（仅本地）
    proc_discovered: set[str] = set()
    if is_local and scan_processes:
        for agent_type in KNOWN_AGENTS:
            agent = _scan_processes(agent_type)
            if agent:
                result.agents.append(agent)
                proc_discovered.add(agent_type)

    # 2. 端口扫描 + HTTP 健康检查
    all_ports_to_scan: list[tuple[str, int]] = []
    for agent_type, info in KNOWN_AGENTS.items():
        for port in info["ports"]:
            all_ports_to_scan.append((agent_type, port))

    # 去重端口
    scanned_ports: set[int] = set()
    for agent_type, port in all_ports_to_scan:
        if port in scanned_ports:
            continue
        scanned_ports.add(port)
        result.total_ports_scanned += 1

        if not _check_port_open(scan_host, port):
            continue

        # 端口开放，找到对应 agent 类型
        info = KNOWN_AGENTS[agent_type]
        healthy, resp_text, version = _check_http_health(
            scan_host, port, info["health_paths"]
        )

        # 如果进程已发现且端口也是这个类型，跳过重复添加
        agent_key = f"{agent_type}:{port}"
        already_found = any(
            a.agent_type == agent_type and a.port == port
            for a in result.agents
        )

        if healthy and not already_found:
            result.agents.append(DiscoveredAgent(
                agent_type=agent_type,
                label=info["label"],
                icon=info["icon"],
                port=port,
                host=scan_host,
                health_url=f"http://{scan_host}:{port}{info['health_paths'][0]}",
                is_healthy=True,
                version=version,
            ))
        elif not healthy and not already_found:
            # 端口开放但健康检查失败
            result.agents.append(DiscoveredAgent(
                agent_type=agent_type,
                label=info["label"],
                icon=info["icon"],
                port=port,
                host=scan_host,
                is_healthy=False,
                error="端口已开放但健康检查失败",
            ))

    # 排序：healthy 的排前面
    result.agents.sort(key=lambda a: (not a.is_healthy, a.agent_type))
    return result
