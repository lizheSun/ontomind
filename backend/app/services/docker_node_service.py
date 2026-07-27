"""Docker 节点 & 容器管理服务.

支持三种连接方式：
- local: 本机 Docker（默认 unix socket）
- ssh: 远程 Docker over SSH（DOCKER_HOST=ssh://user@host[:port]）
- docker-api: 远程 Docker TCP API（TLS 可选）
"""
import json
import logging
import os
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException, NotFoundException, ValidationException
from app.db.models.docker_node_model import DockerHost
from app.db.repositories.docker_node_repo import DockerNodeRepository
from app.schemas.docker_node_schema import (
    ContainerCreate, ContainerInfo, DockerHostCreate, DockerHostResponse, NodeTestResult,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _docker_env(node: DockerHost) -> Dict[str, str]:
    """根据节点连接类型构建 docker CLI 所需的环境变量."""
    env = os.environ.copy()
    conn = node.conn_type
    if conn == "local":
        pass  # 使用默认 unix socket
    elif conn == "ssh":
        port = node.ssh_port or 22
        env["DOCKER_HOST"] = f"ssh://{node.ssh_user}@{node.address}:{port}"
    elif conn == "docker-api":
        scheme = "https" if node.tls_certs else "http"
        env["DOCKER_HOST"] = f"{scheme}://{node.address}"
        if node.tls_certs:
            env["DOCKER_TLS_VERIFY"] = "1"
            env["DOCKER_CERT_PATH"] = node.tls_certs
    return env


def _run_docker(node: DockerHost, args: List[str], timeout: int = 30) -> Tuple[int, str, str]:
    """在指定节点上执行 docker 命令，返回 (exit_code, stdout, stderr)."""
    env = _docker_env(node)
    cmd = ["docker"] + args
    try:
        proc = subprocess.run(
            cmd, env=env, capture_output=True, text=True, timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Docker 命令超时"
    except FileNotFoundError:
        return -1, "", "docker CLI 未找到，请确认已安装 Docker"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class DockerNodeService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DockerNodeRepository(db)

    # ---- 节点 CRUD ----

    def list_nodes(self) -> List[DockerHostResponse]:
        nodes = self.repo.list_ordered()
        return [DockerHostResponse.model_validate(n) for n in nodes]

    def auto_mount_local(self) -> DockerHostResponse:
        """自动探测本机 Docker 并「一键挂载」为 local 节点。

        - 如果已有本地节点（conn_type=local + address=127.0.0.1），直接刷新信息后返回
        - 如果已存在但被删除过（软删除或不存在），正常创建新节点
        """
        import socket

        # 1) 先探测 Docker 是否可用
        code, stdout, stderr = _run_docker(
            DockerHost(name="_probe", address="127.0.0.1", conn_type="local"),
            ["info", "--format", "{{.Name}}|{{.ServerVersion}}|{{.NCPU}}|{{.MemTotal}}|{{.OSType}}"],
            timeout=15,
        )
        if code != 0:
            raise BusinessException(
                f"本机 Docker 不可用: {stderr.strip()}",
                code="DOCKER_UNAVAILABLE",
            )

        info_parts = stdout.strip().split("|", 4)
        docker_name = info_parts[0] if len(info_parts) > 0 else socket.gethostname()
        server_version = info_parts[1] if len(info_parts) > 1 else ""
        ncpu = info_parts[2] if len(info_parts) > 2 else ""
        mem_raw = info_parts[3] if len(info_parts) > 3 else ""

        mem_str = ""
        if mem_raw and mem_raw.isdigit():
            gb = int(mem_raw) / (1024 * 1024 * 1024)
            mem_str = f"{gb:.1f} GB"
        else:
            mem_str = mem_raw

        # 2) 磁盘信息
        disk_str = ""
        code2, out2, _ = _run_docker(
            DockerHost(name="_probe", address="127.0.0.1", conn_type="local"),
            ["system", "df", "--format", "{{.Size}}"],
            timeout=10,
        )
        if code2 == 0:
            total_disk = 0
            for line in out2.strip().split("\n"):
                try:
                    total_disk += float(line.strip())
                except ValueError:
                    pass
            if total_disk > 0:
                disk_str = f"{total_disk:.1f} GB" if total_disk < 1000 else f"{total_disk / 1024:.1f} TB"

        # 3) 检查是否已有本地节点，有则刷新信息，无则新建
        existing = self.repo.get_local_node()
        hostname = socket.gethostname()

        if existing:
            existing.online = True
            existing.cpu = f"{ncpu} 核" if ncpu else existing.cpu
            existing.mem = mem_str or existing.mem
            existing.disk = disk_str or existing.disk
            existing.server_version = server_version or existing.server_version
            existing.remark = f"自动挂载: {hostname} ({docker_name})"
            self.db.flush()
            self.db.commit()
            logger.info(f"刷新本地 Docker 节点: {existing.name} (v{server_version}, {ncpu}核, {mem_str}, {disk_str})")
            return DockerHostResponse.model_validate(existing)

        # 智能命名
        base_name = "本机"
        candidate = base_name
        idx = 2
        while self.repo.get_by_name(candidate):
            candidate = f"{base_name}-{idx}"
            idx += 1

        payload = DockerHostCreate(
            name=candidate,
            address="127.0.0.1",
            conn_type="local",
        )
        node = DockerHost(
            **payload.model_dump(exclude_none=True),
            online=True,
            cpu=f"{ncpu} 核" if ncpu else "",
            mem=mem_str,
            disk=disk_str,
            server_version=server_version,
            remark=f"自动挂载: {hostname} ({docker_name})",
        )
        self.db.add(node)
        self.db.flush()
        self.db.commit()
        logger.info(f"一键挂载本机 Docker: {node.name} (v{server_version}, {ncpu}核, {mem_str}, {disk_str})")
        return DockerHostResponse.model_validate(node)

    def create_node(self, payload: DockerHostCreate) -> DockerHostResponse:
        existing = self.repo.get_by_name(payload.name)
        if existing:
            raise BusinessException(f"节点 '{payload.name}' 已存在", code="NODE_NAME_CONFLICT")
        if payload.conn_type == "ssh" and not payload.ssh_user:
            raise ValidationException("SSH 连接需要配置 ssh_user")
        node = DockerHost(**payload.model_dump())
        self.db.add(node)
        self.db.flush()
        self.db.commit()
        logger.info(f"创建 Docker 节点: {node.name} ({node.conn_type})")
        return DockerHostResponse.model_validate(node)

    def delete_node(self, node_id: int) -> None:
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")
        self.db.delete(node)
        self.db.flush()
        self.db.commit()
        logger.info(f"删除 Docker 节点: {node.name}")

    # ---- 节点连接测试 ----

    def test_node(self, node_id: int) -> NodeTestResult:
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")
        code, stdout, stderr = _run_docker(node, ["info", "--format", "{{.Name}} {{.ServerVersion}} {{.NCPU}} {{.MemTotal}}"], timeout=15)
        ok = code == 0
        info = stdout.strip() if ok else stderr.strip()
        if ok:
            node.online = True
        else:
            node.online = False
        self.db.flush()
        self.db.commit()
        return NodeTestResult(success=ok, message=info)

    # ---- 镜像管理 ----

    def list_images(self, node_id: int) -> List[Dict[str, str]]:
        """列出节点上的 Docker 镜像."""
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")
        code, stdout, stderr = _run_docker(
            node,
            ["images", "--format", "{{.ID}}|{{.Repository}}|{{.Tag}}|{{.Size}}|{{.CreatedAt}}"],
            timeout=15,
        )
        if code != 0:
            logger.warning(f"获取镜像列表失败: {stderr.strip()}")
            return []
        images: List[Dict[str, str]] = []
        for line in stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("|", 4)
            if len(parts) >= 3:
                images.append({
                    "id": parts[0],
                    "repository": parts[1] if len(parts) > 1 and parts[1] != "<none>" else "",
                    "tag": parts[2] if len(parts) > 2 else "latest",
                    "size": parts[3] if len(parts) > 3 else "",
                    "created_at": parts[4] if len(parts) > 4 else "",
                })
        return images

    def pull_image(self, node_id: int, image: str) -> Dict[str, str]:
        """拉取镜像（同步等待完成）."""
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")
        code, stdout, stderr = _run_docker(node, ["pull", image], timeout=300)
        if code != 0:
            raise BusinessException(f"拉取镜像失败: {stderr.strip()}", code="IMAGE_PULL_FAILED")
        return {"image": image, "output": stdout.strip()}

    def remove_image(self, node_id: int, image_full: str) -> None:
        """删除镜像."""
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")
        code, stdout, stderr = _run_docker(node, ["rmi", "-f", image_full], timeout=30)
        if code != 0:
            raise BusinessException(f"删除镜像失败: {stderr.strip()}", code="IMAGE_REMOVE_FAILED")

    # ---- 容器列表 ----

    def list_containers(self, node_id: int) -> List[ContainerInfo]:
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")
        fmt = "{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}|{{.CreatedAt}}|{{.Labels}}"
        code, stdout, stderr = _run_docker(node, ["ps", "-a", "--format", fmt], timeout=20)
        if code != 0:
            raise BusinessException(f"无法列出容器: {stderr}", code="DOCKER_ERROR")
        result: List[ContainerInfo] = []
        for line in stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("|", 6)
            if len(parts) < 6:
                continue
            cid, name, image, status_str, ports, created, labels = parts
            # 解析状态
            status_label = "unknown"
            if status_str.startswith("Up "):
                status_label = "running"
            elif status_str.startswith("Exited"):
                status_label = "exited"
            elif status_str.startswith("Created"):
                status_label = "created"
            elif "Restarting" in status_str:
                status_label = "restarting"
            elif "Paused" in status_str:
                status_label = "paused"
            # 尝试解析 expert slug
            expert_slug: Optional[str] = None
            if labels:
                for kv in labels.split(","):
                    if kv.startswith("ontomind.expert="):
                        expert_slug = kv.split("=", 1)[1]
                        break
            result.append(ContainerInfo(
                id=cid,
                name=name,
                nodeId=node_id,
                expertSlug=expert_slug,
                image=image,
                status=status_label,
                ports=ports if ports else "",
                createdAt=created,
            ))
        return result

    # ---- 容器操作 ----

    def start_container(self, node_id: int, container_id: str) -> None:
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")
        code, _, stderr = _run_docker(node, ["start", container_id])
        if code != 0:
            raise BusinessException(f"启动容器失败: {stderr}", code="DOCKER_START_ERROR")

    def stop_container(self, node_id: int, container_id: str) -> None:
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")
        code, _, stderr = _run_docker(node, ["stop", container_id])
        if code != 0:
            raise BusinessException(f"停止容器失败: {stderr}", code="DOCKER_STOP_ERROR")

    def delete_container(self, node_id: int, container_id: str, force: bool = False) -> None:
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")
        args = ["rm"]
        if force:
            args.append("-f")
        args.append(container_id)
        code, _, stderr = _run_docker(node, args)
        if code != 0:
            raise BusinessException(f"删除容器失败: {stderr}", code="DOCKER_RM_ERROR")

    def container_logs(self, node_id: int, container_id: str,
                       tail: str = "200", since: str = "") -> str:
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")
        args = ["logs", "--tail", tail, "--timestamps"]
        if since:
            args.extend(["--since", since])
        args.append(container_id)
        code, stdout, stderr = _run_docker(node, args, timeout=30)
        if code != 0:
            return f"[docker logs 失败] {stderr}"
        return stdout

    # ---- Docker Hub 镜像搜索 ----

    async def search_hub(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索 Docker Hub 官方仓库（只读，无需认证）."""
        url = "https://hub.docker.com/v2/search/repositories/"
        params = {"query": query, "page_size": min(limit, 100)}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])
                return [
                    {
                        "name": f"{r.get('namespace','')}/{r.get('name','')}".strip("/"),
                        "description": r.get("short_description", ""),
                        "stars": r.get("star_count", 0),
                        "pulls": r.get("pull_count", 0),
                        "official": r.get("is_official", False),
                    }
                    for r in results[:limit]
                ]
        except Exception as e:
            logger.warning(f"Docker Hub 搜索失败: {e}")
            return []

    # ---- 创建容器 ----

    def create_container(self, node_id: int, payload: ContainerCreate) -> ContainerInfo:
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")
        # 构建 docker run 参数
        args = ["run", "-d", "--name", payload.name]
        if payload.expert_slug:
            args.extend(["--label", f"ontomind.expert={payload.expert_slug}"])
        for binding in (payload.ports or []):
            if binding.strip():
                args.extend(["-p", binding.strip()])
        for env_kv in (payload.env_vars or []):
            if env_kv.strip():
                args.extend(["-e", env_kv.strip()])
        for vol in (payload.volumes or []):
            if vol.strip():
                args.extend(["-v", vol.strip()])
        if payload.restart_policy and payload.restart_policy != "no":
            args.extend(["--restart", payload.restart_policy])
        if payload.network:
            args.extend(["--network", payload.network])
        args.append(payload.image)
        if payload.extra_args:
            args.extend(payload.extra_args.strip().split())
        code, stdout, stderr = _run_docker(node, args, timeout=60)
        if code != 0:
            raise BusinessException(f"创建容器失败: {stderr}", code="DOCKER_CREATE_ERROR")
        created_id = stdout.strip()[:12] or "unknown"
        logger.info(f"节点 {node.name} 创建容器: {payload.name} ({created_id})")
        return ContainerInfo(
            id=created_id,
            name=payload.name,
            nodeId=node_id,
            expertSlug=payload.expert_slug,
            image=payload.image,
            status="created",
            ports=", ".join(payload.ports or []),
            createdAt="",
        )
