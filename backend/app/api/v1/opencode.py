"""OpenCode / AIDE 后端桥接.

AIDE 页面把 opencode 的 Web UI 以 iframe 形式嵌入平台。
本模块只负责探活与启停，**不做**消息转发 / 事件透传 / 会话存储
（iframe 内的 opencode 直接跟自己的后端通信）。

端点：
1. **GET  /web/status** — 探活，返回可 iframe 嵌入的最佳 URL
2. **POST /web/start**  — 拉起独立 `opencode web`（serve 无 UI 时的兜底）
3. **POST /web/stop**   — 停掉独立 `opencode web`

⚠️ 历史：原「对话工作台」（前端 SDK 直连 opencode serve）已于 2026-08-03 下线，
   随之删除 `/health`、`/spawn`、`/session-link` 三个端点与 `opencode_sessions` 表。
"""
from __future__ import annotations

import asyncio
import os
import shutil
import socket
import subprocess
from typing import Optional

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.v1.auth import get_current_user_id
from app.core.config import settings
from app.core.exceptions import BusinessException


router = APIRouter()

# opencode serve 端点：默认 127.0.0.1:4096（跟 opencode serve 默认一致）
OPENCODE_HOST = settings.OPENCODE_HOST
OPENCODE_PORT = settings.OPENCODE_PORT
OPENCODE_BASE = f"http://{OPENCODE_HOST}:{OPENCODE_PORT}"
DSH_WEB_HOST = settings.DSH_WEB_HOST
DSH_WEB_PORT = settings.DSH_WEB_PORT
DSH_WEB_BASE = f"http://{DSH_WEB_HOST}:{DSH_WEB_PORT}"


def _port_open(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# ============================================================
# AIDE — opencode web UI 嵌入支持
#
# 说明：opencode ≥ 1.18 的 `serve` 已内置完整浏览器 UI（GET / 返回 HTML），
#      且响应头没有 X-Frame-Options / CSP frame-ancestors，可以直接 iframe。
#      所以 AIDE 优先复用对话工作台已有的 serve(4096)；
#      只有 serve 不可用时才回退到独立 `opencode web`（默认 4097）。
# ============================================================

OPENCODE_WEB_PORT = settings.OPENCODE_WEB_PORT

# ---- 探测结果缓存（AIDE 页面会频繁调 /web/status，别每次都开子进程）----
# opencode --version 开子进程要 ~500ms，是整个 status 端点的最大开销。
# CLI 版本在进程生命周期内几乎不会变，缓存 10 分钟。
_VERSION_CACHE: dict[str, object] = {"value": None, "at": 0.0}
_VERSION_TTL = 600.0

# serve 是否内置 UI：同一个 opencode 版本行为固定，缓存 60s 足够。
_HTML_CACHE: dict[str, object] = {"value": None, "at": 0.0, "url": ""}
_HTML_TTL = 60.0


def _cli_version(cli: Optional[str]) -> str:
    """带缓存地取 opencode CLI 版本（未命中才开子进程）."""
    import time as _time

    if not cli:
        return ""
    now = _time.monotonic()
    if _VERSION_CACHE["value"] is not None and now - float(_VERSION_CACHE["at"]) < _VERSION_TTL:
        return str(_VERSION_CACHE["value"])
    try:
        r = subprocess.run(  # noqa: S603
            [cli, "--version"], capture_output=True, text=True, timeout=5,
        )
        version = (r.stdout or r.stderr).strip()
    except Exception:
        version = ""
    _VERSION_CACHE["value"] = version
    _VERSION_CACHE["at"] = now
    return version


def _is_dsh_web_cmd(low: str) -> bool:
    if "deepseek-harness" in low:
        return "web" in low or "--profile web" in low
    padded = f" {low} "
    if " dsh " in padded or low.startswith("dsh ") or "/dsh " in low or low.endswith("/dsh"):
        return "web" in low or "--profile web" in low
    return False


def _find_dsh_web_processes() -> list[dict]:
    """扫描本机 `dsh web` / `dsh --profile web` 进程."""
    try:
        import psutil
    except ImportError:
        return []
    results: list[dict] = []
    for proc in psutil.process_iter(["pid", "cmdline", "create_time"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            joined = " ".join(str(a) for a in cmdline)
            if not _is_dsh_web_cmd(joined.lower()):
                continue
            port = DSH_WEB_PORT
            for i, arg in enumerate(cmdline):
                if str(arg) == "--port" and i + 1 < len(cmdline):
                    try:
                        port = int(cmdline[i + 1])
                    except ValueError:
                        pass
            results.append({
                "pid": proc.info["pid"],
                "port": port,
                "url": f"http://{DSH_WEB_HOST}:{port}",
                "started_at": proc.info.get("create_time"),
                "cmdline": joined,
            })
        except Exception:
            continue
    return results


def _find_web_processes() -> list[dict]:
    """扫描本机 `opencode web` 进程（psutil 不可用时退化为空列表）.

    注意：遍历几百个进程要 ~50ms，只在 `?detail=1` 时才调。
    """
    try:
        import psutil
    except ImportError:
        return []
    results: list[dict] = []
    for proc in psutil.process_iter(["pid", "cmdline", "create_time"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            if len(cmdline) < 2:
                continue
            if "opencode" not in str(cmdline[0]) or cmdline[1] != "web":
                continue
            port = OPENCODE_WEB_PORT
            for i, arg in enumerate(cmdline):
                if arg == "--port" and i + 1 < len(cmdline):
                    try:
                        port = int(cmdline[i + 1])
                    except ValueError:
                        pass
            results.append({
                "pid": proc.info["pid"],
                "port": port,
                "url": f"http://{OPENCODE_HOST}:{port}",
                "started_at": proc.info.get("create_time"),
                "cmdline": " ".join(cmdline),
            })
        except Exception:
            continue
    return results


async def _serves_html(base_url: str) -> bool:
    """判断某个 opencode 端点是否直接提供 HTML UI（可 iframe）. 带 60s 缓存."""
    import time as _time

    now = _time.monotonic()
    if (
        _HTML_CACHE["value"] is not None
        and _HTML_CACHE["url"] == base_url
        and now - float(_HTML_CACHE["at"]) < _HTML_TTL
    ):
        return bool(_HTML_CACHE["value"])
    try:
        async with httpx.AsyncClient(timeout=3.0) as cli:
            # HEAD 比 GET 快（不传 body），opencode 支持
            resp = await cli.head(base_url, follow_redirects=True)
            ctype = resp.headers.get("content-type", "")
            ok = resp.status_code == 200 and "text/html" in ctype
            if not ok and resp.status_code >= 400:
                # 少数服务不支持 HEAD，回退 GET
                resp = await cli.get(base_url, follow_redirects=True)
                ctype = resp.headers.get("content-type", "")
                ok = resp.status_code == 200 and "text/html" in ctype
    except Exception:
        ok = False
    _HTML_CACHE["value"] = ok
    _HTML_CACHE["at"] = now
    _HTML_CACHE["url"] = base_url
    return ok


@router.get("/web/status")
async def web_status(fast: bool = False, detail: bool = False):
    """AIDE 页面探活：返回可 iframe 嵌入的最佳 URL.

    优先级：
    1. serve(4096) 若能直接返回 HTML（opencode ≥ 1.18）→ 直接嵌，零额外进程
    2. 已有 `opencode web` 实例 → 嵌那个
    3. 本机 DeepSeek Harness web（默认 3080）→ 嵌那个
    4. 都没有 → healthy=False，前端展示「一键拉起」

    性能参数：
    - ``fast=1``  : 只做端口探活（~4ms），跳过 HTML 探测和版本查询。前端轮询用。
    - ``detail=1``: 额外遍历进程列表（~50ms）。仅诊断/展示实例明细时用。
    """
    serve_alive = _port_open(OPENCODE_HOST, OPENCODE_PORT)
    web_alive = _port_open(OPENCODE_HOST, OPENCODE_WEB_PORT)
    dsh_alive = _port_open(DSH_WEB_HOST, DSH_WEB_PORT)
    web_url = f"http://{OPENCODE_HOST}:{OPENCODE_WEB_PORT}"

    if fast:
        # 快路径：只靠端口 + 上一次的 HTML 缓存判断，不发 HTTP、不开子进程
        cached_html = bool(_HTML_CACHE["value"]) if _HTML_CACHE["url"] == OPENCODE_BASE else True
        serve_has_ui = serve_alive and cached_html
        version = str(_VERSION_CACHE["value"] or "")
        cli_path = ""
        dsh_cli = ""
    else:
        cli_path = shutil.which("opencode") or ""
        version = _cli_version(cli_path)
        serve_has_ui = await _serves_html(OPENCODE_BASE) if serve_alive else False
        dsh_cli = shutil.which("dsh") or ""

    # 决策嵌入源：OpenCode 优先，否则本机 DSH web（默认 3080）
    if serve_has_ui:
        embed_url, source = OPENCODE_BASE, "serve"
    elif web_alive:
        embed_url, source = web_url, "web"
    elif dsh_alive:
        embed_url, source = DSH_WEB_BASE, "dsh"
    else:
        embed_url, source = "", "none"

    return {
        "code": "SUCCESS",
        "data": {
            "healthy": bool(embed_url),
            "embed_url": embed_url,
            "embed_source": source,
            "cli_installed": bool(cli_path) if not fast else bool(version),
            "cli_path": cli_path,
            "version": version,
            "serve_base_url": OPENCODE_BASE,
            "serve_port": OPENCODE_PORT,
            "serve_healthy": serve_alive,
            "serve_has_ui": serve_has_ui,
            "web_url": web_url,
            "web_port": OPENCODE_WEB_PORT,
            "web_healthy": web_alive,
            "web_instances": _find_web_processes() if detail else [],
            "dsh_web_url": DSH_WEB_BASE,
            "dsh_web_port": DSH_WEB_PORT,
            "dsh_web_healthy": dsh_alive,
            "dsh_cli_installed": bool(dsh_cli) if not fast else dsh_alive,
        },
    }


class WebStartRequest(BaseModel):
    kind: str = Field("opencode", description="opencode | dsh")
    port: int | None = Field(None, ge=1024, le=65535)
    cors: str = Field(
        "http://localhost:5173",
        description="允许的前端 origin（逗号分隔可传多个）",
    )
    hostname: str = Field("127.0.0.1", description="监听地址")


@router.post("/web/start")
async def web_start(
    payload: WebStartRequest,
    _user_id: int = Depends(get_current_user_id),
):
    """拉起本机 web UI（opencode web 或 DeepSeek Harness web）供 AIDE iframe 嵌入.

    幂等：端口已在跑则直接返回现有实例。
    """
    kind = (payload.kind or "opencode").strip().lower()
    if kind == "dsh":
        return await _start_dsh_web(payload)
    return await _start_opencode_web(payload)


async def _start_opencode_web(payload: WebStartRequest) -> dict:
    port = payload.port or OPENCODE_WEB_PORT
    if _port_open(OPENCODE_HOST, port):
        return {
            "code": "SUCCESS",
            "message": "opencode web 已在运行",
            "data": {
                "already_running": True,
                "kind": "opencode",
                "port": port,
                "url": f"http://{OPENCODE_HOST}:{port}",
            },
        }

    cli = shutil.which("opencode")
    if not cli:
        raise BusinessException(
            "本机未找到 opencode CLI，请先安装："
            "curl -fsSL https://opencode.ai/install | bash",
            code="OPENCODE_CLI_NOT_FOUND",
            status_code=400,
        )

    args = [cli, "web", "--port", str(port), "--hostname", payload.hostname]
    for origin in (payload.cors or "").split(","):
        origin = origin.strip()
        if origin:
            args.extend(["--cors", origin])

    env = os.environ.copy()
    env.setdefault("OPENCODE_NO_OPEN", "1")
    env.setdefault("BROWSER", "none")

    proc = subprocess.Popen(  # noqa: S603
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env=env,
    )

    for _ in range(150):
        if _port_open(OPENCODE_HOST, port):
            _HTML_CACHE["value"] = None
            _HTML_CACHE["at"] = 0.0
            _HTML_CACHE["url"] = ""
            return {
                "code": "SUCCESS",
                "message": "opencode web 已启动",
                "data": {
                    "already_running": False,
                    "kind": "opencode",
                    "pid": proc.pid,
                    "port": port,
                    "url": f"http://{OPENCODE_HOST}:{port}",
                },
            }
        await asyncio.sleep(0.1)

    raise BusinessException(
        f"opencode web 启动超时（15s 内端口 {port} 未就绪），"
        f"请手工执行 `opencode web --port {port}` 排查",
        code="OPENCODE_WEB_START_TIMEOUT",
        status_code=500,
    )


async def _start_dsh_web(payload: WebStartRequest) -> dict:
    port = payload.port or DSH_WEB_PORT
    if _port_open(DSH_WEB_HOST, port):
        return {
            "code": "SUCCESS",
            "message": "DeepSeek Harness web 已在运行",
            "data": {
                "already_running": True,
                "kind": "dsh",
                "port": port,
                "url": f"http://{DSH_WEB_HOST}:{port}",
            },
        }

    cli = shutil.which("dsh")
    if not cli:
        raise BusinessException(
            "本机未找到 dsh CLI。请安装 DeepSeek Harness，或手工执行："
            "`dsh --profile web`（默认 http://127.0.0.1:3080/）",
            code="DSH_CLI_NOT_FOUND",
            status_code=400,
        )

    env = os.environ.copy()
    env.setdefault("BROWSER", "none")
    args = [cli, "web", "--no-open", "--host", payload.hostname, "--port", str(port)]
    proc = subprocess.Popen(  # noqa: S603
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env=env,
    )

    for _ in range(150):
        if _port_open(DSH_WEB_HOST, port):
            return {
                "code": "SUCCESS",
                "message": "DeepSeek Harness web 已启动",
                "data": {
                    "already_running": False,
                    "kind": "dsh",
                    "pid": proc.pid,
                    "port": port,
                    "url": f"http://{DSH_WEB_HOST}:{port}",
                },
            }
        await asyncio.sleep(0.1)

    raise BusinessException(
        f"DSH web 启动超时（15s 内端口 {port} 未就绪）。"
        f"请手工执行 `dsh --profile web` 或 `dsh web --port {port}`",
        code="DSH_WEB_START_TIMEOUT",
        status_code=500,
    )


class WebStopRequest(BaseModel):
    kind: str = Field("opencode", description="opencode | dsh")
    port: int | None = Field(None, ge=1024, le=65535)


@router.post("/web/stop")
async def web_stop(
    payload: WebStopRequest,
    _user_id: int = Depends(get_current_user_id),
):
    """停掉指定端口的本机 web UI."""
    import signal as _signal

    kind = (payload.kind or "opencode").strip().lower()
    if kind == "dsh":
        port = payload.port or DSH_WEB_PORT
        matched = [p for p in _find_dsh_web_processes() if p["port"] == port]
        label = "DeepSeek Harness web"
    else:
        port = payload.port or OPENCODE_WEB_PORT
        matched = [p for p in _find_web_processes() if p["port"] == port]
        label = "opencode web"

    if not matched:
        return {
            "code": "SUCCESS",
            "message": f"端口 {port} 上没有 {label} 进程",
            "data": {"stopped": [], "port": port, "kind": kind},
        }

    killed: list[int] = []
    for p in matched:
        try:
            os.kill(p["pid"], _signal.SIGTERM)
            killed.append(p["pid"])
        except ProcessLookupError:
            pass

    await asyncio.sleep(0.5)
    for pid in killed:
        try:
            os.kill(pid, _signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass

    _HTML_CACHE["value"] = None
    _HTML_CACHE["at"] = 0.0
    _HTML_CACHE["url"] = ""

    return {
        "code": "SUCCESS",
        "message": f"已停止端口 {port} 的 {label}",
        "data": {"stopped": killed, "port": port, "kind": kind},
    }


