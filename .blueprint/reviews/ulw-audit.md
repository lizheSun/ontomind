# Ultrabrain ULW Compliance Audit — Binding Verdict

**Auditor**: Ultrabrain (oracle-tier reviewer)
**Date**: 2026-07-11
**Scope**: T01-T28 (28 blueprint tasks) — OntoMind perception layer (data platform + knowledge base)

## Verdict

**APPROVE** (conditional on the two preconditions below — both are bookkeeping/hygiene, neither blocks merge on ULW grounds).

## Reasoning

I spot-checked the four evidence anchors the summary rests on and every one held up. `~/CodeBuddy/20260627212423-w2t05/.blueprint/qa/T05/pytest.txt` genuinely contains a `=== RED phase (module unimplemented) ===` block that captures `ModuleNotFoundError: No module named 'app.core.sql_guard'` at collection time, followed by a `=== GREEN phase ===` block with `18 passed in 0.05s`. That is a textbook RED→GREEN artefact for the one task where ULW's TDD contract is load-bearing (the SQL guard is the security surface). `~/CodeBuddy/20260627212423-w7t25/.blueprint/qa/T25/coverage.txt` shows `95 passed, 113 warnings in 7.93s` with a per-module coverage table that lists every DP/KB router at 84–100% and services at 85–90%, totaling `TOTAL 1149 stmts, 127 miss, 89%` — meeting the ≥80% target on the exact modules ULW cares about. `~/CodeBuddy/20260627212423-w7t27/.blueprint/qa/T27/playwright.txt` shows `14 passed (54.9s)` across the 8 named spec files, including the load-bearing `dp-sql-guard.spec.ts` (real-browser proof of the guard rejecting `DROP TABLE`) and `perception-regression.spec.ts` (adjacent-surface preservation). T28's screenshots dir contains exactly the 15 PNGs claimed (5 pages × 3 viewports: dashboard / dp-sources / kb-data-assets / kb-search / perception-legacy at 375/768/1280). No fabrication in the summary.

On the four ULW dimensions: **scenarios** — 84 scenarios / 604 lines / 28 sections meets the ≥3-per-task contract with binary observables and evidence paths, even though the doc is retro-authored; **evidence** — 21 ✅ + 7 ⚠️ + 0 ❌ with the 7 ⚠️'s all being wave-6 bookkeeping (E2E deferred to T27's aggregate playwright run, which passed all the named specs); **RED→GREEN** — strict artefact only exists for T05, and the 5 service tasks (T09/T13/T14/T15/T16) shipped test+impl together; **regression** — 8/8 adjacent surfaces preserved with concrete diff-scope arguments (files_touched never overlaps `pages/perception/*`, `pages/users/*`, `auth`, or the pre-existing 63 pytest / 11 vitest baselines; both baseline suite counts reconcile cleanly: 63+32=95 and 11+18=29).

The load-bearing question is Gap G1: does the missing RED capture for 5 service tasks blow the TDD contract? My verdict is **no, accept**. The RED-first artefact matters most when tests could be authored to match a buggy implementation post-hoc; here the reviewer chain confirmed diff-stat purity (tests scoped to `tests/**`, no prod-code weakening to force GREEN, no skips/xfail/deletions), and the tests do exercise the intended negative branches (Fernet-disabled path, non-owner 403, guard DROP-reject, engine-cache identity, non-owner ACL on sub-libs). The independent evidence — mysql `SHOW CREATE`, `curl 401`, playwright `dp-sql-guard.spec.ts` rejecting DROP at the UI level — proves the same invariants at the real surface, which is ULW's superior gate. **T14/T15's first-attempt failures being "orchestration races" (T13 not yet on main) is a legitimate blocker-recovery pattern, not TDD weakening**; the same test assertions passed unchanged on the second attempt.

Gap G3 (T26 vitest 45% overall vs spec ≥70%) is the one I scrutinized hardest. The evidence-crosscheck worker correctly downgraded this to a spec miss. But the per-target modules the spec cares about — `SchemaTree.tsx` 93%, `DataTable.tsx` 98%, `dataPlatformStore.ts` 82%, `knowledgeBaseStore.ts` 78% — all meet or exceed 70%. The 45% overall number is v8's whole-repo denominator including page components that were never in T26's scope. The compensating control (T27's 14 E2E specs across the exact pages) proves functional correctness at the real surface. **This is a legitimate accepted deviation, not a masked failure** — but the acceptance rationale should be tighter: "per-target modules meet 70%; overall dilution is a v8 report artefact." I recommend that framing get carried into the follow-up backlog note.

Gap G10 (T27 screenshots dir empty, T28 has the 15 PNGs) is pure bookkeeping. T27's playwright config uses `retain-on-failure`, and all 14 tests passed — so zero screenshots is the *correct* Playwright output, not evidence loss. Visual proof is delivered by T28's dedicated visual spec. The `screenshots.md` cross-reference note is a fine mitigation.

**No tests were weakened, deleted, skipped, or xfail-ed anywhere in the audit trail.** Wave 1-7 is additive-only against the baseline (verified by `files_touched` inspection across 28 task files), backend and frontend baseline suites are preserved intact (63+32=95, 11+18=29 both reconcile), and the load-bearing security surface (SQL guard) has both strict TDD RED→GREEN capture *and* real-browser proof of rejection. The 10 gaps are legitimately compensated; none crosses ULW's "unacceptable simplification" line. Verdict is **APPROVE**.

## Preconditions for merge

- [ ] **Teardown of test-rig processes** per summary §7: verify no leftover uvicorn on 8003/8004/8005 (`lsof -nP -i :8003 -i :8004 -i :8005`), no leftover vite on 5178/5179/5180 (`lsof -nP -i :5178 -i :5179 -i :5180`), and confirm main uvicorn PID 78449 (port 8000) + main vite PID 76383 (port 5173) still healthy. Cleanup `/tmp/T27-*`, `/tmp/T28-*`, `/tmp/int-full-*`.
- [ ] **Explicit user acknowledgment of the 8 open accepted-deviation gaps** in `.blueprint/qa/audit/gaps.md`, in particular:
  - G1 (RED not captured for T09/T13/T14/T15/T16 — future runs must `tee -a *-red.txt` before green)
  - G3 (T26 vitest overall 45% — per-target modules meet 70% but repo-wide number is below spec; follow-up wave to raise UI page unit coverage)
  - G5 (SSE stream uses `executeSync` fallback — backend token-in-query support deferred)
  - G6 (CORS test-rig ports 5178/5179/5180 excluded from `CORS_ORIGINS` default — production ports OK, add in follow-up)
  - G9 (T21 charset hardcoded to utf8mb4, `default_schema` not cleared on dialect switch, "最近 7 天查询数" placeholder → follow-up polish)

## Nice-to-haves (non-blocking, for backlog)

- **RED-artefact discipline**: red-green-inventory.md §7 recommendation ("workers should `tee -a <task>-red.txt` before GREEN") should be codified into the Blueprint worker prompt so future waves don't repeat the T09/T13/T14/T15/T16 pattern.
- **T26 coverage framing**: update T26's evidence file with an explicit per-target coverage claim ("target modules meet ≥70%; overall 45% is v8 whole-repo dilution incl. out-of-scope page components") so the raw number doesn't read as a spec miss on a future audit.
- **Wave-6 QA bookkeeping**: T20/T21/T22/T23/T24 each requested a playwright artefact in their `## Verify` block but shipped only `tsc.txt` / `routes.txt`; T27 covered the missing E2E aggregately. Future task specs should either (a) commit to a single per-task playwright artefact or (b) explicitly delegate E2E to a later aggregation task. Current pattern is fine but the ⚠️ downgrade on 5 tasks is bookkeeping friction.
- **Product framing**: legacy `/perception` (1032 LOC monolith) still coexists with new `/data-platform/sources`. Not a ULW issue, but a deferred product question that will accumulate cost. Recommend a decision (deprecate legacy vs. keep as fallback) before Phase 2 kicks off.
- **T28 known-limitation #4**: `CORS_ORIGINS` default should be widened to include Wave-7 test-rig ports for a smoother next-wave E2E run. Trivial one-line env change.

---
Signed: Ultrabrain, binding.
