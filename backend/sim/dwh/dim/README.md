# DIM 层

DDL 文件：`dim_tables.sql`

包含 6 张表：

- `dim_channel`
- `dim_customer`
- `dim_date`
- `dim_funding_partner`
- `dim_org`
- `dim_product`

## 作用

**维度层**：共享维度（客户/产品/日期/渠道/机构/资金方）。客户走 SCD Type 2。

## 与其他文件的关系

- 完整 DDL 也在 `../schema.sql`（本文件是从中拆出的分层视图）
- ETL 逻辑：`../etl/dim_transform.sql` 或 `../etl.py`
