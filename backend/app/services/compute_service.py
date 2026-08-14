"""算力管理 Service — 节点管理 + Docker 操作 + 容器终端.

本地节点使用 docker SDK，远程节点通过 SSH 执行 docker CLI。
"""
import asyncio
import base64
import hashlib
import json
import logging
import re
import shlex
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.exceptions import BusinessException, NotFoundException, ValidationException
from app.db.models.compute_node_model import (
    ComputeNode,
    NodeStatus,
    AuthType,
)
from app.db.repositories.compute_node_repo import ComputeNodeRepository
from app.schemas.compute_schema import (
    ComputeNodeCreate,
    ComputeNodeUpdate,
    ComputeNodeResponse,
    ConnectionTestResponse,
    ImageInfo,
    ImagePullResponse,
    ContainerInfo,
    ContainerCreateRequest,
    ContainerLogsResponse,
    ContainerInspectResponse,
    ContainerUpdateRequest,
    ContainerExecRequest,
    ContainerExecResponse,
    ContainerExecLogsResponse,
    AideContainerSource,
    PortMapping,
    VolumeMapping,
    EnvVar,
    ContainerServiceResponse,
    ContainerServiceCreate,
    ServiceRefreshResult,
    ServiceLaunchRequest,
)
from app.db.models.container_service_model import (
    ContainerService,
    ServiceKind,
    ServiceStatus,
)
from app.db.repositories.container_service_repo import ContainerServiceRepository

logger = logging.getLogger(__name__)

# 容器内常见 shell 候选，按优先级排序（控制台自动探测用）
SHELL_CANDIDATES = ["/bin/bash", "/bin/ash", "/bin/sh"]

# AIDE 可嵌入的 opencode 服务类型
_AIDE_KINDS = {ServiceKind.OPENCODE_WEB, ServiceKind.OPENCODE_SERVE}

# ---------------------------------------------------------------------------
# 短 TTL 缓存
#
# 为什么需要：`list_containers` 要对每个容器做 docker inspect 并查镜像 ENV/CMD，
# 单次约 0.5–2s。而 AIDE 轮询 + 服务刷新 + 发布校验会在几秒内反复调它，
# 叠加起来能把连接池和 Docker daemon 都打满（实测出现过
# `QueuePool limit of size 10 overflow 20 reached`）。
#
# 容器列表在 3s 内几乎不会变，缓存足够安全；需要强一致的路径（如发布后回读）
# 显式传 `fresh=True` 绕过。
# ---------------------------------------------------------------------------
_CONTAINERS_TTL = 3.0
_LISTEN_TTL = 3.0
# {(node_id, all): (expire_at, [ContainerInfo])}
_containers_cache: Dict[Any, Any] = {}
# {(node_id, container_id): (expire_at, {port: bind})}
_listen_cache: Dict[Any, Any] = {}


def _cache_get(store: Dict[Any, Any], key: Any) -> Any:
    hit = store.get(key)
    if not hit:
        return None
    expire_at, value = hit
    if time.monotonic() > expire_at:
        store.pop(key, None)
        return None
    return value


def _cache_put(store: Dict[Any, Any], key: Any, value: Any, ttl: float) -> None:
    store[key] = (time.monotonic() + ttl, value)
    # 顺手清理过期项，避免长期运行后无界增长
    if len(store) > 64:
        now = time.monotonic()
        for k in [k for k, (exp, _) in store.items() if exp < now]:
            store.pop(k, None)


def invalidate_container_cache(node_id: Optional[int] = None) -> None:
    """容器发生变更（创建/删除/启停/重建）后必须失效缓存，否则会读到旧状态。"""
    if node_id is None:
        _containers_cache.clear()
        _listen_cache.clear()
        return
    for k in [k for k in _containers_cache if k[0] == node_id]:
        _containers_cache.pop(k, None)
    for k in [k for k in _listen_cache if k[0] == node_id]:
        _listen_cache.pop(k, None)


# ---- 密码加密工具（基于 SECRET_KEY 派生 AES key） ----

def _get_cipher() -> Fernet:
    """用 SECRET_KEY 派生出 Fernet 兼容的 32 字节 key。"""
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def _encrypt(plain: str) -> str:
    if not plain:
        return ""
    return _get_cipher().encrypt(plain.encode()).decode()


def _decrypt(cipher: str) -> str:
    if not cipher:
        return ""
    return _get_cipher().decrypt(cipher.encode()).decode()


# ---- Docker 操作辅助 ----

def _parse_docker_table(output: str, headers: List[str]) -> List[Dict[str, str]]:
    """解析 docker CLI 表格输出为 dict 列表。"""
    lines = output.strip().split("\n")
    if len(lines) <= 1:
        return []
    # 跳过表头
    results = []
    for line in lines[1:]:
        parts = re.split(r"\s{2,}", line.strip())
        row = {}
        for i, header in enumerate(headers):
            row[header] = parts[i] if i < len(parts) else ""
        results.append(row)
    return results


def _get_ssh_command(node: ComputeNode, cmd: str) -> str:
    """生成 SSH + docker 命令。"""
    return f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p {node.port} {node.username}@{node.host} {cmd}"


async def _ssh_exec(node: ComputeNode, command: str, timeout: int = 30) -> str:
    """通过 asyncssh 远程执行命令并返回 stdout。"""
    import asyncssh

    connect_kwargs: Dict[str, Any] = {
        "host": node.host,
        "port": node.port,
        "username": node.username,
        "known_hosts": None,
        "connect_timeout": 10,
    }
    if node.auth_type == AuthType.PASSWORD.value:
        connect_kwargs["password"] = _decrypt(node.password or "")
    else:
        key_data = _decrypt(node.private_key or "")
        connect_kwargs["client_keys"] = [asyncssh.import_private_key(key_data)]

    try:
        async with asyncssh.connect(**connect_kwargs) as conn:
            result = await conn.run(command, timeout=timeout)
            if result.exit_status != 0 and result.exit_status is not None:
                stderr = result.stderr or ""
                if "Is the docker daemon running" in stderr:
                    raise BusinessException("远程节点上的 Docker 未运行", "DOCKER_NOT_RUNNING")
                raise BusinessException(
                    f"命令执行失败 (exit={result.exit_status}): {stderr[:200]}",
                    "SSH_COMMAND_ERROR",
                )
            return result.stdout or ""
    except asyncssh.Error as e:
        raise BusinessException(f"SSH 连接/执行失败: {e}", "SSH_ERROR")
    except OSError as e:
        raise BusinessException(f"网络不可达: {e}", "SSH_CONNECT_ERROR")


# ---- docker inspect → 结构化配置 ----

def _ports_from_inspect(insp: Dict[str, Any]) -> List[PortMapping]:
    """从 docker inspect 还原端口映射。

    Docker 的 PortBindings/Ports 结构是 {"<containerPort>/<proto>": [{HostIp, HostPort}, ...]}，
    同一个容器端口通常同时有 IPv4(0.0.0.0) 和 IPv6(::) 两条绑定，需要去重。
    """
    host_config = insp.get("HostConfig") or {}
    net_settings = insp.get("NetworkSettings") or {}
    # 优先用 HostConfig.PortBindings（创建时的声明，容器停止后依然存在）
    raw = host_config.get("PortBindings") or net_settings.get("Ports") or {}

    seen: set = set()
    result: List[PortMapping] = []
    for key, bindings in raw.items():
        if not bindings:
            continue
        # key 形如 "80/tcp"
        parts = str(key).split("/")
        try:
            container_port = int(parts[0])
        except (ValueError, IndexError):
            continue
        protocol = parts[1] if len(parts) > 1 and parts[1] in ("tcp", "udp") else "tcp"
        for b in bindings:
            if not isinstance(b, dict):
                continue
            hp = b.get("HostPort")
            if not hp:
                continue
            try:
                host_port = int(hp)
            except (TypeError, ValueError):
                continue
            dedup_key = (host_port, container_port, protocol)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            result.append(PortMapping(
                host_port=host_port, container_port=container_port, protocol=protocol,
            ))
    result.sort(key=lambda p: (p.host_port, p.container_port))
    return result


def _volumes_from_inspect(insp: Dict[str, Any]) -> List[VolumeMapping]:
    """从 docker inspect 还原卷挂载（bind + named volume）。"""
    result: List[VolumeMapping] = []
    for m in insp.get("Mounts") or []:
        if not isinstance(m, dict):
            continue
        mtype = m.get("Type")
        dst = m.get("Destination") or ""
        if not dst:
            continue
        if mtype == "volume":
            src = m.get("Name") or ""
        else:
            src = m.get("Source") or ""
        if not src:
            continue
        result.append(VolumeMapping(
            host_path=src, container_path=dst, read_only=not m.get("RW", True),
        ))
    return result


def _envs_from_inspect(insp: Dict[str, Any], image_envs: Optional[List[str]] = None) -> List[EnvVar]:
    """从 docker inspect 还原环境变量，过滤掉镜像自带的默认值。

    容器的 Config.Env 包含「镜像 ENV + 创建时 -e」两部分。
    直接全部回填会导致重建时把镜像默认值写死（例如 PATH），
    所以要减去镜像自身声明的 ENV。
    """
    base = set(image_envs or [])
    result: List[EnvVar] = []
    for item in (insp.get("Config") or {}).get("Env") or []:
        if not isinstance(item, str) or item in base:
            continue
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        # 环境变量名必须符合 schema 的 pattern，不合法的跳过（避免整个响应 500）
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", k):
            continue
        result.append(EnvVar(key=k, value=v))
    return result


def _command_from_inspect(insp: Dict[str, Any], image_cmd: Optional[List[str]] = None) -> str:
    """从 docker inspect 还原启动命令；与镜像默认 CMD 相同时返回空串。"""
    config = insp.get("Config") or {}
    cmd = config.get("Cmd") or []
    if not cmd:
        return ""
    if image_cmd and list(cmd) == list(image_cmd):
        return ""   # 与镜像默认一致 → 视为「未覆盖」
    return " ".join(str(c) for c in cmd)


def _entrypoint_from_inspect(
    insp: Dict[str, Any], image_entrypoint: Optional[List[str]] = None
) -> Optional[List[str]]:
    """还原自定义 entrypoint；与镜像默认一致则返回 None（表示不覆盖）。

    重建容器时如果只带 Cmd 不带 Entrypoint，
    原来用 `--entrypoint` 覆盖过的容器会退回镜像默认 entrypoint，
    导致「改个端口后容器起不来了」。
    """
    config = insp.get("Config") or {}
    ep = config.get("Entrypoint")
    if not ep:
        return None
    if image_entrypoint and list(ep) == list(image_entrypoint):
        return None
    return [str(x) for x in ep]


def _network_from_inspect(insp: Dict[str, Any]) -> str:
    host_config = insp.get("HostConfig") or {}
    mode = host_config.get("NetworkMode") or ""
    if mode in ("default", ""):
        return "bridge"
    return str(mode)


def _restart_from_inspect(insp: Dict[str, Any]) -> str:
    host_config = insp.get("HostConfig") or {}
    name = ((host_config.get("RestartPolicy") or {}).get("Name") or "no")
    return str(name) or "no"


def _ports_display(mappings: List[PortMapping]) -> str:
    return ", ".join(m.display() for m in mappings)


# ---- 容器内端口监听探测（/proc/net/tcp 解析） ----

# 探测容器内 LISTEN 端口 + 绑定地址。
# 不用 ss/netstat：精简镜像（alpine/distroless/openeuler-min）常常没有这些命令，
# 而 /proc/net/tcp 是内核接口，一定存在。
_PROBE_LISTEN_CMD = (
    "awk 'NR>1 && $4==\"0A\" {print $2}' /proc/net/tcp 2>/dev/null; "
    "awk 'NR>1 && $4==\"0A\" {print $2}' /proc/net/tcp6 2>/dev/null"
)


def _parse_listen_table(raw: str) -> Dict[int, str]:
    """解析 /proc/net/tcp 的 local_address 列 → {端口: 绑定地址}.

    格式是 `<hex-ip>:<hex-port>`，IP 为小端 hex。只需区分三类：
    - 00000000 (IPv4 0.0.0.0) / 0…0 (IPv6 ::) → 全网卡，宿主可访问
    - 0100007F (IPv4 127.0.0.1)               → 仅容器内，宿主访问不到
    - 其它                                     → 具体网卡地址
    """
    result: Dict[int, str] = {}
    for line in (raw or "").split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        ip_hex, _, port_hex = line.rpartition(":")
        try:
            port = int(port_hex, 16)
        except ValueError:
            continue
        if port <= 0 or port > 65535:
            continue

        ip_hex = ip_hex.upper()
        if ip_hex in ("00000000", "00000000000000000000000000000000"):
            bind = "0.0.0.0"
        elif ip_hex == "0100007F":
            bind = "127.0.0.1"
        elif set(ip_hex) <= {"0"}:
            bind = "0.0.0.0"
        elif ip_hex.endswith("0100007F") or ip_hex == "00000000000000000000000001000000":
            bind = "127.0.0.1"
        else:
            bind = f"0x{ip_hex}"

        # 同端口同时有 v4/v6 时，优先记 0.0.0.0（能被宿主访问的那个）
        prev = result.get(port)
        if prev is None or (prev == "127.0.0.1" and bind == "0.0.0.0"):
            result[port] = bind
    return result


def _default_service_name(kind: ServiceKind, port: int) -> str:
    if kind == ServiceKind.OPENCODE_WEB:
        return f"opencode web :{port}"
    if kind == ServiceKind.OPENCODE_SERVE:
        return f"opencode serve :{port}"
    return f"service :{port}"


def _detect_kind_from_command(cmd: str) -> ServiceKind:
    """从启动命令猜服务类型（自动登记时用）."""
    low = (cmd or "").lower()
    if "opencode" not in low:
        return ServiceKind.OTHER
    if " serve" in low or low.endswith("serve"):
        return ServiceKind.OPENCODE_SERVE
    if " web" in low or low.endswith("web"):
        return ServiceKind.OPENCODE_WEB
    return ServiceKind.OTHER


def _extract_port_from_command(cmd: str, default: Optional[int] = None) -> Optional[int]:
    """从命令里抓 --port <n>."""
    m = re.search(r"--port[= ]+(\d{1,5})", cmd or "")
    if m:
        try:
            p = int(m.group(1))
            if 1 <= p <= 65535:
                return p
        except ValueError:
            pass
    return default



class ComputeService:
    """算力管理服务"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ComputeNodeRepository(db)
        self.svc_repo = ContainerServiceRepository(db)

    # ==================== 节点管理 ====================

    def _to_response(self, node: ComputeNode) -> ComputeNodeResponse:
        return ComputeNodeResponse(
            id=node.id,
            name=node.name,
            description=node.description,
            host=node.host,
            port=node.port,
            username=node.username,
            auth_type=node.auth_type.value if isinstance(node.auth_type, AuthType) else node.auth_type,
            is_local=node.is_local,
            status=node.status.value if isinstance(node.status, NodeStatus) else node.status,
            last_checked_at=node.last_checked_at,
            created_at=node.created_at,
            updated_at=node.updated_at,
        )

    def ensure_local_node(self) -> ComputeNodeResponse:
        """确保本地节点存在，不存在则自动创建。"""
        local = self.repo.get_local_node()
        if local:
            return self._to_response(local)
        # 自动创建本地节点
        local = self.repo.create({
            "name": "localhost",
            "description": "本机 Docker 环境",
            "host": "127.0.0.1",
            "port": 22,
            "username": "root",
            "auth_type": AuthType.PASSWORD,
            "is_local": True,
            "status": NodeStatus.UNKNOWN,
        })
        self.db.commit()
        return self._to_response(local)

    def list_nodes(self) -> List[ComputeNodeResponse]:
        nodes = self.repo.get_all()
        return [self._to_response(n) for n in nodes]

    def get_node(self, node_id: int) -> ComputeNodeResponse:
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")
        return self._to_response(node)

    def create_node(self, data: ComputeNodeCreate) -> ComputeNodeResponse:
        existing = self.repo.get_by_name(data.name)
        if existing:
            raise BusinessException(f"节点名称 '{data.name}' 已存在", "DUPLICATE_NAME")

        create_dict = data.model_dump(exclude_unset=True)
        # 加密敏感字段
        if create_dict.get("password"):
            create_dict["password"] = _encrypt(create_dict["password"])
        if create_dict.get("private_key"):
            create_dict["private_key"] = _encrypt(create_dict["private_key"])

        node = self.repo.create(create_dict)
        self.db.commit()
        return self._to_response(node)

    def update_node(self, node_id: int, data: ComputeNodeUpdate) -> ComputeNodeResponse:
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")

        update_dict = data.model_dump(exclude_unset=True, exclude_none=True)
        # 名称唯一性检查
        if "name" in update_dict and update_dict["name"] != node.name:
            existing = self.repo.get_by_name(update_dict["name"])
            if existing:
                raise BusinessException(f"节点名称 '{update_dict['name']}' 已存在", "DUPLICATE_NAME")
        # 加密敏感字段
        if update_dict.get("password"):
            update_dict["password"] = _encrypt(update_dict["password"])
        if update_dict.get("private_key"):
            update_dict["private_key"] = _encrypt(update_dict["private_key"])

        updated = self.repo.update(node_id, update_dict)
        self.db.commit()
        return self._to_response(updated)

    def delete_node(self, node_id: int) -> bool:
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")
        if node.is_local:
            raise BusinessException("本地节点不可删除", "CANNOT_DELETE_LOCAL")
        self.repo.delete(node_id)
        self.db.commit()
        return True

    async def test_connection(self, node_id: int) -> ConnectionTestResponse:
        """测试节点 SSH 连通性和 Docker 可用性。"""
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")

        try:
            if node.is_local:
                # 本地节点：检查 Docker socket
                proc = await asyncio.create_subprocess_exec(
                    "docker", "info",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
                if proc.returncode != 0:
                    raise BusinessException(
                        f"Docker 不可用: {(stderr or b'').decode()[:200]}",
                        "DOCKER_NOT_RUNNING",
                    )
                message = "本地 Docker 连接正常"
            else:
                # 远程节点：SSH 连接并检查 docker
                output = await _ssh_exec(node, "docker info --format '{{.ServerVersion}}'")
                message = f"SSH 连接成功，Docker 版本: {output.strip()}"
                node.status = NodeStatus.ONLINE
        except BusinessException:
            node.status = NodeStatus.OFFLINE
            node.last_checked_at = datetime.now(timezone.utc)
            self.db.commit()
            raise
        except Exception as e:
            node.status = NodeStatus.OFFLINE
            node.last_checked_at = datetime.now(timezone.utc)
            self.db.commit()
            raise BusinessException(f"连接失败: {e}", "CONNECTION_FAILED")

        node.status = NodeStatus.ONLINE
        node.last_checked_at = datetime.now(timezone.utc)
        self.db.commit()
        return ConnectionTestResponse(success=True, message=message, node_id=node_id)

    # ==================== Docker 操作（本地） ====================

    def _local_docker(self):
        """获取本地 Docker 客户端。"""
        import docker
        try:
            # timeout 防止 daemon 无响应时无限挂起（默认 60s 对 pull 不够，单独放大）
            return docker.from_env(timeout=120)
        except docker.errors.DockerException as e:
            raise BusinessException(
                f"无法连接本地 Docker：{e}。请确认 Docker Desktop / dockerd 已启动。",
                "DOCKER_CONNECT_ERROR",
            )

    # ==================== 镜像管理 ====================

    async def list_images(self, node_id: int) -> List[ImageInfo]:
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")

        if node.is_local:
            return await asyncio.to_thread(self._list_images_local)
        else:
            output = await _ssh_exec(node, "docker images --format '{{.ID}}\t{{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}'")
            return self._parse_images_output(output)

    def _list_images_local(self) -> List[ImageInfo]:
        client = self._local_docker()
        images = client.images.list()
        result = []
        for img in images:
            tags = img.tags if img.tags else ["<none>:<none>"]
            size = self._format_size(img.attrs.get("Size", 0))
            created = img.attrs.get("Created", "")[:19]
            result.append(ImageInfo(
                id=img.short_id.replace("sha256:", ""),
                tags=tags,
                size=size,
                created=created,
            ))
        return result

    def _parse_images_output(self, output: str) -> List[ImageInfo]:
        result = []
        for line in output.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            img_id = parts[0]
            repo = parts[1]
            tag = parts[2]
            size = parts[3]
            created = parts[4] if len(parts) > 4 else ""
            tag_str = f"{repo}:{tag}" if repo and repo != "<none>" else tag
            result.append(ImageInfo(id=img_id, tags=[tag_str], size=size, created=created))
        return result

    # ==================== 容器管理 ====================

    async def list_containers(self, node_id: int, all_containers: bool = False, fresh: bool = False) -> List[ContainerInfo]:
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")

        if not fresh:
            cached = _cache_get(_containers_cache, (node_id, all_containers))
            if cached is not None:
                return cached

        if node.is_local:
            result = await asyncio.to_thread(self._list_containers_local, all_containers)
        else:
            result = await self._list_containers_remote(node, all_containers)

        _cache_put(_containers_cache, (node_id, all_containers), result, _CONTAINERS_TTL)
        return result

    def _list_containers_local(self, all_containers: bool) -> List[ContainerInfo]:
        client = self._local_docker()
        containers = client.containers.list(all=all_containers)
        result: List[ContainerInfo] = []
        # 镜像 ENV/CMD 缓存，用于过滤容器 env 里镜像自带的默认值
        image_cache: Dict[str, Dict[str, Any]] = {}

        for c in containers:
            insp = c.attrs or {}
            image_ref = (insp.get("Config") or {}).get("Image") or ""
            if image_ref and image_ref not in image_cache:
                try:
                    img = client.images.get(image_ref)
                    icfg = (img.attrs or {}).get("Config") or {}
                    image_cache[image_ref] = {
                        "env": icfg.get("Env") or [],
                        "cmd": icfg.get("Cmd") or [],
                    }
                except Exception:
                    image_cache[image_ref] = {"env": [], "cmd": []}
            meta = image_cache.get(image_ref, {"env": [], "cmd": []})

            port_mappings = _ports_from_inspect(insp)
            state = insp.get("State") or {}
            try:
                image_name = ", ".join(c.image.tags) if c.image and c.image.tags else (
                    c.image.short_id if c.image else image_ref
                )
            except Exception:
                image_name = image_ref

            result.append(ContainerInfo(
                id=c.short_id,
                name=c.name,
                image=image_name,
                status=c.status,
                ports=_ports_display(port_mappings),
                created=(insp.get("Created") or "")[:19],
                port_mappings=port_mappings,
                volume_mappings=_volumes_from_inspect(insp),
                env_vars=_envs_from_inspect(insp, meta["env"]),
                command=_command_from_inspect(insp, meta["cmd"]),
                restart=_restart_from_inspect(insp),
                network=_network_from_inspect(insp),
                state_detail=state.get("Status") or c.status,
                exit_code=state.get("ExitCode"),
            ))
        return result

    async def _list_containers_remote(
        self, node: ComputeNode, all_containers: bool
    ) -> List[ContainerInfo]:
        """远程节点：用 docker inspect 拿全量 JSON，保证与本地口径一致。"""
        flag = "-a" if all_containers else ""
        ids_out = await _ssh_exec(node, f"docker ps {flag} -q")
        ids = [i.strip() for i in ids_out.strip().split("\n") if i.strip()]
        if not ids:
            return []

        raw = await _ssh_exec(node, f"docker inspect {' '.join(ids)}", timeout=60)
        try:
            items = json.loads(raw)
        except json.JSONDecodeError:
            raise BusinessException("解析远程容器信息失败", "INSPECT_ERROR")

        result: List[ContainerInfo] = []
        for insp in items:
            if not isinstance(insp, dict):
                continue
            config = insp.get("Config") or {}
            state = insp.get("State") or {}
            port_mappings = _ports_from_inspect(insp)
            result.append(ContainerInfo(
                id=(insp.get("Id") or "")[:12],
                name=(insp.get("Name") or "").lstrip("/"),
                image=config.get("Image") or "",
                status=state.get("Status") or "unknown",
                ports=_ports_display(port_mappings),
                created=(insp.get("Created") or "")[:19],
                port_mappings=port_mappings,
                volume_mappings=_volumes_from_inspect(insp),
                # 远程不额外查镜像 ENV（多一次 SSH 往返不划算），全量返回
                env_vars=_envs_from_inspect(insp),
                command=_command_from_inspect(insp),
                restart=_restart_from_inspect(insp),
                network=_network_from_inspect(insp),
                state_detail=state.get("Status") or "",
                exit_code=state.get("ExitCode"),
            ))
        return result

    async def create_container(self, node_id: int, data: ContainerCreateRequest) -> ContainerInfo:
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")

        self._validate_container_request(data)

        # 创建整体加超时上限：镜像缺失时会触发拉取，网络不可达时 docker SDK 会长时间挂起，
        # 没有这层超时就是「点了新建容器一直转圈、最后什么提示都没有」。
        timeout = 900 if data.auto_pull else 120
        try:
            if node.is_local:
                return await asyncio.wait_for(
                    asyncio.to_thread(self._create_container_local, data), timeout=timeout,
                )
            return await asyncio.wait_for(
                self._create_container_remote(node, data), timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise BusinessException(
                f"创建容器超时（>{timeout}s）。常见原因：镜像 '{data.image}' 需要联网拉取但网络不可达。"
                f"建议先在「镜像」页确认镜像已存在，或关闭「自动拉取」后重试。",
                "CONTAINER_CREATE_TIMEOUT",
            )

    @staticmethod
    def _validate_container_request(data: ContainerCreateRequest) -> None:
        """创建前的语义校验，把错误挡在 docker 调用之前，给出可执行的提示。"""
        if not data.image or not data.image.strip():
            raise ValidationException("镜像不能为空，例如 nginx:1.27-alpine", "IMAGE_REQUIRED")

        # 容器路径必须是绝对路径
        for v in data.volumes:
            if not v.container_path.startswith("/"):
                raise ValidationException(
                    f"容器内路径必须是绝对路径：'{v.container_path}' 应写成 '/{v.container_path.lstrip('/')}'",
                    "VOLUME_PATH_INVALID",
                )
            # 宿主侧要么绝对路径，要么合法的命名卷
            hp = v.host_path
            if not hp.startswith("/") and not re.match(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$", hp):
                raise ValidationException(
                    f"宿主路径 '{hp}' 非法：应为绝对路径（/data/app）或命名卷（appdata）",
                    "VOLUME_HOST_INVALID",
                )

        # host 网络下端口映射无效，直接提示而不是静默丢弃
        if data.network == "host" and data.ports:
            raise ValidationException(
                "network=host 时容器直接使用宿主网络，不能再做端口映射，请移除端口映射或改用 bridge",
                "PORTS_WITH_HOST_NETWORK",
            )

        # 宿主端口不能在同一次请求里重复
        seen: set = set()
        for p in data.ports:
            key = (p.host_port, p.protocol)
            if key in seen:
                raise ValidationException(
                    f"宿主端口 {p.host_port}/{p.protocol} 重复映射，请检查端口配置",
                    "PORT_DUPLICATED",
                )
            seen.add(key)

    def _ensure_image_local(self, client, image: str, auto_pull: bool) -> None:
        """确保镜像在本地存在。

        原实现直接 containers.run()，镜像缺失时 docker SDK 会隐式 pull，
        在无外网/镜像不存在时会长时间挂起且没有任何可读错误 —— 这是「创建容器一直转圈」的根因。
        现在改成显式检查 + 显式拉取 + 明确报错。
        """
        import docker

        try:
            client.images.get(image)
            return
        except docker.errors.ImageNotFound:
            pass
        except docker.errors.APIError as e:
            raise BusinessException(f"检查镜像失败: {e}", "IMAGE_INSPECT_ERROR")

        if not auto_pull:
            raise BusinessException(
                f"本地不存在镜像 '{image}'，且未开启自动拉取。请先在「镜像」页拉取该镜像。",
                "IMAGE_NOT_FOUND",
            )

        try:
            logger.info(f"本地无镜像 {image}，开始拉取")
            client.images.pull(image)
        except docker.errors.NotFound:
            raise BusinessException(
                f"镜像 '{image}' 在仓库中不存在，请检查镜像名和 tag 是否正确",
                "IMAGE_NOT_IN_REGISTRY",
            )
        except docker.errors.APIError as e:
            msg = str(e)
            if "unauthorized" in msg.lower():
                raise BusinessException(
                    f"拉取镜像 '{image}' 未授权，请先 docker login 或改用公开镜像", "IMAGE_UNAUTHORIZED",
                )
            raise BusinessException(
                f"拉取镜像 '{image}' 失败（通常是网络不可达或镜像仓库不可用）：{msg[:300]}",
                "IMAGE_PULL_ERROR",
            )

    def _create_container_local(self, data: ContainerCreateRequest) -> ContainerInfo:
        import docker

        client = self._local_docker()
        self._ensure_image_local(client, data.image, data.auto_pull)

        kwargs: Dict[str, Any] = {"image": data.image, "detach": True}
        if data.name:
            kwargs["name"] = data.name
        if data.command:
            # shlex 切分，避免整串被当成单个 argv 传进去
            kwargs["command"] = shlex.split(data.command)
        if data.entrypoint:
            kwargs["entrypoint"] = data.entrypoint
        if data.ports:
            # docker SDK: {"<containerPort>/<proto>": hostPort}
            # 注意方向 —— 旧实现把宿主/容器端口写反了
            kwargs["ports"] = {p.to_docker_key(): p.host_port for p in data.ports}
        if data.envs:
            kwargs["environment"] = [e.to_cli() for e in data.envs]
        if data.volumes:
            kwargs["volumes"] = {
                v.host_path: {"bind": v.container_path, "mode": "ro" if v.read_only else "rw"}
                for v in data.volumes
            }
        if data.restart and data.restart != "no":
            kwargs["restart_policy"] = {"Name": data.restart}
        if data.network and data.network != "bridge":
            kwargs["network_mode"] = data.network

        try:
            if data.start:
                container = client.containers.run(**kwargs)
            else:
                kwargs.pop("detach", None)
                container = client.containers.create(**kwargs)
        except docker.errors.APIError as e:
            raise BusinessException(self._explain_docker_error(e, data), "CONTAINER_CREATE_ERROR")
        except Exception as e:
            raise BusinessException(f"创建容器失败: {e}", "CONTAINER_CREATE_ERROR")

        # 重新读取真实状态，而不是回显请求内容
        try:
            container.reload()
        except Exception:
            pass
        invalidate_container_cache()   # 容器集合变了
        return self._container_info_from_sdk(client, container)

    @staticmethod
    def _explain_docker_error(err: Exception, data: ContainerCreateRequest) -> str:
        """把 docker 的原始报错翻译成用户能直接行动的中文提示。"""
        msg = str(err)
        low = msg.lower()
        if "already in use" in low or "conflict" in low:
            return (
                f"容器名 '{data.name}' 已被占用。请换一个名字，"
                f"或先删除同名容器后重试。"
            )
        if "port is already allocated" in low or "address already in use" in low:
            ports = ", ".join(str(p.host_port) for p in data.ports) or "?"
            return (
                f"宿主端口 {ports} 已被其他进程/容器占用。请改用别的宿主端口。"
            )
        if "no such image" in low or "not found" in low:
            return f"镜像 '{data.image}' 不存在，请检查镜像名与 tag。"
        if "invalid mount" in low or "mount" in low and "denied" in low:
            return (
                f"挂载被拒绝：请确认宿主路径存在且 Docker 有权访问（macOS 需在 "
                f"Docker Desktop → Settings → Resources → File Sharing 中授权该目录）。原始信息：{msg[:200]}"
            )
        if "network" in low and ("not found" in low or "no such" in low):
            return f"网络 '{data.network}' 不存在，请先创建该 Docker 网络或改用 bridge。"
        return f"创建容器失败: {msg[:400]}"

    def _container_info_from_sdk(self, client, container) -> ContainerInfo:
        """把 docker SDK 的 container 对象转成 ContainerInfo（含结构化配置）。"""
        try:
            insp = container.attrs or {}
        except Exception:
            insp = {}
        config = insp.get("Config") or {}
        state = insp.get("State") or {}
        image_ref = config.get("Image") or ""
        image_env: List[str] = []
        image_cmd: List[str] = []
        if image_ref:
            try:
                icfg = (client.images.get(image_ref).attrs or {}).get("Config") or {}
                image_env = icfg.get("Env") or []
                image_cmd = icfg.get("Cmd") or []
            except Exception:
                pass

        port_mappings = _ports_from_inspect(insp)
        try:
            image_name = ", ".join(container.image.tags) if container.image and container.image.tags else image_ref
        except Exception:
            image_name = image_ref

        return ContainerInfo(
            id=container.short_id,
            name=container.name,
            image=image_name,
            status=container.status,
            ports=_ports_display(port_mappings),
            created=(insp.get("Created") or "")[:19],
            port_mappings=port_mappings,
            volume_mappings=_volumes_from_inspect(insp),
            env_vars=_envs_from_inspect(insp, image_env),
            command=_command_from_inspect(insp, image_cmd),
            restart=_restart_from_inspect(insp),
            network=_network_from_inspect(insp),
            state_detail=state.get("Status") or container.status,
            exit_code=state.get("ExitCode"),
        )

    async def _create_container_remote(self, node: ComputeNode, data: ContainerCreateRequest) -> ContainerInfo:
        # 远程：先确认镜像存在，避免 docker run 隐式 pull 卡住 SSH 会话
        if data.auto_pull:
            check = await _ssh_exec(
                node,
                f"docker image inspect {shlex.quote(data.image)} >/dev/null 2>&1 && echo EXISTS || echo MISSING",
            )
            if "MISSING" in check:
                logger.info(f"远程节点 {node.name} 无镜像 {data.image}，开始拉取")
                await _ssh_exec(node, f"docker pull {shlex.quote(data.image)}", timeout=600)

        cmd_parts = ["docker", "run", "-d" if data.start else "--rm=false"]
        if not data.start:
            cmd_parts = ["docker", "create"]
        if data.name:
            cmd_parts += ["--name", shlex.quote(data.name)]
        for p in data.ports:
            cmd_parts += ["-p", p.to_cli()]
        for e in data.envs:
            cmd_parts += ["-e", shlex.quote(e.to_cli())]
        for v in data.volumes:
            cmd_parts += ["-v", shlex.quote(v.to_cli())]
        if data.restart and data.restart != "no":
            cmd_parts += [f"--restart={data.restart}"]
        if data.network and data.network != "bridge":
            cmd_parts += ["--network", shlex.quote(data.network)]
        if data.entrypoint:
            # docker run 只支持单个 --entrypoint（可执行文件），额外参数走 command
            cmd_parts += ["--entrypoint", shlex.quote(data.entrypoint[0])]
        cmd_parts.append(shlex.quote(data.image))
        if data.entrypoint and len(data.entrypoint) > 1:
            cmd_parts += [shlex.quote(a) for a in data.entrypoint[1:]]
        if data.command:
            cmd_parts.append(data.command)

        cmd = " ".join(cmd_parts)
        try:
            container_id = (await _ssh_exec(node, cmd, timeout=120)).strip().split("\n")[-1]
        except BusinessException as e:
            raise BusinessException(self._explain_docker_error(e, data), "CONTAINER_CREATE_ERROR")

        if not container_id:
            raise BusinessException("远程创建容器未返回容器 ID", "CONTAINER_CREATE_ERROR")

        # 回读真实状态
        remote = await self._list_containers_remote(node, all_containers=True)
        for c in remote:
            if container_id.startswith(c.id) or c.id.startswith(container_id[:12]):
                return c
        return ContainerInfo(
            id=container_id[:12],
            name=data.name or container_id[:12],
            image=data.image,
            status="running" if data.start else "created",
            ports=_ports_display(data.ports),
            port_mappings=data.ports,
            volume_mappings=data.volumes,
            env_vars=data.envs,
            command=data.command or "",
            restart=data.restart,
            network=data.network or "bridge",
        )

    async def start_container(self, node_id: int, container_id: str) -> ContainerInfo:
        return await self._container_action(node_id, container_id, "start")

    async def stop_container(self, node_id: int, container_id: str) -> ContainerInfo:
        return await self._container_action(node_id, container_id, "stop")

    async def restart_container(self, node_id: int, container_id: str) -> ContainerInfo:
        return await self._container_action(node_id, container_id, "restart")

    async def _container_action(self, node_id: int, container_id: str, action: str) -> ContainerInfo:
        """统一的启停/重启入口 —— 操作后回读容器真实状态。

        旧实现远程分支返回 ContainerInfo(id=..., name="", image="", status=...)，
        前端拿到空 name/image 会把表格行渲染成空白，这里统一回读。
        """
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")

        if node.is_local:
            return await asyncio.to_thread(self._container_action_local, container_id, action)

        await _ssh_exec(node, f"docker {action} {shlex.quote(container_id)}", timeout=90)
        invalidate_container_cache(node_id)
        # 回读真实状态
        for c in await self._list_containers_remote(node, all_containers=True):
            if c.id.startswith(container_id[:12]) or container_id.startswith(c.id):
                return c
        raise NotFoundException(f"容器 {container_id} 不存在")

    async def remove_container(self, node_id: int, container_id: str, force: bool = False) -> bool:
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")
        if node.is_local:
            await asyncio.to_thread(self._container_action_local, container_id, "remove", force=force)
        else:
            flag = "-f " if force else ""
            await _ssh_exec(node, f"docker rm {flag}{shlex.quote(container_id)}", timeout=90)

        invalidate_container_cache()
        # 容器没了，它的服务登记也应清掉，否则 DB 里留一堆 unreachable 脏数据
        try:
            removed = self.svc_repo.delete_by_container(container_id)
            if removed:
                self.db.commit()
                logger.info(f"容器 {container_id[:12]} 已删除，清理 {removed} 条服务登记")
        except Exception as e:
            logger.warning(f"清理容器服务登记失败: {e}")
        return True

    def _container_action_local(self, container_id: str, action: str, **kwargs) -> ContainerInfo:
        client = self._local_docker()
        try:
            container = client.containers.get(container_id)
        except Exception as e:
            msg = str(e)
            if "No such container" in msg or "not found" in msg.lower():
                # 目标状态已达成（stop/remove 幂等）
                if action in ("stop", "remove"):
                    logger.info(f"容器 {container_id} 已不存在，{action} 视为成功")
                    return ContainerInfo(
                        id=container_id, name="", image="", status="removed",
                    )
                raise NotFoundException(f"容器 {container_id} 不存在")
            raise BusinessException(f"读取容器失败: {msg}", "CONTAINER_ACTION_ERROR")

        try:
            if action == "start":
                container.start()
            elif action == "stop":
                container.stop(timeout=10)
            elif action == "restart":
                container.restart(timeout=10)
            elif action == "remove":
                container.remove(force=kwargs.get("force", False))
                return ContainerInfo(
                    id=container_id, name=container.name, image="", status="removed",
                )
        except Exception as docker_err:
            msg = str(docker_err)
            if "No such container" in msg or "not found" in msg.lower():
                logger.info(f"容器 {container_id} 已不存在，{action} 操作跳过")
                return ContainerInfo(id=container_id, name="", image="", status="removed")
            # 启动失败最常见原因是端口被占用 / 挂载不可用，给出可读提示
            low = msg.lower()
            if "port is already allocated" in low or "address already in use" in low:
                raise BusinessException(
                    f"启动失败：容器需要的宿主端口已被占用。请停掉占用端口的进程，"
                    f"或用「修改配置」换一个宿主端口。原始信息：{msg[:200]}",
                    "PORT_ALLOCATED",
                )
            raise BusinessException(f"容器 {action} 失败: {msg[:300]}", "CONTAINER_ACTION_ERROR")

        try:
            container.reload()
        except Exception:
            pass
        invalidate_container_cache()   # 状态/端口可能变了
        return self._container_info_from_sdk(client, container)

    async def get_container_logs(self, node_id: int, container_id: str, tail: int = 100) -> ContainerLogsResponse:
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")
        if node.is_local:
            logs = await asyncio.to_thread(self._get_logs_local, container_id, tail)
        else:
            logs = await _ssh_exec(node, f"docker logs --tail {tail} {container_id}")
        return ContainerLogsResponse(logs=logs)

    def _get_logs_local(self, container_id: str, tail: int) -> str:
        client = self._local_docker()
        try:
            container = client.containers.get(container_id)
            return container.logs(tail=tail).decode("utf-8", errors="replace")
        except Exception:
            raise NotFoundException(f"容器 {container_id} 不存在")

    async def inspect_container(self, node_id: int, container_id: str) -> ContainerInspectResponse:
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")
        if node.is_local:
            data = await asyncio.to_thread(self._inspect_local, container_id)
        else:
            raw = await _ssh_exec(node, f"docker inspect {container_id}")
            try:
                data = json.loads(raw)[0]
            except (json.JSONDecodeError, IndexError):
                raise BusinessException("解析容器信息失败", "INSPECT_ERROR")
        return ContainerInspectResponse(data=data)

    def _inspect_local(self, container_id: str) -> dict:
        client = self._local_docker()
        try:
            container = client.containers.get(container_id)
            return container.attrs
        except Exception:
            raise NotFoundException(f"容器 {container_id} 不存在")

    # ==================== 容器终端 ====================

    def _assert_container_running(self, container_id: str) -> None:
        """进终端前先确认容器在跑，否则 docker exec 会静默失败。"""
        client = self._local_docker()
        try:
            container = client.containers.get(container_id)
        except Exception:
            raise NotFoundException(f"容器 {container_id} 不存在")
        if container.status != "running":
            raise BusinessException(
                f"容器当前状态为 {container.status}，无法打开终端。请先启动容器。",
                "CONTAINER_NOT_RUNNING",
            )

    async def resolve_shell(self, node_id: int, container_id: str, requested: str) -> str:
        """决定实际使用的 shell：请求的存在就用它，否则回退到容器内可用的。"""
        shells = await self.detect_shells(node_id, container_id)
        if not shells:
            raise BusinessException(
                "容器内找不到可用的 shell（已尝试 /bin/bash、/bin/ash、/bin/sh）。"
                "该镜像可能是 distroless 类型，无法打开交互终端。",
                "NO_SHELL_AVAILABLE",
            )
        if requested in shells:
            return requested
        fallback = shells[0]
        logger.info(f"容器 {container_id} 无 {requested}，回退到 {fallback}")
        return fallback

    async def exec_terminal_local(self, container_id: str, cmd: str = "/bin/sh"):
        """通过 Python pty.openpty() + docker exec -it 创建真实 PTY 终端。

        返回 (master_fd: int, proc: subprocess.Popen):
        - master_fd: PTY 主端文件描述符（阻塞读/写），已设为 raw 模式
        - proc: docker exec 子进程
        - 终端大小通过 fcntl.ioctl(master_fd, termios.TIOCSWINSZ, ...) 调整

        PTY 设为 raw 模式确保：
        - 每个字节即时通过，不等换行符（行缓冲关闭）
        - 不自带回显（由容器内 bash 的 readline 负责 echo）
        - Ctrl+C / Ctrl+D 等控制字符原样传递
        """
        import pty
        import os as os_module
        import subprocess as sp
        import termios as t
        import tty

        self._assert_container_running(container_id)

        master_fd, slave_fd = pty.openpty()

        # PTY master 设 raw 模式：关闭 echo、行缓冲、信号处理
        # 所有终端处理交由容器内的 bash 和 xterm.js 协商
        tty.setraw(master_fd, t.TCSANOW)

        proc = sp.Popen(
            ["docker", "exec", "-it", container_id, cmd],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
        )
        os_module.close(slave_fd)  # 父进程关闭 slave，只用 master

        return master_fd, proc

    async def exec_terminal_remote(self, node: ComputeNode, container_id: str, cmd: str = "/bin/sh"):
        """在远程节点容器中启动交互式终端 — 返回 asyncssh 进程（已分配 PTY）。"""
        import asyncssh

        connect_kwargs: Dict[str, Any] = {
            "host": node.host,
            "port": node.port,
            "username": node.username,
            "known_hosts": None,
            "connect_timeout": 10,
        }
        if node.auth_type == AuthType.PASSWORD.value:
            connect_kwargs["password"] = _decrypt(node.password or "")
        else:
            key_data = _decrypt(node.private_key or "")
            connect_kwargs["client_keys"] = [asyncssh.import_private_key(key_data)]

        conn = await asyncssh.connect(**connect_kwargs)
        ssh_process = await conn.create_process(
            f"docker exec -it {container_id} {cmd}",
            term_type="xterm-256color",
        )
        return ssh_process, conn

    # ---- 辅助 ----

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f}KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f}MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f}GB"

    # ==================== 容器修改 ====================

    async def update_container(self, node_id: int, container_id: str, data: ContainerUpdateRequest) -> ContainerInfo:
        """修改容器配置：读取原配置 → merge 新配置 → stop → remove → recreate。

        Docker 不支持在已存在的容器上改 ports/volumes/envs/network，所以必须重建。
        字段语义：None = 沿用原值，[] = 清空该项。
        """
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")

        # 1. 读取当前完整配置
        if node.is_local:
            insp = await asyncio.to_thread(self._inspect_local, container_id)
        else:
            raw = await _ssh_exec(node, f"docker inspect {shlex.quote(container_id)}")
            try:
                insp = json.loads(raw)[0]
            except (json.JSONDecodeError, IndexError):
                raise BusinessException("无法读取容器配置", "INSPECT_ERROR")

        config = insp.get("Config") or {}
        cur_image = config.get("Image") or ""
        cur_name = (insp.get("Name") or "").lstrip("/")
        was_running = ((insp.get("State") or {}).get("Status") or "") == "running"

        # 镜像自带的 ENV/CMD，用于把「镜像默认值」从回填里剔除
        image_env: List[str] = []
        image_cmd: List[str] = []
        image_entrypoint: List[str] = []
        if node.is_local and cur_image:
            try:
                client = self._local_docker()
                icfg = (client.images.get(cur_image).attrs or {}).get("Config") or {}
                image_env = icfg.get("Env") or []
                image_cmd = icfg.get("Cmd") or []
                image_entrypoint = icfg.get("Entrypoint") or []
            except Exception:
                pass

        # 2. merge：None → 沿用，[] → 清空
        merged = ContainerCreateRequest(
            image=data.image or cur_image,
            name=data.name or cur_name or None,
            command=data.command if data.command is not None else (
                _command_from_inspect(insp, image_cmd) or None
            ),
            # entrypoint 始终沿用原容器的自定义值，否则重建后启动命令会变
            entrypoint=_entrypoint_from_inspect(insp, image_entrypoint),
            ports=data.ports if data.ports is not None else _ports_from_inspect(insp),
            envs=data.envs if data.envs is not None else _envs_from_inspect(insp, image_env),
            volumes=data.volumes if data.volumes is not None else _volumes_from_inspect(insp),
            restart=data.restart or _restart_from_inspect(insp),
            network=data.network or _network_from_inspect(insp),
            auto_pull=True,
            start=was_running,   # 原来在跑就重建后自动起来
        )
        self._validate_container_request(merged)

        # 3. stop（失败不阻塞，可能本来就停着）
        try:
            if node.is_local:
                await asyncio.to_thread(self._container_action_local, container_id, "stop")
            else:
                await _ssh_exec(node, f"docker stop -t 10 {shlex.quote(container_id)}", timeout=60)
        except Exception:
            logger.warning(f"停止容器 {container_id} 失败（可能已停止），继续")

        # 4. remove —— 必须成功，否则重名会创建失败
        try:
            if node.is_local:
                await asyncio.to_thread(
                    self._container_action_local, container_id, "remove", force=True,
                )
            else:
                await _ssh_exec(node, f"docker rm -f {shlex.quote(container_id)}", timeout=60)
        except NotFoundException:
            logger.info(f"旧容器 {container_id} 已不存在，跳过删除")
        except Exception as e:
            raise BusinessException(f"删除旧容器失败: {e}", "CONTAINER_RECREATE_ERROR")

        # 5. recreate
        try:
            if node.is_local:
                created = await asyncio.to_thread(self._create_container_local, merged)
            else:
                created = await self._create_container_remote(node, merged)
        except BusinessException as e:
            # 重建失败是最糟的情况（旧容器已删），把原因和补救路径讲清楚
            # 顺带清掉指向已消失容器的服务登记
            try:
                if self.svc_repo.delete_by_container(container_id):
                    self.db.commit()
            except Exception:
                pass
            raise BusinessException(
                f"旧容器已删除，但按新配置重建失败：{e.message}。"
                f"请在「新建容器」中用镜像 {merged.image} 重新创建。",
                "CONTAINER_RECREATE_FAILED",
            )

        # 重建后容器 ID 变了：把服务登记迁到新 ID，否则「服务」页全变 unreachable。
        # 服务进程本身没有随容器重建自动起来，状态交给下一次 refresh 判定。
        try:
            moved = 0
            for row in self.svc_repo.list_by_container(container_id):
                # 新容器上若已有同端口登记（极少见），删掉旧的避免唯一键冲突
                dup = self.svc_repo.get_by_container_port(created.id, row.container_port)
                if dup and dup.id != row.id:
                    self.svc_repo.delete(row.id)
                    continue
                row.container_id = created.id
                row.container_name = created.name
                row.image = created.image
                row.status = ServiceStatus.UNKNOWN
                row.status_detail = "容器已按新配置重建，服务需重新启动"
                row.host_reachable = False
                row.is_aide_source = False
                row.host_port = next(
                    (pm.host_port for pm in created.port_mappings
                     if pm.container_port == row.container_port),
                    None,
                )
                row.access_url = self._build_access_url(node, row.host_port)
                moved += 1
            if moved:
                self.db.commit()
                logger.info(f"容器重建：{moved} 条服务登记已迁移到新容器 {created.id[:12]}")
        except Exception as e:
            logger.warning(f"迁移服务登记失败: {e}")

        return created

    # ==================== 快速命令执行 ====================

    # 内存中追踪 exec 会话：{exec_id: {...}}
    _exec_sessions: Dict[str, Dict[str, Any]] = {}

    async def container_exec(self, node_id: int, container_id: str, data: ContainerExecRequest) -> ContainerExecResponse:
        """在容器内执行命令。

        sync  模式：直接跑，返回 stdout/stderr + exit_code（适合 ls/ps/df 这类快命令）
        async 模式：nohup 后台跑，输出重定向到日志文件，返回 exec_id 供轮询
        """
        import uuid

        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")

        # 解析命令：template_id 优先
        cmd = data.command or ""
        if data.template_id:
            cmd = self._resolve_template(data.template_id, data.params or {})
        if not cmd.strip():
            raise ValidationException(
                "命令不能为空。可以先在上方选一个命令模板，或直接输入如 `ps aux`", "COMMAND_REQUIRED",
            )

        exec_id = uuid.uuid4().hex[:12]

        if data.mode == "sync":
            logs, exit_code = await self._exec_sync(node, container_id, cmd, data.workdir, data.timeout)
            return ContainerExecResponse(
                exec_id=exec_id, container_id=container_id, command=cmd,
                started=True, mode="sync", logs=logs, exit_code=exit_code, running=False,
            )

        # ---- async ----
        log_path = f"/tmp/omd-exec-{exec_id}.log"
        done_path = f"/tmp/omd-exec-{exec_id}.done"
        # 用 heredoc 传命令体，彻底避开单/双引号转义地狱（旧实现用 sh -c '{cmd}'，
        # 命令里只要含单引号就会被截断甚至变成注入）
        wrapper = (
            f"rm -f {log_path} {done_path}; "
            f"nohup sh -c {shlex.quote(cmd)} > {log_path} 2>&1; "
            f"echo $? > {done_path}"
        )
        # 整体再放到后台，让 exec 立即返回
        bg = f"nohup sh -c {shlex.quote(wrapper)} >/dev/null 2>&1 & echo started"

        try:
            if node.is_local:
                await asyncio.to_thread(self._local_shell_exec, container_id, bg, data.workdir)
            else:
                await _ssh_exec(
                    node,
                    f"docker exec {shlex.quote(container_id)} sh -c {shlex.quote(bg)}",
                )
        except BusinessException:
            raise
        except Exception as e:
            raise BusinessException(f"命令执行失败: {e}", "EXEC_ERROR")

        self._exec_sessions[exec_id] = {
            "node_id": node_id,
            "container_id": container_id,
            "log_path": log_path,
            "done_path": done_path,
            "command": cmd,
            "is_local": node.is_local,
            "node": None if node.is_local else node,
        }

        # 起的是 opencode web/serve → 自动登记成容器服务（「服务」页 + AIDE 源立刻可见）
        if _detect_kind_from_command(cmd) != ServiceKind.OTHER:
            # 等一下让端口起来，探测结果才准
            await asyncio.sleep(2.0)
            await self._auto_register_from_command(node_id, container_id, cmd, exec_id)

        return ContainerExecResponse(
            exec_id=exec_id, container_id=container_id, command=cmd,
            started=True, mode="async", running=True,
        )

    async def _auto_register_from_command(
        self, node_id: int, container_id: str, cmd: str, exec_id: str
    ) -> None:
        """用户用「快速命令」起了 opencode 服务时，自动登记到 container_services。

        这样容器内启动的服务立刻在「服务」页可见，AIDE 也能选到它，
        不需要用户再手工登记一次。识别失败就安静跳过（不影响 exec 本身）。
        """
        kind = _detect_kind_from_command(cmd)
        if kind == ServiceKind.OTHER:
            return
        port = _extract_port_from_command(cmd)
        if not port:
            return
        try:
            log_path = None
            m = re.search(r">\s*(/\S+\.log)", cmd)
            if m:
                log_path = m.group(1)
            await self.upsert_service(
                node_id,
                ContainerServiceCreate(
                    container_id=container_id,
                    container_port=port,
                    kind=kind.value,
                    name=_default_service_name(kind, port),
                    command=cmd[:2000],
                    log_path=log_path,
                ),
                exec_id=exec_id,
            )
            logger.info(f"自动登记容器服务: {container_id[:12]} :{port} {kind.value}")
        except Exception as e:
            logger.warning(f"自动登记容器服务失败（不影响命令执行）: {e}")

    async def _exec_sync(
        self, node: ComputeNode, container_id: str, cmd: str,
        workdir: Optional[str], timeout: int,
    ) -> tuple:
        """同步执行并返回 (输出, exit_code)。"""
        if node.is_local:
            def run() -> tuple:
                client = self._local_docker()
                try:
                    container = client.containers.get(container_id)
                except Exception:
                    raise NotFoundException(f"容器 {container_id} 不存在")
                kwargs: Dict[str, Any] = {"cmd": ["sh", "-c", cmd], "demux": False}
                if workdir:
                    kwargs["workdir"] = workdir
                exit_code, output = container.exec_run(**kwargs)
                text = output.decode("utf-8", errors="replace") if output else ""
                return text, exit_code

            try:
                return await asyncio.wait_for(asyncio.to_thread(run), timeout=timeout + 5)
            except asyncio.TimeoutError:
                raise BusinessException(
                    f"命令执行超过 {timeout}s 未返回。长时间任务请改用「后台执行」模式。",
                    "EXEC_TIMEOUT",
                )

        # 远程：把 exit code 附在输出末尾一并取回
        wd = f"cd {shlex.quote(workdir)} && " if workdir else ""
        remote_cmd = (
            f"docker exec {shlex.quote(container_id)} sh -c "
            f"{shlex.quote(wd + cmd + '; echo __OMD_EXIT__$?')}"
        )
        try:
            raw = await _ssh_exec(node, remote_cmd, timeout=timeout + 10)
        except BusinessException as e:
            # SSH 层因非零退出抛异常时，仍尽量把输出还给用户
            return f"{e.message}", 1
        marker = "__OMD_EXIT__"
        if marker in raw:
            body, _, tail = raw.rpartition(marker)
            code = int(tail.strip()) if tail.strip().isdigit() else 0
            return body, code
        return raw, 0

    def _local_shell_exec(self, container_id: str, cmd: str, workdir: Optional[str] = None) -> str:
        """本地 docker exec 执行 shell 命令并返回输出。"""
        client = self._local_docker()
        try:
            container = client.containers.get(container_id)
        except Exception:
            raise NotFoundException(f"容器 {container_id} 不存在")
        try:
            kwargs: Dict[str, Any] = {"cmd": ["sh", "-c", cmd], "demux": False}
            if workdir:
                kwargs["workdir"] = workdir
            exit_code, output = container.exec_run(**kwargs)
            result = output.decode("utf-8", errors="replace") if output else ""
            if exit_code != 0:
                logger.warning(f"容器内命令返回非零: exit={exit_code}, output={result[:200]}")
            return result.strip()
        except Exception as e:
            raise BusinessException(f"容器内执行失败: {e}", "LOCAL_EXEC_ERROR")

    async def get_exec_logs(self, node_id: int, container_id: str, exec_id: str) -> ContainerExecLogsResponse:
        """获取后台命令的日志输出和状态。

        运行状态判定改用 sentinel 文件（.done 内含 exit code），
        不再依赖 `fuser`（绝大多数精简镜像里都没有这个命令，
        导致旧实现永远判定为「已退出」）。
        """
        session = self._exec_sessions.get(exec_id)
        if not session:
            raise NotFoundException(f"Exec 会话 {exec_id} 不存在（可能后端已重启）")

        log_path = session["log_path"]
        done_path = session["done_path"]
        is_local = session["is_local"]
        node = session.get("node")

        # 一次调用同时取回：日志内容 + done 标记
        probe = (
            f"cat {log_path} 2>/dev/null; "
            f"printf '__OMD_DONE__'; "
            f"cat {done_path} 2>/dev/null"
        )
        try:
            if is_local:
                raw = await asyncio.to_thread(self._local_shell_exec, container_id, probe)
            else:
                raw = await _ssh_exec(
                    node, f"docker exec {shlex.quote(container_id)} sh -c {shlex.quote(probe)}",
                )
        except Exception as e:
            logger.warning(f"读取 exec 日志失败: {e}")
            raw = ""

        logs, _, done_part = raw.rpartition("__OMD_DONE__")
        if not _:
            logs, done_part = raw, ""
        done_str = done_part.strip()
        running = done_str == ""
        exit_code: Optional[int] = None
        if done_str.isdigit():
            exit_code = int(done_str)

        return ContainerExecLogsResponse(
            exec_id=exec_id,
            logs=logs if logs.strip() else "(暂无输出)",
            running=running,
            exit_code=exit_code,
        )

    @staticmethod
    def _resolve_template(template_id: str, params: dict) -> str:
        """用参数填充命令模板。"""
        from app.schemas.compute_schema import COMMAND_TEMPLATES

        template = None
        for t in COMMAND_TEMPLATES:
            if t["id"] == template_id:
                template = t
                break
        if not template:
            raise BusinessException(f"命令模板 '{template_id}' 不存在", "TEMPLATE_NOT_FOUND")

        cmd = template["command"]
        tmpl_params = template.get("params", {})
        merged: Dict[str, Any] = {}
        for key, spec in tmpl_params.items():
            val = params.get(key, spec.get("default"))
            merged[key] = val
        for key, val in merged.items():
            if val is None:
                continue
            # 模板参数来自用户输入，做基础清理防止把整条命令改写
            sval = str(val)
            if any(ch in sval for ch in (";", "&&", "||", "`", "$(", "\n")):
                raise ValidationException(
                    f"参数 {key} 含非法字符（; && || ` $( 换行），请只填写普通值",
                    "TEMPLATE_PARAM_INVALID",
                )
            cmd = cmd.replace(f"{{{key}}}", sval)
        return cmd

    @staticmethod
    def list_command_templates() -> List[dict]:
        from app.schemas.compute_schema import COMMAND_TEMPLATES
        return COMMAND_TEMPLATES

    @staticmethod
    def list_container_presets() -> List[dict]:
        from app.schemas.compute_schema import CONTAINER_PRESETS
        return CONTAINER_PRESETS

    # ==================== 容器服务登记（container_services） ====================
    #
    # 设计要点：
    # 1. DB 存的是「声明 + 最近一次探测快照」，**不是可信实时状态**
    # 2. 真实性靠 refresh_services() 主动回探：容器还在吗 → 端口在听吗 → 绑的什么地址 → 宿主连得上吗
    # 3. AIDE 源 = opencode 类 + 宿主可达，直接从 DB 查，页面不用每次扫全部容器

    def _to_service_response(self, row: ContainerService) -> ContainerServiceResponse:
        return ContainerServiceResponse(
            id=row.id,
            node_id=row.node_id,
            node_name=row.node_name,
            container_id=row.container_id,
            container_name=row.container_name,
            image=row.image,
            kind=row.kind.value if isinstance(row.kind, ServiceKind) else str(row.kind),
            name=row.name,
            container_port=row.container_port,
            host_port=row.host_port,
            access_url=row.access_url,
            command=row.command,
            log_path=row.log_path,
            exec_id=row.exec_id,
            status=row.status.value if isinstance(row.status, ServiceStatus) else str(row.status),
            status_detail=row.status_detail,
            bind_address=row.bind_address,
            host_reachable=bool(row.host_reachable),
            last_checked_at=row.last_checked_at,
            is_aide_source=bool(row.is_aide_source),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def list_services(self, node_id: Optional[int] = None) -> List[ContainerServiceResponse]:
        rows = (
            self.svc_repo.list_by_node(node_id)
            if node_id is not None
            else self.svc_repo.list_all_ordered()
        )
        return [self._to_service_response(r) for r in rows]

    def delete_service(self, service_id: int) -> bool:
        row = self.svc_repo.get_by_id(service_id)
        if not row:
            raise NotFoundException(f"服务登记 ID={service_id} 不存在")
        self.svc_repo.delete(service_id)
        self.db.commit()
        return True

    async def _resolve_container_meta(
        self, node: ComputeNode, container_id: str
    ) -> Optional[ContainerInfo]:
        """拿容器当前信息（名称/镜像/端口映射），找不到返回 None."""
        try:
            containers = await self.list_containers(node.id, all_containers=True)
        except Exception as e:
            logger.warning(f"节点 {node.name} 容器列表获取失败: {e}")
            return None
        for c in containers:
            if c.id.startswith(container_id[:12]) or container_id.startswith(c.id[:12]):
                return c
        return None

    async def upsert_service(
        self,
        node_id: int,
        data: ContainerServiceCreate,
        user_id: Optional[int] = None,
        exec_id: Optional[str] = None,
    ) -> ContainerServiceResponse:
        """登记（或更新）一个容器服务，随后立刻探测一次真实状态。"""
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")

        meta = await self._resolve_container_meta(node, data.container_id)
        if meta is None:
            raise NotFoundException(
                f"容器 {data.container_id} 在节点 {node.name} 上不存在，无法登记服务"
            )

        kind = ServiceKind(data.kind)
        # 从容器端口映射反查宿主端口
        host_port: Optional[int] = None
        for pm in meta.port_mappings:
            if pm.container_port == data.container_port:
                host_port = pm.host_port
                break

        access_url = self._build_access_url(node, host_port)

        payload = {
            "node_id": node.id,
            "node_name": node.name,
            "container_id": meta.id,
            "container_name": meta.name,
            "image": meta.image,
            "kind": kind,
            "name": data.name or _default_service_name(kind, data.container_port),
            "container_port": data.container_port,
            "host_port": host_port,
            "access_url": access_url,
            "command": data.command,
            "log_path": data.log_path,
        }
        if exec_id:
            payload["exec_id"] = exec_id

        existing = self.svc_repo.get_by_container_port(meta.id, data.container_port)
        if existing:
            # 保留原 exec_id（除非本次带了新的）
            if not exec_id:
                payload.pop("exec_id", None)
            row = self.svc_repo.update(existing.id, payload)
        else:
            payload.setdefault("status", ServiceStatus.UNKNOWN)
            payload["created_by_user_id"] = user_id
            row = self.svc_repo.create(payload)
        self.db.commit()

        # 登记后立刻探一次，避免前端看到 unknown
        refreshed = await self.refresh_service(row.id)
        return refreshed

    @staticmethod
    def _build_access_url(node: ComputeNode, host_port: Optional[int]) -> Optional[str]:
        """构造宿主访问 URL。

        本地节点走 localhost；远程节点走节点 host（前端浏览器需能直连该地址）。
        """
        if not host_port:
            return None
        host = "localhost" if node.is_local else node.host
        return f"http://{host}:{host_port}"

    async def refresh_service(self, service_id: int) -> ContainerServiceResponse:
        """探测单个服务真实状态并写回 DB。"""
        row = self.svc_repo.get_by_id(service_id)
        if not row:
            raise NotFoundException(f"服务登记 ID={service_id} 不存在")
        node = self.repo.get_by_id(row.node_id)
        if not node:
            self._mark_service(row, ServiceStatus.UNREACHABLE, "所属节点已删除")
            self.db.commit()
            return self._to_service_response(row)

        await self._probe_one(node, row)
        self.db.commit()
        return self._to_service_response(row)

    async def refresh_services(self, node_id: Optional[int] = None) -> ServiceRefreshResult:
        """批量探测所有（或指定节点的）服务，保证 DB 状态的实时性。"""
        rows = (
            self.svc_repo.list_by_node(node_id)
            if node_id is not None
            else self.svc_repo.list_all_ordered()
        )

        # 按节点分组，同节点只查一次容器列表 + 复用 listen 探测
        by_node: Dict[int, List[ContainerService]] = {}
        for r in rows:
            by_node.setdefault(r.node_id, []).append(r)

        for nid, group in by_node.items():
            node = self.repo.get_by_id(nid)
            if not node:
                for r in group:
                    self._mark_service(r, ServiceStatus.UNREACHABLE, "所属节点已删除")
                continue
            # 容器列表 + 每个容器的 listen 表都缓存起来，避免同容器重复 exec
            containers: Dict[str, ContainerInfo] = {}
            try:
                # 8s 硬超时：离线远程节点 SSH 要等 ~10s，会拖垮整次刷新
                for c in await asyncio.wait_for(
                    self.list_containers(nid, all_containers=True), timeout=8.0,
                ):
                    containers[c.id] = c
            except asyncio.TimeoutError:
                for r in group:
                    self._mark_service(
                        r, ServiceStatus.UNREACHABLE, "节点响应超时（>8s），可能已离线",
                    )
                continue
            except Exception as e:
                for r in group:
                    self._mark_service(r, ServiceStatus.UNREACHABLE, f"节点不可达: {e}")
                continue

            listen_cache: Dict[str, Dict[int, str]] = {}
            # 同一容器串行（复用 listen_cache），不同容器并发 —— 探测都是 IO 等待，
            # 串行时 N 个服务 = N × (exec + HTTP) 延迟，并发后约等于单个的耗时。
            by_container: Dict[str, List[ContainerService]] = {}
            for r in group:
                by_container.setdefault(r.container_id, []).append(r)

            async def _probe_container_group(rows_of_c: List[ContainerService]) -> None:
                for rr in rows_of_c:
                    await self._probe_one(
                        node, rr, containers=containers, listen_cache=listen_cache,
                    )

            await asyncio.gather(
                *(_probe_container_group(v) for v in by_container.values()),
                return_exceptions=True,
            )

        self.db.commit()

        services = [self._to_service_response(r) for r in rows]
        return ServiceRefreshResult(
            total=len(services),
            running=sum(1 for s in services if s.status == "running"),
            stopped=sum(1 for s in services if s.status == "stopped"),
            unreachable=sum(1 for s in services if s.status == "unreachable"),
            services=services,
        )

    def _mark_service(
        self,
        row: ContainerService,
        status: ServiceStatus,
        detail: Optional[str] = None,
        *,
        bind_address: Optional[str] = None,
        host_reachable: bool = False,
    ) -> None:
        row.status = status
        row.status_detail = detail
        row.bind_address = bind_address
        row.host_reachable = host_reachable
        row.is_aide_source = bool(
            row.kind in _AIDE_KINDS and status == ServiceStatus.RUNNING and host_reachable
        )
        row.last_checked_at = datetime.now(timezone.utc)

    async def _probe_one(
        self,
        node: ComputeNode,
        row: ContainerService,
        containers: Optional[Dict[str, ContainerInfo]] = None,
        listen_cache: Optional[Dict[str, Dict[int, str]]] = None,
    ) -> None:
        """探测一个服务的真实状态，就地更新 row（不 commit）。

        四步递进，任一步失败即可给出准确原因：
        1. 容器还在吗、是否 running
        2. 端口映射变了吗（用户可能重建过容器）→ 同步 host_port / access_url
        3. 容器内那个端口真的在 LISTEN 吗、绑的什么地址
        4. 宿主真的连得上 access_url 吗
        """
        # ---- 1. 容器状态 ----
        meta: Optional[ContainerInfo] = None
        if containers is not None:
            for cid, c in containers.items():
                if cid.startswith(row.container_id[:12]) or row.container_id.startswith(cid[:12]):
                    meta = c
                    break
        else:
            meta = await self._resolve_container_meta(node, row.container_id)

        if meta is None:
            self._mark_service(row, ServiceStatus.UNREACHABLE, "容器已不存在（可能被删除）")
            return
        # 容器名/镜像可能变了，同步过来
        row.container_name = meta.name
        row.image = meta.image
        if meta.status != "running":
            self._mark_service(row, ServiceStatus.STOPPED, f"容器未运行（{meta.status}）")
            return

        # ---- 2. 同步端口映射 ----
        host_port: Optional[int] = None
        for pm in meta.port_mappings:
            if pm.container_port == row.container_port:
                host_port = pm.host_port
                break
        row.host_port = host_port
        row.access_url = self._build_access_url(node, host_port)

        # ---- 3. 容器内端口是否 LISTEN ----
        try:
            listens = await self._probe_listen_ports(
                node, meta.id, cache=listen_cache,
            )
        except Exception as e:
            self._mark_service(row, ServiceStatus.UNKNOWN, f"端口探测失败: {e}")
            return

        bind = listens.get(row.container_port)
        if bind is None:
            self._mark_service(
                row, ServiceStatus.STOPPED,
                f"容器内端口 {row.container_port} 没有进程监听（服务可能已退出，查看日志排查）",
            )
            return

        if host_port is None:
            self._mark_service(
                row, ServiceStatus.RUNNING,
                f"服务在跑（绑 {bind}），但容器未映射该端口到宿主，浏览器无法访问。"
                f"需重建容器并添加端口映射。",
                bind_address=bind, host_reachable=False,
            )
            return

        if bind == "127.0.0.1":
            self._mark_service(
                row, ServiceStatus.RUNNING,
                "服务只绑了 127.0.0.1（容器内 loopback），Docker 端口映射对它无效，"
                "宿主访问不到。重启服务时加 --hostname 0.0.0.0。",
                bind_address=bind, host_reachable=False,
            )
            return

        # ---- 4. 宿主实际可达性 ----
        reachable, detail = await self._probe_host_reachable(row.access_url)
        if reachable:
            self._mark_service(
                row, ServiceStatus.RUNNING, "服务正常，宿主可访问",
                bind_address=bind, host_reachable=True,
            )
        else:
            self._mark_service(
                row, ServiceStatus.RUNNING,
                f"容器内在监听（绑 {bind}），但宿主访问 {row.access_url} 失败：{detail}",
                bind_address=bind, host_reachable=False,
            )

    async def _probe_listen_ports(
        self,
        node: ComputeNode,
        container_id: str,
        cache: Optional[Dict[str, Dict[int, str]]] = None,
    ) -> Dict[int, str]:
        """探测容器内所有 LISTEN 端口 → {端口: 绑定地址}。

        两层缓存：
        - `cache` 入参：单次批量操作内同容器只探一次（调用方传入）
        - 模块级短 TTL 缓存：跨请求复用，避免 AIDE 轮询把 docker exec 打满
        """
        if cache is not None and container_id in cache:
            return cache[container_id]

        gkey = (node.id, container_id)
        hit = _cache_get(_listen_cache, gkey)
        if hit is not None:
            if cache is not None:
                cache[container_id] = hit
            return hit

        if node.is_local:
            raw = await asyncio.to_thread(
                self._local_shell_exec, container_id, _PROBE_LISTEN_CMD,
            )
        else:
            raw = await _ssh_exec(
                node,
                f"docker exec {shlex.quote(container_id)} sh -c {shlex.quote(_PROBE_LISTEN_CMD)}",
                timeout=20,
            )
        parsed = _parse_listen_table(raw)
        _cache_put(_listen_cache, gkey, parsed, _LISTEN_TTL)
        if cache is not None:
            cache[container_id] = parsed
        return parsed

    @staticmethod
    async def _probe_host_reachable(url: Optional[str]) -> tuple:
        """从后端所在主机探测 URL 可达性。

        ⚠️ 局限：后端与浏览器可能不在同一台机器上。这里探的是「后端视角」，
        对本地开发（两者同机）等价于浏览器视角，足够用；
        前端仍会展示 access_url 让用户自行确认。
        """
        if not url:
            return False, "无宿主访问地址"
        try:
            async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as cli:
                resp = await cli.get(url)
            if resp.status_code < 500:
                return True, f"HTTP {resp.status_code}"
            return False, f"HTTP {resp.status_code}"
        except httpx.ConnectError:
            return False, "连接被拒绝"
        except httpx.TimeoutException:
            return False, "连接超时"
        except Exception as e:
            return False, str(e)[:120]

    # ==================== 一键启动服务（启动 + 自动登记） ====================

    async def launch_service(
        self,
        node_id: int,
        container_id: str,
        data: ServiceLaunchRequest,
        user_id: Optional[int] = None,
    ) -> ContainerServiceResponse:
        """在容器内后台启动 opencode 服务，并登记到 DB。

        强制 `--hostname 0.0.0.0`：绑 127.0.0.1 时 Docker 端口映射失效，
        宿主访问不到（这是最常踩的坑，直接在这层堵掉）。
        """
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")

        meta = await self._resolve_container_meta(node, container_id)
        if meta is None:
            raise NotFoundException(f"容器 {container_id} 不存在")
        if meta.status != "running":
            raise BusinessException(
                f"容器当前是 {meta.status}，请先启动容器再启动服务",
                "CONTAINER_NOT_RUNNING",
            )

        kind = ServiceKind(data.kind)
        subcmd = "web" if kind == ServiceKind.OPENCODE_WEB else "serve"
        port = data.container_port
        log_path = f"/var/log/opencode/{subcmd}-{port}.log"

        parts = [
            "opencode", subcmd,
            "--port", str(port),
            "--hostname", data.hostname,
        ]
        cors = (data.cors or "").strip()
        if cors:
            for origin in cors.split(","):
                origin = origin.strip()
                if origin:
                    parts += ["--cors", shlex.quote(origin)]
        launch_cmd = " ".join(parts)

        # 如果该端口已经在监听，直接登记而不重复起进程（幂等）
        try:
            listens = await self._probe_listen_ports(node, meta.id)
        except Exception:
            listens = {}
        already = port in listens

        exec_id: Optional[str] = None
        if not already:
            exec_resp = await self.container_exec(
                node_id,
                meta.id,
                ContainerExecRequest(
                    command=(
                        f"mkdir -p /var/log/opencode && "
                        f"nohup {launch_cmd} > {log_path} 2>&1 &"
                    ),
                    mode="async",
                ),
            )
            exec_id = exec_resp.exec_id
            # 等端口起来（opencode web 首启要构建资源，给足时间）
            for _ in range(40):
                await asyncio.sleep(0.5)
                try:
                    if port in await self._probe_listen_ports(node, meta.id):
                        break
                except Exception:
                    continue

        return await self.upsert_service(
            node_id,
            ContainerServiceCreate(
                container_id=meta.id,
                container_port=port,
                kind=data.kind,
                name=_default_service_name(kind, port),
                command=launch_cmd,
                log_path=log_path,
            ),
            user_id=user_id,
            exec_id=exec_id,
        )

    async def stop_service(self, service_id: int) -> ContainerServiceResponse:
        """停掉容器内该端口上的服务进程（保留 DB 登记，便于再次启动）。"""
        row = self.svc_repo.get_by_id(service_id)
        if not row:
            raise NotFoundException(f"服务登记 ID={service_id} 不存在")
        node = self.repo.get_by_id(row.node_id)
        if not node:
            raise NotFoundException("所属节点不存在")

        port = row.container_port
        # 按命令特征杀进程：pkill 不一定存在，用 /proc 遍历兜底
        kill_cmd = (
            f"(pkill -f -- '--port {port}' 2>/dev/null) || "
            f"(for p in /proc/[0-9]*; do "
            f"  if tr '\\0' ' ' < $p/cmdline 2>/dev/null | grep -q -- '--port {port}'; then "
            f"    kill $(basename $p) 2>/dev/null; fi; done); "
            f"echo stopped"
        )
        try:
            if node.is_local:
                await asyncio.to_thread(self._local_shell_exec, row.container_id, kill_cmd)
            else:
                await _ssh_exec(
                    node,
                    f"docker exec {shlex.quote(row.container_id)} sh -c {shlex.quote(kill_cmd)}",
                    timeout=30,
                )
        except Exception as e:
            raise BusinessException(f"停止服务失败: {e}", "SERVICE_STOP_ERROR")

        await asyncio.sleep(1.0)
        return await self.refresh_service(service_id)

    # ==================== AIDE 容器源发现 ====================

    async def get_aide_sources(
        self, node_id: Optional[int] = None, refresh: bool = False
    ) -> List[AideContainerSource]:
        """AIDE 可嵌入源 —— 直接读 DB 登记表。

        - `refresh=True` 时先回探一遍再返回，保证实时性
        - 只返回 opencode 类 + 宿主可达的服务
        """
        if refresh:
            await self.refresh_services(node_id=node_id)

        rows = self.svc_repo.list_aide_sources()
        if node_id is not None:
            rows = [r for r in rows if r.node_id == node_id]

        return [
            AideContainerSource(
                node_id=r.node_id,
                node_name=r.node_name,
                container_id=r.container_id,
                container_name=r.container_name,
                port=r.host_port or 0,
                container_port=r.container_port,
                image=r.image or "",
            )
            for r in rows
            if r.host_port
        ]

    async def discover_services(
        self, node_id: Optional[int] = None, include_offline: bool = False
    ) -> ServiceRefreshResult:
        """扫描所有容器，把「正在监听 opencode 端口」的服务自动补登记到 DB。

        用途：用户可能在控制台里手工起了服务、或后端重装过，
        这个入口把现实里已存在但 DB 没记的服务同步进来。

        性能：
        - **默认跳过已知离线的远程节点**。SSH 连不通要等 ~10s 超时，
          AIDE 首屏/轮询会因此整体卡 10s+（实测就是这个原因）。
          需要顺带重试离线节点时传 `include_offline=True`。
        - 每个节点加 8s 硬超时，避免单个坏节点拖垮整次扫描。
        """
        nodes: List[ComputeNode]
        if node_id is not None:
            n = self.repo.get_by_id(node_id)
            nodes = [n] if n else []
        else:
            nodes = self.repo.get_all()
            if not include_offline:
                # 本地节点永不跳过；远程节点只在非 offline 时才扫
                nodes = [
                    n for n in nodes
                    if n and (
                        n.is_local
                        or (n.status.value if hasattr(n.status, "value") else n.status)
                        != NodeStatus.OFFLINE.value
                    )
                ]

        for node in nodes:
            if not node:
                continue
            try:
                containers = await asyncio.wait_for(
                    self.list_containers(node.id, all_containers=False), timeout=8.0,
                )
            except asyncio.TimeoutError:
                logger.warning(f"节点 {node.name} 容器列表超时（>8s），跳过发现")
                continue
            except Exception:
                logger.warning(f"节点 {node.name} 容器列表获取失败，跳过发现")
                continue

            running = [c for c in containers if c.status == "running"]
            if not running:
                continue

            # 并发探测各容器的 LISTEN 端口 —— 串行时 N 个容器 = N × exec 延迟，
            # 这是 AIDE 首屏/轮询慢的主要来源。
            async def _safe_probe(c: ContainerInfo):
                try:
                    return c, await self._probe_listen_ports(node, c.id)
                except Exception:
                    return c, None

            probed = await asyncio.gather(*(_safe_probe(c) for c in running))

            for c, listens in probed:
                if listens is None:
                    continue

                # 只自动登记 opencode 常用端口（4096/4097）以及已有映射的端口
                mapped = {pm.container_port for pm in c.port_mappings}
                candidates = {p for p in listens if p in (4096, 4097)} | (
                    {p for p in listens if p in mapped}
                )
                for port in candidates:
                    if self.svc_repo.get_by_container_port(c.id, port):
                        continue  # 已登记，refresh 阶段会更新状态
                    kind = (
                        ServiceKind.OPENCODE_WEB
                        if port in (4096, 4097)
                        else ServiceKind.OTHER
                    )
                    host_port = next(
                        (pm.host_port for pm in c.port_mappings if pm.container_port == port),
                        None,
                    )
                    self.svc_repo.create({
                        "node_id": node.id,
                        "node_name": node.name,
                        "container_id": c.id,
                        "container_name": c.name,
                        "image": c.image,
                        "kind": kind,
                        "name": _default_service_name(kind, port),
                        "container_port": port,
                        "host_port": host_port,
                        "access_url": self._build_access_url(node, host_port),
                        "command": "（自动发现，非平台启动）",
                        "status": ServiceStatus.UNKNOWN,
                    })
            self.db.commit()

        # 发现后统一探一遍真实状态
        return await self.refresh_services(node_id=node_id)


    # ==================== shell 探测 ====================

    async def detect_shells(self, node_id: int, container_id: str) -> List[str]:
        """探测容器内可用的 shell，供控制台自动选择。

        「opencode 容器点控制台就报错」的根因之一：前端硬编码 /bin/bash，
        而很多镜像（alpine/distroless）只有 /bin/sh 或 /bin/ash，
        docker exec 直接失败且没有可读提示。
        """
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")

        probe = "; ".join(
            f"[ -x {s} ] && echo {s}" for s in SHELL_CANDIDATES
        )
        try:
            if node.is_local:
                out = await asyncio.to_thread(self._local_shell_exec, container_id, probe)
            else:
                out = await _ssh_exec(
                    node, f"docker exec {shlex.quote(container_id)} sh -c {shlex.quote(probe)}",
                )
        except Exception as e:
            logger.warning(f"探测 shell 失败: {e}")
            return []

        found = [line.strip() for line in (out or "").split("\n") if line.strip() in SHELL_CANDIDATES]
        # 按 SHELL_CANDIDATES 的优先级排序
        return sorted(set(found), key=lambda s: SHELL_CANDIDATES.index(s))

    # ==================== 镜像拉取 ====================

    async def pull_image(self, node_id: int, image: str) -> ImagePullResponse:
        node = self.repo.get_by_id(node_id)
        if not node:
            raise NotFoundException(f"节点 ID={node_id} 不存在")

        if node.is_local:
            def do_pull() -> str:
                client = self._local_docker()
                self._ensure_image_local(client, image, auto_pull=True)
                return "拉取成功"

            try:
                msg = await asyncio.wait_for(asyncio.to_thread(do_pull), timeout=900)
            except asyncio.TimeoutError:
                raise BusinessException(
                    f"拉取镜像 '{image}' 超过 15 分钟未完成，请检查网络后重试", "IMAGE_PULL_TIMEOUT",
                )
            return ImagePullResponse(image=image, success=True, message=msg)

        await _ssh_exec(node, f"docker pull {shlex.quote(image)}", timeout=900)
        return ImagePullResponse(image=image, success=True, message="拉取成功")

