"""发布管道 —— Bundle → Docker 容器，五阶段可观测.

    ① resolve    解析 bundle → 产物清单（含 sha256）
    ② validate   再校验一次（DB 可能被手改过）
    ③ write      内存 tar 原子上传；幂等跳过未变文件；清理孤儿产物
    ④ reload     重启容器内 opencode 服务
    ⑤ verify     回读 GET /agent 逐项比对；skill 用 opencode run 探测

**为什么必须重启**（实测结论，见 docs/PRD-agent-skill-platform.md §2.5）：
- `PATCH /config` 返回 200 但 agent 不出现在 `GET /agent`，也不落盘
- 写 opencode.jsonc 后不重启不热感知
→ 唯一可靠路径：写文件（为真）+ 重启（生效）+ GET /agent（校验）

**为什么不用 GET /api/skill 校验 skill**：
该端点在 skill 明确可用时仍返回 `data: []`，不可信。
改用容器内 `opencode run "列出可用 skills"` 作为权威判据。
"""
import asyncio
import io
import json
import logging
import shlex
import tarfile
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import httpx
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException, NotFoundException, ValidationException
from app.db.models.container_service_model import ServiceKind
from app.db.models.deployment_model import DeployScope, DeployStatus
from app.db.repositories.deployment_repo import DeploymentRepository
from app.schemas.agent_factory_schema import (
    DeploymentResponse,
    DeployRequest,
    RenderedArtifact,
    VerifyItem,
)
from app.services import agent_render_service as render
from app.services import agent_validate_service as validate
from app.services.agent_factory_service import AgentFactoryService
from app.services.compute_service import ComputeService, _ssh_exec

logger = logging.getLogger(__name__)

# 目标目录：global 对容器内所有项目生效；project 只对该工作区生效
SCOPE_DIRS = {
    DeployScope.GLOBAL.value: "/root/.config/opencode",
    DeployScope.PROJECT.value: "/workspace/.opencode",
}


class AgentDeployService:
    """Bundle 发布服务。"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = DeploymentRepository(db)
        self.factory = AgentFactoryService(db)
        self.compute = ComputeService(db)

    # ==================== 主流程 ====================

    async def deploy(
        self, bundle_id: int, req: DeployRequest, user_id: Optional[int] = None
    ) -> DeploymentResponse:
        started = time.time()

        # 重启会中断进行中的会话，必须显式确认
        if not req.restart_confirmed:
            raise ValidationException(
                "发布需要重启容器内的 opencode 服务才能生效（实测 PATCH /config 与文件热感知均不可用），"
                "这会中断进行中的会话。请确认后重试（restart_confirmed=true）。",
                code="RESTART_CONFIRMATION_REQUIRED",
            )

        # ---------- ① resolve ----------
        bundle_row, bundle_dict, agents, skills, skill_perms, task_ovr = (
            self.factory.resolve_bundle_for_deploy(bundle_id)
        )
        node = self.compute.repo.get_by_id(req.node_id)
        if not node:
            raise NotFoundException(f"节点 ID={req.node_id} 不存在")

        meta = await self.compute._resolve_container_meta(node, req.container_id)
        if meta is None:
            raise NotFoundException(
                f"容器 {req.container_id} 在节点 {node.name} 上不存在"
            )
        if meta.status != "running":
            raise BusinessException(
                f"容器当前是 {meta.status}，请先启动容器再发布",
                "CONTAINER_NOT_RUNNING",
            )

        target_dir = SCOPE_DIRS[req.scope]
        artifacts = render.render_bundle(bundle_dict, agents, skills, skill_perms, task_ovr)

        dep = self.repo.create({
            "bundle_id": bundle_row.id,
            "bundle_name": bundle_row.name,
            "bundle_version": bundle_row.current_version,
            "node_id": node.id,
            "node_name": node.name,
            "container_id": meta.id,
            "container_name": meta.name,
            "scope": req.scope,
            "target_dir": target_dir,
            "status": DeployStatus.VALIDATING.value,
            "deployed_by_user_id": user_id,
        })
        self.db.commit()

        try:
            # ---------- ② validate ----------
            result = validate.validate_bundle(bundle_dict, agents, skills)
            if not result.ok:
                errs = [f"· {i.field}: {i.message}" for i in result.issues if i.level == "error"]
                raise ValidationException(
                    "编排方案校验未通过，已中止发布：\n" + "\n".join(errs),
                    code="BUNDLE_VALIDATION_FAILED",
                )

            # ---------- ③ write ----------
            dep.status = DeployStatus.WRITING.value
            self.db.commit()

            # 排除本次记录（dep 已入库但产物清单还没写），否则拿到自己导致幂等失效
            prev = self.repo.latest_for_target(bundle_row.id, meta.id, exclude_id=dep.id)
            prev_paths = self._prev_paths(prev)
            written, skipped = await self._write_artifacts(
                node, meta.id, target_dir, artifacts, prev,
            )
            pruned: List[str] = []
            if req.prune:
                pruned = await self._prune_orphans(
                    node, meta.id, target_dir, artifacts, prev_paths,
                )

            dep.artifacts_json = {
                "files": [
                    {
                        "path": a.path,
                        "sha256": a.sha256,
                        "bytes": a.bytes,
                        "skipped": a.path in skipped,
                    }
                    for a in artifacts
                ],
                "written": len(written),
                "skipped": len(skipped),
                "pruned": pruned,
            }
            self.db.commit()

            # ---------- ④ reload ----------
            dep.status = DeployStatus.RELOADING.value
            self.db.commit()
            reload_detail = await self._reload_service(node, meta.id)
            dep.restart_used = True
            self.db.commit()

            # ---------- ⑤ verify ----------
            dep.status = DeployStatus.VERIFYING.value
            self.db.commit()
            verify = await self._verify(
                node, meta.id, agents, skills, reload_detail,
            )
            dep.verify_json = verify
            all_ok = verify.get("summary", {}).get("all_match", False)
            dep.status = (
                DeployStatus.SUCCESS.value if all_ok else DeployStatus.PARTIAL.value
            )
            if not all_ok:
                miss = verify.get("summary", {}).get("mismatched", [])
                dep.error_detail = (
                    f"产物已写入并重启，但回读校验有 {len(miss)} 处不一致：{', '.join(miss)}。"
                    f"常见原因：agent 名与文件名不符、YAML 格式问题、"
                    f"或该 scope 未被 opencode 扫描（试试换 scope）。"
                )
            dep.duration_ms = int((time.time() - started) * 1000)
            self.db.commit()
            return self._resp(dep)

        except Exception as e:
            dep.status = DeployStatus.FAILED.value
            dep.error_detail = getattr(e, "message", None) or str(e)
            dep.duration_ms = int((time.time() - started) * 1000)
            self.db.commit()
            raise

    # ==================== ③ write ====================

    @staticmethod
    def _prev_paths(prev) -> List[str]:
        if not prev or not prev.artifacts_json:
            return []
        files = (prev.artifacts_json or {}).get("files") or []
        return [f.get("path") for f in files if f.get("path")]

    @staticmethod
    def _prev_hashes(prev) -> Dict[str, str]:
        if not prev or not prev.artifacts_json:
            return {}
        files = (prev.artifacts_json or {}).get("files") or []
        return {f["path"]: f.get("sha256", "") for f in files if f.get("path")}

    async def _write_artifacts(
        self,
        node,
        container_id: str,
        target_dir: str,
        artifacts: Sequence[RenderedArtifact],
        prev,
    ) -> Tuple[List[str], List[str]]:
        """上传产物。返回 (已写入路径, 跳过路径)。

        幂等：sha256 与上次发布相同且文件仍存在 → 跳过。
        用 tar 而非 echo 写文件：原子、支持嵌套目录、彻底避开引号与中文编码问题。
        """
        prev_hashes = self._prev_hashes(prev)
        skipped: List[str] = []
        to_write: List[RenderedArtifact] = []

        if prev_hashes:
            # 校验容器内文件是否真的还在（可能被人手删了）
            existing = await self._list_existing(node, container_id, target_dir, artifacts)
            for a in artifacts:
                if prev_hashes.get(a.path) == a.sha256 and a.path in existing:
                    skipped.append(a.path)
                else:
                    to_write.append(a)
        else:
            to_write = list(artifacts)

        if not to_write:
            logger.info(f"[deploy] 全部 {len(artifacts)} 个产物内容未变，跳过写入")
            return [], skipped

        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            for a in to_write:
                data = a.content.encode("utf-8")
                ti = tarfile.TarInfo(name=a.path)
                ti.size = len(data)
                ti.mode = 0o755 if a.is_executable else 0o644
                ti.mtime = int(time.time())
                tar.addfile(ti, io.BytesIO(data))
        payload = buf.getvalue()

        if node.is_local:
            def _put() -> None:
                client = self.compute._local_docker()
                c = client.containers.get(container_id)
                c.exec_run(["sh", "-c", f"mkdir -p {shlex.quote(target_dir)}"])
                if not c.put_archive(target_dir, payload):
                    raise BusinessException("上传产物失败（put_archive 返回 False）", "DEPLOY_WRITE_FAILED")

            await asyncio.to_thread(_put)
        else:
            # 远程：tar 走 base64 过 SSH，避免二进制在 shell 管道里被破坏
            import base64

            b64 = base64.b64encode(payload).decode()
            cmd = (
                f"docker exec -i {shlex.quote(container_id)} sh -c "
                f"{shlex.quote(f'mkdir -p {target_dir}')} && "
                f"echo {shlex.quote(b64)} | base64 -d | "
                f"docker exec -i {shlex.quote(container_id)} tar -x -C {shlex.quote(target_dir)}"
            )
            await _ssh_exec(node, cmd, timeout=300)

        return [a.path for a in to_write], skipped

    async def _list_existing(
        self,
        node,
        container_id: str,
        target_dir: str,
        artifacts: Sequence[RenderedArtifact],
    ) -> set:
        """检查产物文件在容器内是否存在（幂等判断的第二个条件）。"""
        paths = [f"{target_dir}/{a.path}" for a in artifacts]
        # 单条命令批量测试，避免 N 次 exec
        probe = "; ".join(f"[ -f {shlex.quote(p)} ] && echo {shlex.quote(p)}" for p in paths)
        try:
            if node.is_local:
                out = await asyncio.to_thread(
                    self.compute._local_shell_exec, container_id, probe,
                )
            else:
                out = await _ssh_exec(
                    node,
                    f"docker exec {shlex.quote(container_id)} sh -c {shlex.quote(probe)}",
                    timeout=30,
                )
        except Exception:
            return set()
        prefix = f"{target_dir}/"
        return {
            line.strip()[len(prefix):]
            for line in (out or "").split("\n")
            if line.strip().startswith(prefix)
        }

    async def _prune_orphans(
        self,
        node,
        container_id: str,
        target_dir: str,
        artifacts: Sequence[RenderedArtifact],
        prev_paths: Sequence[str],
    ) -> List[str]:
        """清理上次发布过、本次已移除的产物。

        不清理会留下「孤儿 agent」—— 用户从方案里删掉了某个 agent，
        但容器里的 .md 还在，OpenCode 依然会加载它。
        只删本 bundle 之前写过的路径，绝不碰其它文件。
        """
        current = {a.path for a in artifacts}
        orphans = [p for p in prev_paths if p and p not in current]
        if not orphans:
            return []

        cmds = " ; ".join(
            f"rm -f {shlex.quote(f'{target_dir}/{p}')}" for p in orphans
        )
        # 顺带清掉空的 skill 目录
        cmds += (
            f" ; find {shlex.quote(target_dir)}/skills -mindepth 1 -type d -empty "
            f"-delete 2>/dev/null || true"
        )
        try:
            if node.is_local:
                await asyncio.to_thread(
                    self.compute._local_shell_exec, container_id, cmds,
                )
            else:
                await _ssh_exec(
                    node,
                    f"docker exec {shlex.quote(container_id)} sh -c {shlex.quote(cmds)}",
                    timeout=60,
                )
            logger.info(f"[deploy] 清理 {len(orphans)} 个孤儿产物: {orphans}")
        except Exception as e:
            logger.warning(f"[deploy] 清理孤儿产物失败（不影响发布）: {e}")
        return orphans

    # ==================== ④ reload ====================

    async def _reload_service(self, node, container_id: str) -> Dict[str, Any]:
        """重启容器内的 opencode 服务，使新产物生效。

        复用 container_services 登记：找到该容器上的 opencode 服务，
        杀掉进程再按原命令拉起。控制面校验需要 serve（web 不暴露 /agent）。
        """
        rows = self.compute.svc_repo.list_by_container(container_id)
        oc = [
            r for r in rows
            if (r.kind.value if hasattr(r.kind, "value") else str(r.kind))
            in (ServiceKind.OPENCODE_SERVE.value, ServiceKind.OPENCODE_WEB.value)
        ]
        # serve 优先（它才有 /agent 控制面）
        oc.sort(key=lambda r: 0 if "serve" in str(r.kind) else 1)

        if not oc:
            return {
                "restarted": False,
                "reason": (
                    "该容器没有登记的 opencode 服务，未执行重启。"
                    "产物已写入，下次服务启动时会生效。"
                    "建议到「算力管理 → 服务」页启动一个 opencode serve。"
                ),
                "control_url": None,
            }

        svc = oc[0]
        port = svc.container_port
        cors = "http://localhost:5173"
        subcmd = (
            "serve"
            if (svc.kind.value if hasattr(svc.kind, "value") else str(svc.kind))
            == ServiceKind.OPENCODE_SERVE.value
            else "web"
        )
        log_path = svc.log_path or f"/var/log/opencode/{subcmd}-{port}.log"

        # 杀掉旧进程（按端口特征匹配；pkill 可能不存在，用 /proc 兜底）
        kill = (
            f"(pkill -f -- '--port {port}' 2>/dev/null) || "
            f"(for p in /proc/[0-9]*; do "
            f"  if tr '\\0' ' ' < $p/cmdline 2>/dev/null | grep -q -- '--port {port}'; then "
            f"    kill $(basename $p) 2>/dev/null; fi; done); echo killed"
        )
        # 必须 --hostname 0.0.0.0，否则宿主访问不到（Docker 头号坑）
        start = (
            f"mkdir -p $(dirname {log_path}) && cd /workspace && "
            f"nohup opencode {subcmd} --port {port} --hostname 0.0.0.0 "
            f"--cors {cors} > {log_path} 2>&1 &"
        )

        if node.is_local:
            await asyncio.to_thread(self.compute._local_shell_exec, container_id, kill)
            await asyncio.sleep(1.5)

            def _start() -> None:
                client = self.compute._local_docker()
                c = client.containers.get(container_id)
                # detach 启动，不等它退出
                c.exec_run(["sh", "-c", start], detach=True)

            await asyncio.to_thread(_start)
        else:
            await _ssh_exec(
                node,
                f"docker exec {shlex.quote(container_id)} sh -c {shlex.quote(kill)}",
                timeout=60,
            )
            await asyncio.sleep(1.5)
            await _ssh_exec(
                node,
                f"docker exec -d {shlex.quote(container_id)} sh -c {shlex.quote(start)}",
                timeout=60,
            )

        # 等端口重新监听（serve 冷启动要几秒）
        listening = False
        for _ in range(40):
            await asyncio.sleep(0.5)
            try:
                if port in await self.compute._probe_listen_ports(node, container_id):
                    listening = True
                    break
            except Exception:
                continue

        # 刷新服务登记状态（会重新探测 host_port / 可达性）
        try:
            await self.compute.refresh_service(svc.id)
        except Exception:
            pass

        # 重新从 DB 取一次：refresh_service 内部 commit 过，
        # 且端口映射可能刚被探测出来，必须回读而不是用旧的内存对象
        fresh = self.compute.svc_repo.get_by_id(svc.id)
        host_port = (fresh.host_port if fresh else None) or svc.host_port
        if not host_port:
            # 兜底：直接从容器端口映射里找（服务登记可能还没探到）
            try:
                meta = await self.compute._resolve_container_meta(node, container_id)
                if meta:
                    for pm in meta.port_mappings:
                        if pm.container_port == port:
                            host_port = pm.host_port
                            break
            except Exception:
                pass

        control_url = None
        if subcmd == "serve" and host_port:
            host = "localhost" if node.is_local else node.host
            control_url = f"http://{host}:{host_port}"

        return {
            "restarted": True,
            "service_id": svc.id,
            "kind": subcmd,
            "port": port,
            "listening": listening,
            "control_url": control_url,
            "reason": None if listening else f"重启后端口 {port} 在 20s 内未恢复监听，请查看 {log_path}",
        }

    # ==================== ⑤ verify ====================

    async def _verify(
        self,
        node,
        container_id: str,
        agents: Sequence[Dict[str, Any]],
        skills: Sequence[Dict[str, Any]],
        reload_detail: Dict[str, Any],
    ) -> Dict[str, Any]:
        """回读校验 —— 发布结果必须可证伪，不做 fire-and-forget。"""
        items: List[Dict[str, Any]] = []
        control_url = reload_detail.get("control_url")

        # ---- agent：GET /agent 是可靠的权威依据 ----
        actual_agents: Dict[str, Dict[str, Any]] = {}
        agent_probe_error: Optional[str] = None
        if control_url:
            try:
                async with httpx.AsyncClient(timeout=8.0) as cli:
                    resp = await cli.get(f"{control_url}/agent")
                if resp.status_code == 200:
                    for a in resp.json():
                        actual_agents[a.get("name")] = a
                else:
                    agent_probe_error = f"GET /agent 返回 HTTP {resp.status_code}"
            except Exception as e:
                agent_probe_error = f"GET /agent 不可达：{str(e)[:120]}"
        else:
            agent_probe_error = (
                "未找到可用的 opencode serve 控制面（web 模式不暴露 /agent）。"
                "产物已写入，但无法自动校验。建议在该容器启动 opencode serve。"
            )

        for a in agents:
            name = a.get("name")
            act = actual_agents.get(name)
            if act is None:
                items.append(VerifyItem(
                    kind="agent", name=name, match=False,
                    expected={"mode": a.get("mode")},
                    detail=agent_probe_error or "OpenCode 未加载该 agent（检查文件名与 name 是否一致）",
                ).model_dump())
                continue

            # 逐项比对关键字段
            diffs: List[str] = []
            if a.get("description") and act.get("description") != a.get("description"):
                diffs.append("description")
            exp_mode = a.get("mode")
            # mode=all 时 OpenCode 会归一化，不算差异
            if exp_mode and exp_mode != "all" and act.get("mode") != exp_mode:
                diffs.append(f"mode(期望 {exp_mode}，实际 {act.get('mode')})")
            if a.get("temperature") is not None and act.get("temperature") != a.get("temperature"):
                diffs.append("temperature")
            exp_perm = a.get("permission_json") or {}
            perm_diffs = self._compare_permission(exp_perm, act.get("permission") or [])
            diffs.extend(perm_diffs)

            items.append(VerifyItem(
                kind="agent", name=name, match=not diffs,
                expected={
                    "mode": exp_mode,
                    "temperature": a.get("temperature"),
                    "permission": exp_perm,
                },
                actual={
                    "mode": act.get("mode"),
                    "temperature": act.get("temperature"),
                    "permission_rules": len(act.get("permission") or []),
                },
                detail=None if not diffs else "字段不一致：" + ", ".join(diffs),
            ).model_dump())

        # ---- skill：/api/skill 不可信，用 opencode run 探测 ----
        skill_names_actual: set = set()
        skill_probe_error: Optional[str] = None
        if skills:
            try:
                skill_names_actual = await self._probe_skills(node, container_id)
            except Exception as e:
                skill_probe_error = f"探测失败：{str(e)[:120]}"

        for s in skills:
            name = s.get("name")
            hit = name in skill_names_actual
            items.append(VerifyItem(
                kind="skill", name=name, match=hit,
                detail=None if hit else (
                    skill_probe_error
                    or "OpenCode 未列出该 skill（检查目录名与 frontmatter name 是否一致）"
                ),
            ).model_dump())

        mismatched = [i["name"] for i in items if not i["match"]]
        return {
            "items": items,
            "reload": reload_detail,
            "summary": {
                "total": len(items),
                "matched": len(items) - len(mismatched),
                "mismatched": mismatched,
                "all_match": not mismatched,
                "agent_probe_error": agent_probe_error,
                "skill_probe_error": skill_probe_error,
            },
        }

    @staticmethod
    def _compare_permission(
        expected: Dict[str, Any], actual_rules: Sequence[Dict[str, Any]]
    ) -> List[str]:
        """比对权限。

        OpenCode 会把 permission 展开成 [{permission,pattern,action}]，
        且**注入自己的默认规则**（如 external_directory 的一堆 skill 路径），
        所以只做「我们声明的规则是否都在里面」的单向包含检查。
        """
        if not expected:
            return []
        # 同 (permission, pattern) 可能有多条（OpenCode 默认 + 我们的），取最后一条为准
        actual_map: Dict[Tuple[str, str], str] = {}
        for r in actual_rules:
            key = (r.get("permission"), r.get("pattern"))
            actual_map[key] = r.get("action")

        diffs: List[str] = []
        for key, val in expected.items():
            if isinstance(val, str):
                got = actual_map.get((key, "*"))
                if got != val:
                    diffs.append(f"permission.{key}(期望 {val}，实际 {got})")
            elif isinstance(val, dict):
                for pat, act in val.items():
                    got = actual_map.get((key, pat))
                    if got != act:
                        diffs.append(f"permission.{key}[{pat}](期望 {act}，实际 {got})")
        return diffs

    async def _probe_skills(self, node, container_id: str) -> set:
        """用 opencode run 让模型列出可用 skills —— 唯一可靠的 skill 校验方式。

        实测：GET /api/skill 在 skill 明确可用时仍返回 data:[]，不能用。
        """
        cmd = (
            "cd /workspace && opencode run --agent build "
            "'列出你可用的 skills 名称清单，只输出名称，每行一个，不要解释' 2>&1"
        )
        if node.is_local:
            out = await asyncio.wait_for(
                asyncio.to_thread(self.compute._local_shell_exec, container_id, cmd),
                timeout=180,
            )
        else:
            out = await _ssh_exec(
                node,
                f"docker exec {shlex.quote(container_id)} sh -c {shlex.quote(cmd)}",
                timeout=180,
            )
        names: set = set()
        for line in (out or "").split("\n"):
            t = line.strip().lstrip("-*• ").strip()
            # 去 ANSI 转义
            t = __import__("re").sub(r"\x1b\[[0-9;]*[A-Za-z]", "", t).strip()
            if t and __import__("re").match(r"^[a-z0-9]+(-[a-z0-9]+)*$", t):
                names.add(t)
        return names

    # ==================== 查询 ====================

    def _resp(self, row) -> DeploymentResponse:
        return DeploymentResponse(
            id=row.id,
            bundle_id=row.bundle_id,
            bundle_name=row.bundle_name,
            bundle_version=row.bundle_version,
            node_id=row.node_id,
            node_name=row.node_name,
            container_id=row.container_id,
            container_name=row.container_name,
            scope=row.scope,
            target_dir=row.target_dir,
            status=row.status,
            artifacts_json=row.artifacts_json,
            verify_json=row.verify_json,
            restart_used=bool(row.restart_used),
            error_detail=row.error_detail,
            duration_ms=row.duration_ms,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def list_deployments(
        self,
        bundle_id: Optional[int] = None,
        node_id: Optional[int] = None,
        container_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[DeploymentResponse]:
        rows = self.repo.list_filtered(
            bundle_id=bundle_id, node_id=node_id,
            container_id=container_id, status=status,
        )
        return [self._resp(r) for r in rows]

    def get_deployment(self, deployment_id: int) -> DeploymentResponse:
        row = self.repo.get_by_id(deployment_id)
        if not row:
            raise NotFoundException(f"发布记录 ID={deployment_id} 不存在")
        return self._resp(row)

    async def reverify(self, deployment_id: int) -> DeploymentResponse:
        """重新回读校验（不重新写文件、不重启）。"""
        row = self.repo.get_by_id(deployment_id)
        if not row:
            raise NotFoundException(f"发布记录 ID={deployment_id} 不存在")
        node = self.compute.repo.get_by_id(row.node_id)
        if not node:
            raise NotFoundException("所属节点已删除")

        _, _, agents, skills, _, _ = self.factory.resolve_bundle_for_deploy(row.bundle_id)
        # 复用上次的 reload 信息拿 control_url；没有就重新推断
        reload_detail = (row.verify_json or {}).get("reload") or {}
        if not reload_detail.get("control_url"):
            reload_detail = await self._infer_control_url(node, row.container_id)

        verify = await self._verify(node, row.container_id, agents, skills, reload_detail)
        row.verify_json = verify
        all_ok = verify.get("summary", {}).get("all_match", False)
        row.status = DeployStatus.SUCCESS.value if all_ok else DeployStatus.PARTIAL.value
        row.error_detail = None if all_ok else (
            f"回读校验有 {len(verify['summary']['mismatched'])} 处不一致："
            f"{', '.join(verify['summary']['mismatched'])}"
        )
        self.db.commit()
        return self._resp(row)

    async def _infer_control_url(self, node, container_id: str) -> Dict[str, Any]:
        """从服务登记推断控制面 URL（reverify 用）。"""
        rows = self.compute.svc_repo.list_by_container(container_id)
        for r in rows:
            kind = r.kind.value if hasattr(r.kind, "value") else str(r.kind)
            if kind != ServiceKind.OPENCODE_SERVE.value:
                continue
            host_port = r.host_port
            if not host_port:
                # 服务登记里没有映射，直接查容器的端口映射
                try:
                    meta = await self.compute._resolve_container_meta(node, container_id)
                    if meta:
                        for pm in meta.port_mappings:
                            if pm.container_port == r.container_port:
                                host_port = pm.host_port
                                break
                except Exception:
                    pass
            if host_port:
                host = "localhost" if node.is_local else node.host
                return {
                    "restarted": False,
                    "control_url": f"http://{host}:{host_port}",
                    "kind": "serve",
                    "port": r.container_port,
                }
        return {
            "restarted": False,
            "control_url": None,
            "reason": (
                "该容器没有「已映射宿主端口的 opencode serve」，无法回读校验。"
                "opencode web 不暴露 /agent 控制面；请在该容器启动 serve 并映射端口。"
            ),
        }
