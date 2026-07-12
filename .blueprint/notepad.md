# Ultrawork Notepad — 感知层（数据平台 + 知识库）
Started: 2026-07-11T12:20+08:00
Repo: /Users/sun/CodeBuddy/20260627212423
Backend PID: 78449 (uvicorn, no --reload, on :8000)
Frontend PID: 76354 (npm) / 76383 (vite on :5173)
DB: MySQL, ontomind/ontomind_secret, ontomind database
Admin: id=1 admin / admin123 (superuser)

## Plan (exhaustive, atomic)
_pending plan-agent output_

## Scenarios (the contract)
### Data Platform
- S-DP-01 (happy): 用户登录后进入 /data → "新建数据源" → 填 MySQL 连接串 → "测试连接" 返回 success → 保存 → 列表出现新条目
- S-DP-02 (happy): 选中该数据源 → 进 SQL Editor → `SELECT * FROM users LIMIT 10` → 执行 → 结果表格显示行 + 列名 + 耗时 → 历史面板出现一条记录
- S-DP-03 (happy): "AI 生成 SQL" tab → 输入"最近 7 天新增的用户数" → LLM 返回 SQL → 预览 → 用户确认后执行
- S-DP-04 (edge): 输入 `DROP TABLE users` → 前后端双重拦截，返回 403 + 中文错误
- S-DP-05 (edge): 保存的数据源密码字段加密入库，DB SELECT 出来非明文
- S-DP-06 (regression): 登录、原有 users 相关页面不受影响

### Knowledge Base
- S-KB-01 (happy): /kb 侧栏切换 4 个子库（数据资产/代码库/文档库/业务经验）
- S-KB-02 (happy): 数据资产库新增（中文名/英文名/所属域/责任人/描述） → 列表 → 详情可编辑
- S-KB-03 (happy): 文档库上传 .md → 落到 uploads/ → 详情页可预览
- S-KB-04 (happy): 全局搜索关键词，跨 4 库返回聚合结果
- S-KB-05 (edge): 未登录访问 /kb/* → 302 到 /login
- S-KB-06 (edge): 标题 >200 字符 → 422 + 前端 form-level 错误

### UI/UX
- S-UI-01: /data 和 /kb Lighthouse Performance ≥ 90, Accessibility ≥ 90
- S-UI-02: 三视口（1440x900 / 1280x800 / 375x812）无横向滚动、无遮挡
- S-UI-03: 深色主基调，色彩层次 ≤ 6，字体 hero ≥28px / body 14-15px

## Now
Waiting for 5 parallel explore/librarian results (bg_cbb390f1 / bg_477d074a / bg_9c4c4d89 / bg_89251e9f / bg_4372d627).

## Todo (remaining, ordered)
1. Collect 5 recon results
2. Feed all context into plan agent → get wave graph
3. Execute waves per plan agent, TDD each task
4. visual-qa on all pages after each wave
5. Reviewer gate (ultrabrain reviewer) on final diff
6. Manual QA per scenario, capture artifacts
7. Teardown QA resources (kill dev workers, close browser sessions, remove tmp files)

## Findings (non-obvious facts with file:line refs)
_pending_

## Learnings
_pending_

---

## ULW Compliance Audit (Wave 7 close-out, per user choice C)

Started: 2026-07-11T15:30+08:00
Scope: All 28 tasks (T01-T28) — retroactive audit.
Owner: orchestrator; final gate = ultrabrain reviewer.

### Audit contract

Every task must satisfy 3 dimensions:

1. **Scenario contract**: happy path + edge + adjacent-surface regression, each with binary observable + evidence path.
2. **Evidence artifacts**: RED→GREEN test proof (when task produced tests) + real-surface artifact (curl/mysql/vitest/playwright/screenshot).
3. **Adjacent surface preserved**: no regression on prior features (users/login/perception page, prior 63 backend tests, prior 11 vitest).

### Audit artifacts (to be produced under `.blueprint/qa/audit/`)

- `scenarios.md` — 3+ scenarios per T01-T28 with binary observable + evidence path
- `evidence-crosscheck.md` — 28-row table: task | acceptance criteria | evidence artifact path | PASS/FAIL
- `red-green-inventory.md` — T05, T09, T13, T14, T15, T16, T25, T26 (test-producing tasks) — RED then GREEN cited
- `regression-adjacency.md` — legacy /perception, /login, /users, existing pytest suites
- `gaps.md` — any ULW anti-pattern still present + accepted-deviation reason
- `summary.md` — final ULW-format sign-off with go/no-go verdict

### Reviewer gate

Ultrabrain reviewer will be called with `.blueprint/qa/audit/summary.md` + notepad path. Binding verdict written to `.blueprint/reviews/ulw-audit.md`. Loop until unconditional approval.

### Teardown before declaring done

- No leftover uvicorn on ports 8003/8004/8005
- No leftover vite on 5178/5179/5180
- Ports back to only 8000 (main uvicorn) + 5173 (main vite)
- `/tmp/T27-*`, `/tmp/T28-*`, `/tmp/int-full-*` scratch logs cleaned or moved to `.blueprint/qa/T*/`

## Now
Awaiting T27 (bg_c84590a3) + T28 (bg_e1d5eb18) background completion before starting audit artifacts.
