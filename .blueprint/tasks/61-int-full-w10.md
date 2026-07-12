# T61 · int-full-w10 集成 + 全套回归

## Goal
合并 T44-T60 全部 17 个 branch 到 `blueprint/int-full-w10`。跑 backend pytest（全量）+ frontend vitest（全量）+ typecheck + build。修复集成冲突。

## Files touched
- `.blueprint/qa/T61/backend-pytest.txt` (NEW)
- `.blueprint/qa/T61/frontend-vitest.txt` (NEW)
- `.blueprint/qa/T61/typecheck.txt` (NEW)
- `.blueprint/qa/T61/build.txt` (NEW)
- `.blueprint/qa/T61/merge-conflicts.md` (NEW — 冲突解决记录)
- 必要时修补 `backend/app/**` 与 `frontend/src/**` 的集成 bug

## Depends on
- T44-T60（全部完成）

## 步骤
1. `git checkout -b blueprint/int-full-w10 main`
2. 逐个 merge：`git merge --no-ff blueprint/T44 blueprint/T45 ... blueprint/T60`
3. 有冲突就分析并选择正确解，记录到 merge-conflicts.md
4. `cd backend && pytest -q` → 保存输出
5. `cd frontend && npm run typecheck && npm run test -- --run && npm run build` → 保存输出
6. 冒烟：启动服务，访问 `/resources`, `/agent-jobs`, `/agent-looper`
7. `docker compose up -d` 全栈跑一遍

## Acceptance
- 所有 merge 完成，无未解决冲突
- backend pytest 100% 通过
- frontend vitest 100% 通过 + typecheck 干净 + build 成功
- 手工冒烟 3 个页面无 console error

## Verify
```bash
cd backend && pytest -q > .blueprint/qa/T61/backend-pytest.txt
cd frontend && npm run typecheck > .blueprint/qa/T61/typecheck.txt
cd frontend && npm run test -- --run > .blueprint/qa/T61/frontend-vitest.txt
cd frontend && npm run build > .blueprint/qa/T61/build.txt
```

## Commit
`chore(int): merge T44-T60 into blueprint/int-full-w10`
