# ETL 脚本目录

## 生产入口

Python 脚本 `../etl.py` 是一键跑通所有层的入口（推荐执行方式）：

```bash
python3 dwh/etl.py
```

## 分层 SQL 文件

从 `etl.py` 抽出的分层 SQL，方便按需查看/调试：

- `ods_transform.sql`  业务库 → ODS
- `dim_transform.sql`  维度装载（含 SCD Type 2 客户维）
- `dwd_transform.sql`  ODS + 维度打宽 → 明细事实
- `dws_transform.sql`  按主题聚合
- `ads_transform.sql`  应用集市

## 依赖顺序

```
dim ← 独立
ods ← 业务库
dwd ← ods + dim
dws ← dwd
ads ← dws + dwd
```

`etl.py` 中已按此顺序执行；单独跑 SQL 文件时请遵循同样顺序。

## 模板变量

SQL 中的占位符（生产用调度器填充）：
- `${today}` — 抽数日期（默认 `2025-07-01`）
- `${date}` — 统计日期（如 `2025-06-15`）
- `${month}` — 统计月份（如 `202506`）
