# PRD：OpenCode Agent / Skill 平台化管理

> **版本**：v1.0.0
> **日期**：2026-08-04
> **状态**：已评审，进入实现
> **目标读者**：本仓库后续 Agent / 开发者

---

## 0. 一句话

把 OpenCode 的 **Agent 设计（含 Agent Loop 编排模式）** 和 **Skill 设计** 从"手写散落文件"升级为
**平台化的模板管理 + 版本化 + 一键发布到 Docker 节点容器 + 发布后回读校验**，模板信息全部落 MySQL。

---

## 1. 背景与问题

现状：OpenCode 的 agent / skill 靠人手写文件散落在各处，导致

| 问题 | 具体表现 |
|---|---|
| 无沉淀 | 一个好用的 agent 写完只存在于某台机器的 `~/.config/opencode/agents/` |
| 无版本 | 改坏了没法回滚，也不知道上次改了什么 |
| 无复用 | 想在另一个容器用同一套 agent，只能手工 copy |
| 无编排视图 | "谁能调谁、能嵌几层、迭代上限多少" 散落在多个文件的多个字段里，看不到全貌 |
| **配置写错静默失效** | 权限键写错（如 `write` 而非 `edit`）OpenCode **直接忽略不报错**，极难排查 |
| 发布无凭证 | 文件 copy 过去了，但 OpenCode 到底认没认？没有校验手段 |

---

## 2. 研究结论（实证，非推测）

> 依据：OpenCode 官方文档 + `https://opencode.ai/config.json` 权威 JSON Schema
> + 对 `localhost:4096`（宿主 v1.18.4）与容器内 `serve`（v1.18.12）的**实机验证**。

### 2.1 Agent 定义机制

两条定义通道，**可共存**：

| 通道 | 位置 | 说明 |
|---|---|---|
| **Markdown** | `~/.config/opencode/agents/<name>.md`（全局）<br>`.opencode/agents/<name>.md`（项目） | **文件名即 agent 名**；YAML frontmatter + 正文 = system prompt |
| **JSON** | `opencode.json(c)` 的 `agent.<name>` | 结构化，适合批量 |

**权威字段**（`$defs.AgentConfig.properties`，无 required）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `mode` | `subagent` \| `primary` \| `all` | 默认 `all` |
| `description` | string | **必填（语义上）**，primary 依据它决定何时委派 subagent |
| `prompt` | string | 支持 `{file:./prompts/x.txt}` |
| `model` | string | `provider/model-id` |
| `temperature` | number | 0.0–1.0 |
| `top_p` | number | 0.0–1.0 |
| `steps` | integer | 迭代上限（`maxSteps` 已废弃） |
| `permission` | PermissionConfig | 见 2.2 |
| `tools` | object | **已废弃**，改用 `permission` |
| `hidden` | boolean | 藏起 `@` 补全，仍可被 Task 调用 |
| `disable` | boolean | 禁用 |
| `color` | `^#[0-9a-fA-F]{6}$` 或 `primary\|secondary\|accent\|success\|warning\|error\|info` | |
| `variant` | string | |
| `options` | object | 透传给 provider（如 `reasoningEffort`） |

### 2.2 权限系统（平台校验的重点）

**15 个合法权限键**，其余键被 **静默忽略**：

```
read  edit  glob  grep  list  bash  task  external_directory
todowrite  question  webfetch  websearch  lsp  doom_loop  skill
```

- 动作三态：`allow` | `ask` | `deny`
- **10 个键支持 glob→动作 细粒度映射**：
  `read edit glob grep list bash task external_directory lsp skill`
  其余 5 个（`todowrite question webfetch websearch doom_loop`）**只接受简写动作**
- **最后匹配规则胜出** → `"*"` 必须写在最前面

实测确认（写入容器后 `GET /agent` 回读）：

```
edit       *            -> deny
bash       *            -> ask
bash       git diff     -> allow
bash       git log*     -> allow
skill      *            -> deny
skill      probe-*      -> allow
```

### 2.3 Agent Loop 机制

```
Primary Agent（主对话，Tab 切换）
   ├─ 自动委派：依据 subagent 的 description
   ├─ 手动召唤：@subagent-name
   └─ 经 Task tool 调用 → 派生 child session
```

四个旋钮决定 Loop 形态：

| 旋钮 | 作用域 | 语义 |
|---|---|---|
| `permission.task` | agent | glob 白/黑名单。`deny` 会把该 subagent **从 Task 工具描述里整条移除**（模型看不到就不会调） |
| `subagent_depth` | 全局 | 默认 `1`；`0`=禁止派生，`2`=允许再嵌一层 |
| `steps` | agent | 迭代上限，触顶后模型收到"总结并列出剩余任务"的特殊提示 |
| `mode` | agent | `primary` 可直接对话；`subagent` 只能被调 |

内置：primary `build`/`plan`；subagent `general`/`explore`/`scout`；
隐藏系统 primary `compaction`/`title`/`summary`。

### 2.4 Skill 机制

- **一个目录一个 skill**：`<name>/SKILL.md`
- **6 个发现路径**：`.opencode/skills/`、`~/.config/opencode/skills/`、
  `.claude/skills/`、`~/.claude/skills/`、`.agents/skills/`、`~/.agents/skills/`
- **frontmatter 只认 5 个字段**，其余忽略：
  `name`(必填)、`description`(必填)、`license`、`compatibility`、`metadata`(string→string)
- `name` 约束：1–64 字符，`^[a-z0-9]+(-[a-z0-9]+)*$`，且 **必须等于目录名**
- `description`：1–1024 字符，是模型选 skill 的**唯一依据**
- 加载：模型看到 `<available_skills>` 清单 → 调 `skill({name:"x"})` 载入正文
- 权限：`permission.skill` 支持 glob；`deny` 使 skill 对该 agent **完全不可见**

**主流优秀实践 = 渐进披露（Progressive Disclosure）**

本地 55 个 skill 实证的通用结构：

```
arkcli-shared/                 pdf/
├── SKILL.md   ← 常驻上下文     ├── SKILL.md
└── references/  ← 命中才读     ├── reference.md
    ├── global-flags.md         ├── forms.md
    └── troubleshooting.md      └── scripts/*.py  ← 9 个可执行脚本
```

`arkcli-shared/SKILL.md` 内含一张"什么场景读哪个 reference"的**路由表** ——
把上下文预算当一等公民管理。**结论：Skill 必须支持多文件。**

### 2.5 运行时控制面（实测结果，决定发布策略）

| 端点 | 实测结论 | 平台如何用 |
|---|---|---|
| `GET /agent` | ✅ **可靠**。返回全部 agent，权限已展开为 `{permission,pattern,action}[]` | **发布后回读校验的权威依据** |
| `GET /global/health` | ✅ 返回 `{healthy,version}` | 探活 + 版本 |
| `GET /config` | ✅ 返回合并后配置 | 辅助诊断 |
| `PATCH /config` | ⚠️ **返回 200 但不生效**：agent 不出现在 `GET /agent`，也不落盘 | **不采用**（原计划的热注入方案被实测否决） |
| `GET /api/skill` | ❌ **不可信**：skill 明确可用时仍返回 `data: []` | **不作为校验依据** |
| `POST /session/:id/message`（带 `agent`） | ✅ | 平台内试跑 |

**Skill 生效的权威判据**（实测有效）：
在容器内执行 `opencode run --agent build "列出你可用的 skills"`，
输出真实包含 `probe-skill` → 证明 skill 已被 OpenCode 加载。

### 2.6 关键实测证据链

| # | 验证项 | 结果 |
|---|---|---|
| 1 | 容器内 `serve` 绑 `0.0.0.0:4096` | ✅ LISTEN 4096 |
| 2 | `GET /agent` / `GET /global/health` 从宿主经 14096 可达 | ✅ v1.18.12 |
| 3 | `put_archive()` 内存 tar 原子上传（含嵌套 `references/`） | ✅ 4 个文件全部就位 |
| 4 | 重启 serve 后 Markdown agent 被发现 | ✅ `probe-reviewer` 出现，**中文 description + 全部 glob 权限规则逐条正确** |
| 5 | 重启 serve 后 JSON agent 被发现 | ✅ `probe-json` 出现 |
| 6 | 多文件 skill 被 OpenCode 实际加载 | ✅ `opencode run` 输出含 `probe-skill` |
| 7 | `PATCH /config` 热注入 | ❌ 200 但不生效、不落盘 |
| 8 | 写 `opencode.jsonc` 后不重启 | ❌ 不热感知 |

**→ 结论：唯一可靠路径 = 写文件（为真） + 重启容器内服务（生效） + `GET /agent` 回读（校验）**

---

## 3. 核心设计决策

| 决策点 | 选择 | 理由 |
|---|---|---|
| **发布通道** | 写文件 + 重启服务生效 | 实测 `PATCH /config` 不生效（§2.5）；文件抗重启、可版本化、可手改 |
| **文件传输** | 本地 `put_archive()` 内存 tar；远程 `tar+base64` over SSH | 原子性；彻底避开 `echo`/引号/中文编码问题（实测通过） |
| **发布单元** | **Bundle（编排方案）**，非单个 agent | Loop 是"一组 agent + 全局旋钮"的整体，拆开发布会产生半成品状态 |
| **发布后校验** | 回读 `GET /agent` 逐项比对；skill 用 `opencode run` 探测 | 不做 fire-and-forget，发布结果必须可证伪 |
| **Skill 存储** | 正文 `LONGTEXT` + 独立 `skill_files` 表 | 支撑 references/scripts 的真实结构（§2.4） |
| **校验时机** | **设计态就拦**（不合法存不进 DB） | 权限键写错 OpenCode 静默忽略，事后极难排查 |
| **默认作用域** | 容器内全局 `/root/.config/opencode/` | 对该容器所有项目生效；可选项目级 `/workspace/.opencode/` |
| **重启影响** | 发布前明确告知"将重启服务，进行中的会话会中断" | 诚实建模，不偷偷重启 |

---

## 4. 数据模型（新增 7 表，6 → 13）

```
agent_templates ─┬─< agent_template_versions        版本快照，可回滚
                 └─< bundle_members >─ agent_bundles ─< deployments
skill_templates ─┬─< skill_files                    references/scripts
                 └─< bundle_members
```

### 4.1 `agent_templates` — Agent 设计态

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | varchar(64) **uniq** | agent 名，即文件名。正则 `^[a-z0-9]+(-[a-z0-9]+)*$` |
| `display_name` | varchar(128) | 展示名 |
| `description` | varchar(1024) | **必填**，决定委派 |
| `mode` | enum | `subagent`/`primary`/`all` |
| `model` | varchar(128) | `provider/model-id`，空=继承 |
| `prompt` | LONGTEXT | system prompt |
| `temperature` / `top_p` | float | 可空 |
| `steps` | int | 迭代上限 |
| `permission_json` | JSON | 权限配置（15 键） |
| `options_json` | JSON | provider 透传 |
| `color` | varchar(32) | |
| `hidden` / `disable` | bool | |
| `category` | varchar(64) | 分类（review/security/docs/...） |
| `is_builtin_preset` | bool | 内置预设不可删 |
| `source` | enum | `platform`/`imported` |
| `current_version` | int | 当前版本号 |
| `created_by_user_id` | int | |

### 4.2 `agent_template_versions` — 版本快照

`agent_template_id`(FK CASCADE) · `version` · `snapshot_json` · `change_note` · `created_by_user_id`
**uniq(`agent_template_id`,`version`)**

### 4.3 `skill_templates` — Skill 设计态

`name`(varchar64 **uniq**, 强校验) · `description`(varchar1024, ≤1024) · `license` · `compatibility`
· `metadata_json` · `body`(LONGTEXT) · `category` · `is_builtin_preset` · `source` · `current_version`

### 4.4 `skill_files` — Skill 附属文件

`skill_template_id`(FK CASCADE) · `rel_path`(varchar512，如 `references/x.md`) · `content`(LONGTEXT) · `is_executable`(bool)
**uniq(`skill_template_id`,`rel_path`)**

> 校验：禁止 `..`、禁止绝对路径、禁止与 `SKILL.md` 重名、单文件 ≤1MB

### 4.5 `agent_bundles` — 编排方案（Loop 模式）

`name`(varchar128 **uniq**) · `description` · `pattern`(enum，见 §5) · `default_agent`
· `subagent_depth`(int, 0–3) · `global_permission_json` · `topology_json` · `is_builtin_preset` · `current_version`

### 4.6 `bundle_members` — Bundle 成员

`bundle_id`(FK CASCADE) · `member_type`(enum `agent`/`skill`) · `agent_template_id`(nullable FK)
· `skill_template_id`(nullable FK) · `role`(enum `primary`/`subagent`/`skill`)
· `skill_permission`(enum `allow`/`ask`/`deny`) · `sort_order`

### 4.7 `deployments` — 发布记录

`bundle_id`(FK) · `bundle_version` · `node_id`(FK compute_nodes) · `container_id` · `container_name`
· `scope`(enum `global`/`project`) · `target_dir` · `status`(enum) · `artifacts_json`(产物清单+sha256)
· `verify_json`(回读比对结果) · `restart_used`(bool) · `error_detail` · `duration_ms` · `deployed_by_user_id`

`status` 取值：`pending` → `validating` → `writing` → `reloading` → `verifying` → `success` | `partial` | `failed`

---

## 5. 内置 Loop 模式预设（6 个）

| 模式 | 构成 | 关键旋钮 |
|---|---|---|
| `single` 单体 | 1 primary 全权限 | — |
| `plan-build` 双阶段 | plan(`edit`/`bash`=ask) → build(全开) | `default_agent: plan` |
| `orchestrator-workers` 编排 | 1 orchestrator + N specialist | `task: {"*":"deny","worker-*":"allow"}`，`subagent_depth:1` |
| `research-loop` 调研环 | researcher(primary) + searcher/verifier | `steps:30`，Plan→Search→Reflect→Synthesize |
| `review-loop` 评审环 | implementer + reviewer(`edit`=deny) | `task:{"reviewer":"allow"}` |
| `pipeline` 流水线 | coordinator + 顺序 subagent 链 | 按 `sort_order` 串行 |

**8 个 Agent 预设**：code-reviewer、security-auditor、docs-writer、debugger、
test-writer、refactorer、explorer、orchestrator

**4 个 Skill 预设**（演示渐进披露）：git-release、api-contract、db-migration、incident-report

---

## 6. 校验规则（设计态拦截，专业度核心）

```
PERMISSION_KEYS = {read,edit,glob,grep,list,bash,task,external_directory,
                   todowrite,question,webfetch,websearch,lsp,doom_loop,skill}
GLOB_CAPABLE    = {read,edit,glob,grep,list,bash,task,external_directory,lsp,skill}
```

| # | 规则 | 级别 | 原因 |
|---|---|---|---|
| 1 | 未知权限键 | **error** | OpenCode 静默忽略，必须前置拦截 |
| 2 | 非 GLOB_CAPABLE 的键给了 object | **error** | 不被支持 |
| 3 | 动作不在 allow/ask/deny | **error** | |
| 4 | `"*"` 未放首位 | warning | 最后匹配胜出，该规则可能不生效 |
| 5 | agent/skill `name` 不合正则 | **error** | |
| 6 | skill `name` ≠ 目录名 | **error** | OpenCode 强制要求 |
| 7 | `description` 空或 >1024 | **error** | |
| 8 | `skill_files.rel_path` 含 `..`/绝对路径/与 SKILL.md 冲突 | **error** | 路径穿越 |
| 9 | bundle 无 primary 成员 | **error** | 无法对话 |
| 10 | `permission.task` 指向 bundle 外的 subagent | **error** | 死引用 |
| 11 | `subagent_depth=0` 但 bundle 含 subagent | warning | 永不会被调用 |
| 12 | `temperature`/`top_p` 越界 | warning | |
| 13 | `color` 格式非法 | **error** | |
| 14 | `default_agent` 非 primary | **error** | OpenCode 会 fallback 到 build |
| 15 | 高危组合（`edit:allow` + `bash:allow`） | warning | 发布前二次确认 |

---

## 7. 发布管道（五阶段，每阶段可观测）

```
① resolve   解析 bundle → 全量产物清单（含 sha256）
② validate  再校验一次（DB 可能被手改过）
③ write     本地 put_archive(内存 tar) / 远程 tar+base64 over SSH
            幂等：同 sha256 跳过；清理旧产物（避免残留孤儿 agent）
④ reload    重启容器内 opencode 服务（复用 stop_service + launch_service）
            ⚠️ 会中断进行中的会话，发布前明确告知
⑤ verify    GET /agent 逐项比对 name/mode/description/permission
            skill 用 opencode run 探测清单
            → success | partial | failed，差异写入 verify_json
```

**产物布局**（`scope=global`，容器内 `/root/.config/opencode/`）：

```
agents/<agent-name>.md            ← 每个 agent 一个 md
skills/<skill-name>/SKILL.md      ← 每个 skill 一个目录
skills/<skill-name>/references/*  ← 附属文件
opencode.jsonc                    ← 写 subagent_depth / default_agent / permission.skill
```

---

## 8. API 契约（24 端点，前缀 `/api/v1/agent-factory`）

### Agent
```
GET    /agents                      列表（category/mode/keyword 筛选）
POST   /agents                      创建（含校验）
GET    /agents/{id}                 详情
PUT    /agents/{id}                 更新
DELETE /agents/{id}                 删除（内置预设禁删）
POST   /agents/{id}/versions        存快照
GET    /agents/{id}/versions        版本列表
POST   /agents/{id}/rollback        回滚到指定版本
POST   /agents/{id}/preview         渲染 .md 预览（不落盘）
POST   /agents/validate             校验（不落库）
POST   /agents/import               从容器/文本反向导入
```

### Skill
```
GET    /skills                      列表
POST   /skills                      创建
GET    /skills/{id}                 详情（含 files）
PUT    /skills/{id}                 更新
DELETE /skills/{id}                 删除
PUT    /skills/{id}/files           批量替换附属文件
POST   /skills/{id}/preview         渲染目录预览
```

### Bundle
```
GET    /bundles                     列表
POST   /bundles                     创建
GET    /bundles/{id}                详情（含 members）
PUT    /bundles/{id}                更新
DELETE /bundles/{id}                删除
PUT    /bundles/{id}/members        设置成员
POST   /bundles/{id}/validate       校验（拓扑一致性）
POST   /bundles/{id}/preview        全量产物预览
```

### Deploy
```
POST   /bundles/{id}/deploy         发布（body: node_id, container_id, scope, restart_confirmed）
GET    /deployments                 发布历史
GET    /deployments/{id}            发布详情（含 artifacts/verify）
POST   /deployments/{id}/verify     重新回读校验
```

### Meta
```
GET    /presets                     预设清单（6 Loop + 8 Agent + 4 Skill）
GET    /permission-keys             15 权限键 + glob 能力元数据
```

统一响应：`{"code":"SUCCESS","message":"...","data":...}`（沿用仓库约定）

---

## 9. 前端信息架构

新增顶级导航 **Agent 工厂**（`/agent-factory`），4 个 tab：

| Tab | 核心组件 |
|---|---|
| **Agent 设计器** | 左列表 / 右表单；**15 键 × 三态权限矩阵** + glob 规则行编辑（带 `*` 置顶提示）；Prompt 编辑；**右侧实时 `.md` 预览** |
| **Skill 设计器** | frontmatter 表单（只暴露 5 个合法字段 + "其余会被忽略"说明）；正文编辑；**附属文件树**（增删改 references/scripts）；渐进披露建议 |
| **编排方案** | 选 6 模式预设 → 生成骨架；拖拽挑成员；**Task 权限矩阵**；**SVG 拓扑图**（primary 居中，箭头=允许，虚线=ask，灰=deny）；旋钮区 |
| **发布中心** | 选节点→容器（复用 `container_services` 可用性）；**产物 diff 预览**；重启确认；五阶段进度；**校验结果表**（期望 vs 容器实际） |

每个输入都带 placeholder + 示例（延续既有 UX 标准）。

---

## 10. 验收用例

| # | 用例 | 通过标准 |
|---|---|---|
| A1 | 创建 agent，权限键写错 `write` | 返回 error，明确指出"未知权限键 write，合法键为 edit（write/edit/apply_patch 由 edit 统一管控）" |
| A2 | `"*"` 未置顶 | 返回 warning 说明可能不生效 |
| A3 | 渲染预览 | 生成的 `.md` 与手写等价（frontmatter 字段顺序/引号正确） |
| S1 | 创建含 `references/` 的 skill | 文件树正确，`rel_path` 校验生效 |
| S2 | `rel_path` 传 `../evil.md` | 返回 error |
| B1 | 组 `review-loop` bundle | 拓扑图正确渲染；`task` 权限指向合法 |
| B2 | bundle 无 primary | 返回 error |
| D1 | 发布到 `opencode` 容器 | 五阶段全绿；容器内 `find` 能看到产物 |
| D2 | 发布后 `GET /agent` 回读 | 新 agent 出现，`mode`/`description`/`permission` 逐条一致 |
| D3 | skill 生效验证 | 容器内 `opencode run "列出可用 skills"` 输出含新 skill |
| D4 | 二次发布（内容未变） | 幂等，sha256 相同则跳过写入 |
| D5 | 试跑 | 用 `POST /session/:id/message` 带 `agent` 参数实际调用新 agent 成功 |

---

## 11. 风险与对策

| 风险 | 对策 |
|---|---|
| ~~`PATCH /config` 不生效~~ | ✅ 已实测确认，方案改为"写文件+重启"，**风险已消除** |
| ~~`/api/skill` 不可信~~ | ✅ 已实测确认，改用 `opencode run` 探测 skill 清单 |
| 重启中断进行中会话 | 发布前弹确认（`restart_confirmed` 必填）；提示"建议在无人使用时发布" |
| 容器重建丢产物 | `deployments` 记录容器 ID；复用既有"容器重建迁移"机制，标记 `需重新发布` |
| 权限配置导致越权 | 校验器前置 + 发布前 diff + 高危组合二次确认 |
| 大 skill 传输 | tar 原生支持；单文件 ≤1MB、单 skill ≤10MB |
| 产物漂移（有人手改容器内文件） | `artifacts_json` 存 sha256，`verify` 阶段可发现 |

---

## 12. 明确不做（本轮）

- Agent 效果评测 / A-B 对比
- 团队级发布权限（沿用现有登录鉴权）
- 从 GitHub 直接导入 skill 仓库（预留 `source` 字段）
- Agent 运行时监控（token / 耗时统计）
- MCP server 平台化管理（机制同构，可作下一期）

---

## 13. 附录：实测命令备查

```bash
# 容器内起 serve（控制面必须用 serve，web 不暴露 /agent）
docker exec -d <c> sh -c 'cd /workspace && exec opencode serve \
  --port 4096 --hostname 0.0.0.0 --cors http://localhost:5173 \
  > /var/log/opencode/serve-4096.log 2>&1'

# 回读校验
curl -s http://localhost:<hostPort>/agent | jq '.[].name'
curl -s http://localhost:<hostPort>/global/health

# skill 生效的权威判据
docker exec <c> sh -c 'cd /workspace && opencode run --agent build \
  "列出你可用的 skills 名称清单，只输出名称"'
```
