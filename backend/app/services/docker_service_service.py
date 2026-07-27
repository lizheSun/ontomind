"""Docker service — 管理 opencode docker 容器生命周期.

Docker 可用时：真实 `docker run/start/stop`.
Docker 不可用时：mock 模式，只在 DB 里模拟状态（host_port 落到 4096 让前端可连本机 opencode）.
"""
from __future__ import annotations

import shutil
import socket
import subprocess
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException, NotFoundException
from app.db.models.docker_service_model import DockerService
from app.db.repositories.docker_service_repo import DockerServiceRepository
from app.schemas.docker_service_schema import DockerServiceCreate, DockerServiceUpdate


def _docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        r = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True, text=True, timeout=2,
        )
        return r.returncode == 0
    except Exception:
        return False


def _find_free_port(start: int = 4200, end: int = 4400) -> int:
    for p in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", p))
                return p
        except OSError:
            continue
    raise BusinessException(
        f"端口 {start}-{end} 已用尽", code="DOCKER_PORT_EXHAUSTED"
    )


def _port_open(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _serialize(ds: DockerService) -> dict[str, Any]:
    return {
        "id": ds.id,
        "name": ds.name,
        "slug": ds.slug,
        "expert_id": ds.expert_id,
        "image": ds.image,
        "container_name": ds.container_name,
        "container_id": ds.container_id,
        "host": ds.host,
        "host_port": ds.host_port,
        "container_port": ds.container_port,
        "opencode_args": ds.opencode_args or [],
        "env": ds.env or {},
        "volumes": ds.volumes or [],
        "status": ds.status,
        "started_at": ds.started_at.isoformat() if ds.started_at else None,
        "stopped_at": ds.stopped_at.isoformat() if ds.stopped_at else None,
        "error_message": ds.error_message,
        "description": ds.description,
        "created_at": ds.created_at.isoformat() if ds.created_at else None,
        "updated_at": ds.updated_at.isoformat() if ds.updated_at else None,
        "docker_available": _docker_available(),
    }


class DockerServiceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DockerServiceRepository(db)

    def list(self, skip: int = 0, limit: int = 200) -> list[dict[str, Any]]:
        rows = self.repo.list_ordered(skip, limit)
        for ds in rows:
            self._refresh_status(ds, commit=False)
        self.db.commit()
        return [_serialize(ds) for ds in rows]

    def get(self, ds_id: int) -> dict[str, Any]:
        ds = self.repo.get_by_id(ds_id)
        if not ds:
            raise NotFoundException(f"服务不存在: {ds_id}")
        self._refresh_status(ds, commit=True)
        return _serialize(ds)

    def create(self, payload: DockerServiceCreate, user_id: Optional[int] = None) -> dict[str, Any]:
        if self.repo.get_by_slug(payload.slug):
            raise BusinessException(f"slug 已存在: {payload.slug}", code="DOCKER_SLUG_DUP")
        ds = DockerService(
            name=payload.name,
            slug=payload.slug,
            expert_id=payload.expert_id,
            image=payload.image,
            host=payload.host or "127.0.0.1",
            host_port=payload.host_port,
            container_port=payload.container_port or 4096,
            opencode_args=payload.opencode_args or [],
            env=payload.env or {},
            volumes=payload.volumes or [],
            description=payload.description,
            status="stopped",
            created_by_user_id=user_id,
        )
        self.db.add(ds)
        self.db.commit()
        self.db.refresh(ds)
        return _serialize(ds)

    def update(self, ds_id: int, payload: DockerServiceUpdate) -> dict[str, Any]:
        ds = self.repo.get_by_id(ds_id)
        if not ds:
            raise NotFoundException(f"服务不存在: {ds_id}")
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(ds, k, v)
        self.db.commit()
        self.db.refresh(ds)
        return _serialize(ds)

    def delete(self, ds_id: int) -> None:
        ds = self.repo.get_by_id(ds_id)
        if not ds:
            raise NotFoundException(f"服务不存在: {ds_id}")
        if ds.status == "running":
            try:
                self._stop_real(ds)
            except Exception:
                pass
        self.db.delete(ds)
        self.db.commit()

    def start(self, ds_id: int) -> dict[str, Any]:
        ds = self.repo.get_by_id(ds_id)
        if not ds:
            raise NotFoundException(f"服务不存在: {ds_id}")

        if _docker_available():
            self._start_real(ds)
        else:
            self._start_mock(ds)
        self.db.refresh(ds)
        return _serialize(ds)

    def stop(self, ds_id: int) -> dict[str, Any]:
        ds = self.repo.get_by_id(ds_id)
        if not ds:
            raise NotFoundException(f"服务不存在: {ds_id}")
        if _docker_available():
            self._stop_real(ds)
        else:
            self._stop_mock(ds)
        self.db.refresh(ds)
        return _serialize(ds)

    def logs(self, ds_id: int, tail: int = 200) -> str:
        ds = self.repo.get_by_id(ds_id)
        if not ds:
            raise NotFoundException(f"服务不存在: {ds_id}")
        if not _docker_available() or not ds.container_id:
            return "(docker 不可用或容器未启动 —— mock 模式无日志)"
        try:
            r = subprocess.run(
                ["docker", "logs", "--tail", str(tail), ds.container_id],
                capture_output=True, text=True, timeout=5,
            )
            return (r.stdout or "") + (r.stderr or "")
        except Exception as exc:
            return f"(读取日志失败: {exc})"

    # ---- internal ----
    def _refresh_status(self, ds: DockerService, commit: bool = False) -> None:
        if ds.status == "error":
            return
        online = _port_open(ds.host, ds.host_port or ds.container_port)
        new_status = "running" if online else "stopped"
        if ds.status != new_status:
            ds.status = new_status
            if not online and not ds.stopped_at:
                ds.stopped_at = datetime.now(timezone.utc)
        if commit:
            self.db.commit()

    def _start_mock(self, ds: DockerService) -> None:
        ds.status = "running"
        ds.started_at = datetime.now(timezone.utc)
        ds.error_message = None
        if not ds.host_port:
            ds.host_port = ds.container_port  # 回退到本机默认
        self.db.commit()

    def _stop_mock(self, ds: DockerService) -> None:
        ds.status = "stopped"
        ds.stopped_at = datetime.now(timezone.utc)
        self.db.commit()

    def _start_real(self, ds: DockerService) -> None:
        host_port = ds.host_port or _find_free_port()
        container_name = ds.container_name or f"ontomind-oc-{ds.slug}"

        # 已有容器直接 start
        existing = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name=^{container_name}$",
             "--format", "{{.ID}}"],
            capture_output=True, text=True, timeout=5,
        )
        if existing.returncode == 0 and existing.stdout.strip():
            container_id = existing.stdout.strip().split("\n")[0]
            subprocess.run(["docker", "start", container_id],
                           capture_output=True, timeout=10)
        else:
            args = [
                "docker", "run", "-d",
                "--name", container_name,
                "-p", f"{host_port}:{ds.container_port}",
            ]
            for k, v in (ds.env or {}).items():
                args.extend(["-e", f"{k}={v}"])
            for vol in (ds.volumes or []):
                host_p = vol.get("host") if isinstance(vol, dict) else None
                cont_p = vol.get("container") if isinstance(vol, dict) else None
                if host_p and cont_p:
                    args.extend(["-v", f"{host_p}:{cont_p}"])
            args.append(ds.image)
            args.extend(ds.opencode_args or [])

            run = subprocess.run(args, capture_output=True, text=True, timeout=45)
            if run.returncode != 0:
                ds.status = "error"
                ds.error_message = (run.stderr or "docker run 失败").strip()
                self.db.commit()
                raise BusinessException(
                    f"启动失败: {ds.error_message}",
                    code="DOCKER_START_FAILED", status_code=500,
                )
            container_id = run.stdout.strip()

        ds.container_id = container_id
        ds.container_name = container_name
        ds.host_port = host_port
        ds.status = "running"
        ds.started_at = datetime.now(timezone.utc)
        ds.error_message = None
        self.db.commit()

    def _stop_real(self, ds: DockerService) -> None:
        if not ds.container_id:
            self._stop_mock(ds)
            return
        subprocess.run(
            ["docker", "stop", ds.container_id],
            capture_output=True, text=True, timeout=15,
        )
        ds.status = "stopped"
        ds.stopped_at = datetime.now(timezone.utc)
        self.db.commit()
