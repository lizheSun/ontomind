# 数据仓库 sim_dw

> Kimball 星型建模。分层：ODS → DIM → DWD → DWS → ADS。

## 命名规范

`<layer>_<domain>_<entity>[_<grain>]`

- **layer**：`ods` / `dim` / `dwd` / `dws` / `ads`
- **domain**：`credit` / `risk` / `finance` / `marketing` / `csm` / `funding` / `events` / `cif` / `intake` 等
- **entity**：业务对象，如 `loan`、`application`、`customer`
- **grain**（可选）：粒度，如 `day` / `month`

例子：
- `ods_credit_loan` — 借据贴源
- `dim_customer` — 客户维度（SCD Type 2）
- `dwd_credit_loan` — 借据明细事实（打宽）
- `dws_credit_product_day` — 每日产品汇总
- `ads_credit_daily_dashboard` — 每日信贷驾驶舱

## 分层职责

| 层 | 职责 | 表数 |
|---|---|---|
| **ODS** | 贴源，几乎 1:1 复制业务库，带 `ods_stat_date` 支持增量 | 16 |
| **DIM** | 共享维度（客户/产品/日期/渠道/机构/资金方），客户走 SCD Type 2 | 6 |
| **DWD** | 明细事实，清洗 + 打宽维度（把常用维度字段冗余到事实表） | 11 |
| **DWS** | 主题汇总，按 天 / 月 粒度做核心聚合 | 11 |
| **ADS** | 应用集市，面向具体报表/驾驶舱 | 5 |

**共 49 张表**。

## 维度模型

**5 大共享维度**：
- `dim_customer`（客户，SCD2）
- `dim_product`（产品）
- `dim_date`（日期，182 天）
- `dim_channel`（渠道）
- `dim_org`（组织，19 个）
- `dim_funding_partner`（资金方，6 个）

**核心事实表**（明细粒度）：
- `dwd_credit_application`（申请）
- `dwd_credit_decision`（决策）
- `dwd_credit_loan`（借据）
- `dwd_credit_repayment`（还款流水）
- `dwd_credit_overdue`（逾期）
- `dwd_credit_collection`（催收）
- `dwd_marketing_attribution`（归因）
- `dwd_marketing_ad_cost`（广告成本）
- `dwd_finance_gl_journal`（凭证）
- `dwd_events_app_event`（埋点）
- `dwd_csm_ticket`（工单）

## ETL 一键跑通

```bash
mysql -u root sim_dw < schema.sql   # 建表
python3 etl.py                       # 抽数
```

**耗时**：< 30 秒（小规模数据）

## 数据规模（当前）

```bash
mysql -u root -e "
SELECT table_schema, table_name, table_rows
FROM information_schema.tables
WHERE table_schema='sim_dw'
ORDER BY table_rows DESC LIMIT 10"
```

Top 10：
- `dwd_events_app_event`: 42w
- `dws_customer_active_day`: 30w
- `dwd_credit_repayment`: 1.7w
- `dwd_credit_application`: 1.8w
- `dwd_finance_gl_journal`: 3.9w

## SCD Type 2 说明

`dim_customer` 使用 Type 2 缓慢变化维：
- `valid_from`、`valid_to` 记录版本有效期
- `is_current` 标识当前记录
- 首次装载全部 `is_current=1`
- 未来 SCD 变更时：老记录 `valid_to` = 变更前日期，`is_current=0`；新记录插入

## sample_queries.sql

见同目录 `sample_queries.sql`，10+ 个典型分析问题的 SQL。

## ETL 逻辑

见 `etl.py`。每层的 INSERT 逻辑均为标准 SQL，可读可改。ODS 用 `ods_stat_date` 支持增量批次。
