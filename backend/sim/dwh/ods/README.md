# ODS 层

DDL 文件：`ods_tables.sql`

包含 16 张表：

- `ods_cif_customer`
- `ods_collection_case`
- `ods_credit_limit`
- `ods_credit_loan`
- `ods_credit_overdue`
- `ods_credit_repayment_actual`
- `ods_credit_repayment_plan`
- `ods_csm_ticket`
- `ods_events_app_event`
- `ods_finance_gl_journal`
- `ods_funding_share`
- `ods_funding_split`
- `ods_intake_application`
- `ods_marketing_ad_cost`
- `ods_marketing_attribution`
- `ods_risk_decision`

## 作用

**贴源层**：几乎 1:1 复制业务系统数据。带 `ods_stat_date` 字段支持批次增量。

## 与其他文件的关系

- 完整 DDL 也在 `../schema.sql`（本文件是从中拆出的分层视图）
- ETL 逻辑：`../etl/ods_transform.sql` 或 `../etl.py`
