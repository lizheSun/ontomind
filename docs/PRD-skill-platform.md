# PRD：Skill 可视化设计 & 统一管理平台

> **版本**：v1.0.0
> **日期**：2026-08-04
> **状态**：已评审（3 项关键决策已确认），进入实现
> **前置**：本平台是 [PRD-agent-skill-platform.md](./PRD-agent-skill-platform.md) 的扩展，复用其已验证的渲染/校验/发布管道

---

## 0. 一句话

把内部 AI Agent Skill 体系（原子技能 + 组合编排技能、8 大核心模块）从「零散配置文件 + 线下文档手工维护」
升级为**一站式可视化平台**，覆盖设计→调试→版控→灰度→运维→归档全生命周期，
同时保证产出物 **100% 符合 OpenCode 原生 Skill 加载规范**。

---

## 1. 关键实测发现（决定整个架构，务必先读）

在真实 OpenCode 容器（**v1.18.12**）上做了两组探针实验：

| 实验 | 构造 | 结果 |
|---|---|---|
| **A** | frontmatter 顶层塞 `risk_level` / `owner` / `qps_limit` | ✅ skill **正常加载**；这些字段被 **静默忽略** |
| **B** | 同样信息放进 `metadata:` 子映射 | ✅ 正常加载，字段 **保留在文件中** |

复核官方文档 + `opencode.ai/config.json`：**SKILL.md frontmatter 只认 5 个字段**

```
name (必填) · description (必填) · license · compatibility · metadata (string→string)
```

### 由此推出的核心矛盾

> 硬性约束 1 要求「导出**合规**的 SKILL.md」
> 模块 1–7 需要 40+ 个 OpenCode **不认识**的治理字段（风险等级/QPS/熔断/RBAC/AK-SK/Trace…）

若把治理字段硬塞进 frontmatter：产出物**不合规**，且这些配置**永远不会生效** ——
用户以为配了限流，实际没有。**这是必须在架构层解决的安全隐患，不是实现细节。**

---

## 2. 架构决策：双平面（Control Plane / Data Plane 分离）

```
┌──────────────────────────────────────────────────────────────────┐
│  治理平面 Control Plane（平台自有）                                 │
│  MySQL 存全量治理配置 · 平台 Skill 网关强制执行                      │
│                                                                   │
│   鉴权(RBAC) → 限流(QPS/会话频次) → 入参校验(JSON Schema)           │
│   → 执行(三形态) → 熔断降级 → 出参脱敏/字段过滤 → 会话变量写入        │
│   → Trace 落库 → 指标聚合 → 告警                                   │
└──────────────────────────────────────────────────────────────────┘
                        ↕ 同一份 Skill 定义（单一数据源）
┌──────────────────────────────────────────────────────────────────┐
│  执行平面 Data Plane（OpenCode 原生，文件为真）                      │
│  SKILL.md（仅 5 合法字段）+ references/ + scripts/                  │
│  → 100% 合规，OpenCode 直接加载                                    │
└──────────────────────────────────────────────────────────────────┘
```

### 三条落地规则

| 规则 | 做法 | 依据 |
|---|---|---|
| **合规兜底** | frontmatter 只输出 5 合法字段，治理字段**绝不出现在顶层** | 实验 A：顶层非法字段被静默忽略 |
| **可追溯** | 治理摘要以 `metadata.omd_*` 导出（如 `omd_risk_level: high`）；`omd_` 前缀避免与未来官方字段冲突 | 实验 B：metadata 内容会保留 |
| **强制执行** | 治理语义由**平台 Skill 网关**在调用链上执行，不依赖 OpenCode | 唯一可靠路径 |

### 导出包结构

```
<导出根>/
├── .opencode/skills/<skill-name>/     ← 项目级（约束 2）
│   ├── SKILL.md                       ← 100% 合规，5 字段
│   ├── references/*.md                ← 渐进披露
│   └── scripts/*                      ← 0o755
└── _ontomind/                         ← 治理平面产物，在 OpenCode 扫描路径**之外**
    ├── skill.manifest.json            ← 治理全量配置（含 Schema、执行、策略）
    └── README.md                       ← 部署说明
```

> 全局级导出时路径换成 `~/.config/opencode/skills/<skill-name>/`（约束 2）。
> `_ontomind/` 刻意放在 skills 之外 —— 否则会被 OpenCode 当成一个 skill 目录扫描。

---

## 3. 页面菜单结构

沿用现有「Agent 工厂」导航，Skill 部分升级为**独立二级菜单**：

```
Skill 平台  /skill-platform
├── ① 设计器      /skill-platform/design        模块 1+2+3（三段式：元数据 / 契约 / 执行）
├── ② 治理策略    /skill-platform/governance    模块 4+5（容错熔断 / 安全权限）
├── ③ 版本与发布  /skill-platform/release       模块 6（快照/回滚/灰度/审计）
├── ④ 观测大盘    /skill-platform/observe       模块 7（指标/Trace/告警）
└── ⑤ 技能广场    /skill-platform/market        模块 8（复用克隆）
```

**为什么模块 1/2/3 合成一个「设计器」**：三者是同一个 Skill 的三个切面，
分成三个页面会让用户反复跳转、丢失上下文。用**分段导航 + 右侧常驻产物预览**更顺。

---

## 4. 数据模型（新增 9 表，13 → 22）

复用现有 `skill_templates` / `skill_files` 作为**定义主体**（已验证可被 OpenCode 加载），
在其上扩展治理表。

```
skill_templates ─┬─< skill_files                    （已有）SKILL.md 正文 + 附属文件
                 ├─── skill_meta                    ① 治理元数据（1:1）
                 ├─< skill_params                   ② 入参/出参 Schema
                 ├─── skill_exec_prompt             ③ Prompt 型执行配置（1:1）
                 ├─── skill_exec_api                ③ API 型执行配置（1:1）
                 ├─< skill_exec_flow_nodes          ③ 编排型流程节点
                 ├─── skill_policy                  ④+⑤ 容错熔断 + 安全权限（1:1）
                 ├─< skill_versions                 ⑥ 配置快照
                 ├─< skill_audit_logs               ⑥ 变更审计
                 └─< skill_invocations              ⑦ 调用 Trace
```

### 4.1 `skill_meta` — 模块 1 治理元数据

| 字段 | 类型 | 说明 |
|---|---|---|
| `skill_template_id` | FK uniq | 1:1 |
| `skill_kind` | enum | `prompt` / `api` / `flow`（三形态，约束 4）|
| `name_zh` / `name_en` | varchar | 中英文名 |
| `biz_tags_json` | JSON | 业务标签 |
| `risk_level` | enum | `low`(低危查询) / `medium` / `high`(高危资金操作) |
| `owner` / `owner_email` | varchar | 责任人 |
| `biz_line` | varchar | 归属业务线 |
| `qps_limit` | int | 限流 QPS |
| `session_call_limit` | int | 单会话调用频次上限 |
| `lifecycle` | enum | `draft`→`testing`→`canary`→`released`→`frozen`→`archived` |
| `lifecycle_note` | varchar | 状态变更说明 |

### 4.2 `skill_params` — 模块 2 参数契约

| 字段 | 说明 |
|---|---|
| `skill_template_id` FK · `direction` enum(`in`/`out`) | 入参 / 出参 |
| `name` · `data_type`(string/number/integer/boolean/object/array) · `title` · `description` | 基础 |
| `required` bool · `default_value` · `enum_json` · `regex_pattern` · `min_val`/`max_val` | 校验 |
| `source` enum | `dialog`(对话抽取) / `context`(会话上下文) / `system`(系统内置) / `const` |
| `context_key` | source=context 时读哪个会话变量 |
| `mask_rule` enum | `none`/`phone`/`idcard`/`bankcard`/`email`/`all`/`custom` |
| `mask_pattern` | 自定义脱敏正则 |
| `write_to_context` · `context_write_key` | 出参写回会话上下文 |
| `filtered` bool | 出参字段过滤（不返回给模型）|
| `sort_order` | 排序 |

> 出参固定外壳 `{code, msg, data, session_vars}`（需求指定），
> `skill_params(direction=out)` 描述的是 `data` 内部结构。

### 4.3 `skill_exec_prompt` — 模块 3 Prompt 推理型

`system_prompt` LONGTEXT · `few_shots_json`（[{input,output}]）· `output_constraint` ·
`output_format` enum(`text`/`json`/`markdown`) · `temperature` · `max_tokens`

### 4.4 `skill_exec_api` — 模块 3 API 调用型

| 字段 | 说明 |
|---|---|
| `http_method` enum | GET/POST/PUT/DELETE/PATCH |
| `url_test` / `url_staging` / `url_prod` | **多环境隔离**（需求明确）|
| `headers_json` | 静态请求头 |
| `auth_type` enum | `none`/`bearer`/`ak_sk`/`api_key`/`basic` |
| **`secret_ref`** | **配置中心引用键**，如 `cc://skill/pay-query/aksk`（约束 5：禁明文）|
| `param_mapping_json` | 入参 → 请求字段映射 |
| `timeout_ms` · `retry_times` · `retry_backoff_ms` | 超时重试 |
| `success_path` / `data_path` | 响应取值 JSONPath |

> ⚠️ **约束 5 落地**：表里**没有**明文密钥列。只存 `secret_ref`，
> 校验器会拒绝任何形如 `AKIA...`/`sk-...`/长 base64 的疑似明文（见 §6）。

### 4.5 `skill_exec_flow_nodes` — 模块 3 编排型

`node_key` · `node_type` enum(`start`/`skill`/`branch`/`loop`/`end`) ·
`ref_skill_id` FK · `condition_expr` · `loop_config_json` ·
`var_mapping_json`（上下游变量透传）· `on_fail_next`（失败跳转）·
`next_keys_json` · `pos_x`/`pos_y`（画布坐标）

### 4.6 `skill_policy` — 模块 4 + 5

**容错熔断**：`timeout_ms` · `retry_times` · `circuit_threshold`(失败率%) ·
`circuit_window_sec` · `circuit_cooldown_sec` · `fallback_mode` enum(`none`/`static`/`skill`/`prompt`) ·
`fallback_payload` · `error_map_json`（错误码 → 用户友好话术）

**安全权限**：`allowed_agents_json` · `allowed_roles_json`（RBAC）·
`require_confirm` bool（高危二次确认）· `account_whitelist_json` · `account_blacklist_json` ·
`ctx_read_keys_json` / `ctx_write_keys_json`（会话变量读写权限）· `session_isolation` enum

### 4.7 `skill_versions` — 模块 6

`skill_template_id` FK · `version` · `snapshot_json`（**全配置快照**，含以上所有表）·
`change_note` · `lifecycle_at_snapshot` · uniq(`skill_template_id`,`version`)

`canary_json`：`{mode: 'percent'|'whitelist', percent: 10, accounts: [...]}`

### 4.8 `skill_audit_logs` — 模块 6

`skill_template_id` · `action` · `field_path` · `before_json` / `after_json` ·
`operator_user_id` · `operator_name` · `ip` · `created_at`

### 4.9 `skill_invocations` — 模块 7 Trace

`trace_id` uniq · `skill_template_id` · `skill_name` · `agent_name` · `session_id` ·
`account_id` · `env` · `status` enum(`success`/`param_error`/`network_error`/`service_error`/`timeout`/`circuit_open`/`denied`) ·
`error_code` · `error_msg` · `input_json`(脱敏后) · `output_json`(脱敏后) ·
`duration_ms` · `retry_count` · `fallback_used` · `created_at`

---

## 5. 各模块交互逻辑

### 模块 1 元数据（设计器 · 段 1）

- 左列表（按业务线/风险等级/生命周期筛选）｜右三段导航
- **形态选择器**置顶（`prompt`/`api`/`flow`）—— 决定段 3 渲染哪个面板（约束 4）
- 风险等级选 `high` 时：自动勾上「高危二次确认」并给出提示
- **生命周期流转**：只允许合法迁移，非法路径按钮置灰
  ```
  draft → testing → canary → released → frozen → archived
                                 ↑__________↓（frozen 可回 released）
  archived 为终态；任意状态可 → archived
  ```
- 右侧常驻 **SKILL.md 实时预览**（后端渲染，与落盘完全一致）

### 模块 2 参数契约（设计器 · 段 2）

- 入参 / 出参分两个 Tab，行式增删（复用既有 `ContainerConfigEditor` 范式）
- 每行：名称 · 类型 · 必填 · 默认值 · 枚举 · 正则 · 来源 · 脱敏 · 写回上下文
- **实时生成 JSON Schema 预览**（右侧）
- **在线调试**：填入参样例 → 按 Schema 校验 → 显示逐字段结果（不真正调用）
- 出参外壳固定展示 `{code,msg,data,session_vars}`，用户只编辑 `data` 结构

### 模块 3 执行逻辑（设计器 · 段 3，按形态差异化）

| 形态 | 面板内容 |
|---|---|
| **Prompt** | 系统提示词（带模板按钮）· Few-shot 列表（input/output 对）· 输出约束 · 格式/温度 |
| **API** | 方法 + 三环境 URL（带环境切换）· 请求头 · 鉴权方式 · **密钥引用键**（明文即拦截）· 参数映射 · 超时重试 · 响应取值路径 |
| **Flow** | SVG 流程图（复用 `LoopTopology` 的绘制经验）· 节点面板（原子 Skill / 分支 / 循环）· 变量透传映射 · 失败跳转 |

### 模块 4–8（本轮出设计与表结构，实现排后期）

- **模块 4**：三类异常（参数/网络/服务）统一映射面板；熔断阈值滑块 + 冷却时间；降级四选一
- **模块 5**：RBAC 多选（智能体 / 角色）· 脱敏规则表 · 黑白名单 · 会话变量读写勾选矩阵
- **模块 6**：版本时间线（快照 diff）· 一键回滚 · 灰度配置（比例/白名单）· 审计日志表
- **模块 7**：指标卡（QPS/耗时/成功率）· 失败类型分布 · Trace 查询表 + 详情抽屉 · 告警阈值
- **模块 8**：卡片广场（仅 `lifecycle=released`）· 一键克隆（复制全配置，`name` 追加 `-copy`，状态回 `draft`）

---

## 6. 校验规则（实时拦截，非功能要求 2）

| # | 规则 | 级别 | 依据 |
|---|---|---|---|
| 1 | `name` 必须 kebab-case `^[a-z0-9]+(-[a-z0-9]+)*$`，1–64 | **error** | 约束 3 |
| 2 | 目录名 == `name` | **error** | 约束 3 |
| 3 | `description` 1–1024 | **error** | OpenCode 限制 |
| 4 | `metadata` 值必须 string | **error** | OpenCode 限制 |
| 5 | 附属文件路径禁 `..` / 绝对路径 / 与 SKILL.md 重名 | **error** | 路径穿越 |
| 6 | **`secret_ref` 疑似明文密钥**（`AKIA`/`sk-`/`ghp_`/长 hex/长 base64）| **error** | 约束 5 |
| 7 | `auth_type != none` 时 `secret_ref` 必填 | **error** | 约束 5 |
| 8 | `risk_level=high` 但未开二次确认 | warning | 风控 |
| 9 | 生命周期非法迁移（如 draft → released）| **error** | 模块 1 |
| 10 | `lifecycle >= canary` 但缺 owner / 出参 Schema | **error** | 上线门禁 |
| 11 | 参数名重复 / 非法标识符 | **error** | Schema |
| 12 | `enum` 与 `data_type` 不匹配 | **error** | Schema |
| 13 | `regex_pattern` 非法正则 | **error** | Schema |
| 14 | Flow 有环 / 存在孤立节点 / 无 start-end 通路 | **error** | 编排 |
| 15 | Flow 引用了未上线（非 released）的 Skill | warning | 依赖 |
| 16 | API 型缺生产环境 URL 但 `lifecycle=released` | **error** | 上线门禁 |
| 17 | 正文 > 400 行且无 references | warning | 渐进披露 |

---

## 7. 标准 SKILL.md 模板样例

平台导出的 **合规产物**（治理配置只以 `omd_*` 摘要形式出现在 metadata）：

```markdown
---
name: pay-order-query
description: 查询支付订单状态与明细。当用户询问订单是否支付成功、支付金额、支付时间或需要核对交易流水时使用。
license: MIT
compatibility: opencode
metadata:
  omd_skill_kind: api
  omd_risk_level: high
  omd_owner: sunleone
  omd_biz_line: payment
  omd_lifecycle: released
  omd_version: "7"
  omd_qps_limit: "50"
  omd_require_confirm: "true"
  omd_manifest: _ontomind/skill.manifest.json
---

# 支付订单查询

## 我做什么
- 按订单号 / 商户单号查询支付状态、金额、渠道、支付时间
- 返回标准化结构，敏感字段（银行卡号、手机号）已脱敏

## 何时用我
用户询问「订单支付成功了吗」「这笔钱到账没」「帮我查下流水」时。
**高危技能**：涉及资金信息，调用前需用户二次确认。

## 入参
| 参数 | 类型 | 必填 | 来源 | 说明 |
|---|---|---|---|---|
| `order_no` | string | 是 | 对话抽取 | 订单号，18 位数字 |
| `merchant_id` | string | 否 | 会话上下文 | 商户号，默认取当前会话商户 |

## 出参
`{code, msg, data, session_vars}`；`data` 含 `status` / `amount` / `channel` / `paid_at`。

## 边界与禁止
- 只读查询，**不做任何资金操作**
- 查不到订单时明确告知，不要编造
- 不要在回复里输出完整银行卡号

> 错误码对照与降级话术见 [references/error-codes.md](references/error-codes.md)。
> 多环境地址与鉴权见治理清单 `_ontomind/skill.manifest.json`（不含明文密钥）。
```

---

## 8. 分阶段落地

| 阶段 | 内容 | 验收 |
|---|---|---|
| **P1** 数据与规则 | 9 表 + schema + 校验器（17 规则）+ 双平面渲染器 | 单测覆盖全部规则；导出物经容器实测可被 OpenCode 加载 |
| **P2** 服务与接口 | CRUD + 生命周期流转 + 快照/回滚 + 导出打包 + 克隆 | curl 全端点通；导出 zip 结构符合约束 2 |
| **P3** 设计器（模块 1-3）| 三段式设计器 + 三形态面板 + Schema 编辑器 + 实时预览 | Playwright 全链路；违规实时拦截 |
| **P4** 治理页（模块 4-5）| 容错熔断 + 安全权限配置页 | 配置落库并出现在 manifest |
| **P5** 网关（治理生效）| Skill 调用网关：鉴权→限流→校验→执行→熔断→脱敏→Trace | 限流/熔断/脱敏可实测触发 |
| **P6** 版控与观测（模块 6-7）| 灰度 + 审计 + 指标大盘 + Trace 查询 + 告警 | 有真实调用数据后大盘非空 |
| **P7** 广场（模块 8）| 克隆复用 | 一键克隆产出可用草稿 |

> **本轮交付 P1 + P2 + P3**（含 PRD）。P4–P7 出设计与表结构，实现排后。
> P5 是治理真正生效的关键，建议紧随其后 —— 否则模块 4/5 的配置只是「记录」而非「管控」。

---

## 9. 相比原手工模式的收益

| 维度 | 原手工模式 | 平台化后 | 收益 |
|---|---|---|---|
| **新建 Skill** | 手写 SKILL.md + 散配置文件 + 线下文档，易漏字段 | 表单填写 + 实时校验 + 一键导出 | 从 ~2h → **~15min**；格式错误**归零**（17 条规则前置拦截）|
| **配置一致性** | 配置碎片化，文档与实际漂移 | MySQL 单一数据源，导出物由渲染器生成 | 消除漂移 |
| **规范合规** | 靠人记 kebab-case、目录规范 | 违规实时拦截，无法保存 | 不合规产出**归零** |
| **版本管控** | 无，改坏了不知道改了什么 | 全配置快照 + 一键回滚 + 变更审计 | 回滚从「翻 git/凭记忆」→ **一次点击** |
| **多环境切换** | 手改配置文件，易把测试地址发到生产 | 三环境字段隔离 + 上线门禁校验 | 环境串号风险**归零** |
| **密钥安全** | 明文散落在配置文件 | 只存配置中心引用键，明文即拦截 | 满足约束 5，**杜绝明文入库** |
| **权限配置** | 无统一管控，靠约定 | RBAC 可视化绑定 + 黑白名单 + 二次确认 | 高危技能有强制闸门 |
| **故障排查** | 翻多处日志拼链路 | Trace 一次查询看全链（入参/出参/耗时/错误）| 定位从「小时级」→ **分钟级** |
| **复用** | 复制粘贴，各自演化 | 广场一键克隆已验收技能 | 减少重复开发 |
| **双角色协作** | 研发改文件，运营看不懂 | 运营配元数据/话术，研发配执行逻辑 | 分工清晰，无需研发代改 |

---

## 10. 明确不做（本轮）

- Skill 效果评测 / A-B
- 跨租户多团队隔离（沿用现有登录鉴权）
- 从 Git 直接导入 Skill 仓库（预留 `source`）
- 实时流式 Trace（先落库后查询）
- 网关的分布式限流（P5 先做单实例，后续接 Redis）

---

## 11. 附录：与 Agent 工厂的关系

| 能力 | 归属 | 说明 |
|---|---|---|
| Skill 定义（SKILL.md 正文、多文件） | **复用** `skill_templates` / `skill_files` | 已实测可被 OpenCode 加载 |
| 渲染器 / 校验器 / 发布管道 | **复用** `agent_render_service` 等 | 已实测发布到容器 3/3 校验通过 |
| 治理配置（本 PRD 9 表） | **新增** | Agent 工厂不涉及 |
| 编排方案（Agent Loop） | Agent 工厂 | Skill 平台的 `flow` 形态是**技能内部**编排，与 Agent 间编排不同层 |
