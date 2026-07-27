"""算力调度 API — Docker 服务管理 + 调度任务管理 + 运行记录 + 日志."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.docker_service_schema import DockerServiceCreate, DockerServiceUpdate
from app.schemas.schedule_task_schema import ScheduleTaskCreate, ScheduleTaskUpdate
from app.services.docker_service_service import DockerServiceService
from app.services.schedule_task_service import ScheduleTaskService

router = APIRouter()


def _ok(data, message: str = "操作成功"):
    return {"code": "SUCCESS", "message": message, "data": data}


# ==================== Docker Services ====================
@router.get("/docker-services")
def list_docker_services(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    _uid: int = Depends(get_current_user_id),
):
    return _ok(DockerServiceService(db).list(skip, limit))


@router.post("/docker-services")
def create_docker_service(
    payload: DockerServiceCreate,
    db: Session = Depends(get_db),
    uid: int = Depends(get_current_user_id),
):
    return _ok(DockerServiceService(db).create(payload, uid), "服务已创建")


@router.get("/docker-services/{ds_id}")
def get_docker_service(
    ds_id: int,
    db: Session = Depends(get_db),
    _uid: int = Depends(get_current_user_id),
):
    return _ok(DockerServiceService(db).get(ds_id))


@router.patch("/docker-services/{ds_id}")
def update_docker_service(
    ds_id: int,
    payload: DockerServiceUpdate,
    db: Session = Depends(get_db),
    _uid: int = Depends(get_current_user_id),
):
    return _ok(DockerServiceService(db).update(ds_id, payload), "服务已更新")


@router.delete("/docker-services/{ds_id}")
def delete_docker_service(
    ds_id: int,
    db: Session = Depends(get_db),
    _uid: int = Depends(get_current_user_id),
):
    DockerServiceService(db).delete(ds_id)
    return _ok(None, "服务已删除")


@router.post("/docker-services/{ds_id}/start")
def start_docker_service(
    ds_id: int,
    db: Session = Depends(get_db),
    _uid: int = Depends(get_current_user_id),
):
    return _ok(DockerServiceService(db).start(ds_id), "服务已启动")


@router.post("/docker-services/{ds_id}/stop")
def stop_docker_service(
    ds_id: int,
    db: Session = Depends(get_db),
    _uid: int = Depends(get_current_user_id),
):
    return _ok(DockerServiceService(db).stop(ds_id), "服务已停止")


@router.get("/docker-services/{ds_id}/logs")
def docker_service_logs(
    ds_id: int,
    tail: int = Query(200, ge=0, le=5000),
    db: Session = Depends(get_db),
    _uid: int = Depends(get_current_user_id),
):
    return _ok({"logs": DockerServiceService(db).logs(ds_id, tail)})


# ==================== Schedule Tasks ====================
@router.get("/tasks")
def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    _uid: int = Depends(get_current_user_id),
):
    return _ok(ScheduleTaskService(db).list(skip, limit))


@router.post("/tasks")
def create_task(
    payload: ScheduleTaskCreate,
    db: Session = Depends(get_db),
    uid: int = Depends(get_current_user_id),
):
    return _ok(ScheduleTaskService(db).create(payload, uid), "任务已创建")


@router.get("/tasks/{task_id}")
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    _uid: int = Depends(get_current_user_id),
):
    return _ok(ScheduleTaskService(db).get(task_id))


@router.patch("/tasks/{task_id}")
def update_task(
    task_id: int,
    payload: ScheduleTaskUpdate,
    db: Session = Depends(get_db),
    _uid: int = Depends(get_current_user_id),
):
    return _ok(ScheduleTaskService(db).update(task_id, payload), "任务已更新")


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    _uid: int = Depends(get_current_user_id),
):
    ScheduleTaskService(db).delete(task_id)
    return _ok(None, "任务已删除")


@router.post("/tasks/{task_id}/toggle")
def toggle_task(
    task_id: int,
    enabled: bool = True,
    db: Session = Depends(get_db),
    _uid: int = Depends(get_current_user_id),
):
    return _ok(ScheduleTaskService(db).toggle(task_id, enabled), "任务已更新")


@router.post("/tasks/{task_id}/trigger")
def trigger_task(
    task_id: int,
    db: Session = Depends(get_db),
    uid: int = Depends(get_current_user_id),
):
    return _ok(ScheduleTaskService(db).trigger(task_id, "manual", uid), "任务已触发")


# ==================== Task Runs ====================
@router.get("/tasks/{task_id}/runs")
def list_task_runs(
    task_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _uid: int = Depends(get_current_user_id),
):
    return _ok(ScheduleTaskService(db).list_runs(task_id, skip, limit))


@router.get("/runs/{run_id}")
def get_run(
    run_id: int,
    db: Session = Depends(get_db),
    _uid: int = Depends(get_current_user_id),
):
    return _ok(ScheduleTaskService(db).get_run(run_id))


@router.post("/runs/{run_id}/cancel")
def cancel_run(
    run_id: int,
    db: Session = Depends(get_db),
    _uid: int = Depends(get_current_user_id),
):
    return _ok(ScheduleTaskService(db).cancel_run(run_id), "运行已取消")


@router.get("/runs/{run_id}/logs")
def get_run_logs(
    run_id: int,
    since_seq: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
    _uid: int = Depends(get_current_user_id),
):
    return _ok(ScheduleTaskService(db).get_logs(run_id, since_seq, limit))