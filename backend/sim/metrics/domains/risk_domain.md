# 风险域 指标

> 关注逾期率、Vintage、反欺诈

共 **31** 个指标。

## 一级指标（5 个）

| ID | 中文 | 英文 | 定义 | 责任部门 |
|---|---|---|---|---|
| M0066 | M1 逾期率 | `overdue_rate_m1` | M1 及以上逾期借据数 / 总借据数 | 风险管理部 |
| M0067 | M3 逾期率 | `overdue_rate_m3` | M3 及以上逾期借据数 / 总借据数 | 风险管理部 |
| M0069 | 首期逾期率 | `first_overdue_rate` | 第一期出现逾期的借据占比 | 风险管理部 |
| M0070 | 逾期金额 | `overdue_amount` | 所有活跃逾期的应还未还本金合计 | 风险管理部 |
| M0083 | 坏客户率 | `bad_customer_rate` | 坏客户率（详见风险管理办法） | 风险管理部 |

## 二级指标（14 个）

| ID | 中文 | 英文 | 定义 | 责任部门 |
|---|---|---|---|---|
| M0068 | M2 逾期率 | `overdue_rate_m2` | M2 及以上逾期占比 | 风险管理部 |
| M0071 | A 级客户数 | `grade_a_customer_count` | 风险等级=A 的当前客户数 | 风险管理部 |
| M0072 | B 级客户数 | `grade_b_customer_count` | 风险等级=B 的当前客户数 | 风险管理部 |
| M0073 | C 级客户数 | `grade_c_customer_count` | 风险等级=C 的当前客户数 | 风险管理部 |
| M0074 | D 级客户数 | `grade_d_customer_count` | 风险等级=D 的当前客户数 | 风险管理部 |
| M0075 | E 级客户数 | `grade_e_customer_count` | 风险等级=E 的当前客户数 | 风险管理部 |
| M0076 | 反欺诈拦截数 | `antifraud_hit_count` | 当日反欺诈规则拦截的申请数 | 风险管理部 |
| M0078 | 黑名单命中数 | `blacklist_hit_count` | 决策日志中命中黑名单的次数 | 风险管理部 |
| M0079 | Vintage MOB3 逾期率 | `vintage_mob3_overdue_rate` | 放款后 3 个月的逾期率（按放款月分组） | 风险管理部 |
| M0081 | 模型 KS | `model_ks` | 模型 KS（详见风险管理办法） | 风险管理部 |
| M0082 | 模型 PSI | `model_psi` | 模型 PSI（详见风险管理办法） | 风险管理部 |
| M0084 | M1 催回率 | `recovery_rate_m1` | M1 催回率（详见风险管理办法） | 风险管理部 |
| M0085 | M2 催回率 | `recovery_rate_m2` | M2 催回率（详见风险管理办法） | 风险管理部 |
| M0086 | M3 催回率 | `recovery_rate_m3` | M3 催回率（详见风险管理办法） | 风险管理部 |

## 三级指标（12 个）

| ID | 中文 | 英文 | 定义 | 责任部门 |
|---|---|---|---|---|
| M0077 | 反欺诈事件数 | `antifraud_event_count` | 当日触发的所有反欺诈事件 | 风险管理部 |
| M0080 | 模型分均值 | `model_score_avg` | 模型分均值（详见风险管理办法） | 风险管理部 |
| M0087 | 催收案件数 | `collection_case_count` | 催收案件数（详见风险管理办法） | 风险管理部 |
| M0088 | 催收动作数 | `collection_action_count` | 催收动作数（详见风险管理办法） | 风险管理部 |
| M0089 | 承诺兑现率 | `ptp_fulfillment_rate` | 承诺兑现率（详见风险管理办法） | 风险管理部 |
| M0090 | 拒绝原因 TOP1 | `rejection_reason_top1` | 拒绝原因 TOP1（详见风险管理办法） | 风险管理部 |
| M0091 | 共享设备数 | `device_share_count` | 共享设备数（详见风险管理办法） | 风险管理部 |
| M0178 | A 级客户放款金额 | `disburse_amount_grade_a` | 当前风险等级=A 的客户放款额 | 风险管理部 |
| M0179 | B 级客户放款金额 | `disburse_amount_grade_b` | 当前风险等级=B 的客户放款额 | 风险管理部 |
| M0180 | C 级客户放款金额 | `disburse_amount_grade_c` | 当前风险等级=C 的客户放款额 | 风险管理部 |
| M0181 | D 级客户放款金额 | `disburse_amount_grade_d` | 当前风险等级=D 的客户放款额 | 风险管理部 |
| M0182 | E 级客户放款金额 | `disburse_amount_grade_e` | 当前风险等级=E 的客户放款额 | 风险管理部 |


## 完整定义

参见 `../catalog/metrics.yaml`。
