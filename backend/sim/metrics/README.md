# 信优消费金融 指标体系

## 总览

- 指标总数：**200**
- 领域：8 个（用户/信贷/财务/风险/营销/经营管理/资金/合规）
- 分级：一级 40 / 二级 70 / 三级 90

## 目录

```
metrics/
├── governance/              治理办法
│   ├── 01_管理办法.md
│   ├── 02_命名规范.md
│   ├── 03_口径管理.md
│   └── 04_分级分类.md
├── catalog/                 指标目录（本体数据字典）
│   ├── metrics.yaml         结构化（Data Agent 消费）
│   └── metrics.md           可读版
└── domains/                 分领域 + 分部门
    ├── user_domain.md
    ├── credit_domain.md
    ├── finance_domain.md
    ├── risk_domain.md
    ├── marketing_domain.md
    ├── operation_domain.md
    ├── funding_domain.md
    ├── compliance_domain.md
    └── departments/
        ├── risk_mgmt.md
        ├── finance.md
        ├── self_credit_product.md
        ├── platform_product.md
        ├── profit_share_product.md
        └── marketing.md
```

## 快速验证一个指标

```bash
mysql -u root sim_dw -e "
  SELECT stat_date, COUNT(DISTINCT customer_id) AS dau
  FROM dws_customer_active_day
  WHERE stat_date = '2025-06-15'
  GROUP BY stat_date"
```

## 本体化设计

- `metrics.yaml` 每个条目就是一个本体实体
- `aliases` 提供同义词表（NL2SQL 消歧关键）
- `sql_template` 是从语义到物理的映射
- `related_metrics` 建立概念间关联
- `filters` 显式化口径过滤
