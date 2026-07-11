# ADS 层

DDL 文件：`ads_tables.sql`

包含 5 张表：

- `ads_credit_daily_dashboard`
- `ads_finance_daily_dashboard`
- `ads_marketing_roi_daily`
- `ads_operation_daily`
- `ads_risk_daily_dashboard`

## 作用

**应用层**：面向具体报表/驾驶舱的定制表。

## 与其他文件的关系

- 完整 DDL 也在 `../schema.sql`（本文件是从中拆出的分层视图）
- ETL 逻辑：`../etl/ads_transform.sql` 或 `../etl.py`
