"""消金场景命名规则 / PII 模式 / 分层前缀。"""
from __future__ import annotations

import re
from typing import Any, Optional

ABBREV_DICT: dict[str, str] = {
    "id": "标识",
    "no": "编号",
    "num": "号码",
    "amt": "金额",
    "bal": "余额",
    "dt": "日期",
    "ts": "时间戳",
    "tm": "时间",
    "cnt": "数量",
    "qty": "数量",
    "flg": "标志",
    "flag": "标志",
    "pct": "百分比",
    "rate": "利率",
    "ovd": "逾期",
    "cust": "客户",
    "customer": "客户",
    "acct": "账户",
    "account": "账户",
    "txn": "交易",
    "trans": "交易",
    "prod": "产品",
    "product": "产品",
    "chnl": "渠道",
    "channel": "渠道",
    "apply": "申请",
    "loan": "贷款",
    "repay": "还款",
    "repayment": "还款",
    "credit": "授信",
    "limit": "额度",
    "score": "评分",
    "risk": "风险",
    "phone": "手机号",
    "mobile": "手机号",
    "tel": "电话",
    "email": "邮箱",
    "addr": "地址",
    "address": "地址",
    "name": "姓名",
    "idcard": "身份证",
    "id_no": "证件号",
    "card": "卡",
    "bank": "银行",
    "status": "状态",
    "type": "类型",
    "code": "编码",
    "desc": "描述",
    "remark": "备注",
    "create": "创建",
    "update": "更新",
    "delete": "删除",
    "user": "用户",
    "org": "机构",
    "branch": "网点",
    "city": "城市",
    "prov": "省份",
    "province": "省份",
    "gender": "性别",
    "birthday": "生日",
    "birth": "出生",
    "age": "年龄",
    "income": "收入",
    "interest": "利息",
    "principal": "本金",
    "fee": "费用",
    "penalty": "罚息",
    "contract": "合同",
    "order": "订单",
    "bill": "账单",
    "period": "期次",
    "term": "期限",
    "due": "到期",
    "overdue": "逾期",
    "dpd": "逾期天数",
}

LAYER_PREFIX_DOMAIN: dict[str, str] = {
    "ods_": "ODS",
    "dwd_": "DWD",
    "dws_": "DWS",
    "dim_": "DIM",
    "fact_": "FACT",
    "ads_": "ADS",
    "tmp_": "TMP",
    "stg_": "STG",
}

PII_NAME_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    (re.compile(r"(id[_]?card|身份证|sfz|id_no)", re.I), "L3", 0.92),
    (re.compile(r"(bank[_]?card|card[_]?no|银行卡|卡号)", re.I), "L3", 0.9),
    (re.compile(r"(phone|mobile|tel|手机|电话)", re.I), "L3", 0.9),
    (re.compile(r"(email|邮箱|邮件)", re.I), "L2", 0.88),
    (re.compile(r"(addr|address|地址)", re.I), "L2", 0.85),
    (re.compile(r"(^name$|_name$|姓名|真实姓名)", re.I), "L2", 0.82),
    (re.compile(r"(amt|amount|bal|balance|limit|score|额度|金额|评分)", re.I), "L1", 0.75),
]

_PHONE_RE = re.compile(r"^1\d{10}$")
_IDCARD_RE = re.compile(r"^\d{17}[\dXx]$")
_CAMEL_RE = re.compile(r"([a-z0-9])([A-Z])")
_NON_ALNUM_RE = re.compile(r"[^a-zA-Z0-9\u4e00-\u9fff]+")


def split_identifier(name: str) -> list[str]:
    raw = (name or "").strip()
    if not raw:
        return []
    s = _CAMEL_RE.sub(r"\1_\2", raw)
    s = _NON_ALNUM_RE.sub("_", s)
    parts = [p.lower() for p in s.split("_") if p]
    return parts


def expand_name_to_biz(name: str) -> tuple[Optional[str], float]:
    parts = split_identifier(name)
    if not parts:
        return None, 0.0
    zh: list[str] = []
    hit = 0
    for p in parts:
        if p in ABBREV_DICT:
            zh.append(ABBREV_DICT[p])
            hit += 1
        elif re.fullmatch(r"[\u4e00-\u9fff]+", p):
            zh.append(p)
            hit += 1
        else:
            zh.append(p)
    if hit == 0:
        return None, 0.0
    biz = "".join(zh) if all(re.fullmatch(r"[\u4e00-\u9fff]+", x) for x in zh) else "_".join(zh)
    conf = 0.7 + 0.05 * min(hit, 4)
    if hit == len(parts):
        conf = min(0.88, conf + 0.08)
    return biz[:12], min(0.88, conf)


def detect_layer_domain(table_name: str) -> Optional[str]:
    lower = (table_name or "").lower()
    for prefix, domain in LAYER_PREFIX_DOMAIN.items():
        if lower.startswith(prefix):
            return domain
    return None


def detect_pii_level(
    column_name: str, profile: Optional[dict[str, Any]] = None
) -> tuple[Optional[str], float, dict[str, Any]]:
    name = column_name or ""
    evidence: dict[str, Any] = {"matched_by": "name"}
    for pattern, level, conf in PII_NAME_PATTERNS:
        if pattern.search(name):
            evidence["pattern"] = pattern.pattern
            if profile:
                samples = []
                top_k = profile.get("top_k") or []
                for item in top_k[:5]:
                    if isinstance(item, dict):
                        samples.append(str(item.get("value", "")))
                    else:
                        samples.append(str(item))
                if level == "L3" and any("phone" in name.lower() or "mobile" in name.lower() for _ in [0]):
                    if any(_PHONE_RE.match(s) for s in samples if s):
                        conf = min(0.97, conf + 0.05)
                        evidence["sample_shape"] = "phone_11"
                if "id" in name.lower() and any(_IDCARD_RE.match(s) for s in samples if s):
                    conf = min(0.97, conf + 0.05)
                    evidence["sample_shape"] = "id_card_18"
            return level, conf, evidence
    return None, 0.0, {}


def is_join_key_candidate(
    column_name: str,
    column_key: Optional[str],
    profile: Optional[dict[str, Any]] = None,
) -> tuple[bool, float, dict[str, Any]]:
    key = (column_key or "").upper()
    if key == "PRI":
        return True, 0.95, {"reason": "primary_key"}
    name = (column_name or "").lower()
    if name.endswith(("_id", "_no", "_code")) or name in {"id", "code", "no"}:
        ratio = None
        if profile and profile.get("distinct_ratio") is not None:
            ratio = float(profile["distinct_ratio"])
        if ratio is not None and ratio > 0.9:
            return True, 0.8, {"reason": "name_suffix_high_cardinality", "distinct_ratio": ratio}
        if ratio is None:
            return True, 0.72, {"reason": "name_suffix"}
    return False, 0.0, {}


def is_entity_table_candidate(
    table_name: str,
    *,
    has_single_pk: bool,
    row_count: Optional[int],
) -> tuple[bool, float, dict[str, Any]]:
    lower = (table_name or "").lower()
    if any(x in lower for x in ("log", "detail", "tmp", "his", "hist", "snapshot")):
        return False, 0.0, {"reason": "excluded_name"}
    if not has_single_pk:
        return False, 0.0, {"reason": "no_single_pk"}
    conf = 0.75
    evidence: dict[str, Any] = {"reason": "single_pk"}
    if row_count is not None and row_count >= 1000:
        conf = 0.85
        evidence["row_count"] = row_count
    elif row_count is not None and row_count >= 100:
        conf = 0.78
        evidence["row_count"] = row_count
    return True, conf, evidence
