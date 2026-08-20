"""Competency Question 服务。"""
from __future__ import annotations

import json
import logging
from collections import deque
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.db.models.ontology_model import OntologyCQ, OntologyCQVerifyStatus
from app.db.repositories.ontology_repo import (
    OntologyCQRepository,
    OntologyLinkTypeRepository,
    OntologyMappingRepository,
    OntologyMetricRepository,
    OntologyObjectTypeRepository,
    OntologyRepository,
)
from app.schemas.ontology_schema import CQCreate
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

_DEFAULT_CQS = [
    {"question": "某客户申请了哪些贷款？", "category": "关系遍历", "related_keys": ["Party", "LoanApplication"]},
    {"question": "某申请是否生成了合约？", "category": "存在性", "related_keys": ["LoanApplication", "LoanContract"]},
    {"question": "某合约下有哪些贷款账户？", "category": "关系遍历", "related_keys": ["LoanContract", "LoanAccount"]},
    {"question": "某账户触发了哪些风险事件？", "category": "关系遍历", "related_keys": ["LoanAccount", "RiskEvent"]},
    {"question": "逾期账户数量有多少？", "category": "计数", "related_keys": ["LoanAccount", "RiskEvent"]},
    {"question": "某产品对应多少申请？", "category": "聚合", "related_keys": ["CreditProduct", "LoanApplication"]},
    {"question": "申请来自哪个获客渠道？", "category": "关系遍历", "related_keys": ["LoanApplication", "AcquisitionChannel"]},
    {"question": "评分卡用了哪些风险特征？", "category": "关系遍历", "related_keys": ["ScorecardModel", "RiskFeature"]},
    {"question": "合约由什么抵押物担保？", "category": "关系遍历", "related_keys": ["LoanContract", "Collateral"]},
    {"question": "某账户近期还款行为如何？", "category": "条件", "related_keys": ["LoanAccount", "RepaymentBehavior"]},
]


def _enum_val(v: Any) -> str:
    return v.value if hasattr(v, "value") else str(v)


class OntologyCQService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.ontologies = OntologyRepository(db)
        self.cqs = OntologyCQRepository(db)
        self.object_types = OntologyObjectTypeRepository(db)
        self.link_types = OntologyLinkTypeRepository(db)
        self.mappings = OntologyMappingRepository(db)
        self.metrics = OntologyMetricRepository(db)

    def _resp(self, row: OntologyCQ) -> dict[str, Any]:
        return {
            "id": row.id,
            "ontology_id": row.ontology_id,
            "question": row.question,
            "category": row.category,
            "verify_status": _enum_val(row.verify_status),
            "verify_note": row.verify_note,
            "related_keys": row.related_keys_json or [],
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def _ensure(self, oid: int) -> None:
        if not self.ontologies.get(oid):
            raise NotFoundException(f"本体不存在: {oid}")

    def list_cqs(self, oid: int) -> list[dict[str, Any]]:
        self._ensure(oid)
        return [self._resp(r) for r in self.cqs.list(oid)]

    def create_cq(self, oid: int, data: CQCreate) -> dict[str, Any]:
        self._ensure(oid)
        row = OntologyCQ(
            ontology_id=oid,
            question=data.question.strip(),
            category=data.category,
            verify_status=OntologyCQVerifyStatus.PENDING,
            related_keys_json=list(data.related_keys) if data.related_keys else [],
        )
        self.cqs.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._resp(row)

    def generate_cqs(self, oid: int, mode: str = "llm") -> list[dict[str, Any]]:
        self._ensure(oid)
        ots = self.object_types.list(oid)
        ot_keys = {ot.key for ot in ots if _enum_val(ot.status) != "rejected"}
        created: list[dict[str, Any]] = []

        items: list[dict[str, Any]] = []
        if mode == "llm":
            client = LLMClient()
            if client.is_configured():
                try:
                    data = client.chat_json(
                        [
                            {
                                "role": "system",
                                "content": (
                                    "基于本体生成 10~15 个 Competency Questions。"
                                    '输出 JSON: {"cqs":[{"question","category","related_keys"}]}。'
                                    "分类参考: 存在性/计数/关系遍历/聚合/时间/条件"
                                ),
                            },
                            {
                                "role": "user",
                                "content": json.dumps(
                                    {
                                        "object_types": [
                                            {"key": o.key, "display_name": o.display_name}
                                            for o in ots[:40]
                                        ]
                                    },
                                    ensure_ascii=False,
                                ),
                            },
                        ]
                    )
                    items = list((data or {}).get("cqs") or [])
                except Exception as exc:
                    logger.warning("CQ LLM generate fallback: %s", exc)

        if not items:
            items = [
                cq
                for cq in _DEFAULT_CQS
                if not cq["related_keys"] or all(k in ot_keys for k in cq["related_keys"])
            ]
            if not items:
                items = _DEFAULT_CQS[:5]

        for item in items:
            row = OntologyCQ(
                ontology_id=oid,
                question=str(item.get("question") or "").strip(),
                category=item.get("category"),
                verify_status=OntologyCQVerifyStatus.PENDING,
                related_keys_json=list(item.get("related_keys") or []),
            )
            if not row.question:
                continue
            self.cqs.add(row)
            self.db.flush()
            created.append(self._resp(row))
        self.db.commit()
        return created

    def _match_concepts(self, question: str, related_keys: list[str], oid: int) -> list[str]:
        ots = self.object_types.list(oid)
        metrics = self.metrics.list(oid)
        found: list[str] = list(related_keys or [])
        q = (question or "").lower()
        for ot in ots:
            tokens = [ot.key.lower(), (ot.display_name or "").lower()]
            for a in ot.aliases_json or []:
                tokens.append(str(a).lower())
            if any(t and t in q for t in tokens):
                if ot.key not in found:
                    found.append(ot.key)
        for m in metrics:
            if m.key.lower() in q or (m.display_name or "").lower() in q:
                if m.key not in found:
                    found.append(m.key)
        return found

    def _bfs_reachable(self, oid: int, keys: list[str], *, depth: int = 3) -> tuple[bool, Optional[str]]:
        if len(keys) <= 1:
            return True, None
        links = [
            lk
            for lk in self.link_types.list(oid)
            if _enum_val(lk.status) in ("accepted", "draft")
        ]
        adj: dict[str, set[str]] = {}
        for lk in links:
            adj.setdefault(lk.from_key, set()).add(lk.to_key)
            adj.setdefault(lk.to_key, set()).add(lk.from_key)

        start = keys[0]
        targets = set(keys[1:])
        seen = {start}
        q: deque[tuple[str, int]] = deque([(start, 0)])
        reached: set[str] = {start}
        while q:
            node, d = q.popleft()
            if d >= depth:
                continue
            for nb in adj.get(node, ()):
                if nb not in seen:
                    seen.add(nb)
                    reached.add(nb)
                    q.append((nb, d + 1))
        missing = [k for k in targets if k not in reached]
        if missing:
            return False, f"缺少可达路径: {start} → {', '.join(missing)}（depth<={depth}）"
        return True, None

    def _mapping_coverage(self, oid: int, keys: list[str]) -> tuple[bool, Optional[str]]:
        maps = [
            m
            for m in self.mappings.list(oid)
            if _enum_val(m.status) in ("accepted", "draft")
        ]
        mapped = {m.element_key for m in maps if _enum_val(m.element_type) == "object_type"}
        # also property keys like Class.prop — only check object types here
        missing = [k for k in keys if k not in mapped]
        if missing:
            return False, f"缺少物理映射: {', '.join(missing)}"
        return True, None

    def verify_cq(self, cq_id: int) -> dict[str, Any]:
        row = self.cqs.get(cq_id)
        if not row:
            raise NotFoundException(f"CQ 不存在: {cq_id}")
        keys = self._match_concepts(row.question, list(row.related_keys_json or []), row.ontology_id)
        notes: list[str] = []
        ok = True

        if not keys:
            ok = False
            notes.append("未能匹配到本体概念")
        else:
            reach_ok, reach_note = self._bfs_reachable(row.ontology_id, keys)
            if not reach_ok:
                ok = False
                notes.append(reach_note or "关系不可达")
            map_ok, map_note = self._mapping_coverage(row.ontology_id, keys)
            if not map_ok:
                ok = False
                notes.append(map_note or "映射缺失")

        row.related_keys_json = keys
        row.verify_status = OntologyCQVerifyStatus.PASS if ok else OntologyCQVerifyStatus.FAIL
        row.verify_note = "；".join(notes) if notes else "可达且已映射"
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._resp(row)

    def verify_all(self, oid: int) -> dict[str, Any]:
        self._ensure(oid)
        rows = self.cqs.list(oid)
        results = [self.verify_cq(r.id) for r in rows]
        passed = sum(1 for r in results if r["verify_status"] == "pass")
        total = len(results)
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total, 4) if total else 0.0,
            "results": results,
        }
