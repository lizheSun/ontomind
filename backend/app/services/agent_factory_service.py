"""Agent 工厂 Service — Agent / Skill / Bundle 的 CRUD、版本、导入.

事务边界在本层（repo 只 flush，Service 负责 commit），符合 backend/STANDARDS.md。

设计要点：
- **写入前必过校验器**：OpenCode 对非法权限键静默忽略，必须在设计态拦住
- 内置预设（is_builtin_preset）允许改内容但**不允许删**，避免用户误删失去参考
- 版本快照存整份 JSON 而非 diff，保证回滚绝对可靠
"""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException, NotFoundException, ValidationException
from app.db.models.agent_bundle_model import (
    AgentBundle,
    BundleMember,
    MemberRole,
    MemberType,
)
from app.db.models.agent_template_model import AgentTemplate, TemplateSource
from app.db.models.skill_template_model import SkillFile, SkillTemplate
from app.db.repositories.agent_bundle_repo import (
    AgentBundleRepository,
    BundleMemberRepository,
)
from app.db.repositories.agent_template_repo import (
    AgentTemplateRepository,
    AgentTemplateVersionRepository,
)
from app.db.repositories.skill_template_repo import (
    SkillFileRepository,
    SkillTemplateRepository,
)
from app.schemas.agent_factory_schema import (
    AgentBundleCreate,
    AgentBundleResponse,
    AgentBundleUpdate,
    AgentImportRequest,
    AgentTemplateCreate,
    AgentTemplateResponse,
    AgentTemplateUpdate,
    AgentVersionResponse,
    BundleMemberItem,
    BundleMemberResponse,
    PreviewResponse,
    SkillFileItem,
    SkillTemplateCreate,
    SkillTemplateResponse,
    SkillTemplateUpdate,
    ValidationResult,
)
from app.services import agent_render_service as render
from app.services import agent_validate_service as validate

logger = logging.getLogger(__name__)

# agent .md 的 frontmatter 分隔
_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.S)


class AgentFactoryService:
    """Agent 工厂服务。"""

    def __init__(self, db: Session):
        self.db = db
        self.agent_repo = AgentTemplateRepository(db)
        self.version_repo = AgentTemplateVersionRepository(db)
        self.skill_repo = SkillTemplateRepository(db)
        self.file_repo = SkillFileRepository(db)
        self.bundle_repo = AgentBundleRepository(db)
        self.member_repo = BundleMemberRepository(db)

    # ==================== 通用 ====================

    @staticmethod
    def _raise_if_invalid(result: ValidationResult, what: str) -> None:
        """校验不通过就抛业务异常，错误信息带上具体字段与修正建议。"""
        if result.ok:
            return
        errors = [i for i in result.issues if i.level == "error"]
        lines = [f"· {i.field}: {i.message}" for i in errors]
        raise ValidationException(
            f"{what}校验未通过（{len(errors)} 处错误）：\n" + "\n".join(lines),
            code="TEMPLATE_VALIDATION_FAILED",
        )

    # ==================== Agent ====================

    def _agent_to_dict(self, row: AgentTemplate) -> Dict[str, Any]:
        """ORM → dict（渲染器/校验器/快照共用的中间表示）。"""
        return {
            "name": row.name,
            "display_name": row.display_name,
            "description": row.description,
            "mode": row.mode,
            "model": row.model,
            "prompt": row.prompt,
            "temperature": row.temperature,
            "top_p": row.top_p,
            "steps": row.steps,
            "permission_json": row.permission_json,
            "options_json": row.options_json,
            "color": row.color,
            "hidden": bool(row.hidden),
            "disable": bool(row.disable),
            "category": row.category,
        }

    def _agent_resp(self, row: AgentTemplate) -> AgentTemplateResponse:
        return AgentTemplateResponse(
            id=row.id,
            is_builtin_preset=bool(row.is_builtin_preset),
            source=row.source,
            current_version=row.current_version,
            created_at=row.created_at,
            updated_at=row.updated_at,
            **self._agent_to_dict(row),
        )

    def list_agents(
        self,
        category: Optional[str] = None,
        mode: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> List[AgentTemplateResponse]:
        rows = self.agent_repo.list_filtered(category=category, mode=mode, keyword=keyword)
        return [self._agent_resp(r) for r in rows]

    def get_agent(self, agent_id: int) -> AgentTemplateResponse:
        row = self.agent_repo.get_by_id(agent_id)
        if not row:
            raise NotFoundException(f"Agent 模板 ID={agent_id} 不存在")
        return self._agent_resp(row)

    def create_agent(
        self, data: AgentTemplateCreate, user_id: Optional[int] = None
    ) -> AgentTemplateResponse:
        payload = data.model_dump()
        self._raise_if_invalid(validate.validate_agent(payload), "Agent")

        if self.agent_repo.get_by_name(data.name):
            raise BusinessException(
                f"Agent 名 '{data.name}' 已存在。它同时是落盘文件名，必须唯一。",
                "AGENT_NAME_DUPLICATED",
            )

        row = self.agent_repo.create({
            **payload,
            "source": TemplateSource.PLATFORM.value,
            "is_builtin_preset": False,
            "current_version": 1,
            "created_by_user_id": user_id,
        })
        self.db.commit()
        return self._agent_resp(row)

    def update_agent(
        self, agent_id: int, data: AgentTemplateUpdate
    ) -> AgentTemplateResponse:
        row = self.agent_repo.get_by_id(agent_id)
        if not row:
            raise NotFoundException(f"Agent 模板 ID={agent_id} 不存在")

        patch = data.model_dump(exclude_unset=True)
        merged = {**self._agent_to_dict(row), **patch}
        self._raise_if_invalid(validate.validate_agent(merged), "Agent")

        updated = self.agent_repo.update(agent_id, patch)
        self.db.commit()
        return self._agent_resp(updated)

    def delete_agent(self, agent_id: int) -> bool:
        row = self.agent_repo.get_by_id(agent_id)
        if not row:
            raise NotFoundException(f"Agent 模板 ID={agent_id} 不存在")
        if row.is_builtin_preset:
            raise BusinessException(
                f"'{row.name}' 是内置预设，不可删除（可以修改它，或另建一个新 agent）",
                "PRESET_NOT_DELETABLE",
            )
        used = self.member_repo.count_by_agent(agent_id)
        if used:
            raise BusinessException(
                f"'{row.name}' 正被 {used} 个编排方案引用，请先从方案中移除再删除",
                "AGENT_IN_USE",
            )
        self.agent_repo.delete(agent_id)
        self.db.commit()
        return True

    def preview_agent(self, agent_id: int) -> PreviewResponse:
        """渲染 .md 预览（不落盘）—— 让用户所见即所得。"""
        row = self.agent_repo.get_by_id(agent_id)
        if not row:
            raise NotFoundException(f"Agent 模板 ID={agent_id} 不存在")
        d = self._agent_to_dict(row)
        content = render.render_agent_md(d)
        import hashlib

        from app.schemas.agent_factory_schema import RenderedArtifact

        art = RenderedArtifact(
            path=f"agents/{row.name}.md",
            content=content,
            sha256=hashlib.sha256(content.encode()).hexdigest(),
            bytes=len(content.encode()),
        )
        return PreviewResponse(
            artifacts=[art],
            validation=validate.validate_agent(d),
            tree=[art.path],
        )

    def validate_agent_payload(self, payload: Dict[str, Any]) -> ValidationResult:
        """不落库的纯校验（前端边编辑边校验用）。"""
        return validate.validate_agent(payload)

    # ---- 版本 ----

    def create_agent_version(
        self, agent_id: int, change_note: Optional[str], user_id: Optional[int] = None
    ) -> AgentVersionResponse:
        row = self.agent_repo.get_by_id(agent_id)
        if not row:
            raise NotFoundException(f"Agent 模板 ID={agent_id} 不存在")

        next_ver = self.version_repo.max_version(agent_id) + 1
        snap = self._agent_to_dict(row)
        v = self.version_repo.create({
            "agent_template_id": agent_id,
            "version": next_ver,
            "snapshot_json": snap,
            "change_note": change_note,
            "created_by_user_id": user_id,
        })
        row.current_version = next_ver
        self.db.commit()
        return AgentVersionResponse(
            id=v.id,
            agent_template_id=agent_id,
            version=v.version,
            snapshot_json=v.snapshot_json,
            change_note=v.change_note,
            created_at=v.created_at,
        )

    def list_agent_versions(self, agent_id: int) -> List[AgentVersionResponse]:
        if not self.agent_repo.get_by_id(agent_id):
            raise NotFoundException(f"Agent 模板 ID={agent_id} 不存在")
        return [
            AgentVersionResponse(
                id=v.id,
                agent_template_id=v.agent_template_id,
                version=v.version,
                snapshot_json=v.snapshot_json,
                change_note=v.change_note,
                created_at=v.created_at,
            )
            for v in self.version_repo.list_by_template(agent_id)
        ]

    def rollback_agent(self, agent_id: int, version: int) -> AgentTemplateResponse:
        row = self.agent_repo.get_by_id(agent_id)
        if not row:
            raise NotFoundException(f"Agent 模板 ID={agent_id} 不存在")
        v = self.version_repo.get_version(agent_id, version)
        if not v:
            raise NotFoundException(f"版本 v{version} 不存在")

        snap = dict(v.snapshot_json or {})
        # name 不回滚 —— 它是落盘文件名，改了会变成另一个 agent
        snap.pop("name", None)
        self._raise_if_invalid(
            validate.validate_agent({**snap, "name": row.name}), "回滚目标版本",
        )
        for k, val in snap.items():
            if hasattr(row, k):
                setattr(row, k, val)
        self.db.commit()
        return self._agent_resp(row)

    # ---- 导入 ----

    def import_agent(
        self, data: AgentImportRequest, user_id: Optional[int] = None
    ) -> AgentTemplateResponse:
        """从 agent .md 文本反向导入。

        用途：把散落在容器/本地的手写 agent 收进平台管理。
        """
        parsed = self._parse_agent_md(data.content)
        name = (data.name or parsed.get("name") or "").strip()
        if not name:
            raise ValidationException(
                "无法确定 agent 名。OpenCode 的 agent 名来自文件名，"
                "请在请求里显式传 name（如 code-reviewer）",
                code="AGENT_NAME_REQUIRED",
            )
        parsed["name"] = name
        if data.category:
            parsed["category"] = data.category

        self._raise_if_invalid(validate.validate_agent(parsed), "导入的 Agent")

        existing = self.agent_repo.get_by_name(name)
        if existing and not data.overwrite:
            raise BusinessException(
                f"Agent '{name}' 已存在。如需覆盖请传 overwrite=true",
                "AGENT_NAME_DUPLICATED",
            )

        if existing:
            for k, v in parsed.items():
                if k != "name" and hasattr(existing, k):
                    setattr(existing, k, v)
            existing.source = TemplateSource.IMPORTED.value
            self.db.commit()
            return self._agent_resp(existing)

        row = self.agent_repo.create({
            **parsed,
            "source": TemplateSource.IMPORTED.value,
            "is_builtin_preset": False,
            "current_version": 1,
            "created_by_user_id": user_id,
        })
        self.db.commit()
        return self._agent_resp(row)

    @staticmethod
    def _parse_agent_md(text: str) -> Dict[str, Any]:
        """解析 agent .md → dict。

        只做「够用」的 YAML 子集解析：标量 + 一层嵌套（permission）。
        不引入 pyyaml 是为了与渲染器保持对称，且避免它对 glob 键的引号处理差异。
        """
        m = _FM_RE.match(text.strip() + "\n")
        if not m:
            # 没有 frontmatter：整体当 prompt
            return {"description": "", "prompt": text.strip()}

        fm_text, body = m.group(1), m.group(2)
        out: Dict[str, Any] = {"prompt": body.strip() or None}

        def _val(raw: str) -> Any:
            raw = raw.strip()
            if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
                return raw[1:-1].replace('\\"', '"').replace("\\\\", "\\")
            if raw.startswith("'") and raw.endswith("'") and len(raw) >= 2:
                return raw[1:-1]
            low = raw.lower()
            if low == "true":
                return True
            if low == "false":
                return False
            if low in ("null", "~", ""):
                return None
            try:
                return int(raw)
            except ValueError:
                pass
            try:
                return float(raw)
            except ValueError:
                pass
            return raw

        def _key(raw: str) -> str:
            raw = raw.strip()
            if raw.startswith('"') and raw.endswith('"'):
                return raw[1:-1]
            if raw.startswith("'") and raw.endswith("'"):
                return raw[1:-1]
            return raw

        # 用「缩进栈」跟踪层级：(indent, 该层的容器 dict)
        # 之前只记 cur_key 会导致嵌套块结束后，同级键被错误塞进上一个嵌套容器里
        # （表现为 edit/read/grep 全跑进了 permission.bash 内部）
        stack: List[Tuple[int, Dict[str, Any]]] = [(-1, out)]

        for line in fm_text.split("\n"):
            if not line.strip() or line.strip().startswith("#"):
                continue
            if ":" not in line:
                continue
            indent = len(line) - len(line.lstrip())

            # 回退到正确的父层：栈顶缩进必须小于当前行
            while len(stack) > 1 and stack[-1][0] >= indent:
                stack.pop()
            container = stack[-1][1]

            k_raw, _, v_raw = line.partition(":")
            k, v = _key(k_raw), v_raw.strip()

            if v == "":
                # 开启一个嵌套块
                child: Dict[str, Any] = {}
                # permission 在 DB 里叫 permission_json
                container[("permission_json" if (k == "permission" and container is out) else k)] = child
                stack.append((indent, child))
            else:
                container[k] = _val(v)

        # 字段名对齐 DB
        if "top_p" in out:
            out["top_p"] = out.pop("top_p")
        if "maxSteps" in out:  # 兼容废弃字段
            out["steps"] = out.pop("maxSteps")
        out.setdefault("description", "")
        out.setdefault("mode", "subagent")
        # 只保留 DB 认识的键，其余丢弃（避免把 OpenCode 忽略的字段带进来）
        allowed = {
            "name", "display_name", "description", "mode", "model", "prompt",
            "temperature", "top_p", "steps", "permission_json", "options_json",
            "color", "hidden", "disable", "category",
        }
        return {k: v for k, v in out.items() if k in allowed}

    # ==================== Skill ====================

    def _skill_to_dict(self, row: SkillTemplate, with_files: bool = True) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "name": row.name,
            "display_name": row.display_name,
            "description": row.description,
            "license": row.license,
            "compatibility": row.compatibility,
            "metadata_json": row.metadata_json,
            "body": row.body,
            "category": row.category,
        }
        if with_files:
            d["files"] = [
                {
                    "rel_path": f.rel_path,
                    "content": f.content or "",
                    "is_executable": bool(f.is_executable),
                }
                for f in self.file_repo.list_by_skill(row.id)
            ]
        return d

    def _skill_resp(self, row: SkillTemplate) -> SkillTemplateResponse:
        d = self._skill_to_dict(row)
        files = [SkillFileItem(**f) for f in d.pop("files", [])]
        return SkillTemplateResponse(
            id=row.id,
            files=files,
            is_builtin_preset=bool(row.is_builtin_preset),
            source=row.source,
            current_version=row.current_version,
            created_at=row.created_at,
            updated_at=row.updated_at,
            **d,
        )

    def list_skills(
        self, category: Optional[str] = None, keyword: Optional[str] = None
    ) -> List[SkillTemplateResponse]:
        rows = self.skill_repo.list_filtered(category=category, keyword=keyword)
        return [self._skill_resp(r) for r in rows]

    def get_skill(self, skill_id: int) -> SkillTemplateResponse:
        row = self.skill_repo.get_by_id(skill_id)
        if not row:
            raise NotFoundException(f"Skill 模板 ID={skill_id} 不存在")
        return self._skill_resp(row)

    def create_skill(
        self, data: SkillTemplateCreate, user_id: Optional[int] = None
    ) -> SkillTemplateResponse:
        payload = data.model_dump()
        files = payload.pop("files", []) or []
        self._raise_if_invalid(
            validate.validate_skill({**payload, "files": files}), "Skill",
        )

        if self.skill_repo.get_by_name(data.name):
            raise BusinessException(
                f"Skill 名 '{data.name}' 已存在。它同时是落盘目录名，必须唯一。",
                "SKILL_NAME_DUPLICATED",
            )

        row = self.skill_repo.create({
            **payload,
            "source": TemplateSource.PLATFORM.value,
            "is_builtin_preset": False,
            "current_version": 1,
            "created_by_user_id": user_id,
        })
        for f in files:
            self.file_repo.create({
                "skill_template_id": row.id,
                "rel_path": f["rel_path"],
                "content": f.get("content") or "",
                "is_executable": bool(f.get("is_executable")),
            })
        self.db.commit()
        return self._skill_resp(row)

    def update_skill(
        self, skill_id: int, data: SkillTemplateUpdate
    ) -> SkillTemplateResponse:
        row = self.skill_repo.get_by_id(skill_id)
        if not row:
            raise NotFoundException(f"Skill 模板 ID={skill_id} 不存在")

        patch = data.model_dump(exclude_unset=True)
        new_files = patch.pop("files", None)

        cur = self._skill_to_dict(row)
        merged = {**cur, **patch}
        if new_files is not None:
            merged["files"] = new_files
        self._raise_if_invalid(validate.validate_skill(merged), "Skill")

        if patch:
            self.skill_repo.update(skill_id, patch)
        if new_files is not None:
            # 整批替换（前端传全量）
            self.file_repo.delete_by_skill(skill_id)
            for f in new_files:
                self.file_repo.create({
                    "skill_template_id": skill_id,
                    "rel_path": f["rel_path"],
                    "content": f.get("content") or "",
                    "is_executable": bool(f.get("is_executable")),
                })
        self.db.commit()
        return self._skill_resp(self.skill_repo.get_by_id(skill_id))

    def delete_skill(self, skill_id: int) -> bool:
        row = self.skill_repo.get_by_id(skill_id)
        if not row:
            raise NotFoundException(f"Skill 模板 ID={skill_id} 不存在")
        if row.is_builtin_preset:
            raise BusinessException(
                f"'{row.name}' 是内置预设，不可删除（可以修改它，或另建一个新 skill）",
                "PRESET_NOT_DELETABLE",
            )
        used = self.member_repo.count_by_skill(skill_id)
        if used:
            raise BusinessException(
                f"'{row.name}' 正被 {used} 个编排方案引用，请先从方案中移除再删除",
                "SKILL_IN_USE",
            )
        self.skill_repo.delete(skill_id)
        self.db.commit()
        return True

    def preview_skill(self, skill_id: int) -> PreviewResponse:
        row = self.skill_repo.get_by_id(skill_id)
        if not row:
            raise NotFoundException(f"Skill 模板 ID={skill_id} 不存在")
        d = self._skill_to_dict(row)
        arts = render.render_skill_files(d)
        return PreviewResponse(
            artifacts=arts,
            validation=validate.validate_skill(d),
            tree=render.artifacts_tree(arts),
        )

    # ==================== Bundle ====================

    def _bundle_members(self, bundle_id: int) -> Tuple[
        List[BundleMemberResponse], List[Dict[str, Any]], List[Dict[str, Any]],
        Dict[str, str], Dict[str, str],
    ]:
        """展开 bundle 成员。

        返回 (响应列表, agent dicts, skill dicts, skill 权限映射, task 覆盖映射)。

        同时为每个 subagent 成员计算**最终生效的委派动作**及其**来源**，
        让用户在页面上能直接看到「这条权限是哪来的」——
        原来 task 规则藏在 agent 模板的 JSON 里，是最大的隐性规则来源。
        """
        members = self.member_repo.list_by_bundle(bundle_id)
        resp: List[BundleMemberResponse] = []
        agents: List[Dict[str, Any]] = []
        skills: List[Dict[str, Any]] = []
        skill_perms: Dict[str, str] = {}
        task_overrides: Dict[str, str] = {}

        # 先建索引，便于后面算 effective_task
        agent_rows: Dict[int, Any] = {}
        for m in members:
            if m.member_type == MemberType.AGENT.value and m.agent_template_id:
                a = self.agent_repo.get_by_id(m.agent_template_id)
                if a:
                    agent_rows[m.agent_template_id] = a

        primary_rows = [
            agent_rows[m.agent_template_id]
            for m in members
            if m.member_type == MemberType.AGENT.value
            and m.role == MemberRole.PRIMARY.value
            and m.agent_template_id in agent_rows
        ]

        for m in members:
            item = BundleMemberResponse(
                id=m.id,
                member_type=m.member_type,
                agent_template_id=m.agent_template_id,
                skill_template_id=m.skill_template_id,
                role=m.role,
                skill_permission=m.skill_permission,
                task_permission=m.task_permission,
                sort_order=m.sort_order,
            )
            if m.member_type == MemberType.AGENT.value and m.agent_template_id:
                a = agent_rows.get(m.agent_template_id)
                if a:
                    item.member_name = a.name
                    item.member_description = a.description
                    item.member_mode = a.mode
                    d = self._agent_to_dict(a)
                    # bundle 里的 role 覆盖模板自身的 mode
                    # （同一个 agent 在不同方案里可以是 primary 也可以是 subagent）
                    if m.role in ("primary", "subagent"):
                        d["mode"] = m.role
                    agents.append(d)

                    if m.role == MemberRole.SUBAGENT.value:
                        if m.task_permission:
                            task_overrides[a.name] = m.task_permission
                        eff, src, detail = self._resolve_effective_task(
                            a.name, m.task_permission, primary_rows,
                        )
                        item.effective_task = eff
                        item.task_source = src
                        item.task_source_detail = detail
            elif m.member_type == MemberType.SKILL.value and m.skill_template_id:
                s = self.skill_repo.get_by_id(m.skill_template_id)
                if s:
                    item.member_name = s.name
                    item.member_description = s.description
                    skills.append(self._skill_to_dict(s))
                    if m.skill_permission:
                        skill_perms[s.name] = m.skill_permission
            resp.append(item)

        return resp, agents, skills, skill_perms, task_overrides

    @staticmethod
    def _resolve_effective_task(
        subagent_name: str,
        override: Optional[str],
        primaries: List[Any],
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """算出某 subagent 最终能不能被委派，并说清是哪条规则决定的。

        优先级：方案内覆盖 > agent 模板的 permission.task > 默认 allow。
        """
        if override:
            return override, "bundle", f"本方案显式设为 {override}"

        if not primaries:
            return None, None, "方案里没有 primary，无人可委派"

        # 多 primary 时取「最宽松」的那个（只要有一个能调就算能调）
        rank = {"allow": 2, "ask": 1, "deny": 0}
        best_act, best_detail = "deny", None
        for p in primaries:
            rule = (p.permission_json or {}).get("task")
            act = render.resolve_task_action(rule, subagent_name, default="allow")
            # 找出命中的具体规则，用于溯源说明
            hit_pat = None
            if isinstance(rule, dict):
                import fnmatch

                for pat in rule:
                    if fnmatch.fnmatchcase(subagent_name, pat):
                        hit_pat = pat
            if rank.get(act, 0) >= rank.get(best_act, 0):
                best_act = act
                if rule is None:
                    best_detail = f"{p.name} 未配置 task，默认允许"
                elif isinstance(rule, str):
                    best_detail = f"{p.name} 模板 task 简写为 {rule}"
                elif hit_pat:
                    best_detail = f'{p.name} 模板规则 "{hit_pat}": {act} 命中'
                else:
                    best_detail = f"{p.name} 模板 task 无匹配规则，默认允许"

        source = "default" if best_detail and "默认" in best_detail else "template"
        return best_act, source, best_detail

    def _bundle_resp(self, row: AgentBundle) -> AgentBundleResponse:
        members, _, _, _, _ = self._bundle_members(row.id)
        return AgentBundleResponse(
            id=row.id,
            name=row.name,
            description=row.description,
            pattern=row.pattern,
            default_agent=row.default_agent,
            subagent_depth=row.subagent_depth,
            global_permission_json=row.global_permission_json,
            topology_json=row.topology_json,
            members=members,
            is_builtin_preset=bool(row.is_builtin_preset),
            current_version=row.current_version,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def list_bundles(
        self, pattern: Optional[str] = None, keyword: Optional[str] = None
    ) -> List[AgentBundleResponse]:
        rows = self.bundle_repo.list_filtered(pattern=pattern, keyword=keyword)
        return [self._bundle_resp(r) for r in rows]

    def get_bundle(self, bundle_id: int) -> AgentBundleResponse:
        row = self.bundle_repo.get_by_id(bundle_id)
        if not row:
            raise NotFoundException(f"编排方案 ID={bundle_id} 不存在")
        return self._bundle_resp(row)

    def _write_members(self, bundle_id: int, members: List[BundleMemberItem]) -> None:
        """整批替换成员，并做引用有效性检查。"""
        self.member_repo.delete_by_bundle(bundle_id)
        for idx, m in enumerate(members):
            if m.member_type == "agent":
                if not m.agent_template_id:
                    raise ValidationException(
                        f"第 {idx + 1} 个成员 member_type=agent 但缺少 agent_template_id",
                        code="MEMBER_REF_MISSING",
                    )
                if not self.agent_repo.get_by_id(m.agent_template_id):
                    raise NotFoundException(
                        f"第 {idx + 1} 个成员引用的 Agent ID={m.agent_template_id} 不存在"
                    )
            else:
                if not m.skill_template_id:
                    raise ValidationException(
                        f"第 {idx + 1} 个成员 member_type=skill 但缺少 skill_template_id",
                        code="MEMBER_REF_MISSING",
                    )
                if not self.skill_repo.get_by_id(m.skill_template_id):
                    raise NotFoundException(
                        f"第 {idx + 1} 个成员引用的 Skill ID={m.skill_template_id} 不存在"
                    )
            self.member_repo.create({
                "bundle_id": bundle_id,
                "member_type": m.member_type,
                "agent_template_id": m.agent_template_id,
                "skill_template_id": m.skill_template_id,
                "role": m.role if m.member_type == "agent" else MemberRole.SKILL.value,
                "skill_permission": m.skill_permission if m.member_type == "skill" else None,
                "task_permission": m.task_permission if m.member_type == "agent" else None,
                "sort_order": m.sort_order if m.sort_order is not None else idx,
            })

    def create_bundle(
        self, data: AgentBundleCreate, user_id: Optional[int] = None
    ) -> AgentBundleResponse:
        if self.bundle_repo.get_by_name(data.name):
            raise BusinessException(f"编排方案名 '{data.name}' 已存在", "BUNDLE_NAME_DUPLICATED")

        payload = data.model_dump()
        members = [BundleMemberItem(**m) for m in (payload.pop("members", []) or [])]

        row = self.bundle_repo.create({
            **payload,
            "is_builtin_preset": False,
            "current_version": 1,
            "created_by_user_id": user_id,
        })
        self._write_members(row.id, members)
        self.db.flush()

        # 成员写完后做拓扑一致性校验
        _, agents, skills, _, _ = self._bundle_members(row.id)
        result = validate.validate_bundle(payload, agents, skills)
        if not result.ok:
            self.db.rollback()
            self._raise_if_invalid(result, "编排方案")

        self.db.commit()
        return self._bundle_resp(row)

    def update_bundle(
        self, bundle_id: int, data: AgentBundleUpdate
    ) -> AgentBundleResponse:
        row = self.bundle_repo.get_by_id(bundle_id)
        if not row:
            raise NotFoundException(f"编排方案 ID={bundle_id} 不存在")

        patch = data.model_dump(exclude_unset=True)
        members = patch.pop("members", None)

        if patch.get("name") and patch["name"] != row.name:
            if self.bundle_repo.get_by_name(patch["name"]):
                raise BusinessException(
                    f"编排方案名 '{patch['name']}' 已存在", "BUNDLE_NAME_DUPLICATED",
                )

        if patch:
            self.bundle_repo.update(bundle_id, patch)
        if members is not None:
            self._write_members(bundle_id, [BundleMemberItem(**m) for m in members])
        self.db.flush()

        row = self.bundle_repo.get_by_id(bundle_id)
        _, agents, skills, _, _ = self._bundle_members(bundle_id)
        bundle_dict = {
            "name": row.name,
            "pattern": row.pattern,
            "default_agent": row.default_agent,
            "subagent_depth": row.subagent_depth,
            "global_permission_json": row.global_permission_json,
        }
        result = validate.validate_bundle(bundle_dict, agents, skills)
        if not result.ok:
            self.db.rollback()
            self._raise_if_invalid(result, "编排方案")

        self.db.commit()
        return self._bundle_resp(row)

    def delete_bundle(self, bundle_id: int) -> bool:
        row = self.bundle_repo.get_by_id(bundle_id)
        if not row:
            raise NotFoundException(f"编排方案 ID={bundle_id} 不存在")
        if row.is_builtin_preset:
            raise BusinessException(
                f"'{row.name}' 是内置预设，不可删除", "PRESET_NOT_DELETABLE",
            )
        self.bundle_repo.delete(bundle_id)
        self.db.commit()
        return True

    def validate_bundle(self, bundle_id: int) -> ValidationResult:
        row = self.bundle_repo.get_by_id(bundle_id)
        if not row:
            raise NotFoundException(f"编排方案 ID={bundle_id} 不存在")
        _, agents, skills, _, _ = self._bundle_members(bundle_id)
        return validate.validate_bundle(
            {
                "name": row.name,
                "pattern": row.pattern,
                "default_agent": row.default_agent,
                "subagent_depth": row.subagent_depth,
                "global_permission_json": row.global_permission_json,
            },
            agents,
            skills,
        )

    def preview_bundle(self, bundle_id: int) -> PreviewResponse:
        """全量产物预览 —— 发布前让用户确认到底会写哪些文件。"""
        row = self.bundle_repo.get_by_id(bundle_id)
        if not row:
            raise NotFoundException(f"编排方案 ID={bundle_id} 不存在")

        _, agents, skills, skill_perms, task_ovr = self._bundle_members(bundle_id)
        bundle_dict = {
            "name": row.name,
            "pattern": row.pattern,
            "default_agent": row.default_agent,
            "subagent_depth": row.subagent_depth,
            "global_permission_json": row.global_permission_json,
        }
        arts = render.render_bundle(bundle_dict, agents, skills, skill_perms, task_ovr)
        return PreviewResponse(
            artifacts=arts,
            validation=validate.validate_bundle(bundle_dict, agents, skills),
            tree=render.artifacts_tree(arts),
        )

    def resolve_bundle_for_deploy(self, bundle_id: int) -> Tuple[
        AgentBundle, Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, str]
    ]:
        """发布器用：解析 bundle 的全部依赖。"""
        row = self.bundle_repo.get_by_id(bundle_id)
        if not row:
            raise NotFoundException(f"编排方案 ID={bundle_id} 不存在")
        _, agents, skills, skill_perms, task_ovr = self._bundle_members(bundle_id)
        bundle_dict = {
            "name": row.name,
            "pattern": row.pattern,
            "default_agent": row.default_agent,
            "subagent_depth": row.subagent_depth,
            "global_permission_json": row.global_permission_json,
        }
        return row, bundle_dict, agents, skills, skill_perms, task_ovr
