"""标准项定义与字段绑定（标准 1:N 字段；字段最多 1 标准）。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException, ConflictException, NotFoundException
from app.db.models.meta_model import (
    MetaBindSource,
    MetaBindStatus,
    MetaColumnStandard,
    MetaColumnStandardHistory,
    MetaStandard,
    MetaStandardStatus,
    MetaStandardVersion,
)
from app.db.repositories.meta_repo import (
    MetaColumnRepository,
    MetaColumnStandardHistoryRepository,
    MetaColumnStandardRepository,
    MetaStandardRepository,
    MetaStandardVersionRepository,
    MetaTableRepository,
)
from app.schemas.metadata_schema import (
    ColumnBindBatchRequest,
    ColumnBindRequest,
    ColumnWorkspaceItem,
    MetaStandardCreate,
    MetaStandardResponse,
    MetaStandardUpdate,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# 消金数仓起步标准：对齐 ODS/DIM 高频列 + 行业口径（身份 / 合约 / 账务 / 风险 / 技术字段）。
# ensure_seed 只补缺失编码，已有项会合并 aliases，不覆盖人工改过的名称/规则。
SEED_STANDARDS: list[dict[str, Any]] = [
    {
        "code": "STD_MOBILE",
        "name": "手机号",
        "aliases": ["phone", "mobile", "tel", "phone_no", "mobile_no", "手机号", "手机号码"],
        "semantic_type": "phone",
        "data_type_expect": "varchar",
        "length_rule": {"min": 11, "max": 11},
        "security_level": "L3",
        "quality_rule": {"regex": r"^1\d{10}$", "null_rate_max": 0.01},
        "mask_rule": "mask_mid4",
        "domain": "identity",
        "description": "中国大陆 11 位手机号（客户本人/注册/联系电话）",
    },
    {
        "code": "STD_ID_CARD",
        "name": "身份证号",
        "aliases": [
            "idcard", "id_no", "id_card", "certno", "cert_no", "sfz",
            "身份证", "证件号", "证件号码",
        ],
        "semantic_type": "id_card",
        "data_type_expect": "varchar",
        "length_rule": {"min": 18, "max": 18},
        "security_level": "L3",
        "quality_rule": {"regex": r"^\d{17}[\dXx]$", "null_rate_max": 0.01},
        "mask_rule": "mask_id",
        "domain": "identity",
        "description": "18 位居民身份证（消金进件/开户主证件）",
    },
    {
        "code": "STD_CUST_ID",
        "name": "客户标识",
        "aliases": ["cust_id", "customer_id", "custid", "客户号", "客户编号"],
        "semantic_type": "identifier",
        "data_type_expect": "bigint",
        "security_level": "L1",
        "quality_rule": {"null_rate_max": 0},
        "domain": "identity",
        "description": "内部客户主键/外键，跨借据、申请、催收案件的主体对齐键",
    },
    {
        "code": "STD_CUST_NAME",
        "name": "客户姓名",
        "aliases": ["cust_name", "customer_name", "real_name", "客户姓名", "借款人姓名"],
        "semantic_type": "person_name",
        "data_type_expect": "varchar",
        "length_rule": {"min": 1, "max": 64},
        "security_level": "L2",
        "quality_rule": {"null_rate_max": 0.05},
        "mask_rule": "mask_name",
        "domain": "identity",
        "description": "自然人客户姓名（不含产品名/活动名等泛化 name 字段）",
    },
    {
        "code": "STD_BANK_CARD",
        "name": "银行卡号",
        "aliases": ["card_no", "bank_card", "bank_card_no", "卡号", "银行卡号"],
        "semantic_type": "identifier",
        "data_type_expect": "varchar",
        "length_rule": {"min": 12, "max": 19},
        "security_level": "L3",
        "quality_rule": {"null_rate_max": 0.1},
        "mask_rule": "mask_bank_card",
        "domain": "identity",
        "description": "放款/还款银行卡号，直接身份标识",
    },
    {
        "code": "STD_EMAIL",
        "name": "电子邮箱",
        "aliases": ["email", "mail", "邮箱"],
        "semantic_type": "email",
        "data_type_expect": "varchar",
        "security_level": "L2",
        "quality_rule": {"regex": r"^[^@\s]+@[^@\s]+\.[^@\s]+$"},
        "mask_rule": "mask_email",
        "domain": "identity",
        "description": "联系邮箱",
    },
    {
        "code": "STD_ADDRESS",
        "name": "联系地址",
        "aliases": ["addr", "address", "address_detail", "地址"],
        "semantic_type": "address",
        "data_type_expect": "varchar",
        "security_level": "L2",
        "mask_rule": "mask_addr",
        "domain": "identity",
        "description": "居住/户籍/联系地址",
    },
    {
        "code": "STD_GENDER",
        "name": "性别",
        "aliases": ["gender", "sex", "性别"],
        "semantic_type": "category",
        "data_type_expect": "varchar",
        "security_level": "L1",
        "domain": "identity",
        "description": "客户性别码值（常见 1男 2女）",
    },
    {
        "code": "STD_BIRTHDAY",
        "name": "出生日期",
        "aliases": ["birthday", "birth", "birth_dt", "birth_date", "生日", "出生日期"],
        "semantic_type": "date",
        "data_type_expect": "date",
        "security_level": "L2",
        "domain": "identity",
        "description": "客户出生日期，可间接识别身份",
    },
    {
        "code": "STD_LOAN_NO",
        "name": "借据号",
        "aliases": ["loan_no", "loan_id", "loan_acct", "借据号", "借据编号"],
        "semantic_type": "identifier",
        "data_type_expect": "varchar",
        "security_level": "L1",
        "quality_rule": {"null_rate_max": 0},
        "domain": "loan",
        "description": "贷款借据/账户编号，合约落地后的核心业务主键",
    },
    {
        "code": "STD_APPLY_NO",
        "name": "申请流水号",
        "aliases": [
            "appl_seq", "apply_no", "applyno", "apply_id", "application_no",
            "申请流水号", "申请编号",
        ],
        "semantic_type": "identifier",
        "data_type_expect": "varchar",
        "security_level": "L1",
        "quality_rule": {"null_rate_max": 0},
        "domain": "loan",
        "description": "授信/支用/放款申请流水，进件对齐键",
    },
    {
        "code": "STD_ACCT_NO",
        "name": "账户号",
        "aliases": ["acct_no", "account_no", "repay_acct_no", "账号", "账户编号"],
        "semantic_type": "identifier",
        "data_type_expect": "varchar",
        "security_level": "L1",
        "domain": "account",
        "description": "贷款账户或还款账号",
    },
    {
        "code": "STD_CONTRACT_NO",
        "name": "合同号",
        "aliases": ["contract_no", "contract_id", "合同号", "合同编号"],
        "semantic_type": "identifier",
        "data_type_expect": "varchar",
        "security_level": "L1",
        "domain": "loan",
        "description": "借款/授信合同编号",
    },
    {
        "code": "STD_PRODUCT_CODE",
        "name": "产品编码",
        "aliases": [
            "product_id", "product_cd", "product_code", "loan_typ", "loan_type",
            "limit_code", "prod_id", "产品编号", "产品编码",
        ],
        "semantic_type": "category",
        "data_type_expect": "varchar",
        "security_level": "L0",
        "domain": "product",
        "description": "信贷/额度产品代码，对齐产品维表",
    },
    {
        "code": "STD_CHANNEL_ID",
        "name": "渠道标识",
        "aliases": ["channel_id", "chnl_id", "dealer_cde", "渠道ID", "渠道编号", "进件渠道"],
        "semantic_type": "identifier",
        "data_type_expect": "varchar",
        "security_level": "L0",
        "domain": "channel",
        "description": "获客/进件/支付渠道编码",
    },
    {
        "code": "STD_TENANT_ID",
        "name": "租户标识",
        "aliases": ["tenant_id", "租户ID"],
        "semantic_type": "identifier",
        "data_type_expect": "varchar",
        "security_level": "L1",
        "quality_rule": {"null_rate_max": 0},
        "domain": "org",
        "description": "多租户隔离键",
    },
    {
        "code": "STD_AMOUNT",
        "name": "交易金额",
        "aliases": ["tx_amt", "amount", "repay_amt", "apply_amt", "ps_instm_amt", "金额"],
        "semantic_type": "amount",
        "data_type_expect": "decimal",
        "security_level": "L1",
        "quality_rule": {"min": 0},
        "domain": "account",
        "description": "发生额（交易/还款/申请金额）。本金、利息、费用请用对应分项标准",
    },
    {
        "code": "STD_PRINCIPAL",
        "name": "本金",
        "aliases": [
            "prin_amt", "prin_bal", "paid_prin_amt", "ovd_prin_bal",
            "ps_prcp_amt", "setl_prcp_amt", "本金",
        ],
        "semantic_type": "amount",
        "data_type_expect": "decimal",
        "security_level": "L1",
        "quality_rule": {"min": 0},
        "domain": "account",
        "description": "贷款本金发生额或余额（含逾期本金）",
    },
    {
        "code": "STD_INTEREST",
        "name": "利息",
        "aliases": [
            "int_amt", "int_bal", "paid_int_amt", "ovd_int_bal",
            "ps_od_int_amt", "ps_norm_int_amt", "利息",
        ],
        "semantic_type": "amount",
        "data_type_expect": "decimal",
        "security_level": "L1",
        "quality_rule": {"min": 0},
        "domain": "account",
        "description": "利息发生额或余额（含罚息/逾期利息）",
    },
    {
        "code": "STD_FEE_AMT",
        "name": "费用金额",
        "aliases": ["fee_amt", "ps_fee_amt", "setl_fee_amt", "费用"],
        "semantic_type": "amount",
        "data_type_expect": "decimal",
        "security_level": "L1",
        "quality_rule": {"min": 0},
        "domain": "account",
        "description": "手续费/其他费项金额",
    },
    {
        "code": "STD_CREDIT_LMT",
        "name": "授信额度",
        "aliases": ["lmt_amt", "credit_limit", "credit_lmt", "额度"],
        "semantic_type": "amount",
        "data_type_expect": "decimal",
        "security_level": "L1",
        "quality_rule": {"min": 0},
        "domain": "loan",
        "description": "客户级或产品级授信/可用额度",
    },
    {
        "code": "STD_INT_RATE",
        "name": "贷款利率",
        "aliases": [
            "interest_rate", "loan_int_rate", "loan_rate", "ps_int_rate",
            "penalty_rate", "loan_od_int_rate", "利率", "费率",
        ],
        "semantic_type": "rate",
        "data_type_expect": "decimal",
        "security_level": "L1",
        "domain": "loan",
        "description": "执行利率/逾期利率/罚息利率（年化或合同约定口径以表注释为准）",
    },
    {
        "code": "STD_BIZ_DATE",
        "name": "业务日期",
        "aliases": ["biz_date", "post_date", "dt", "data_load_biz_date", "营业日期", "业务日期"],
        "semantic_type": "date",
        "data_type_expect": "date",
        "security_level": "L0",
        "domain": "tech",
        "description": "账务/入账业务日期，分区与对账常用",
    },
    {
        "code": "STD_DUE_DATE",
        "name": "到期日",
        "aliases": ["due_date", "ps_due_dt", "last_due_dt", "repay_date", "到期日", "还款日期"],
        "semantic_type": "date",
        "data_type_expect": "date",
        "security_level": "L0",
        "domain": "account",
        "description": "当期应还/借据到期日期",
    },
    {
        "code": "STD_CREATE_TIME",
        "name": "创建时间",
        "aliases": ["create_time", "created_at", "crt_dt", "创建时间"],
        "semantic_type": "timestamp",
        "data_type_expect": "datetime",
        "security_level": "L0",
        "domain": "tech",
        "description": "记录创建时间（技术字段，非业务发生时间）",
    },
    {
        "code": "STD_UPDATE_TIME",
        "name": "更新时间",
        "aliases": ["update_time", "updated_at", "last_chg_dt", "更新时间", "最后修改时间"],
        "semantic_type": "timestamp",
        "data_type_expect": "datetime",
        "security_level": "L0",
        "domain": "tech",
        "description": "记录最后更新时间",
    },
    {
        "code": "STD_STATUS",
        "name": "状态码",
        "aliases": ["status", "sts", "deal_sts", "wf_appr_sts", "post_sts", "状态"],
        "semantic_type": "status_code",
        "data_type_expect": "varchar",
        "security_level": "L0",
        "domain": "loan",
        "description": "业务/审批/处理状态码，具体枚举以码表或注释为准",
    },
    {
        "code": "STD_LOAN_TERM",
        "name": "贷款期数",
        "aliases": [
            "tnr", "term", "loan_term", "total_terms", "repay_term",
            "curr_term", "term_no", "期数", "期限",
        ],
        "semantic_type": "count",
        "data_type_expect": "int",
        "security_level": "L0",
        "quality_rule": {"min": 1, "max": 360},
        "domain": "loan",
        "description": "贷款总期数或当前期次",
    },
    {
        "code": "STD_OVERDUE_DAYS",
        "name": "逾期天数",
        "aliases": ["overdue_days", "ovd_days", "dpd", "逾期天数"],
        "semantic_type": "count",
        "data_type_expect": "int",
        "security_level": "L1",
        "quality_rule": {"min": 0},
        "domain": "risk",
        "description": "账户当前或历史逾期天数（DPD）",
    },
    {
        "code": "STD_RISK_SCORE",
        "name": "风险评分",
        "aliases": ["score", "risk_score", "credit_score", "评分"],
        "semantic_type": "count",
        "data_type_expect": "decimal",
        "security_level": "L1",
        "domain": "risk",
        "description": "申请/行为评分卡输出分",
    },
    {
        "code": "STD_CASE_ID",
        "name": "催收案件号",
        "aliases": ["case_id", "案件号", "案件编号"],
        "semantic_type": "identifier",
        "data_type_expect": "varchar",
        "security_level": "L1",
        "domain": "risk",
        "description": "入催后案件标识，对齐催收作业",
    },
    {
        "code": "STD_IS_DELETED",
        "name": "逻辑删除标志",
        "aliases": ["is_deleted", "deleted", "del_flag", "是否删除"],
        "semantic_type": "boolean_flag",
        "data_type_expect": "tinyint",
        "security_level": "L0",
        "domain": "tech",
        "description": "软删除标记，分析时需过滤",
    },
]


def _snapshot(std: MetaStandard) -> dict[str, Any]:
    return {
        "code": std.code,
        "name": std.name,
        "aliases_json": std.aliases_json,
        "description": std.description,
        "semantic_type": std.semantic_type,
        "data_type_expect": std.data_type_expect,
        "length_rule_json": std.length_rule_json,
        "security_level": std.security_level,
        "quality_rule_json": std.quality_rule_json,
        "mask_rule": std.mask_rule,
        "domain": std.domain,
        "status": std.status.value if hasattr(std.status, "value") else str(std.status),
    }


class MetaStandardService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.standards = MetaStandardRepository(db)
        self.versions = MetaStandardVersionRepository(db)
        self.binds = MetaColumnStandardRepository(db)
        self.history = MetaColumnStandardHistoryRepository(db)
        self.columns = MetaColumnRepository(db)
        self.tables = MetaTableRepository(db)

    def _to_response(self, row: MetaStandard) -> MetaStandardResponse:
        data = MetaStandardResponse.model_validate(row)
        data.bound_column_count = self.standards.count_bindings(row.id)
        return data

    def ensure_seed_standards(self) -> None:
        changed = False
        for s in SEED_STANDARDS:
            existing = self.standards.get_by_code(s["code"])
            if existing:
                old = {str(a) for a in (existing.aliases_json or []) if a}
                new = {str(a) for a in (s.get("aliases") or []) if a}
                if new - old:
                    existing.aliases_json = sorted(old | new)
                    changed = True
                if not existing.domain and s.get("domain"):
                    existing.domain = s["domain"]
                    changed = True
                continue
            self.create_standard(
                MetaStandardCreate(
                    code=s["code"],
                    name=s["name"],
                    aliases=s.get("aliases"),
                    description=s.get("description"),
                    semantic_type=s.get("semantic_type"),
                    data_type_expect=s.get("data_type_expect"),
                    length_rule=s.get("length_rule"),
                    security_level=s.get("security_level", "L0"),
                    quality_rule=s.get("quality_rule"),
                    mask_rule=s.get("mask_rule"),
                    domain=s.get("domain"),
                    status="published",
                )
            )
        if changed:
            self.db.commit()

    def list_standards(
        self,
        *,
        keyword: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[MetaStandardResponse]:
        rows = self.standards.list(keyword=keyword, status=status, limit=limit, offset=offset)
        return [self._to_response(r) for r in rows]

    def get_standard(self, sid: int) -> MetaStandardResponse:
        row = self.standards.get(sid)
        if not row:
            raise NotFoundException(f"标准项不存在: {sid}")
        return self._to_response(row)

    def create_standard(self, data: MetaStandardCreate, user_id: Optional[int] = None) -> MetaStandardResponse:
        if self.standards.get_by_code(data.code.strip()):
            raise ConflictException(f"标准编码已存在: {data.code}")
        row = MetaStandard(
            code=data.code.strip(),
            name=data.name.strip(),
            aliases_json=list(data.aliases) if data.aliases else None,
            description=data.description,
            semantic_type=data.semantic_type,
            data_type_expect=data.data_type_expect,
            length_rule_json=data.length_rule,
            security_level=data.security_level or "L0",
            quality_rule_json=data.quality_rule,
            mask_rule=data.mask_rule,
            domain=data.domain,
            status=MetaStandardStatus(data.status),
            current_version=1,
        )
        self.standards.add(row)
        self.versions.add(
            MetaStandardVersion(
                standard_id=row.id,
                version=1,
                snapshot_json=_snapshot(row),
                change_note="初始版本",
                author_user_id=user_id,
            )
        )
        self.db.commit()
        self.db.refresh(row)
        return self._to_response(row)

    def update_standard(
        self, sid: int, data: MetaStandardUpdate, user_id: Optional[int] = None
    ) -> MetaStandardResponse:
        row = self.standards.get(sid)
        if not row:
            raise NotFoundException(f"标准项不存在: {sid}")
        payload = data.model_dump(exclude_unset=True)
        bump = bool(payload.pop("bump_version", False))
        change_note = payload.pop("change_note", None)
        if "aliases" in payload:
            row.aliases_json = payload.pop("aliases")
        if "length_rule" in payload:
            row.length_rule_json = payload.pop("length_rule")
        if "quality_rule" in payload:
            row.quality_rule_json = payload.pop("quality_rule")
        if "status" in payload and payload["status"] is not None:
            row.status = MetaStandardStatus(payload.pop("status"))
        for k, v in payload.items():
            setattr(row, k, v)
        self.db.flush()
        if bump:
            row.current_version = int(row.current_version or 1) + 1
            self.db.flush()
            self.versions.add(
                MetaStandardVersion(
                    standard_id=row.id,
                    version=row.current_version,
                    snapshot_json=_snapshot(row),
                    change_note=change_note or f"v{row.current_version}",
                    author_user_id=user_id,
                )
            )
        self.db.commit()
        self.db.refresh(row)
        return self._to_response(row)

    def delete_standard(self, sid: int) -> None:
        row = self.standards.get(sid)
        if not row:
            raise NotFoundException(f"标准项不存在: {sid}")
        if self.standards.count_bindings(sid) > 0:
            raise BusinessException("仍有字段绑定该标准项，请先解绑", code="STANDARD_IN_USE")
        self.standards.delete(row)
        self.db.commit()

    def bind_column(
        self, column_id: int, data: ColumnBindRequest, user_id: Optional[int] = None
    ) -> ColumnWorkspaceItem:
        col = self.columns.get(column_id)
        if not col:
            raise NotFoundException(f"字段不存在: {column_id}")
        std = self.standards.get(data.standard_id)
        if not std:
            raise NotFoundException(f"标准项不存在: {data.standard_id}")
        existing = self.binds.get_by_column(column_id)
        if existing:
            self.history.add(
                MetaColumnStandardHistory(
                    column_id=column_id,
                    standard_id=existing.standard_id,
                    standard_version=existing.standard_version,
                    action="replace",
                    snapshot_json={
                        "standard_id": existing.standard_id,
                        "status": existing.status.value
                        if hasattr(existing.status, "value")
                        else str(existing.status),
                    },
                    actor_user_id=user_id,
                )
            )
            existing.standard_id = std.id
            existing.standard_version = int(std.current_version or 1)
            existing.security_level_override = data.security_level_override
            existing.status = MetaBindStatus(data.status)
            existing.source = MetaBindSource(data.source)
            existing.confidence = data.confidence
            existing.evidence_json = data.evidence
            if data.status == "accepted":
                existing.reviewed_by = user_id
                existing.reviewed_at = _utcnow()
            self.db.flush()
        else:
            bind = MetaColumnStandard(
                column_id=column_id,
                standard_id=std.id,
                standard_version=int(std.current_version or 1),
                security_level_override=data.security_level_override,
                status=MetaBindStatus(data.status),
                source=MetaBindSource(data.source),
                confidence=data.confidence,
                evidence_json=data.evidence,
                reviewed_by=user_id if data.status == "accepted" else None,
                reviewed_at=_utcnow() if data.status == "accepted" else None,
            )
            self.binds.add(bind)
            self.history.add(
                MetaColumnStandardHistory(
                    column_id=column_id,
                    standard_id=std.id,
                    standard_version=bind.standard_version,
                    action="bind",
                    snapshot_json={"standard_id": std.id, "status": data.status},
                    actor_user_id=user_id,
                )
            )
        if data.status == "accepted":
            col.pii_level = data.security_level_override or std.security_level
            if std.semantic_type:
                col.semantic_type = std.semantic_type
            if not col.biz_name:
                col.biz_name = std.name
            self.db.flush()
        self.db.commit()
        items = self.list_workspace_columns(column_ids=[column_id])
        return items[0]

    def batch_bind(self, data: ColumnBindBatchRequest, user_id: Optional[int] = None) -> list[ColumnWorkspaceItem]:
        out: list[ColumnWorkspaceItem] = []
        for cid in data.column_ids:
            out.append(
                self.bind_column(
                    cid,
                    ColumnBindRequest(
                        standard_id=data.standard_id,
                        security_level_override=data.security_level_override,
                        status="accepted",
                        source="human",
                    ),
                    user_id=user_id,
                )
            )
        return out

    def unbind_column(self, column_id: int, user_id: Optional[int] = None) -> None:
        existing = self.binds.get_by_column(column_id)
        if not existing:
            raise NotFoundException(f"字段未绑定标准项: {column_id}")
        self.history.add(
            MetaColumnStandardHistory(
                column_id=column_id,
                standard_id=existing.standard_id,
                standard_version=existing.standard_version,
                action="unbind",
                snapshot_json={"standard_id": existing.standard_id},
                actor_user_id=user_id,
            )
        )
        self.binds.delete(existing)
        self.db.commit()

    def list_workspace_columns(
        self,
        *,
        source_id: Optional[int] = None,
        database: Optional[str] = None,
        table_name: Optional[str] = None,
        column_name: Optional[str] = None,
        security_level: Optional[str] = None,
        standard_id: Optional[int] = None,
        bind_status: Optional[str] = None,
        bound: Optional[bool] = None,
        column_ids: Optional[list[int]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ColumnWorkspaceItem]:
        from app.db.models.meta_model import MetaColumn, MetaTable

        q = (
            self.db.query(MetaColumn, MetaTable, MetaColumnStandard, MetaStandard)
            .join(MetaTable, MetaColumn.table_id == MetaTable.id)
            .outerjoin(MetaColumnStandard, MetaColumnStandard.column_id == MetaColumn.id)
            .outerjoin(MetaStandard, MetaStandard.id == MetaColumnStandard.standard_id)
        )
        if column_ids:
            q = q.filter(MetaColumn.id.in_(column_ids))
        if source_id is not None:
            q = q.filter(MetaTable.source_id == source_id)
        if database:
            q = q.filter(MetaTable.database == database)
        if table_name:
            q = q.filter(MetaTable.table_name.like(f"%{table_name.strip()}%"))
        if column_name:
            q = q.filter(MetaColumn.column_name.like(f"%{column_name.strip()}%"))
        if standard_id is not None:
            q = q.filter(MetaColumnStandard.standard_id == standard_id)
        if bind_status:
            q = q.filter(MetaColumnStandard.status == bind_status)
        if bound is True:
            q = q.filter(MetaColumnStandard.id.isnot(None))
        elif bound is False:
            q = q.filter(MetaColumnStandard.id.is_(None))
        if security_level:
            q = q.filter(
                or_(
                    MetaColumnStandard.security_level_override == security_level,
                    MetaColumn.pii_level == security_level,
                    and_(
                        MetaColumnStandard.security_level_override.is_(None),
                        MetaStandard.security_level == security_level,
                    ),
                )
            )
        rows = (
            q.order_by(MetaTable.table_name.asc(), MetaColumn.ordinal.asc(), MetaColumn.id.asc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 500)))
            .all()
        )
        items: list[ColumnWorkspaceItem] = []
        for col, table, bind, std in rows:
            eff = None
            if bind and std:
                eff = bind.security_level_override or std.security_level
            elif col.pii_level:
                eff = col.pii_level
            items.append(
                ColumnWorkspaceItem(
                    id=col.id,
                    table_id=table.id,
                    table_name=table.table_name,
                    column_name=col.column_name,
                    data_type=col.data_type,
                    column_type=col.column_type,
                    nullable=bool(col.nullable),
                    column_key=col.column_key,
                    column_comment=col.column_comment,
                    biz_name=col.biz_name,
                    pii_level=col.pii_level,
                    semantic_type=col.semantic_type,
                    profile_json=col.profile_json,
                    bind_id=bind.id if bind else None,
                    standard_id=std.id if std else None,
                    standard_code=std.code if std else None,
                    standard_name=std.name if std else None,
                    standard_version=bind.standard_version if bind else None,
                    bind_status=(
                        bind.status.value if bind and hasattr(bind.status, "value") else (str(bind.status) if bind else None)
                    ),
                    effective_security_level=eff,
                    length_rule_json=std.length_rule_json if std else None,
                    quality_rule_json=std.quality_rule_json if std else None,
                )
            )
        return items
