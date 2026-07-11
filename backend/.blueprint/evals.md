# Blueprint Self-Evals Rules

> Orchestrator 每完成一个 Task 后，按本规则自我审查。全部通过才进下一 Task；任何 CRITICAL 未过必须停下报告用户。

## 通用规则（每个 Task 都要过）

| # | 规则 | 级别 | 检查方式 |
|---|---|---|---|
| G1 | 输出目录结构与 plan.md 一致 | CRITICAL | `find backend/sim -type d` 比对 |
| G2 | 每个产出目录都有 README.md | HIGH | `find backend/sim -type d ! -path '*seed_data*' ! -path '*__pycache__*' -exec test -e {}/README.md \; -print` |
| G3 | 所有 SQL 文件可解析（无语法错） | CRITICAL | `mysql --dry-run` 或用 sqlparse 静态检查 |
| G4 | 所有 Python 脚本可 import 无报错 | CRITICAL | `python -c "import ast; ast.parse(open(f).read())"` |
| G5 | 涉及敏感数据字段都带 `is_test_data` 标记或明确"虚构"注释 | HIGH | grep 检查 |
| G6 | 文档中提到的表名/字段名 100% 与 schema 对齐 | HIGH | 从 md 抽表名对照 schema |

## Task 01 专属：业务系统 + 种子数据

| # | 规则 | 级别 |
|---|---|---|
| T1.1 | `mysql -u root -e "SHOW DATABASES LIKE 'sim_%'"` 返回 12 行 | CRITICAL |
| T1.2 | 12 库合计表数在 60–70 之间 | HIGH |
| T1.3 | 客户表数量 = 10,000 ± 5% | HIGH |
| T1.4 | 授信申请数在 14k–16k | HIGH |
| T1.5 | 放款数在 7.5k–8.5k | HIGH |
| T1.6 | 授信通过率在 40–55% | HIGH |
| T1.7 | 支用率（授信 30 天内放款）在 55–65% | HIGH |
| T1.8 | M1 逾期率在 3–5%，M3 在 1–1.5% | HIGH |
| T1.9 | 客户年龄分布均值 33 ±2，σ 8 ±1 | MEDIUM |
| T1.10 | 时间戳递增：申请 < 决策 < 放款 < 还款计划开始日 | CRITICAL |
| T1.11 | 4 种产品形态（自营/助贷/联合贷/担保）都有数据，占比 40/30/20/10 (±10%) | HIGH |
| T1.12 | 埋点事件量 500k ±10% | MEDIUM |
| T1.13 | 跨库外键 join 命中率 > 98%（customer_id 在 CIF 和 credit_core 之间） | CRITICAL |
| T1.14 | 每个系统有 README.md + schema.sql + seed.py | CRITICAL |

## Task 02 专属：系统文档

| # | 规则 | 级别 |
|---|---|---|
| T2.1 | 每系统 4 份文档齐全（BRD/PRD/TDD/PROJECT），共 48 份 | CRITICAL |
| T2.2 | 重点 5 系统（CIF/进件/风控/信贷核心/财务）每份 ≥ 2000 字 | HIGH |
| T2.3 | 其余系统每份 ≥ 1200 字 | MEDIUM |
| T2.4 | 每系统 TDD 至少 1 张 mermaid 图（架构或 ER 或流程） | HIGH |
| T2.5 | 文档提到的字段名 100% 存在于 schema.sql | CRITICAL |
| T2.6 | 每份 PROJECT 有里程碑 + RACI + 风险登记 3 个必备章节 | MEDIUM |

## Task 03 专属：数据仓库

| # | 规则 | 级别 |
|---|---|---|
| T3.1 | `sim_dw` 库存在，表数 45–55 张 | CRITICAL |
| T3.2 | 分层齐全：ODS ≥ 15、DIM ≥ 6、DWD ≥ 10、DWS ≥ 10、ADS ≥ 5 | HIGH |
| T3.3 | 命名规范：`<layer>_<domain>_<entity>[_grain]` | HIGH |
| T3.4 | 每张 DW 表带 COMMENT，主要字段带 COMMENT | HIGH |
| T3.5 | `etl.py` 一键跑通，无 error | CRITICAL |
| T3.6 | 客户维度 SCD Type 2（有 valid_from/valid_to/is_current） | HIGH |
| T3.7 | `sample_queries.sql` 至少 10 个 SQL，全部返回 > 0 行 | HIGH |
| T3.8 | 与 sim_credit_core 的关键数据一致（DW 中放款金额 = 业务库放款金额 ±0.01） | CRITICAL |

## Task 04 专属：指标体系

| # | 规则 | 级别 |
|---|---|---|
| T4.1 | 4 份治理文档齐全（管理办法/命名规范/口径管理/分级分类） | CRITICAL |
| T4.2 | 指标总数 ≥ 200 | CRITICAL |
| T4.3 | 每个指标必须字段齐全（id/name_zh/definition/formula/source_tables/sql_template）| CRITICAL |
| T4.4 | 每个指标至少 2 个别名 | HIGH |
| T4.5 | **抽样 30 个指标**，`sql_template` 在 `sim_dw` 上跑得通，不报错 | CRITICAL |
| T4.6 | 6 领域文档齐全（用户/信贷/财务/风险/营销/经营） | CRITICAL |
| T4.7 | 6 部门文档齐全（风管/财务/自营/平台/分润/营销） | CRITICAL |
| T4.8 | 至少 30% 一级指标、40% 二级、30% 三级 | MEDIUM |
| T4.9 | 命名规范中的 20 个示例在 metrics.yaml 里都能找到 | MEDIUM |
| T4.10 | 指标 owner 全部指向 5 个部门之一 | MEDIUM |

## 报告格式（每个 Task 完后写到 `.blueprint/reviews/task-XX.md`）

```
# Review for Task XX

## Summary
- Started at: <ts>
- Finished at: <ts>
- Rules passed: X / Y

## Failed rules
| # | Rule | Level | Detail | Action |
|---|---|---|---|---|
...

## Deviations from plan
- ...

## Verdict
APPROVE | REQUEST_CHANGES | BLOCK
```

**BLOCK 情况**：任何 CRITICAL 未过 → 停下报告用户，等待 `/nudge` 或人工介入。
