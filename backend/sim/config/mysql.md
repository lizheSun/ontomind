## MySQL 本地连接配置

- 主机：`127.0.0.1`
- 端口：`3306`
- 用户：`root`
- 密码：（空）
- 客户端：`mysql -u root`

## 数据库清单

| # | 库名 | 系统 | 归属域 |
|---|---|---|---|
| 1 | `sim_cust_cif` | 客户中心 | 客户 |
| 2 | `sim_loan_intake` | 进件受理 | 进件 |
| 3 | `sim_risk_decision` | 风险决策 | 风险 |
| 4 | `sim_credit_core` | 信贷核心 | 信贷 |
| 5 | `sim_collection` | 催收 | 信贷 |
| 6 | `sim_funding` | 资金/合作方 | 资金 |
| 7 | `sim_finance` | 财务 | 财务 |
| 8 | `sim_marketing` | 营销 | 营销 |
| 9 | `sim_events` | 埋点收集 | 数据平台 |
| 10 | `sim_csm` | 客服 | 运营 |
| 11 | `sim_hr_iam` | HR & 权限 | 内控 |
| 12 | `sim_dp_meta` | 元数据 | 数据平台 |
| 13 | `sim_dw` | 数据仓库 | — |

## 公共约定

- 公司：**信优消费金融有限公司** (Sim Consumer Finance)
- 产品：信优速贷 (SELF_LOAN)、信优合作贷 (PLATFORM_LOAN)、信优联合贷 (JOINT_LOAN)、信优保贷 (GUARANTEE_LOAN)
- 时间：数据跨度 `2025-01-01` ~ `2025-06-30`；"当前时间" `2025-07-01`
- 客户 ID：`C` + 8 位数字
- 敏感数据全部虚构，每条业务记录带 `is_test_data=1`
