"""本体服务 — 认知层自动构建本体.

流水线（借鉴 RIGOR 论文的"确定性抽取 → LLM 增强 → 校验"三段式）：
  1. 确定性抽取：从库表结构（主键/外键/字段类型/数据画像）零成本生成本体草案
     —— 表→类，字段→数据属性，外键→关系，画像/结构→约束
  2. LLM/Agent 增强：对整库 schema 摘要 + 画像做一次调用，精化实体语义、补充语义关系
  3. 校验（可选）：Judge-LLM 审查一致性，产出问题清单

构建产物以「版本」组织落 MySQL；图谱与 OWL 导出按需派生。
"""
import json
import re
import time
from typing import Optional, Callable, Awaitable

from sqlalchemy.orm import Session
from app.db.repositories.metadata_repo import MetaTableRepository, MetaColumnRepository
from app.db.repositories.data_source_repo import DataSourceRepository
from app.db.models.metadata_model import MetaTable, MetaColumn, MetaProfile
from app.db.models.ontology_model import (
    OntologyVersion, OntologyClass, OntologyProperty,
    OntologyRelationship, OntologyConstraint,
)
from app.core.exceptions import NotFoundException, BusinessException

# 事件回调类型：type, content
EventCb = Optional[Callable[[str, str], Awaitable[None]]]


# 数据类型 -> xsd 类型映射
_XSD_MAP = {
    "int": "xsd:integer", "bigint": "xsd:integer", "smallint": "xsd:integer",
    "tinyint": "xsd:integer", "mediumint": "xsd:integer",
    "decimal": "xsd:decimal", "float": "xsd:decimal", "double": "xsd:decimal",
    "numeric": "xsd:decimal", "real": "xsd:decimal",
    "datetime": "xsd:dateTime", "timestamp": "xsd:dateTime", "date": "xsd:date",
    "time": "xsd:time", "year": "xsd:gYear",
    "boolean": "xsd:boolean", "bool": "xsd:boolean",
    "char": "xsd:string", "varchar": "xsd:string", "text": "xsd:string",
    "tinytext": "xsd:string", "mediumtext": "xsd:string", "longtext": "xsd:string",
    "json": "xsd:string", "enum": "xsd:string", "set": "xsd:string",
}
_DEFAULT_XSD = "xsd:string"


def to_pascal(name: str) -> str:
    """表名 user_order / user-order -> UserOrder."""
    parts = re.split(r"[_\s\-]+", name.strip())
    return "".join(p[:1].upper() + p[1:] for p in parts if p)


def _xsd_of(data_type: Optional[str]) -> str:
    if not data_type:
        return _DEFAULT_XSD
    base = data_type.lower().split("(")[0].strip()
    return _XSD_MAP.get(base, _DEFAULT_XSD)


class OntologyService:
    """本体自动构建与查询服务."""

    def __init__(self, db: Session):
        self.db = db
        self.table_repo = MetaTableRepository(db)
        self.col_repo = MetaColumnRepository(db)
        self.ds_repo = DataSourceRepository(db)

    # ========== 构建主流程 ==========

    async def build_ontology(
        self,
        datasource_id: int,
        method: str = "rules",
        llm_config_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        table_ids: Optional[list] = None,
        use_judge: bool = False,
        on_event: EventCb = None,
    ) -> dict:
        """构建本体版本.

        method: rules（仅确定性抽取）/ llm（平台 LLM 增强）/ agent（Agent 增强）
        返回 version 的响应字典。
        """
        if method not in ("rules", "llm", "agent"):
            raise BusinessException(f"不支持的构建方式: {method}", code="BAD_METHOD")

        ds = self.ds_repo.get_by_id(datasource_id)
        if not ds:
            raise NotFoundException(f"数据源不存在: {datasource_id}")

        await self._emit(on_event, "status", f"🚀 开始构建本体（方式: {method}）")

        # 创建版本占位
        version = OntologyVersion(
            datasource_id=datasource_id,
            name=f"{ds.name or '数据源'} 本体 v{datasource_id}-{int(time.time())}",
            status="building",
            method=method,
            llm_config_id=llm_config_id if method == "llm" else None,
            agent_id=agent_id if method == "agent" else None,
        )
        self.db.add(version)
        self.db.flush()

        try:
            # Step 1: 确定性抽取
            await self._emit(on_event, "status", "📐 确定性抽取：表→类，字段→属性，外键→关系")
            draft = self._extract_from_schema(version, datasource_id, table_ids)
            await self._emit(on_event, "status",
                             f"✓ 草案：{draft['stats']['entity']} 类 / "
                             f"{draft['stats']['relationship']} 关系 / "
                             f"{draft['stats']['property']} 属性 / "
                             f"{draft['stats']['constraint']} 约束")

            # Step 2: 增强
            if method in ("llm", "agent"):
                await self._emit(on_event, "status", f"🤖 调用{'平台 LLM' if method == 'llm' else 'Agent'} 进行语义增强...")
                extra = await self._enhance(version, draft, method, llm_config_id, agent_id, on_event)
                if extra:
                    added = self._apply_enhancement(version, draft, extra)
                    await self._emit(on_event, "status", f"✓ 增强：新增 {added} 条语义关系/约束")

            # Step 3: Judge 校验（可选）
            if use_judge:
                await self._emit(on_event, "status", "🔍 Judge-LLM 一致性校验...")
                issues = await self._judge(version, draft, method, llm_config_id, agent_id, on_event)
                draft["stats"]["judge_issues"] = len(issues)
                await self._emit(on_event, "status", f"✓ 校验完成：{len(issues)} 条建议")

            # 统计落库
            version.stats = json.dumps(draft["stats"], ensure_ascii=False)
            version.status = "ready"
            self.db.commit()
            await self._emit(on_event, "done", "✅ 本体构建完成")
            return version.to_response_dict()

        except Exception as e:
            self.db.rollback()
            version.status = "failed"
            version.error = str(e)[:2000]
            try:
                self.db.commit()
            except Exception:
                pass
            await self._emit(on_event, "error", f"构建失败: {e}")
            raise BusinessException(f"本体构建失败: {e}", code="BUILD_FAILED")

    @staticmethod
    async def _emit(on_event: EventCb, etype: str, content: str):
        if on_event:
            try:
                await on_event(etype, content)
            except Exception:
                pass

    # ========== Step 1: 确定性抽取 ==========

    def _extract_from_schema(self, version, datasource_id: int, table_ids: Optional[list]) -> dict:
        """从库表结构生成本体草案，返回统计."""
        q = self.db.query(MetaTable).filter(MetaTable.datasource_id == datasource_id)
        if table_ids:
            q = q.filter(MetaTable.id.in_(table_ids))
        tables = q.filter(MetaTable.sync_status == "synced").all()

        # 表名 -> 类 映射，用于外键解析
        class_by_table = {}
        # 完整 local_name -> class（含被引用但未选中的表）
        class_by_local = {}

        stats = {"entity": 0, "relationship": 0, "property": 0, "constraint": 0, "table": len(tables)}

        def get_or_create_class(table: MetaTable, confidence: float = 1.0) -> OntologyClass:
            key = (table.database_name, table.table_name)
            if key in class_by_table:
                return class_by_table[key]
            local = to_pascal(table.table_name)
            # 避免重名
            base_local = local
            i = 2
            while local in class_by_local:
                local = f"{base_local}{i}"
                i += 1
            cls = OntologyClass(
                version_id=version.id,
                source_table_id=table.id,
                local_name=local,
                label=table.table_comment_llm or table.table_comment or table.table_name,
                definition=table.table_comment_llm or table.business_description or table.table_comment,
                domain=table.domain,
                entity_type="class",
                is_entity=bool(table.entity_candidate or True),
                confidence=confidence,
            )
            self.db.add(cls)
            self.db.flush()
            class_by_table[key] = cls
            class_by_local[local] = cls
            stats["entity"] += 1
            return cls

        # 画像缓存：meta_column_id -> profile
        profiles = {
            p.meta_column_id: p
            for p in self.db.query(MetaProfile).filter(
                MetaProfile.meta_table_id.in_([t.id for t in tables]) if tables else MetaProfile.id == -1
            ).all()
        }

        # 1) 表 -> 类 + 字段 -> 数据属性 + 列约束
        for table in tables:
            has_pk = False
            columns = self.col_repo.get_by_table(table.id)
            for c in columns:
                if c.is_primary_key:
                    has_pk = True
                    break
            if not (has_pk or table.entity_candidate):
                continue  # 非实体表，跳过（其外键可能在别处被引用时再惰性建类）

            cls = get_or_create_class(table)

            for c in columns:
                if c.is_primary_key:
                    continue  # 主键作为实体标识符，不单独建数据属性
                prof = profiles.get(c.id)
                xsd = _xsd_of(c.data_type)
                prop = OntologyProperty(
                    version_id=version.id,
                    class_id=cls.id,
                    name=c.column_name,
                    property_type="data",
                    range_type=xsd,
                    source_column_id=c.id,
                    semantic_type=c.semantic_type or (prof.detected_format if prof else None),
                    confidence=1.0 if c.semantic_type or (prof and prof.detected_format) else 0.7,
                )
                self.db.add(prop)
                self.db.flush()
                stats["property"] += 1

                # ---- 约束 ----
                # 非空 -> 必填（最小基数 1）
                if c.is_nullable is False or (prof and (prof.null_ratio or 0) == 0):
                    self._add_constraint(version.id, "property", prop.id, "cardinality",
                                         json.dumps({"min": 1, "max": -1}), "warn", "schema", 1.0)
                    stats["constraint"] += 1
                # 唯一 -> 函数性
                if c.is_unique or (prof and prof.distinct_count and prof.row_count
                                   and prof.distinct_count >= prof.row_count):
                    self._add_constraint(version.id, "property", prop.id, "functional",
                                         None, "info", "schema", 1.0)
                    stats["constraint"] += 1
                if prof:
                    if prof.is_enum and prof.enum_values:
                        self._add_constraint(version.id, "property", prop.id, "enum",
                                             prof.enum_values, "info", "profile",
                                             prof.format_confidence or 0.9)
                        stats["constraint"] += 1
                    if prof.detected_format in ("email", "phone", "url") and prof.format_confidence:
                        pat = {"email": r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
                               "phone": r"^(?:\+?86)?1[3-9]\d{9}$",
                               "url": r"^https?://"}[prof.detected_format]
                        self._add_constraint(version.id, "property", prop.id, "pattern",
                                             json.dumps({"pattern": pat}), "info", "profile",
                                             prof.format_confidence)
                        stats["constraint"] += 1
                    if prof.min_value is not None and prof.max_value is not None:
                        self._add_constraint(version.id, "property", prop.id, "range",
                                             json.dumps({"min": prof.min_value, "max": prof.max_value}),
                                             "info", "profile", 0.8)
                        stats["constraint"] += 1

        # 2) 外键 -> 关系 + 对象属性
        for table in tables:
            columns = self.col_repo.get_by_table(table.id)
            for c in columns:
                if not (c.is_relationship_key and c.related_table):
                    continue
                from_cls = class_by_table.get((table.database_name, table.table_name))
                if not from_cls:
                    continue
                # 解析目标表
                target_table = self.db.query(MetaTable).filter(
                    MetaTable.datasource_id == datasource_id,
                    MetaTable.database_name == table.database_name,
                    MetaTable.table_name == c.related_table,
                ).first()
                if not target_table:
                    continue
                to_cls = get_or_create_class(target_table, confidence=0.9)

                rel_name = f"has{to_cls.local_name}"
                card = "0..1" if c.is_nullable else "1"
                rel = OntologyRelationship(
                    version_id=version.id,
                    from_class_id=from_cls.id,
                    to_class_id=to_cls.id,
                    name=rel_name,
                    source_column_id=c.id,
                    cardinality=card,
                    confidence=1.0,
                )
                self.db.add(rel)
                self.db.flush()
                stats["relationship"] += 1

                # 对应的对象属性（供 OWL 表达）
                obj_prop = OntologyProperty(
                    version_id=version.id,
                    class_id=from_cls.id,
                    name=rel_name,
                    property_type="object",
                    range_type=to_cls.local_name,
                    source_column_id=c.id,
                    related_class_id=to_cls.id,
                    semantic_type="relation",
                    confidence=1.0,
                )
                self.db.add(obj_prop)
                self.db.flush()
                stats["property"] += 1

                # 关系基数约束
                self._add_constraint(version.id, "relationship", rel.id, "cardinality",
                                     json.dumps({"min": 0 if card == "0..1" else 1, "max": 1}),
                                     "info", "schema", 1.0)
                stats["constraint"] += 1

        self.db.flush()
        return {
            "stats": stats,
            "class_by_local": class_by_local,
            "class_by_table": class_by_table,
        }

    def _add_constraint(self, version_id, target_type, target_id, ctype, expression,
                        severity, source, confidence):
        c = OntologyConstraint(
            version_id=version_id,
            target_type=target_type,
            target_id=target_id,
            constraint_type=ctype,
            expression=expression if isinstance(expression, str) else json.dumps(expression, ensure_ascii=False),
            severity=severity,
            source=source,
            confidence=confidence,
        )
        self.db.add(c)

    # ========== Step 2: LLM / Agent 增强 ==========

    async def _enhance(self, version, draft, method, llm_config_id, agent_id, on_event) -> Optional[dict]:
        """对整库 schema 摘要 + 画像做一次 LLM/Agent 调用，返回增强补丁."""
        summary = self._build_schema_summary(version.id)
        prompt = self._enhance_prompt(summary)
        system_prompt = (
            "你是本体工程专家，擅长从关系数据库 schema 中精炼本体语义。"
            "只返回纯 JSON，不要 markdown 代码块，不要额外文字。"
        )
        try:
            if method == "agent":
                from app.services.metadata_service import MetadataService
                content = await MetadataService(self.db)._call_agent_for_annotation(
                    agent_id, system_prompt, prompt
                )
            else:
                from app.services.llm_config_service import LLMConfigService
                llm_svc = LLMConfigService(self.db)
                result = await llm_svc.chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    config_id=llm_config_id,
                    temperature=0.2,
                    max_tokens=6000,
                )
                content = result["content"].strip()

            await self._emit(on_event, "text", content[:1500] + ("..." if len(content) > 1500 else ""))

            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            return json.loads(content)
        except (json.JSONDecodeError, ValueError) as e:
            await self._emit(on_event, "error", f"增强结果解析失败（已保留草案）: {e}")
            return None
        except Exception as e:
            await self._emit(on_event, "error", f"增强调用失败（已保留草案）: {e}")
            return None

    def _build_schema_summary(self, version_id: int) -> dict:
        """构建供 LLM 阅读的紧凑 schema 摘要（含画像要点）."""
        classes = self.db.query(OntologyClass).filter(
            OntologyClass.version_id == version_id
        ).all()
        relationships = self.db.query(OntologyRelationship).filter(
            OntologyRelationship.version_id == version_id
        ).all()
        props = self.db.query(OntologyProperty).filter(
            OntologyProperty.version_id == version_id,
            OntologyProperty.property_type == "data",
        ).all()

        # 类 local_name -> 属性列表
        props_by_class = {}
        for p in props:
            props_by_class.setdefault(p.class_id, []).append(p)

        class_sum = []
        for c in classes:
            col_list = []
            for p in props_by_class.get(c.id, []):
                col_list.append({
                    "name": p.name,
                    "type": p.range_type,
                    "semantic_type": p.semantic_type,
                })
            class_sum.append({
                "local_name": c.local_name,
                "label": c.label,
                "definition": c.definition,
                "domain": c.domain,
                "columns": col_list,
            })

        rel_sum = [{"from": r.from_class.local_name, "to": r.to_class.local_name,
                    "name": r.name, "cardinality": r.cardinality}
                   for r in relationships]

        return {"classes": class_sum, "relationships": rel_sum}

    @staticmethod
    def _enhance_prompt(summary: dict) -> str:
        return f"""下面是某数据源自动抽取出的本体草案（来自关系数据库 schema）。

{json.dumps(summary, ensure_ascii=False, indent=1)}

请在不改变类名（local_name）的前提下，完善本体语义，并返回 JSON：
{{
  "classes": [
    {{
      "local_name": "类名（必须与原草案一致）",
      "label": "更贴切的中文标签",
      "definition": "一句话业务定义",
      "domain": "业务域，如 用户/订单/商品/支付/营销/库存/财务/通用",
      "entity_type": "class 或 enumeration"
    }}
  ],
  "extra_relationships": [
    {{
      "from": "源类 local_name",
      "to": "目标类 local_name",
      "name": "关系名（如 belongsTo / contains），英文驼峰",
      "cardinality": "0..1 / 1 / 0..* / 1..* 之一"
    }}
  ]
}}

规则：
1. extra_relationships 只补充「schema 外键未体现、但业务上确实存在的语义关系」，不要重复已有关系。
2. 只返回纯 JSON。"""

    def _apply_enhancement(self, version, draft, extra: dict) -> int:
        """应用 LLM 增强补丁，返回新增条目数."""
        added = 0
        class_by_local = draft["class_by_local"]

        # 类语义精化
        for c in extra.get("classes", []):
            local = c.get("local_name")
            cls = class_by_local.get(local)
            if not cls:
                continue
            if c.get("label"):
                cls.label = c["label"]
            if c.get("definition"):
                cls.definition = c["definition"]
            if c.get("domain"):
                cls.domain = c["domain"]
            if c.get("entity_type"):
                cls.entity_type = c["entity_type"]
            cls.confidence = max(cls.confidence or 0.7, 0.85)

        # 额外语义关系
        for r in extra.get("extra_relationships", []):
            frm = class_by_local.get(r.get("from"))
            to = class_by_local.get(r.get("to"))
            name = (r.get("name") or "").strip()
            if not (frm and to and name):
                continue
            card = r.get("cardinality") or "0..*"
            rel = OntologyRelationship(
                version_id=version.id,
                from_class_id=frm.id,
                to_class_id=to.id,
                name=name,
                cardinality=card,
                confidence=0.8,
            )
            self.db.add(rel)
            self.db.flush()
            added += 1
            # 对应对象属性
            obj_prop = OntologyProperty(
                version_id=version.id,
                class_id=frm.id,
                name=name,
                property_type="object",
                range_type=to.local_name,
                related_class_id=to.id,
                semantic_type="relation",
                confidence=0.8,
            )
            self.db.add(obj_prop)
            self.db.flush()
            added += 1
            self._add_constraint(version_id=version.id, target_type="relationship",
                                 target_id=rel.id, ctype="cardinality",
                                 expression={"min": 0, "max": -1}, severity="info",
                                 source="llm", confidence=0.8)
            added += 1

        self.db.flush()
        return added

    # ========== Step 3: Judge 校验 ==========

    async def _judge(self, version, draft, method, llm_config_id, agent_id, on_event) -> list:
        """用 LLM 审查本体一致性，返回问题清单."""
        summary = self._build_schema_summary(version.id)
        prompt = (
            "请审查以下本体的逻辑一致性，重点检查：\n"
            "1. 是否有明显错误的实体定义或关系方向；\n"
            "2. 是否有重复或冗余的关系；\n"
            "3. 关系基数是否合理。\n\n"
            f"{json.dumps(summary, ensure_ascii=False, indent=1)}\n\n"
            "返回 JSON：{\"issues\": [{\"severity\":\"warn|error|info\",\"target\":\"类名或关系名\","
            "\"message\":\"问题描述\"}]}，没有问题时 issues 为空数组。"
        )
        system_prompt = "你是本体质量评审专家，只返回纯 JSON。"
        try:
            if method == "agent" and agent_id:
                from app.services.metadata_service import MetadataService
                content = await MetadataService(self.db)._call_agent_for_annotation(agent_id, system_prompt, prompt)
            else:
                from app.services.llm_config_service import LLMConfigService
                llm_svc = LLMConfigService(self.db)
                result = await llm_svc.chat_completion(
                    messages=[{"role": "system", "content": system_prompt},
                              {"role": "user", "content": prompt}],
                    config_id=llm_config_id, temperature=0.2, max_tokens=3000,
                )
                content = result["content"].strip()
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            data = json.loads(content)
            issues = data.get("issues", [])
            await self._emit(on_event, "text", f"校验建议: {json.dumps(issues, ensure_ascii=False)[:800]}")
            return issues
        except Exception as e:
            await self._emit(on_event, "error", f"校验失败（跳过）: {e}")
            return []

    # ========== 查询与导出 ==========

    def get_version(self, version_id: int) -> dict:
        v = self.db.query(OntologyVersion).filter(OntologyVersion.id == version_id).first()
        if not v:
            raise NotFoundException(f"本体版本不存在: {version_id}")
        return v.to_response_dict()

    def list_versions(self, datasource_id: int) -> list:
        vs = self.db.query(OntologyVersion).filter(
            OntologyVersion.datasource_id == datasource_id
        ).order_by(OntologyVersion.created_at.desc()).all()
        return [v.to_response_dict() for v in vs]

    def delete_version(self, version_id: int):
        v = self.db.query(OntologyVersion).filter(OntologyVersion.id == version_id).first()
        if not v:
            raise NotFoundException(f"本体版本不存在: {version_id}")
        self.db.delete(v)
        self.db.commit()
        return {"message": "已删除", "id": version_id}

    def get_graph(self, version_id: int) -> dict:
        """聚合为图谱 nodes/edges，供前端 G6 渲染."""
        v = self.db.query(OntologyVersion).filter(OntologyVersion.id == version_id).first()
        if not v:
            raise NotFoundException(f"本体版本不存在: {version_id}")

        classes = self.db.query(OntologyClass).filter(
            OntologyClass.version_id == version_id
        ).all()
        relationships = self.db.query(OntologyRelationship).filter(
            OntologyRelationship.version_id == version_id
        ).all()
        props = self.db.query(OntologyProperty).filter(
            OntologyProperty.version_id == version_id
        ).all()

        nodes = []
        for c in classes:
            cls_props = [p for p in props if p.class_id == c.id and p.property_type == "data"]
            nodes.append({
                "id": f"c{c.id}",
                "type": "entity",
                "label": c.label or c.local_name,
                "local_name": c.local_name,
                "domain": c.domain,
                "definition": c.definition,
                "entity_type": c.entity_type,
                "confidence": c.confidence,
                "attr_count": len(cls_props),
            })

        edges = []
        for r in relationships:
            edges.append({
                "id": f"r{r.id}",
                "source": f"c{r.from_class_id}",
                "target": f"c{r.to_class_id}",
                "label": r.name,
                "cardinality": r.cardinality,
                "confidence": r.confidence,
            })

        return {"version_id": version_id, "nodes": nodes, "edges": edges}

    def get_entities(self, version_id: int) -> list:
        classes = self.db.query(OntologyClass).filter(
            OntologyClass.version_id == version_id
        ).order_by(OntologyClass.local_name).all()
        result = []
        for c in classes:
            props = self.db.query(OntologyProperty).filter(
                OntologyProperty.class_id == c.id
            ).order_by(OntologyProperty.id).all()
            result.append({
                **c.to_response_dict(),
                "properties": [p.to_response_dict() for p in props],
            })
        return result

    def get_relationships(self, version_id: int) -> list:
        rels = self.db.query(OntologyRelationship).filter(
            OntologyRelationship.version_id == version_id
        ).order_by(OntologyRelationship.id).all()
        return [r.to_response_dict() for r in rels]

    def get_constraints(self, version_id: int) -> list:
        cons = self.db.query(OntologyConstraint).filter(
            OntologyConstraint.version_id == version_id
        ).order_by(OntologyConstraint.id).all()
        return [c.to_response_dict() for c in cons]

    def update_entity(self, entity_id: int, updates: dict) -> dict:
        c = self.db.query(OntologyClass).filter(OntologyClass.id == entity_id).first()
        if not c:
            raise NotFoundException(f"实体不存在: {entity_id}")
        allowed = {"label", "definition", "domain", "entity_type", "is_entity"}
        for k, val in updates.items():
            if k in allowed:
                setattr(c, k, val)
        self.db.commit()
        return c.to_response_dict()

    def export_owl(self, version_id: int, fmt: str = "turtle") -> str:
        """导出本体为 OWL/RDF 或 JSON.

        fmt: turtle | xml | json
        """
        v = self.db.query(OntologyVersion).filter(OntologyVersion.id == version_id).first()
        if not v:
            raise NotFoundException(f"本体版本不存在: {version_id}")

        if fmt == "json":
            return json.dumps({
                "version": v.to_response_dict(),
                "entities": self.get_entities(version_id),
                "relationships": self.get_relationships(version_id),
                "constraints": self.get_constraints(version_id),
            }, ensure_ascii=False, indent=2)

        # OWL/RDF 序列化
        try:
            from rdflib import Graph, URIRef, Namespace, Literal
            from rdflib.namespace import OWL, RDF, XSD, RDFS
        except ImportError:
            raise BusinessException("缺少 rdflib 依赖，无法导出 OWL（请 pip install rdflib）", code="NO_RDFLIB")

        base = f"http://ontomind.org/ontology/{version_id}#"
        ns = Namespace(base)
        g = Graph()
        g.bind("owl", OWL)
        g.bind("xsd", XSD)
        g.bind("onto", ns)

        classes = self.db.query(OntologyClass).filter(OntologyClass.version_id == version_id).all()
        props = self.db.query(OntologyProperty).filter(OntologyProperty.version_id == version_id).all()
        rels = self.db.query(OntologyRelationship).filter(OntologyRelationship.version_id == version_id).all()

        class_uri = {c.id: ns[c.local_name] for c in classes}

        for c in classes:
            uri = class_uri[c.id]
            g.add((uri, RDF.type, OWL.Class))
            if c.label:
                g.add((uri, RDFS.label, Literal(c.label)))
            if c.definition:
                g.add((uri, RDFS.comment, Literal(c.definition)))

        for p in props:
            if p.property_type == "data":
                frag = class_uri[p.class_id].fragment if p.class_id else None
                uri = ns[p.name] if not frag else ns[f"{frag}_{p.name}"]
                g.add((uri, RDF.type, OWL.DatatypeProperty))
                if p.class_id and p.class_id in class_uri:
                    g.add((uri, RDFS.domain, class_uri[p.class_id]))
                range_uri = _xsd_uri(p.range_type, XSD, ns)
                g.add((uri, RDFS.range, range_uri))
            else:
                # 对象属性（来自外键/语义关系）
                uri = ns[p.name]
                g.add((uri, RDF.type, OWL.ObjectProperty))
                if p.class_id and p.class_id in class_uri:
                    g.add((uri, RDFS.domain, class_uri[p.class_id]))
                if p.related_class_id and p.related_class_id in class_uri:
                    g.add((uri, RDFS.range, class_uri[p.related_class_id]))

        # 关系补充对象属性（若 OntologyRelationship 未对应对象属性）
        for r in rels:
            if r.from_class_id in class_uri and r.to_class_id in class_uri:
                uri = ns[r.name]
                g.add((uri, RDF.type, OWL.ObjectProperty))
                g.add((uri, RDFS.domain, class_uri[r.from_class_id]))
                g.add((uri, RDFS.range, class_uri[r.to_class_id]))

        if fmt == "xml":
            return g.serialize(format="xml")
        return g.serialize(format="turtle")


def _xsd_uri(range_type: Optional[str], XSD, ns):
    """将 xsd:xxx 或类名映射为 URIRef."""
    if not range_type:
        return XSD.string
    if range_type.startswith("xsd:"):
        name = range_type.split(":", 1)[1]
        return getattr(XSD, name, XSD.string)
    # 否则视为类名
    return ns[range_type]
