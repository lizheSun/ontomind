# DWS 层

DDL 文件：`dws_tables.sql`

包含 11 张表：

- `dws_credit_channel_day`
- `dws_credit_customer_day`
- `dws_credit_loan_day`
- `dws_credit_overdue_day`
- `dws_credit_product_day`
- `dws_csm_ticket_day`
- `dws_customer_active_day`
- `dws_finance_income_day`
- `dws_funding_partner_month`
- `dws_marketing_channel_day`
- `dws_risk_grade_day`

## 作用

**汇总层**：按主题按粒度（day/month）聚合，直接支撑指标计算。

## 与其他文件的关系

- 完整 DDL 也在 `../schema.sql`（本文件是从中拆出的分层视图）
- ETL 逻辑：`../etl/dws_transform.sql` 或 `../etl.py`
