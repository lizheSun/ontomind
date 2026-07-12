"""本机主机信息探测 — Agent Platform 与 legacy resources 共用。"""
from __future__ import annotations

import os
import platform
import socket
import subprocess


def detect_local_host_info() -> dict:
    hostname = platform.node()
    try:
        cpu = os.cpu_count() or 1
    except Exception:
        cpu = None

    memory_mb: int | None = None
    try:
        mem_bytes = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"]).decode().strip())
        memory_mb = mem_bytes // (1024 * 1024)
    except Exception:
        try:
            mem_bytes = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
            memory_mb = mem_bytes // (1024 * 1024)
        except Exception:
            memory_mb = None

    system = platform.system()
    os_map = {"Darwin": "macOS", "Linux": "Linux", "Windows": "Windows"}
    os_name = os_map.get(system, system)

    try:
        ip = socket.gethostbyname(hostname)
    except Exception:
        ip = "127.0.0.1"

    return {
        "hostname": hostname,
        "platform": os_name,
        "platform_raw": system,
        "cpu_cores": cpu,
        "memory_mb": memory_mb,
        "ip": ip,
    }
