# Wave 10 Plan Review

## Verdict
CHANGES-REQUESTED

## Reasoning
- **Wave parallelism counts are wrong** in 4 out of 5 waves. The task `depends_on` graph does not match the "5 / 4 / 4 / 4 / 3 parallel" claim in `plan.md` §任务依赖图. W1 is actually a 3-level DAG (T44 → {T45,T46} → {T47,T48}), and W5 is strictly sequential (T61 → T62 → T63), not "3 parallel". Fixing this is a naming/documentation change but critical because an executor reading the plan will over-commit workers.
- **Storage engine mismatch**: `plan.md:102` says "Postgres 状态机足矣" but the entire OntoMind stack is MySQL 8.0 (README, `findings/01-backend-runtime.md`, all prior review artifacts, T44's own `Verify` uses `mysql -uroot`). This is a factual error, not a design choice.
- **5W coverage is partial**: Why/What/How are present and detailed; **Who** (worker/agent assignment per task) and **When** (wave duration, ETA, sequencing dates) are missing. Blueprint fills Who via workflow, but When has no anchor at all.
- **Task file quality is uniformly good**: All 20 tasks (T44-T63) carry Goal, Files touched, Depends on, Acceptance, Verify, Commit. Naming体系 (计算节点 / 智能体容器 / 智能体 / Skill / MCP) is explained clearly in `plan.md:14-24`.
- **Coverage of user's original ask is complete**: UX innovation (T57/T58/T60), MCP discovery (T46/T48), Agent embedding (T56), long-running jobs (T55) all present and traced to concrete files.

## Required changes

1. **`plan.md:102`** — change "Postgres 状态机足矣" to "MySQL 状态机足矣" (or a dialect-agnostic wording). The project runs MySQL 8.0; there is no Postgres path in this codebase.

2. **`plan.md:67-99` (wave parallelism)** — rewrite wave descriptions to reflect actual `depends_on`:
   - W1 is not "5 并行". Actual: `T44 → {T45, T46 (parallel)} → {T47 (needs T46), T48 (needs T46)}`. Call it "W1 · 3 层, 最多 2 并行".
   - W2 is not "4 并行". T50/T51/T52 all depend on T49, so it's `T49 → {T50, T51, T52 parallel}`. Call it "W2 · 2 层, 最多 3 并行".
   - W3 is not "4 并行". T54 needs T53, T55 needs T53, T56 needs T55. Actual: `T53 → {T54, T55 parallel} → T56`. Call it "W3 · 3 层, 最多 2 并行".
   - W4 is correctly 4-parallel (all four W4 deps land in ≤W3). ✅
   - W5 is not "3 并行". T62 depends on T61, T63 depends on T61+T62. Actual: strictly sequential `T61 → T62 → T63`. Call it "W5 · 3 层, 严格串行".

3. **`plan.md`** — add a **Who / When** section (even if brief). Suggested content: "Who — 每 task 由 1 worker + 1 reviewer；同 wave 内的独立分支并行；集成/合并集中在 orchestrator。When — W1-W4 各 wave 目标 ≤1 workday；W5 集成 + E2E ≤1 workday；总预算 5 workday。" This closes the 5W gap.

4. **`.blueprint/tasks/56-agent-embed.md:23-28` (postMessage 协议)** — `plan.md:105` says "只做同源嵌入", but T56 defines a `postMessage` bridge without specifying whether the runner lives in an iframe or in the same document. If it's same-document React, postMessage is unnecessary; if it's iframe (even same-origin), the task must state `<iframe>` and its `sandbox`/`allow` attrs. Add one line under "postMessage 协议" clarifying "同源 iframe + `sandbox='allow-scripts allow-same-origin'`" (or drop postMessage in favor of a Zustand event bus).

5. **`.blueprint/tasks/44-data-model-refactor.md:28-42`** — the plan header claims "5 张核心表 + 7 张关联表", but the list breaks down as 5 core + 6 associations + 1 job table (`agent_run_jobs`) = 12. Either relabel `agent_run_jobs` as its own category (event/log table) in `plan.md:28`, or update the tagline to "5 核心 + 6 关联 + 1 任务日志表".

6. **`.blueprint/tasks/55-agent-jobs.md:26-31`** — `AgentJobService` uses in-process `asyncio.Task` with concurrency 20 but never states what happens on backend restart. `plan.md:102` promises Postgres/MySQL state machine is enough for <1h jobs, so crash recovery is on the critical path. Add an acceptance line: "backend 重启后, `status=running` 的 job 自动 resume from checkpoint (走 T53 `checkpointer.resume()`)".

7. **`.blueprint/tasks/45-naming-migration.md:26`** — "旧路由保留 3 个月的重定向 (301 → 新路由)". `301 Moved Permanently` will convert POST → GET on many clients. Use `308 Permanent Redirect` (or `307` for temporary) so DELETE/POST/PUT survive the redirect.

## Nice-to-haves (non-blocking)
- `.blueprint/tasks/62-playwright-e2e.md` — title says "20+ spec", file list has 22 (T22 counts `template-gallery-onboarding.spec.ts` at the end). Align title with "22 spec".
- `plan.md` — add a footer "Est. LOC delta" and "Est. test count" so T61 集成回归 has a numeric target.
- Consider adding an explicit `agents.loop_strategy` enum (values: `single_shot|react|plan_execute|evaluator_optimizer|reflect`) to T44 rather than free-text, so T53's 5 strategy files match a typed DB column.
- T56 embeds `AgentEmbedRunner` into `AIBIWorkbench.tsx` + `MetadataAnnotator.tsx` — that's scope beyond `/resources`, but is called out in `plan.md:9` and is intentional. Not a block; worth a one-line note in the plan "本 wave 除 `/resources` 外, 还在 AIBI / 元数据页面注入 embed 组件, 属受控扩散".
- Architecture decisions checkpoint: 12-table design ✅ (fine for the domain, no obvious over-normalization), same-origin iframe (needs clarification per Required #4), Cmd+K omnibar ✅ (T57 references OmniBar prior art, has 15+ actions), Zen/God mode ✅ (T58 has store + toggle + FlipCard, localStorage persist). State machine backing store: fix per Required #1.

## One-paragraph verdict
Wave 10 is a substantive, well-decomposed plan — the naming system is crisp, the 12-table model actually maps to the 5-layer 计算节点/容器/智能体/Skill/MCP taxonomy, all 20 task files are properly structured, and the user's original brief (UX innovation, MCP discovery, agent embedding, long-running jobs) is fully covered with traceable file lists. The blockers are cheap to fix: a Postgres→MySQL typo, four inaccurate "N parallel" wave labels that contradict the tasks' own `depends_on`, missing Who/When in the 5W, an ambiguous iframe/postMessage decision in T56, and a missing crash-recovery acceptance in T55. Once those six edits land the plan is APPROVE-ready and can enter execution.
