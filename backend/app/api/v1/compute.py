"""算力管理 API — 节点管理 + Docker 操作 + 容器终端.

端点清单：
- GET    /nodes                              — 节点列表
- GET    /nodes/local                        — 获取/创建本地节点
- POST   /nodes                              — 新增节点
- GET    /nodes/{id}                         — 节点详情
- PUT    /nodes/{id}                         — 更新节点
- DELETE /nodes/{id}                         — 删除节点
- POST   /nodes/{id}/test                    — 测试连接
- GET    /nodes/{id}/images                  — 镜像列表
- GET    /nodes/{id}/containers              — 容器列表
- POST   /nodes/{id}/containers              — 创建容器
- POST   /nodes/{id}/containers/{cid}/start   — 启动容器
- POST   /nodes/{id}/containers/{cid}/stop    — 停止容器
- POST   /nodes/{id}/containers/{cid}/restart — 重启容器
- DELETE /nodes/{id}/containers/{cid}         — 删除容器
- GET    /nodes/{id}/containers/{cid}/logs    — 容器日志
- GET    /nodes/{id}/containers/{cid}/inspect — 容器详情
- WS     /nodes/{id}/containers/{cid}/console — WebSocket 终端（PTY + resize）
"""
import asyncio
import fcntl
import json
import logging
import os as os_module
import struct
import termios
from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from app.core.authorization import require_permission, PlatformPermission
from app.db.session import get_db
from app.schemas.compute_schema import (
    ComputeNodeCreate,
    ComputeNodeUpdate,
    ComputeNodeResponse,
    ConnectionTestResponse,
    ImageInfo,
    ImagePullRequest,
    ImagePullResponse,
    ContainerInfo,
    ContainerCreateRequest,
    ContainerLogsResponse,
    ContainerInspectResponse,
    ContainerUpdateRequest,
    ContainerExecRequest,
    ContainerExecResponse,
    ContainerExecLogsResponse,
    ContainerServiceResponse,
    ContainerServiceCreate,
    ServiceRefreshResult,
    ServiceLaunchRequest,
    AideContainerSource,
)
from app.services.compute_service import ComputeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compute", tags=["算力管理"])


def get_compute_service(db: Session = Depends(get_db)) -> ComputeService:
    return ComputeService(db)


# ==================== 节点管理 ====================

@router.get("/nodes/local", response_model=ComputeNodeResponse)
def get_or_create_local_node(service: ComputeService = Depends(get_compute_service)):
    """获取或自动创建本地节点。"""
    return service.ensure_local_node()


@router.get("/nodes", response_model=list[ComputeNodeResponse])
def list_nodes(service: ComputeService = Depends(get_compute_service)):
    """列出所有节点。"""
    return service.list_nodes()


@router.post("/nodes", response_model=ComputeNodeResponse)
def create_node(
    data: ComputeNodeCreate,
    service: ComputeService = Depends(get_compute_service),
):
    """新增 SSH 节点。"""
    return service.create_node(data)


@router.get("/nodes/{node_id}", response_model=ComputeNodeResponse)
def get_node(node_id: int, service: ComputeService = Depends(get_compute_service)):
    """节点详情。"""
    return service.get_node(node_id)


@router.put("/nodes/{node_id}", response_model=ComputeNodeResponse)
def update_node(
    node_id: int,
    data: ComputeNodeUpdate,
    service: ComputeService = Depends(get_compute_service),
):
    """更新节点配置。"""
    return service.update_node(node_id, data)


@router.delete("/nodes/{node_id}")
def delete_node(node_id: int, service: ComputeService = Depends(get_compute_service)):
    """删除节点（本地节点不可删）。"""
    service.delete_node(node_id)
    return {"code": "SUCCESS", "message": "节点已删除", "data": None}


@router.post("/nodes/{node_id}/test", response_model=ConnectionTestResponse)
async def test_connection(
    node_id: int,
    service: ComputeService = Depends(get_compute_service),
):
    """测试节点 SSH 连通性和 Docker 可用性。"""
    return await service.test_connection(node_id)


# ==================== Docker 镜像 ====================

@router.get("/nodes/{node_id}/images", response_model=list[ImageInfo])
async def list_images(
    node_id: int,
    service: ComputeService = Depends(get_compute_service),
):
    """列出节点上的 Docker 镜像。"""
    return await service.list_images(node_id)


@router.post("/nodes/{node_id}/images/pull", response_model=ImagePullResponse)
async def pull_image(
    node_id: int,
    data: ImagePullRequest,
    service: ComputeService = Depends(get_compute_service),
):
    """拉取镜像到节点（长耗时操作，最长 15 分钟）。"""
    return await service.pull_image(node_id, data.image)


# ==================== Docker 容器 ====================

@router.get("/nodes/{node_id}/containers", response_model=list[ContainerInfo])
async def list_containers(
    node_id: int,
    all: bool = Query(False, description="是否包含已停止的容器"),
    service: ComputeService = Depends(get_compute_service),
):
    """列出节点上的 Docker 容器。"""
    return await service.list_containers(node_id, all_containers=all)


@router.post("/nodes/{node_id}/containers", response_model=ContainerInfo)
async def create_container(
    node_id: int,
    data: ContainerCreateRequest,
    service: ComputeService = Depends(get_compute_service),
):
    """创建并启动容器。"""
    return await service.create_container(node_id, data)


@router.post("/nodes/{node_id}/containers/{container_id}/start", response_model=ContainerInfo)
async def start_container(
    node_id: int,
    container_id: str,
    service: ComputeService = Depends(get_compute_service),
):
    """启动容器。"""
    return await service.start_container(node_id, container_id)


@router.post("/nodes/{node_id}/containers/{container_id}/stop", response_model=ContainerInfo)
async def stop_container(
    node_id: int,
    container_id: str,
    service: ComputeService = Depends(get_compute_service),
):
    """停止容器。"""
    return await service.stop_container(node_id, container_id)


@router.post("/nodes/{node_id}/containers/{container_id}/restart", response_model=ContainerInfo)
async def restart_container(
    node_id: int,
    container_id: str,
    service: ComputeService = Depends(get_compute_service),
):
    """重启容器。"""
    return await service.restart_container(node_id, container_id)


@router.delete("/nodes/{node_id}/containers/{container_id}")
async def remove_container(
    node_id: int,
    container_id: str,
    force: bool = Query(False, description="强制删除（包括运行中的容器）"),
    service: ComputeService = Depends(get_compute_service),
):
    """删除容器。"""
    await service.remove_container(node_id, container_id, force=force)
    return {"code": "SUCCESS", "message": "容器已删除", "data": None}


@router.get("/nodes/{node_id}/containers/{container_id}/logs", response_model=ContainerLogsResponse)
async def get_container_logs(
    node_id: int,
    container_id: str,
    tail: int = Query(100, description="返回最近的日志行数"),
    service: ComputeService = Depends(get_compute_service),
):
    """获取容器日志。"""
    return await service.get_container_logs(node_id, container_id, tail=tail)


@router.get("/nodes/{node_id}/containers/{container_id}/inspect", response_model=ContainerInspectResponse)
async def inspect_container(
    node_id: int,
    container_id: str,
    service: ComputeService = Depends(get_compute_service),
):
    """查看容器详细信息。"""
    return await service.inspect_container(node_id, container_id)


@router.get("/nodes/{node_id}/containers/{container_id}/shells")
async def detect_container_shells(
    node_id: int,
    container_id: str,
    service: ComputeService = Depends(get_compute_service),
):
    """探测容器内可用的 shell（供控制台自动选择，避免硬编码 /bin/bash 失败）。"""
    shells = await service.detect_shells(node_id, container_id)
    return {"shells": shells, "default": shells[0] if shells else None}


# ==================== 容器预设 ====================

@router.get("/container-presets")
def list_container_presets():
    """列出新建容器的预设模板（带完整示例配置，用户直接选而不用手写）。"""
    return ComputeService.list_container_presets()


# ==================== WebSocket 容器终端 ====================

# 协议：
#   前端 → 后端:  Binary WS frame = 终端键盘输入 (stdin)
#                 Text  WS frame = {"type":"resize","rows":N,"cols":M}
#   后端 → 前端:  Binary WS frame = PTY stdout 输出（含 ANSI 转义序列）

@router.websocket("/nodes/{node_id}/containers/{container_id}/console")
async def container_console(
    websocket: WebSocket,
    node_id: int,
    container_id: str,
    cmd: str = Query("/bin/bash", description="终端命令"),
):
    await websocket.accept()

    from app.db.session import get_session_factory

    session_factory = get_session_factory()
    db = session_factory()

    conn = None  # type: ignore[assignment]
    master_fd: int | None = None
    proc = None  # type: ignore[assignment]
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    try:
        service = ComputeService(db)
        node = service.repo.get_by_id(node_id)
        if not node:
            await websocket.send_text(json.dumps({"error": "节点不存在"}))
            await websocket.close()
            return

        # 自动选 shell：请求的不存在则回退（避免镜像没有 bash 时直接失败）
        try:
            shell = await service.resolve_shell(node_id, container_id, cmd)
        except Exception as e:
            detail = getattr(e, "message", None) or str(e)
            await websocket.send_text(json.dumps({"error": detail}))
            await websocket.close()
            return
        if shell != cmd:
            await websocket.send_text(json.dumps({
                "notice": f"容器内无 {cmd}，已自动使用 {shell}",
                "shell": shell,
            }))

        # ---- 启动终端 ----
        if node.is_local:
            master_fd, proc = await service.exec_terminal_local(container_id, shell)
            ssh_process = None

            def resize_pty(rows: int, cols: int) -> None:
                """调整本地 PTY 窗口大小。"""
                try:
                    winsize = struct.pack("HHHH", rows, cols, 0, 0)
                    fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
                except OSError as e:
                    logger.warning(f"PTY resize 失败: {e}")
        else:
            ssh_process, conn = await service.exec_terminal_remote(node, container_id, shell)
            master_fd = None

            def resize_pty(rows: int, cols: int) -> None:
                """调整远程 SSH PTY 窗口大小。"""
                ssh_process.change_terminal_size(cols, rows, 0, 0)

        # ---- PTY → WebSocket（输出方向）- 阻塞读跑在线程池----
        async def pty_to_ws():
            try:
                while not stop_event.is_set():
                    if node.is_local:
                        # 阻塞读 PTY master fd → 输出给前端
                        data = await loop.run_in_executor(
                            None, os_module.read, master_fd, 4096
                        )
                    else:
                        data = await ssh_process.stdout.read(4096)

                    if not data:
                        break
                    await websocket.send_bytes(data)
            except (OSError, asyncio.CancelledError):
                pass
            except Exception as e:
                logger.debug(f"PTY 读结束: {e}")

        # ---- WebSocket → PTY（输入方向）----
        async def ws_to_pty():
            try:
                while not stop_event.is_set():
                    msg = await websocket.receive()

                    if msg.get("type") == "websocket.disconnect":
                        break

                    if "bytes" in msg:
                        # Binary = 键盘输入 → 写入 PTY
                        data = msg["bytes"]
                        if node.is_local:
                            await loop.run_in_executor(
                                None, os_module.write, master_fd, data
                            )
                        else:
                            ssh_process.stdin.write(data)

                    elif "text" in msg:
                        # Text JSON = 控制消息（resize）
                        try:
                            ctrl = json.loads(msg["text"])
                            if ctrl.get("type") == "resize":
                                rows = int(ctrl["rows"])
                                cols = int(ctrl["cols"])
                                resize_pty(rows, cols)
                        except (json.JSONDecodeError, KeyError, ValueError):
                            pass

            except WebSocketDisconnect:
                pass
            except Exception as e:
                logger.debug(f"WS 读取结束: {e}")
            finally:
                stop_event.set()

        await asyncio.gather(pty_to_ws(), ws_to_pty())

    except Exception as e:
        logger.error(f"容器终端异常: {e}")
        try:
            # BusinessException 带 message 属性，优先用它（可读性更好）
            detail = getattr(e, "message", None) or str(e)
            await websocket.send_text(json.dumps({"error": detail}))
        except Exception:
            pass
    finally:
        stop_event.set()
        db.close()

        # 清理 PTY
        if master_fd is not None:
            try:
                os_module.close(master_fd)
            except OSError:
                pass
        # 清理子进程
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        # 清理 SSH
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        # 关闭 WebSocket
        try:
            await websocket.close()
        except Exception:
            pass


# ==================== 容器修改 ====================

@router.put("/nodes/{node_id}/containers/{container_id}", response_model=ContainerInfo)
async def update_container(
    node_id: int,
    container_id: str,
    data: ContainerUpdateRequest,
    service: ComputeService = Depends(get_compute_service),
):
    """修改容器配置（stop → remove → recreate）。可修改端口/卷/环境变量/重启策略。"""
    return await service.update_container(node_id, container_id, data)


# ==================== 快速命令执行 ====================

@router.get("/command-templates")
def list_command_templates():
    """列出可用的命令模板。"""
    return ComputeService.list_command_templates()


@router.post("/nodes/{node_id}/containers/{container_id}/exec", response_model=ContainerExecResponse)
async def container_exec(
    node_id: int,
    container_id: str,
    data: ContainerExecRequest,
    service: ComputeService = Depends(get_compute_service),
):
    """在容器内后台执行命令，返回 exec_id 用于查询日志。"""
    return await service.container_exec(node_id, container_id, data)


@router.get("/nodes/{node_id}/containers/{container_id}/exec/{exec_id}", response_model=ContainerExecLogsResponse)
async def get_exec_logs(
    node_id: int,
    container_id: str,
    exec_id: str,
    service: ComputeService = Depends(get_compute_service),
):
    """获取后台命令的日志和运行状态。"""
    return await service.get_exec_logs(node_id, container_id, exec_id)


# ==================== 容器服务登记（container_services） ====================
#
# 容器内起的服务是运行态，进程信息只活在容器里。这里把它落库并定期回探，
# 让「服务」页能展示状态、AIDE 页能据此列出可选源。
#
# ⚠️ DB 里的 status 是**探测快照**，不是实时值。前端必须展示 last_checked_at
#    并提供刷新入口；需要强一致时带 refresh=true。

@router.get("/services", response_model=list[ContainerServiceResponse])
async def list_services(
    node_id: Optional[int] = Query(None, description="限制到指定节点"),
    refresh: bool = Query(False, description="返回前先回探一遍真实状态"),
    service: ComputeService = Depends(get_compute_service),
):
    """列出已登记的容器服务（含最近一次探测状态）。"""
    if refresh:
        result = await service.refresh_services(node_id=node_id)
        return result.services
    return service.list_services(node_id=node_id)


@router.post("/services/refresh", response_model=ServiceRefreshResult)
async def refresh_services(
    node_id: Optional[int] = Query(None, description="限制到指定节点"),
    service: ComputeService = Depends(get_compute_service),
):
    """批量回探所有服务真实状态并写回 DB（维护状态实时性的主入口）。"""
    return await service.refresh_services(node_id=node_id)


@router.post("/services/discover", response_model=ServiceRefreshResult)
async def discover_services(
    node_id: Optional[int] = Query(None, description="限制到指定节点"),
    service: ComputeService = Depends(get_compute_service),
):
    """扫描容器，把现实中已在跑但 DB 未登记的服务补录进来，然后统一探测。"""
    return await service.discover_services(node_id=node_id)


@router.post("/nodes/{node_id}/containers/{container_id}/services", response_model=ContainerServiceResponse)
async def register_service(
    node_id: int,
    container_id: str,
    data: ContainerServiceCreate,
    service: ComputeService = Depends(get_compute_service),
):
    """手工登记一个已在容器内运行的服务（upsert，按容器+容器端口唯一）。"""
    data.container_id = container_id
    return await service.upsert_service(node_id, data)


@router.post("/nodes/{node_id}/containers/{container_id}/services/launch", response_model=ContainerServiceResponse)
async def launch_service(
    node_id: int,
    container_id: str,
    data: ServiceLaunchRequest,
    service: ComputeService = Depends(get_compute_service),
):
    """在容器内一键启动 opencode web/serve 并自动登记（强制绑 0.0.0.0）。"""
    return await service.launch_service(node_id, container_id, data)


@router.post("/services/{service_id}/refresh", response_model=ContainerServiceResponse)
async def refresh_one_service(
    service_id: int,
    service: ComputeService = Depends(get_compute_service),
):
    """回探单个服务状态。"""
    return await service.refresh_service(service_id)


@router.post("/services/{service_id}/stop", response_model=ContainerServiceResponse)
async def stop_service(
    service_id: int,
    service: ComputeService = Depends(get_compute_service),
):
    """停掉容器内该服务进程（保留登记，可再次启动）。"""
    return await service.stop_service(service_id)


@router.delete("/services/{service_id}")
def delete_service(
    service_id: int,
    service: ComputeService = Depends(get_compute_service),
):
    """删除服务登记（不影响容器内进程）。"""
    service.delete_service(service_id)
    return {"code": "SUCCESS", "message": "服务登记已删除", "data": None}


# ==================== AIDE 容器源 ====================

@router.get("/aide-sources", response_model=list[AideContainerSource])
async def list_aide_sources(
    node_id: Optional[int] = Query(None, description="限制到指定节点"),
    refresh: bool = Query(False, description="返回前先回探状态，保证实时"),
    service: ComputeService = Depends(get_compute_service),
):
    """列出可作为 AIDE 嵌入源的容器服务（读 container_services，opencode 类 + 宿主可达）。"""
    return await service.get_aide_sources(node_id=node_id, refresh=refresh)
