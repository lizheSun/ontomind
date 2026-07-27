"""算力调度 API — 节点管理 / 镜像管理 / 容器管理 / Docker Hub 搜索 / 调度任务 / 运行记录 / 日志 / 本地 OpenCode 服务."""
from typing import Dict, List, Optional

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.docker_node_schema import (
    ContainerCreate, ContainerInfo, DockerHostCreate, DockerHostResponse,
    ImageInfo, NodeTestResult, PullImageRequest,
)
from app.schemas.schedule_task_schema import (
    ScheduleTaskCreate, ScheduleTaskResponse, ScheduleTaskUpdate,
    TaskRunResponse,
)
from app.services.docker_node_service import DockerNodeService
from app.services.opencode_local_service import OpenCodeLocalService
from app.services.schedule_task_service import ScheduleTaskService

router = APIRouter()


# =========================================================================
# 节点管理
# =========================================================================

@router.get("/nodes", response_model=Dict[str, object])
def list_nodes(db: Session = Depends(get_db)):
    svc = DockerNodeService(db)
    nodes = svc.list_nodes()
    return {"code": "SUCCESS", "message": "ok", "data": [n.model_dump() for n in nodes]}


@router.post("/nodes", response_model=Dict[str, object])
def create_node(payload: DockerHostCreate, db: Session = Depends(get_db)):
    svc = DockerNodeService(db)
    node = svc.create_node(payload)
    return {"code": "SUCCESS", "message": "节点创建成功", "data": node.model_dump()}


@router.delete("/nodes/{node_id}", response_model=Dict[str, object])
def delete_node(node_id: int, db: Session = Depends(get_db)):
    svc = DockerNodeService(db)
    svc.delete_node(node_id)
    return {"code": "SUCCESS", "message": "节点已删除", "data": None}


@router.post("/nodes/{node_id}/test", response_model=Dict[str, object])
def test_node(node_id: int, db: Session = Depends(get_db)):
    svc = DockerNodeService(db)
    result = svc.test_node(node_id)
    return {"code": "SUCCESS", "message": "ok", "data": result.model_dump()}


@router.post("/nodes/auto-mount-local", response_model=Dict[str, object])
def auto_mount_local(db: Session = Depends(get_db)):
    """一键挂载本机 Docker：自动探测并创建 local 节点。"""
    svc = DockerNodeService(db)
    node = svc.auto_mount_local()
    return {"code": "SUCCESS", "message": f"已挂载本机 Docker 节点: {node.name}", "data": node.model_dump()}


# =========================================================================
# 容器管理（在指定节点上）
# =========================================================================

@router.get("/nodes/{node_id}/containers", response_model=Dict[str, object])
def list_containers(node_id: int, db: Session = Depends(get_db)):
    svc = DockerNodeService(db)
    containers = svc.list_containers(node_id)
    return {"code": "SUCCESS", "message": "ok", "data": [c.model_dump() for c in containers]}


@router.post("/nodes/{node_id}/containers", response_model=Dict[str, object])
def create_container(node_id: int, payload: ContainerCreate, db: Session = Depends(get_db)):
    svc = DockerNodeService(db)
    container = svc.create_container(node_id, payload)
    return {"code": "SUCCESS", "message": "容器创建成功", "data": container.model_dump()}


@router.post("/nodes/{node_id}/containers/{cid}/start", response_model=Dict[str, object])
def start_container(node_id: int, cid: str, db: Session = Depends(get_db)):
    svc = DockerNodeService(db)
    svc.start_container(node_id, cid)
    return {"code": "SUCCESS", "message": "已启动", "data": None}


@router.post("/nodes/{node_id}/containers/{cid}/stop", response_model=Dict[str, object])
def stop_container(node_id: int, cid: str, db: Session = Depends(get_db)):
    svc = DockerNodeService(db)
    svc.stop_container(node_id, cid)
    return {"code": "SUCCESS", "message": "已停止", "data": None}


@router.delete("/nodes/{node_id}/containers/{cid}", response_model=Dict[str, object])
def delete_container(node_id: int, cid: str, force: bool = Query(False), db: Session = Depends(get_db)):
    svc = DockerNodeService(db)
    svc.delete_container(node_id, cid, force=force)
    return {"code": "SUCCESS", "message": "已删除", "data": None}


@router.get("/nodes/{node_id}/containers/{cid}/logs", response_model=Dict[str, object])
def container_logs(
    node_id: int, cid: str,
    tail: str = Query("200"), since: str = Query(""),
    db: Session = Depends(get_db),
):
    svc = DockerNodeService(db)
    logs = svc.container_logs(node_id, cid, tail=tail, since=since)
    return {"code": "SUCCESS", "message": "ok", "data": logs}


# =========================================================================
# Docker Hub 搜索
# =========================================================================

@router.get("/hub-search", response_model=Dict[str, object])
async def search_hub(q: str = Query(""), limit: int = Query(10), db: Session = Depends(get_db)):
    svc = DockerNodeService(db)
    results = await svc.search_hub(q, limit=limit)
    return {"code": "SUCCESS", "message": "ok", "data": results}


# =========================================================================
# 镜像管理（在指定节点上）
# =========================================================================

@router.get("/nodes/{node_id}/images", response_model=Dict[str, object])
def list_images(node_id: int, db: Session = Depends(get_db)):
    svc = DockerNodeService(db)
    images = svc.list_images(node_id)
    return {"code": "SUCCESS", "message": "ok", "data": images}


@router.post("/nodes/{node_id}/images/pull", response_model=Dict[str, object])
def pull_image(node_id: int, payload: PullImageRequest, db: Session = Depends(get_db)):
    svc = DockerNodeService(db)
    result = svc.pull_image(node_id, payload.image)
    return {"code": "SUCCESS", "message": f"镜像 {payload.image} 拉取成功", "data": result}


@router.delete("/nodes/{node_id}/images/path/{image_name:path}", response_model=Dict[str, object])
def remove_image(node_id: int, image_name: str, db: Session = Depends(get_db)):
    svc = DockerNodeService(db)
    svc.remove_image(node_id, image_name)
    return {"code": "SUCCESS", "message": f"镜像 {image_name} 已删除", "data": None}


# =========================================================================
# 调度任务
# =========================================================================

@router.get("/tasks", response_model=Dict[str, object])
def list_tasks(
    schedule_type: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    search: str = Query(""),
    skip: int = Query(0), limit: int = Query(200),
    db: Session = Depends(get_db),
):
    svc = ScheduleTaskService(db)
    tasks = svc.list_tasks(schedule_type=schedule_type, enabled=enabled,
                           search=search, skip=skip, limit=limit)
    return {"code": "SUCCESS", "message": "ok", "data": [t.model_dump() for t in tasks]}


@router.post("/tasks", response_model=Dict[str, object])
def create_task(payload: ScheduleTaskCreate, db: Session = Depends(get_db)):
    svc = ScheduleTaskService(db)
    task = svc.create_task(payload)
    return {"code": "SUCCESS", "message": "任务创建成功", "data": task.model_dump()}


@router.get("/tasks/{task_id}", response_model=Dict[str, object])
def get_task(task_id: int, db: Session = Depends(get_db)):
    svc = ScheduleTaskService(db)
    task = svc.get_task(task_id)
    return {"code": "SUCCESS", "message": "ok", "data": task.model_dump()}


@router.patch("/tasks/{task_id}", response_model=Dict[str, object])
def update_task(task_id: int, payload: ScheduleTaskUpdate, db: Session = Depends(get_db)):
    svc = ScheduleTaskService(db)
    task = svc.update_task(task_id, payload)
    return {"code": "SUCCESS", "message": "任务已更新", "data": task.model_dump()}


@router.delete("/tasks/{task_id}", response_model=Dict[str, object])
def delete_task(task_id: int, db: Session = Depends(get_db)):
    svc = ScheduleTaskService(db)
    svc.delete_task(task_id)
    return {"code": "SUCCESS", "message": "任务已删除", "data": None}


@router.post("/tasks/{task_id}/toggle", response_model=Dict[str, object])
def toggle_task(task_id: int, db: Session = Depends(get_db)):
    svc = ScheduleTaskService(db)
    task = svc.toggle_enabled(task_id)
    return {"code": "SUCCESS", "message": "ok", "data": task.model_dump()}


@router.post("/tasks/{task_id}/trigger", response_model=Dict[str, object])
def trigger_task(task_id: int, trigger: str = Query("manual"), db: Session = Depends(get_db)):
    svc = ScheduleTaskService(db)
    run = svc.trigger(task_id, trigger=trigger)
    return {"code": "SUCCESS", "message": "任务已触发", "data": run.model_dump()}


# =========================================================================
# 运行记录
# =========================================================================

@router.get("/tasks/{task_id}/runs", response_model=Dict[str, object])
def list_task_runs(
    task_id: int,
    status: Optional[str] = Query(None),
    trigger: Optional[str] = Query(None),
    skip: int = Query(0), limit: int = Query(50),
    db: Session = Depends(get_db),
):
    svc = ScheduleTaskService(db)
    runs = svc.list_runs(task_id=task_id, status=status, trigger=trigger, skip=skip, limit=limit)
    return {"code": "SUCCESS", "message": "ok", "data": [r.model_dump() for r in runs]}


@router.get("/runs", response_model=Dict[str, object])
def list_runs(
    task_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    trigger: Optional[str] = Query(None),
    skip: int = Query(0), limit: int = Query(50),
    db: Session = Depends(get_db),
):
    svc = ScheduleTaskService(db)
    runs = svc.list_runs(task_id=task_id, status=status, trigger=trigger, skip=skip, limit=limit)
    return {"code": "SUCCESS", "message": "ok", "data": [r.model_dump() for r in runs]}


@router.get("/runs/{run_id}", response_model=Dict[str, object])
def get_run(run_id: int, db: Session = Depends(get_db)):
    svc = ScheduleTaskService(db)
    run = svc.get_run(run_id)
    return {"code": "SUCCESS", "message": "ok", "data": run.model_dump()}


@router.post("/runs/{run_id}/cancel", response_model=Dict[str, object])
def cancel_run(run_id: int, db: Session = Depends(get_db)):
    svc = ScheduleTaskService(db)
    run = svc.cancel_run(run_id)
    return {"code": "SUCCESS", "message": "运行已取消", "data": run.model_dump()}


# =========================================================================
# 运行日志（读日志文件）
# =========================================================================

@router.get("/runs/{run_id}/logs", response_model=Dict[str, object])
def get_run_logs(
    run_id: int,
    since_line: int = Query(0, description="增量读取：从第 N 行之后的行"),
    tail: int = Query(500, description="since_line=0 时取最后 N 行"),
    db: Session = Depends(get_db),
):
    svc = ScheduleTaskService(db)
    run_obj = svc.get_run(run_id)
    lines = svc.read_logs(run_obj.log_file, since_line=since_line, tail=tail)
    return {"code": "SUCCESS", "message": "ok", "data": {
        "lines": lines,
        "totalLines": len(lines),
        "sinceLine": since_line,
        "runStatus": run_obj.status,
    }}


# =========================================================================
# 本地 OpenCode 服务（检查 / 启停 web / CLI 一次性执行）
# =========================================================================

@router.get("/opencode/status", response_model=Dict[str, object])
def opencode_status():
    svc = OpenCodeLocalService()
    return {"code": "SUCCESS", "message": "ok", "data": svc.status()}


@router.post("/opencode/start-web", response_model=Dict[str, object])
def opencode_start_web(
    port: int = Body(4096, embed=True),
    cors_origins: str = Body("http://localhost:5173", embed=True),
):
    """启动 opencode serve（默认 4096 端口）。"""
    svc = OpenCodeLocalService()
    result = svc.start_web(port=port, cors_origins=cors_origins)
    return {"code": "SUCCESS", "message": f"opencode serve 已启动: {result['url']}", "data": result}


@router.post("/opencode/stop-web", response_model=Dict[str, object])
def opencode_stop_web(port: int = Body(..., embed=True)):
    """停止指定端口的 opencode serve。"""
    svc = OpenCodeLocalService()
    result = svc.stop_web(port)
    return {"code": "SUCCESS", "message": f"已停止端口 {port} 的 opencode serve", "data": result}


@router.get("/opencode/web-instances", response_model=Dict[str, object])
def opencode_web_instances():
    svc = OpenCodeLocalService()
    return {"code": "SUCCESS", "message": "ok", "data": svc.web_instances()}


@router.post("/opencode/run-cli", response_model=Dict[str, object])
async def opencode_run_cli(
    prompt: str = Body(..., embed=True),
    model: Optional[str] = Body(None, embed=True),
    timeout_sec: int = Body(120, embed=True),
):
    """执行 opencode run 一次性 CLI 任务，返回输出结果。"""
    svc = OpenCodeLocalService()
    result = await svc.run_cli(prompt=prompt, model=model, timeout_sec=timeout_sec)
    return {"code": "SUCCESS", "message": "ok", "data": result}


@router.get("/opencode/runs", response_model=Dict[str, object])
def opencode_list_runs(limit: int = Query(20)):
    svc = OpenCodeLocalService()
    return {"code": "SUCCESS", "message": "ok", "data": svc.list_runs(limit=limit)}


@router.get("/opencode/runs/{run_id}", response_model=Dict[str, object])
def opencode_get_run(run_id: int):
    svc = OpenCodeLocalService()
    return {"code": "SUCCESS", "message": "ok", "data": svc.get_run(run_id)}
