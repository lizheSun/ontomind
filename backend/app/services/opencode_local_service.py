"""OpenCode 本地服务管理.

功能：
- 检测 opencode CLI 是否安装 / 版本
- 启动/停止 opencode web server（serve 命令）
- opencode CLI 一次性执行（run 命令），实时返回输出
- 运行记录管理
"""
import asyncio
import json
import logging
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

import psutil
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import BusinessException, NotFoundException

logger = logging.getLogger(__name__)

# ---- 运行记录（内存 + 文件，不落数据库） ----
_RUNS_DIR = Path("/tmp/ontomind/opencode/runs")
_RUNS_DIR.mkdir(parents=True, exist_ok=True)

_lock = Lock()
_next_run_id = 0

# 运行状态：running / done / error / cancelled
_run_registry: Dict[int, Dict[str, Any]] = {}


def _bump_run_id() -> int:
    global _next_run_id
    with _lock:
        _next_run_id += 1
        _next_run_id = max(_next_run_id, len(list(_RUNS_DIR.glob("*.json"))) + 1)
        return _next_run_id


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _check_opencode() -> Optional[str]:
    """返回 opencode 路径，若未安装则返回 None。"""
    path = shutil.which("opencode")
    if not path:
        path = shutil.which("opencode", path=os.path.expanduser("~/.nvm/versions/node/*/bin"))
    return path


def _opencode_version(opencode_path: str) -> str:
    """返回 opencode --version 的输出."""
    try:
        r = subprocess.run([opencode_path, "--version"], capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or r.stderr.strip()
    except Exception:
        return "unknown"


def _opencode_serve_port(port: int, cors_origins: str = "http://localhost:5173") -> subprocess.Popen:
    """启动 opencode serve 并返回 Popen 对象。"""
    cmd = [
        "opencode", "serve",
        "--port", str(port),
        "--cors", cors_origins,
    ]
    logger.info(f"启动 opencode serve: {' '.join(cmd)}")
    # 日志写到文件
    log_dir = Path("/tmp/ontomind/opencode/serve")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"serve-{port}.log"
    fout = open(str(log_file), "a")
    return subprocess.Popen(
        cmd,
        stdout=fout,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )


def _find_serve_processes() -> List[Dict[str, Any]]:
    """扫描本机正在运行的 opencode serve 进程."""
    results: List[Dict[str, Any]] = []
    for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            if not proc.info["cmdline"]:
                continue
            cmdline = proc.info["cmdline"]
            # 匹配 "opencode serve"
            if len(cmdline) < 2:
                continue
            if "opencode" not in cmdline[0] or "serve" not in cmdline[1]:
                continue
            # 解析 --port
            port = 4096
            cors = ""
            for i, arg in enumerate(cmdline):
                if arg == "--port" and i + 1 < len(cmdline):
                    try:
                        port = int(cmdline[i + 1])
                    except ValueError:
                        pass
                if arg == "--cors" and i + 1 < len(cmdline):
                    cors = cmdline[i + 1]
            results.append({
                "pid": proc.info["pid"],
                "port": port,
                "cors": cors,
                "url": f"http://127.0.0.1:{port}",
                "started_at": proc.info["create_time"],
                "cmdline": " ".join(cmdline),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return results


async def _stream_cli(cmd: List[str], timeout_sec: int = 120) -> str:
    """异步运行命令并返回 stdout 输出。"""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        stdout_bytes, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return "[超时] 执行超过 {} 秒被终止".format(timeout_sec)
    return stdout_bytes.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class OpenCodeLocalService:
    """OpenCode 本地能力服务（不依赖 DB，纯 subprocess）。"""

    # ---- 安装检测 ----

    def status(self) -> Dict[str, Any]:
        """返回 opencode 安装状态 + 版本 + 运行中的 web 实例."""
        path = _check_opencode()
        installed = path is not None
        version = _opencode_version(path) if installed else ""
        running = _find_serve_processes()
        return {
            "installed": installed,
            "path": path or "",
            "version": version,
            "running_instances": running,
        }

    # ---- Web Server 管理 ----

    def start_web(
        self, port: int = 4096, cors_origins: str = "http://localhost:5173",
        custom_args: Optional[str] = None,
    ) -> Dict[str, Any]:
        """启动 opencode serve。

        - 如果指定端口已被占用（openCode 进程），直接返回已有实例
        - 否则新启一个进程
        """
        path = _check_opencode()
        if not path:
            raise BusinessException("未检测到 opencode CLI，请先安装", code="OPENCODE_NOT_FOUND")

        # 检查端口是否已被 opencode serve 占用
        existing = _find_serve_processes()
        for r in existing:
            if r["port"] == port:
                return {
                    "pid": r["pid"],
                    "port": r["port"],
                    "url": r["url"],
                    "reused": True,
                }

        # 启动
        try:
            proc = _opencode_serve_port(port, cors_origins)
            # 等一小会儿确认没崩溃
            time.sleep(1.5)
            if proc.poll() is not None:
                # 读日志
                log_path = Path(f"/tmp/ontomind/opencode/serve/serve-{port}.log")
                last_lines = ""
                if log_path.exists():
                    last_lines = tail_file(str(log_path), 20)
                raise BusinessException(
                    f"opencode serve 启动后立刻退出（exit={proc.returncode}）\n{last_lines}",
                    code="OPENCODE_SERVE_CRASH",
                )
        except BusinessException:
            raise
        except Exception as e:
            raise BusinessException(f"启动 opencode serve 失败: {e}", code="OPENCODE_SERVE_ERROR")

        return {
            "pid": proc.pid,
            "port": port,
            "url": f"http://127.0.0.1:{port}",
            "reused": False,
        }

    def stop_web(self, port: int) -> Dict[str, Any]:
        """停止指定端口的 opencode serve 进程."""
        processes = _find_serve_processes()
        matched = [r for r in processes if r["port"] == port]
        if not matched:
            raise NotFoundException(f"未找到端口 {port} 上运行的 opencode serve 进程")

        killed = []
        for r in matched:
            try:
                os.kill(r["pid"], signal.SIGTERM)
                killed.append(r["pid"])
            except ProcessLookupError:
                pass

        # 温柔等待退出
        time.sleep(0.5)
        for pid in killed:
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass

        return {"stopped": killed, "port": port}

    def web_instances(self) -> List[Dict[str, Any]]:
        """列出所有运行中的 opencode serve 实例."""
        return _find_serve_processes()

    # ---- CLI 一次性执行 ----

    async def run_cli(
        self, prompt: str, model: Optional[str] = None,
        system_prompt: Optional[str] = None, timeout_sec: int = 120,
    ) -> Dict[str, Any]:
        """使用 opencode run 执行一次性 CLI 任务，返回运行记录."""
        path = _check_opencode()
        if not path:
            raise BusinessException("未检测到 opencode CLI", code="OPENCODE_NOT_FOUND")

        run_id = _bump_run_id()
        run_data = {
            "id": run_id,
            "prompt": prompt,
            "model": model,
            "system_prompt": system_prompt,
            "status": "running",
            "output": "",
            "started_at": time.time(),
            "finished_at": None,
        }
        _run_registry[run_id] = run_data

        # 持久化记录
        record_path = _RUNS_DIR / f"{run_id}.json"
        record_path.write_text(json.dumps(run_data, ensure_ascii=False, indent=2))

        try:
            cmd = ["opencode", "run", prompt]
            if model:
                cmd.extend(["--model", model])

            output = await _stream_cli(cmd, timeout_sec)
            run_data["status"] = "done"
            run_data["output"] = output
            run_data["finished_at"] = time.time()
        except Exception as e:
            run_data["status"] = "error"
            run_data["output"] = str(e)
            run_data["finished_at"] = time.time()

        _run_registry[run_id] = run_data
        record_path.write_text(json.dumps(run_data, ensure_ascii=False, indent=2))
        return run_data

    def list_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """列出最近的 CLI 运行记录."""
        records: List[Dict[str, Any]] = []
        json_files = sorted(_RUNS_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)
        for f in json_files[:limit]:
            try:
                records.append(json.loads(f.read_text()))
            except (json.JSONDecodeError, OSError):
                pass
        # 如果有在内存中的最新记录，以内存为准
        for r_id, r_data in _run_registry.items():
            for i, rec in enumerate(records):
                if rec.get("id") == r_id:
                    records[i] = r_data
                    break
        return records[:limit]

    def get_run(self, run_id: int) -> Dict[str, Any]:
        """获取单条 CLI 运行记录."""
        if run_id in _run_registry:
            return _run_registry[run_id]
        record_path = _RUNS_DIR / f"{run_id}.json"
        if not record_path.exists():
            raise NotFoundException(f"CLI 运行记录 #{run_id} 不存在")
        return json.loads(record_path.read_text())

    def cancel_run(self, run_id: int) -> None:
        """取消正在执行的 CLI 运行（标记为 cancelled）."""
        if run_id in _run_registry:
            run = _run_registry[run_id]
            if run["status"] == "running":
                run["status"] = "cancelled"
                run["finished_at"] = time.time()
                run["output"] = (run.get("output", "") or "") + "\n[cancelled by user]"
                record_path = _RUNS_DIR / f"{run_id}.json"
                record_path.write_text(json.dumps(run, ensure_ascii=False, indent=2))


def tail_file(path: str, n: int = 20) -> str:
    """读取文件尾 n 行."""
    try:
        with open(path) as f:
            lines = f.readlines()
            return "".join(lines[-n:])
    except OSError:
        return ""
