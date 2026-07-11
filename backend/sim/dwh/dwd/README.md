# DWD 层

DDL 文件：`dwd_tables.sql`

包含 11 张表：

- `dwd_credit_application`
- `dwd_credit_collection`
- `dwd_credit_decision`
- `dwd_credit_loan`
- `dwd_credit_overdue`
- `dwd_credit_repayment`
- `dwd_csm_ticket`
- `dwd_events_app_event`
- `dwd_finance_gl_journal`
- `dwd_marketing_ad_cost`
- `dwd_marketing_attribution`

## 作用

**明细事实层**：清洗后的明细粒度事实表，冗余打宽常用维度字段。

## 与其他文件的关系

- 完整 DDL 也在 `../schema.sql`（本文件是从中拆出的分层视图）
- ETL 逻辑：`../etl/dwd_transform.sql` 或 `../etl.py`
