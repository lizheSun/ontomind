# T62 · Playwright E2E 20+ spec

## Goal
覆盖：资源页 5 层导航、自动发现、SOP 编辑、长任务、Cmd+K、Zen/God 模式、Agent 嵌入。至少 20 个 spec 全部通过。

## Files touched
- `e2e/tests/resources-navigation.spec.ts` (NEW)
- `e2e/tests/resources-auto-discover.spec.ts` (NEW)
- `e2e/tests/compute-node-detail.spec.ts` (NEW)
- `e2e/tests/agent-container-detail.spec.ts` (NEW)
- `e2e/tests/agent-detail-binding.spec.ts` (NEW)
- `e2e/tests/skill-detail.spec.ts` (NEW)
- `e2e/tests/mcp-detail.spec.ts` (NEW)
- `e2e/tests/sop-editor-nl.spec.ts` (NEW)
- `e2e/tests/sop-editor-dag.spec.ts` (NEW)
- `e2e/tests/sop-templates.spec.ts` (NEW)
- `e2e/tests/agent-job-lifecycle.spec.ts` (NEW)
- `e2e/tests/agent-job-cancel.spec.ts` (NEW)
- `e2e/tests/agent-embed-aibi.spec.ts` (NEW)
- `e2e/tests/agent-embed-metadata.spec.ts` (NEW)
- `e2e/tests/cmdk-search.spec.ts` (NEW)
- `e2e/tests/cmdk-assist.spec.ts` (NEW)
- `e2e/tests/cmdk-act.spec.ts` (NEW)
- `e2e/tests/zen-god-toggle.spec.ts` (NEW)
- `e2e/tests/flip-card.spec.ts` (NEW)
- `e2e/tests/agent-chat-streaming.spec.ts` (NEW)
- `e2e/tests/agent-chat-approval.spec.ts` (NEW)
- `e2e/tests/template-gallery-onboarding.spec.ts` (NEW)
- `e2e/fixtures/seed-data.ts` (NEW — E2E 数据准备)
- `e2e/playwright.config.ts` (更新 workers=4)
- `.blueprint/qa/T62/playwright.txt`

## Depends on
- T61

## 每个 spec 至少
- 1 个 happy path
- 1 个错误场景
- 1 个断言页面无 console.error

## Acceptance
- 22 spec 全部通过
- 单次总时长 <10min
- CI headless 通过

## Verify
```bash
cd e2e
npx playwright install
npx playwright test --workers=4 --reporter=list > ../.blueprint/qa/T62/playwright.txt
```

## Commit
`test(e2e): 22 playwright specs covering wave 10 features`
