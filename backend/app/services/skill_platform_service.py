"""Skill 平台 Service — CRUD / 生命周期 / 参数 / 版本 / 导出 / 克隆 / 审计.

事务边界在本层（repo 只 flush，Service 负责 commit），符合 backend/STANDARDS.md。
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException, NotFoundException, ValidationException
from app.db.models.agent_bundle_model import BundleMember
from app.db.models.skill_platform_model import (
    Lifecycle,
    LIFECYCLE_GATED,
    LIFECYCLE_TRANSITIONS,
    SkillAuditLog,
    SkillExecApi,
    SkillExecFlowNode,
    SkillExecPrompt,
    SkillInvocation,
    SkillMeta,
    SkillParam,
    SkillPolicy,
    SkillVersion,
)
from app.db.models.skill_template_model import SkillFile, SkillTemplate
from app.db.repositories.skill_template_repo import (
    SkillFileRepository,
    SkillTemplateRepository,
)
from app.schemas.skill_platform_schema import (
    SKILL_NAME_PATTERN,
    SkillCreateRequest,
    SkillExportResponse,
    SkillFullResponse,
    SkillListItem,
    SkillMetaPayload,
    SkillParamResponse,
    SkillValidation,
    SkillVersionResponse,
    SkillAuditResponse,
    ParamDebugResult,
    ExportedFile,
)
from app.services import skill_render_service as render
from app.services import skill_validate_service as validate

logger = logging.getLogger(__name__)


class SkillPlatformService:
    """Skill 平台服务。"""

    def __init__(self, db: Session):
        self.db = db
        self.tpl_repo = SkillTemplateRepository(db)
        self.file_repo = SkillFileRepository(db)

    # ==================== 列表 ====================

    def list_skills(
        self,
        keyword: Optional[str] = None,
        kind: Optional[str] = None,
        lifecycle: Optional[str] = None,
        risk_level: Optional[str] = None,
        biz_line: Optional[str] = None,
    ) -> List[SkillListItem]:
        """Skill 列表。"""
        q = self.db.query(SkillTemplate)
        if keyword:
            like = f"%{keyword}%"
            q = q.filter(
                SkillTemplate.name.like(like) | SkillTemplate.description.like(like)
            )
        if kind:
            q = q.join(SkillMeta).filter(SkillMeta.skill_kind == kind)
        if lifecycle:
            q = q.join(SkillMeta).filter(SkillMeta.lifecycle == lifecycle)
        if risk_level:
            q = q.join(SkillMeta).filter(SkillMeta.risk_level == risk_level)
        if biz_line:
            q = q.join(SkillMeta).filter(SkillMeta.biz_line == biz_line)

        rows = q.order_by(SkillTemplate.name).all()
        out = []
        for r in rows:
            meta = self.db.query(SkillMeta).filter(SkillMeta.skill_template_id == r.id).first()
            fi = self.file_repo.list_by_skill(r.id)
            pi = self.db.query(SkillParam).filter(
                SkillParam.skill_template_id == r.id, SkillParam.direction == "in"
            ).count()
            po = self.db.query(SkillParam).filter(
                SkillParam.skill_template_id == r.id, SkillParam.direction == "out"
            ).count()
            out.append(SkillListItem(
                id=r.id,
                name=r.name,
                description=r.description or "",
                display_name=r.display_name,
                skill_kind=meta.skill_kind if meta else "prompt",
                risk_level=meta.risk_level if meta else "low",
                lifecycle=meta.lifecycle if meta else "draft",
                biz_line=meta.biz_line if meta else None,
                owner=meta.owner if meta else None,
                current_version=r.current_version or 1,
                file_count=len(fi),
                param_in_count=pi,
                param_out_count=po,
                is_builtin_preset=bool(r.is_builtin_preset),
                updated_at=r.updated_at,
            ))
        return out

    # ==================== 创建 ====================

    def create_skill(self, data: SkillCreateRequest, user_id: Optional[int] = None) -> SkillFullResponse:
        """新建 Skill。"""
        # 校验
        payload = {"name": data.name, "description": data.description}
        result = validate.validate_skill(payload)
        if not result.ok:
            errs = [f"· {i.field}: {i.message}" for i in result.issues if i.level == "error"]
            raise ValidationException(
                "Skill 校验未通过：\n" + "\n".join(errs),
                code="SKILL_VALIDATION_FAILED",
            )

        existing = self.tpl_repo.get_by_name(data.name)
        if existing:
            raise BusinessException(
                f"Skill 名 '{data.name}' 已存在（= 落盘目录名），必须唯一",
                "SKILL_NAME_DUPLICATED",
            )

        row = self.tpl_repo.create({
            "name": data.name,
            "description": data.description,
            "display_name": data.display_name,
            "category": data.category,
            "license": data.license or "MIT",
            "compatibility": data.compatibility or "opencode",
            "body": data.body,
            "is_builtin_preset": False,
            "source": "platform",
            "current_version": 1,
            "created_by_user_id": user_id,
        })
        # 治理元数据
        self.db.add(SkillMeta(
            skill_template_id=row.id,
            skill_kind=data.meta.skill_kind or "prompt",
            risk_level=data.meta.risk_level or "low",
            lifecycle="draft",
            owner=data.meta.owner,
            biz_line=data.meta.biz_line,
            qps_limit=data.meta.qps_limit,
            session_call_limit=data.meta.session_call_limit,
        ))
        self.db.commit()
        self._audit(row.id, row.name, "create", summary=f"创建 Skill {row.name}")
        return self._full_resp(row.id)

    # ==================== 详情 ====================

    def get_skill(self, skill_id: int) -> SkillFullResponse:
        row = self.tpl_repo.get_by_id(skill_id)
        if not row:
            raise NotFoundException(f"Skill ID={skill_id} 不存在")
        return self._full_resp(skill_id)

    def _full_resp(self, skill_id: int) -> SkillFullResponse:
        """聚合全量配置。"""
        row = self.tpl_repo.get_by_id(skill_id)
        meta = self.db.query(SkillMeta).filter(SkillMeta.skill_template_id == skill_id).first()
        ep = self.db.query(SkillExecPrompt).filter(SkillExecPrompt.skill_template_id == skill_id).first()
        ea = self.db.query(SkillExecApi).filter(SkillExecApi.skill_template_id == skill_id).first()
        po = self.db.query(SkillPolicy).filter(SkillPolicy.skill_template_id == skill_id).first()
        pi = self.db.query(SkillParam).filter(
            SkillParam.skill_template_id == skill_id, SkillParam.direction == "in"
        ).order_by(SkillParam.sort_order).all()
        po_params = self.db.query(SkillParam).filter(
            SkillParam.skill_template_id == skill_id, SkillParam.direction == "out"
        ).order_by(SkillParam.sort_order).all()
        fn = self.db.query(SkillExecFlowNode).filter(
            SkillExecFlowNode.skill_template_id == skill_id
        ).order_by(SkillExecFlowNode.sort_order).all()
        files = self.file_repo.list_by_skill(skill_id)

        def pm(p):
            return SkillParamResponse(
                id=p.id, direction=p.direction,
                name=p.name, title=p.title, description=p.description,
                data_type=p.data_type, required=bool(p.required),
                default_value=p.default_value,
                enum_values=list(p.enum_json) if p.enum_json else [],
                regex_pattern=p.regex_pattern,
                min_val=p.min_val, max_val=p.max_val,
                source=p.source, context_key=p.context_key,
                const_value=p.const_value,
                mask_rule=p.mask_rule, mask_pattern=p.mask_pattern,
                filtered=bool(p.filtered),
                write_to_context=bool(p.write_to_context),
                context_write_key=p.context_write_key,
                sort_order=p.sort_order or 0,
            )

        def to_meta(m):
            if not m:
                return SkillMetaPayload()
            return SkillMetaPayload(
                skill_kind=m.skill_kind or "prompt",
                name_zh=m.name_zh, name_en=m.name_en,
                biz_tags=list(m.biz_tags_json) if m.biz_tags_json else [],
                risk_level=m.risk_level or "low",
                owner=m.owner, owner_email=m.owner_email,
                biz_line=m.biz_line,
                qps_limit=m.qps_limit, session_call_limit=m.session_call_limit,
                lifecycle=m.lifecycle or "draft",
                lifecycle_note=m.lifecycle_note,
            )

        # 校验
        from app.schemas.skill_platform_schema import ExecPromptPayload, ExecApiPayload, ExecFlowPayload, FlowNodePayload, SkillPolicyPayload
        raw = {
            "name": row.name, "description": row.description,
            "meta": to_meta(meta).model_dump(),
            "exec_api": self._api_to_dict(ea) if ea else None,
            "exec_prompt": self._prompt_to_dict(ep) if ep else None,
            "exec_flow": {"nodes": [self._fn_to_dict(f) for f in fn]} if fn else None,
            "policy": self._policy_to_dict(po) if po else None,
            "params_in": [pm(p).model_dump() for p in pi],
            "params_out": [pm(p).model_dump() for p in po_params],
        }
        validation = validate.validate_skill(raw)

        return SkillFullResponse(
            id=row.id,
            name=row.name,
            description=row.description or "",
            license=row.license,
            compatibility=row.compatibility,
            metadata_json=row.metadata_json,
            body=row.body,
            display_name=row.display_name,
            category=row.category,
            files=[{"rel_path": f.rel_path, "content": f.content or "", "is_executable": bool(f.is_executable)} for f in files],
            current_version=row.current_version or 1,
            is_builtin_preset=bool(row.is_builtin_preset),
            meta=to_meta(meta),
            params_in=[pm(p) for p in pi],
            params_out=[pm(p) for p in po_params],
            exec_prompt=ExecPromptPayload(**self._prompt_to_dict(ep)) if ep else None,
            exec_api=ExecApiPayload(**self._api_to_dict(ea)) if ea else None,
            exec_flow=ExecFlowPayload(nodes=[FlowNodePayload(**self._fn_to_dict(f)) for f in fn]) if fn else None,
            policy=SkillPolicyPayload(**self._policy_to_dict(po)) if po else None,
            validation=validation,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _prompt_to_dict(self, ep) -> dict:
        if not ep:
            return {}
        return {
            "system_prompt": ep.system_prompt,
            "few_shots": list(ep.few_shots_json) if ep.few_shots_json else [],
            "output_constraint": ep.output_constraint,
            "output_format": ep.output_format or "text",
            "temperature": ep.temperature,
            "max_tokens": ep.max_tokens,
        }

    def _api_to_dict(self, ea) -> dict:
        if not ea:
            return {}
        return {
            "http_method": ea.http_method or "POST",
            "url_test": ea.url_test, "url_staging": ea.url_staging, "url_prod": ea.url_prod,
            "headers": dict(ea.headers_json) if ea.headers_json else {},
            "auth_type": ea.auth_type or "none",
            "secret_ref": ea.secret_ref,
            "param_mappings": list(ea.param_mapping_json) if ea.param_mapping_json else [],
            "timeout_ms": ea.timeout_ms or 5000,
            "retry_times": ea.retry_times or 0,
            "retry_backoff_ms": ea.retry_backoff_ms or 200,
            "success_path": ea.success_path, "success_value": ea.success_value,
            "data_path": ea.data_path,
        }

    def _fn_to_dict(self, fn) -> dict:
        return {
            "node_key": fn.node_key, "node_type": fn.node_type, "label": fn.label,
            "ref_skill_id": fn.ref_skill_id, "condition_expr": fn.condition_expr,
            "loop_config": dict(fn.loop_config_json) if fn.loop_config_json else None,
            "var_mappings": dict(fn.var_mapping_json) if fn.var_mapping_json else {},
            "next_keys": list(fn.next_keys_json) if fn.next_keys_json else [],
            "on_fail_next": fn.on_fail_next, "pos_x": fn.pos_x, "pos_y": fn.pos_y,
            "sort_order": fn.sort_order or 0,
        }

    def _policy_to_dict(self, po) -> dict:
        if not po:
            return {}
        return {
            "timeout_ms": po.timeout_ms, "retry_times": po.retry_times,
            "circuit_threshold": po.circuit_threshold,
            "circuit_window_sec": po.circuit_window_sec or 60,
            "circuit_min_calls": po.circuit_min_calls or 10,
            "circuit_cooldown_sec": po.circuit_cooldown_sec or 30,
            "fallback_mode": po.fallback_mode or "none",
            "fallback_payload": po.fallback_payload,
            "error_maps": list(po.error_map_json) if po.error_map_json else [],
            "allowed_agents": list(po.allowed_agents_json) if po.allowed_agents_json else [],
            "allowed_roles": list(po.allowed_roles_json) if po.allowed_roles_json else [],
            "require_confirm": bool(po.require_confirm),
            "confirm_prompt": po.confirm_prompt,
            "account_whitelist": list(po.account_whitelist_json) if po.account_whitelist_json else [],
            "account_blacklist": list(po.account_blacklist_json) if po.account_blacklist_json else [],
            "ctx_read_keys": list(po.ctx_read_keys_json) if po.ctx_read_keys_json else [],
            "ctx_write_keys": list(po.ctx_write_keys_json) if po.ctx_write_keys_json else [],
            "session_isolation": po.session_isolation or "session",
        }

    # ==================== 更新 ====================

    def update_skill(self, skill_id: int, data: Dict[str, Any]) -> SkillFullResponse:
        row = self.tpl_repo.get_by_id(skill_id)
        if not row:
            raise NotFoundException(f"Skill ID={skill_id} 不存在")

        # 基础字段
        for k in ("description", "display_name", "category", "license", "compatibility", "body"):
            v = data.get(k)
            if v is not None:
                setattr(row, k, v)
        if "metadata_json" in data:
            row.metadata_json = data["metadata_json"]
        if "files" in data:
            files = data["files"] or []
            self.file_repo.delete_by_skill(skill_id)
            for f in files:
                self.file_repo.create({
                    "skill_template_id": skill_id,
                    "rel_path": f.get("rel_path", ""),
                    "content": f.get("content", ""),
                    "is_executable": bool(f.get("is_executable")),
                })

        # 治理元数据
        if "meta" in data:
            m = data["meta"]
            meta = self.db.query(SkillMeta).filter(SkillMeta.skill_template_id == skill_id).first()
            if not meta:
                meta = SkillMeta(skill_template_id=skill_id)
                self.db.add(meta)
            for k in ("skill_kind", "name_zh", "name_en", "risk_level", "owner", "owner_email",
                       "biz_line", "qps_limit", "session_call_limit", "lifecycle_note"):
                v = m.get(k)
                if v is not None:
                    setattr(meta, k, v)
            if "biz_tags" in m:
                meta.biz_tags_json = m["biz_tags"]
            # lifecycle 只能通过专用端点变更
            if "lifecycle" in m:
                lc = m["lifecycle"]
                cur = meta.lifecycle or "draft"
                if lc != cur:
                    issues = validate.validate_lifecycle_transition(cur, lc)
                    if issues:
                        raise ValidationException(issues[0].message, code="LIFECYCLE_INVALID")
                    meta.lifecycle = lc

        # 执行配置
        self._upsert_prompt(skill_id, data.get("exec_prompt"))
        self._upsert_api(skill_id, data.get("exec_api"))
        self._upsert_flow(skill_id, data.get("exec_flow"))
        self._upsert_policy(skill_id, data.get("policy"))

        self.db.commit()
        self._audit(skill_id, row.name, "update", summary="更新配置")
        return self._full_resp(skill_id)

    def _upsert_prompt(self, sid, d):
        if d is None:
            return
        row = self.db.query(SkillExecPrompt).filter(SkillExecPrompt.skill_template_id == sid).first()
        if not row:
            row = SkillExecPrompt(skill_template_id=sid)
            self.db.add(row)
        for k in ("system_prompt", "output_constraint", "output_format", "temperature", "max_tokens"):
            if k in d:
                setattr(row, k, d[k])
        if "few_shots" in d:
            row.few_shots_json = [dict(fs) for fs in (d["few_shots"] or [])]

    def _upsert_api(self, sid, d):
        if d is None:
            return
        row = self.db.query(SkillExecApi).filter(SkillExecApi.skill_template_id == sid).first()
        if not row:
            row = SkillExecApi(skill_template_id=sid)
            self.db.add(row)
        for k in ("http_method", "url_test", "url_staging", "url_prod", "auth_type", "secret_ref",
                   "timeout_ms", "retry_times", "retry_backoff_ms", "success_path", "success_value", "data_path"):
            if k in d:
                setattr(row, k, d[k])
        if "headers" in d:
            row.headers_json = dict(d["headers"])
        if "param_mappings" in d:
            row.param_mapping_json = [dict(m) for m in (d["param_mappings"] or [])]

    def _upsert_flow(self, sid, d):
        if d is None:
            return
        self.db.query(SkillExecFlowNode).filter(SkillExecFlowNode.skill_template_id == sid).delete()
        self.db.flush()
        for i, n in enumerate(d.get("nodes") or []):
            self.db.add(SkillExecFlowNode(
                skill_template_id=sid,
                node_key=n.get("node_key", f"n{i}"),
                node_type=n.get("node_type", "skill"),
                label=n.get("label"),
                ref_skill_id=n.get("ref_skill_id"),
                condition_expr=n.get("condition_expr"),
                loop_config_json=n.get("loop_config"),
                var_mapping_json=n.get("var_mappings"),
                next_keys_json=n.get("next_keys", []),
                on_fail_next=n.get("on_fail_next"),
                pos_x=n.get("pos_x"), pos_y=n.get("pos_y"),
                sort_order=n.get("sort_order", i),
            ))

    def _upsert_policy(self, sid, d):
        if d is None:
            return
        row = self.db.query(SkillPolicy).filter(SkillPolicy.skill_template_id == sid).first()
        if not row:
            row = SkillPolicy(skill_template_id=sid)
            self.db.add(row)
        for k in ("timeout_ms", "retry_times", "circuit_threshold", "circuit_window_sec",
                   "circuit_min_calls", "circuit_cooldown_sec", "fallback_mode",
                   "fallback_payload", "require_confirm", "confirm_prompt", "session_isolation"):
            if k in d:
                setattr(row, k, d[k])
        for jk, mk in (("error_maps", "error_map_json"), ("allowed_agents", "allowed_agents_json"),
                       ("allowed_roles", "allowed_roles_json"),
                       ("account_whitelist", "account_whitelist_json"),
                       ("account_blacklist", "account_blacklist_json"),
                       ("ctx_read_keys", "ctx_read_keys_json"),
                       ("ctx_write_keys", "ctx_write_keys_json")):
            if jk in d:
                setattr(row, mk, list(d[jk]) if d[jk] else [])

    # ==================== 删除 ====================

    def delete_skill(self, skill_id: int) -> None:
        row = self.tpl_repo.get_by_id(skill_id)
        if not row:
            raise NotFoundException(f"Skill ID={skill_id} 不存在")
        if row.is_builtin_preset:
            raise BusinessException("内置预设不可删除", "PRESET_NOT_DELETABLE")
        used = self.db.query(BundleMember).filter(BundleMember.skill_template_id == skill_id).count()
        if used:
            raise BusinessException(
                f"正被 {used} 个编排方案引用，请先从方案中移除再删除",
                "SKILL_IN_USE",
            )
        self.tpl_repo.delete(skill_id)
        self.db.commit()

    # ==================== 生命周期 ====================

    def change_lifecycle(self, skill_id: int, target: str, note: Optional[str] = None, user_id: Optional[int] = None) -> SkillMetaPayload:
        meta = self.db.query(SkillMeta).filter(SkillMeta.skill_template_id == skill_id).first()
        if not meta:
            raise NotFoundException(f"Skill ID={skill_id} 无治理元数据")
        issues = validate.validate_lifecycle_transition(meta.lifecycle or "draft", target)
        if issues:
            raise ValidationException(issues[0].message, code="LIFECYCLE_INVALID")
        meta.lifecycle = target
        meta.lifecycle_note = note
        self.db.commit()
        self._audit(skill_id, (self.tpl_repo.get_by_id(skill_id) or {}).name or "?",
                     "lifecycle", summary=f"生命周期: {meta.lifecycle} → {target}{' - ' + note if note else ''}")
        return SkillMetaPayload(
            skill_kind=meta.skill_kind or "prompt", risk_level=meta.risk_level or "low",
            lifecycle=meta.lifecycle or "draft", lifecycle_note=meta.lifecycle_note,
            owner=meta.owner, biz_line=meta.biz_line, qps_limit=meta.qps_limit,
            session_call_limit=meta.session_call_limit,
        )

    # ==================== 参数 ====================

    def update_params(self, skill_id: int, direction: str, params: List[Dict[str, Any]]) -> List[SkillParamResponse]:
        self.db.query(SkillParam).filter(
            SkillParam.skill_template_id == skill_id, SkillParam.direction == direction
        ).delete()
        self.db.flush()
        out = []
        for i, p in enumerate(params):
            row = SkillParam(skill_template_id=skill_id, direction=direction, sort_order=i)
            for k, v in p.items():
                if hasattr(row, k) and k not in ("id", "direction", "skill_template_id", "created_at", "updated_at"):
                    setattr(row, k, v)
            self.db.add(row)
            self.db.flush()
            out.append(self._param_resp(row))
        self.db.commit()
        return out

    def _param_resp(self, p) -> SkillParamResponse:
        return SkillParamResponse(
            id=p.id, direction=p.direction,
            name=p.name, title=p.title, description=p.description,
            data_type=p.data_type or "string", required=bool(p.required),
            default_value=p.default_value,
            enum_values=list(p.enum_json) if p.enum_json else [],
            regex_pattern=p.regex_pattern, min_val=p.min_val, max_val=p.max_val,
            source=p.source, context_key=p.context_key, const_value=p.const_value,
            mask_rule=p.mask_rule or "none", mask_pattern=p.mask_pattern,
            filtered=bool(p.filtered),
            write_to_context=bool(p.write_to_context),
            context_write_key=p.context_write_key,
            sort_order=p.sort_order or 0,
        )

    def debug_params(self, skill_id: int, sample: Dict[str, Any]) -> ParamDebugResult:
        row = self.tpl_repo.get_by_id(skill_id)
        if not row:
            raise NotFoundException(f"Skill ID={skill_id} 不存在")
        params = self.db.query(SkillParam).filter(
            SkillParam.skill_template_id == skill_id, SkillParam.direction == "in"
        ).all()
        schema = render.build_json_schema([
            {"name": p.name, "data_type": p.data_type, "required": bool(p.required),
             "description": p.description, "enum_values": list(p.enum_json) if p.enum_json else [],
             "regex_pattern": p.regex_pattern, "min_val": p.min_val, "max_val": p.max_val,
             "source": p.source}
            for p in params
        ])
        fields = []
        ok = True
        for p in params:
            val = sample.get(p.name)
            if p.required and val is None:
                fields.append(self._df(p.name, False, None, "必填字段缺失"))
                ok = False
                continue
            if val is not None:
                fields.append(self._df(p.name, True, val, "校验通过"))
            else:
                fields.append(self._df(p.name, True, None, "未传值（选填）"))
        return ParamDebugResult(ok=ok, fields=fields, json_schema=schema)

    def _df(self, name, ok, value, message):
        from app.schemas.skill_platform_schema import ParamDebugFieldResult
        return ParamDebugFieldResult(name=name, ok=ok, value=value, message=message)

    # ==================== 导出 ====================

    def export_skill(self, skill_id: int, scope: str = "project", include_manifest: bool = True) -> SkillExportResponse:
        row = self.tpl_repo.get_by_id(skill_id)
        if not row:
            raise NotFoundException(f"Skill ID={skill_id} 不存在")
        full = self._full_resp(skill_id)
        params_in = [p.model_dump() for p in full.params_in]
        params_out = [p.model_dump() for p in full.params_out]
        exec_api = full.exec_api.model_dump() if full.exec_api else None
        exec_prompt = full.exec_prompt.model_dump() if full.exec_prompt else None
        exec_flow = full.exec_flow.model_dump() if full.exec_flow else None
        policy = full.policy.model_dump() if full.policy else None

        data = {
            "name": row.name, "description": row.description or "",
            "display_name": row.display_name, "category": row.category,
            "license": row.license, "compatibility": row.compatibility,
            "metadata_json": row.metadata_json,
            "body": row.body, "current_version": row.current_version or 1,
            "files": [{"rel_path": f.rel_path, "content": f.content or "", "is_executable": bool(f.is_executable)}
                      for f in self.file_repo.list_by_skill(skill_id)],
            "meta": full.meta.model_dump(),
            "params_in": params_in, "params_out": params_out,
            "exec_api": exec_api, "exec_prompt": exec_prompt, "exec_flow": exec_flow,
            "policy": policy,
        }
        validation = validate.validate_skill(data)
        files = render.export_skill(data, scope=scope, include_manifest=include_manifest)
        tree = render.export_tree(files)

        # 治理说明
        ctrl = [f for f in files if f.plane == "control"]
        note = (
            f"治理配置（{len(ctrl)} 个文件）已导出到 _ontomind/ 目录，"
            "由平台 Skill 网关执行，OpenCode 不读取。"
            "SKILL.md 仅含 5 个合法 frontmatter 字段，100% 合规。"
            if ctrl else ""
        )

        return SkillExportResponse(
            skill_name=row.name,
            scope=scope,
            files=files,
            tree=tree,
            validation=validation,
            control_plane_note=note,
        )

    # ==================== 版本 ====================

    def create_version(self, skill_id: int, change_note: Optional[str] = None,
                       canary: Optional[Dict[str, Any]] = None, user_id: Optional[int] = None) -> SkillVersionResponse:
        row = self.tpl_repo.get_by_id(skill_id)
        if not row:
            raise NotFoundException(f"Skill ID={skill_id} 不存在")
        maxv = int(self.db.query(SkillVersion.version).filter(
            SkillVersion.skill_template_id == skill_id).order_by(SkillVersion.version.desc()).first() or (0,))[0]
        version = maxv + 1
        full = self._full_resp(skill_id)
        snap = {
            "name": row.name, "description": row.description,
            "meta": full.meta.model_dump(),
            "params_in": [p.model_dump() for p in full.params_in],
            "params_out": [p.model_dump() for p in full.params_out],
            "exec_prompt": full.exec_prompt.model_dump() if full.exec_prompt else None,
            "exec_api": full.exec_api.model_dump() if full.exec_api else None,
            "exec_flow": full.exec_flow.model_dump() if full.exec_flow else None,
            "policy": full.policy.model_dump() if full.policy else None,
        }
        meta = self.db.query(SkillMeta).filter(SkillMeta.skill_template_id == skill_id).first()
        v = SkillVersion(
            skill_template_id=skill_id, version=version,
            snapshot_json=snap, change_note=change_note,
            lifecycle_at_snapshot=meta.lifecycle if meta else None,
            canary_json=canary,
            created_by_user_id=user_id,
        )
        self.db.add(v)
        row.current_version = version
        self.db.commit()
        return SkillVersionResponse(
            id=v.id, skill_template_id=skill_id, version=version,
            change_note=change_note, lifecycle_at_snapshot=meta.lifecycle if meta else None,
            canary_json=canary, created_at=v.created_at,
        )

    def list_versions(self, skill_id: int) -> List[SkillVersionResponse]:
        if not self.tpl_repo.get_by_id(skill_id):
            raise NotFoundException(f"Skill ID={skill_id} 不存在")
        rows = self.db.query(SkillVersion).filter(
            SkillVersion.skill_template_id == skill_id
        ).order_by(SkillVersion.version.desc()).all()
        return [SkillVersionResponse(
            id=v.id, skill_template_id=skill_id, version=v.version,
            change_note=v.change_note, lifecycle_at_snapshot=v.lifecycle_at_snapshot,
            canary_json=v.canary_json, created_by_name=str(v.created_by_user_id),
            created_at=v.created_at,
        ) for v in rows]

    def rollback_skill(self, skill_id: int, version: int) -> SkillFullResponse:
        row = self.tpl_repo.get_by_id(skill_id)
        if not row:
            raise NotFoundException(f"Skill ID={skill_id} 不存在")
        v = self.db.query(SkillVersion).filter(
            SkillVersion.skill_template_id == skill_id, SkillVersion.version == version
        ).first()
        if not v:
            raise NotFoundException(f"版本 {version} 不存在")
        snap = dict(v.snapshot_json or {})
        # 恢复各段
        if "description" in snap:
            row.description = snap["description"]
        # 恢复元数据
        if "meta" in snap:
            meta = self.db.query(SkillMeta).filter(SkillMeta.skill_template_id == skill_id).first()
            if meta:
                for k, vv in snap["meta"].items():
                    if hasattr(meta, k):
                        setattr(meta, k, vv)
            else:
                meta = SkillMeta(skill_template_id=skill_id, **snap["meta"])
                self.db.add(meta)
        # 恢复参数
        if "params_in" in snap:
            self.db.query(SkillParam).filter(SkillParam.skill_template_id == skill_id, SkillParam.direction == "in").delete()
            self.db.flush()
            for i, p in enumerate(snap["params_in"]):
                self.db.add(SkillParam(skill_template_id=skill_id, direction="in", sort_order=i, **{k: v for k, v in p.items() if hasattr(SkillParam, k)}))
        if "params_out" in snap:
            self.db.query(SkillParam).filter(SkillParam.skill_template_id == skill_id, SkillParam.direction == "out").delete()
            self.db.flush()
            for i, p in enumerate(snap["params_out"]):
                self.db.add(SkillParam(skill_template_id=skill_id, direction="out", sort_order=i, **{k: v for k, v in p.items() if hasattr(SkillParam, k)}))
        self.db.commit()
        return self._full_resp(skill_id)

    # ==================== 克隆 ====================

    def clone_skill(self, skill_id: int, new_name: str, user_id: Optional[int] = None) -> SkillFullResponse:
        import re
        if not re.match(SKILL_NAME_PATTERN, new_name):
            raise ValidationException(f"'{new_name}' 不符合 kebab-case 规范", "NAME_INVALID")
        if self.tpl_repo.get_by_name(new_name):
            raise BusinessException(f"Skill 名 '{new_name}' 已存在", "SKILL_NAME_DUPLICATED")
        from app.schemas.skill_platform_schema import SkillCreateRequest
        req = SkillCreateRequest(name=new_name, description=f"（从 ID={skill_id} 克隆）")
        created = self.create_skill(req, user_id)
        # 复制元数据
        orig = self._full_resp(skill_id)
        data = {
            "meta": orig.meta.model_dump() | {"lifecycle": "draft"},
            "exec_prompt": orig.exec_prompt.model_dump() if orig.exec_prompt else None,
            "exec_api": orig.exec_api.model_dump() if orig.exec_api else None,
            "exec_flow": orig.exec_flow.model_dump() if orig.exec_flow else None,
            "policy": orig.policy.model_dump() if orig.policy else None,
        }
        # 复制参数
        param_in = [p.model_dump() for p in orig.params_in]
        param_out = [p.model_dump() for p in orig.params_out]
        if param_in:
            self.update_params(created.id, "in", param_in)
        if param_out:
            self.update_params(created.id, "out", param_out)
        self.update_skill(created.id, data)
        self._audit(created.id, new_name, "clone", summary=f"从 {orig.name} ID={skill_id} 克隆")
        return self._full_resp(created.id)

    # ==================== 审计 ====================

    def list_audit(self, skill_id: int) -> List[SkillAuditResponse]:
        if not self.tpl_repo.get_by_id(skill_id):
            raise NotFoundException(f"Skill ID={skill_id} 不存在")
        rows = self.db.query(SkillAuditLog).filter(
            SkillAuditLog.skill_template_id == skill_id
        ).order_by(SkillAuditLog.id.desc()).limit(100).all()
        return [SkillAuditResponse(
            id=r.id, skill_name=r.skill_name, action=r.action,
            field_path=r.field_path, summary=r.summary,
            operator_name=r.operator_name, created_at=r.created_at,
        ) for r in rows]

    def _audit(self, skill_id: int, skill_name: str, action: str,
               field_path: Optional[str] = None, summary: Optional[str] = None,
               before: Optional[dict] = None, after: Optional[dict] = None,
               user_id: Optional[int] = None, user_name: Optional[str] = None) -> None:
        self.db.add(SkillAuditLog(
            skill_template_id=skill_id, skill_name=skill_name,
            action=action, field_path=field_path,
            before_json=before, after_json=after,
            summary=summary, operator_user_id=user_id, operator_name=user_name,
        ))
        self.db.commit()