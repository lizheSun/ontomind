# T59 · Agent 交互面板升级

## Goal
Tool parts 流式渲染：`input-streaming`（打字光标）、`input-available`（加载中）、`output-available`（结果卡片）、`approval-requested`（审批按钮）。多步骤显示（step-start 作为章节分隔）。审批流：需要用户确认的操作显示 approve/deny 按钮。

## Files touched
- `frontend/src/components/AgentChatPanel/index.tsx` (REPLACE 原有 chat 面板)
- `frontend/src/components/AgentChatPanel/MessagePart.tsx` (NEW)
- `frontend/src/components/AgentChatPanel/ToolPart.tsx` (NEW — 4 种状态)
- `frontend/src/components/AgentChatPanel/StepDivider.tsx` (NEW)
- `frontend/src/components/AgentChatPanel/ApprovalPanel.tsx` (NEW)
- `frontend/src/components/AgentChatPanel/hooks/useAgentStream.ts` (NEW — SSE + parts 解析)
- `frontend/src/components/AgentChatPanel/types.ts` (NEW)
- `backend/app/api/v1/agent_chat.py` (NEW — SSE `stream` 端点 + `/approve` 端点)
- `backend/app/services/agent_chat_service.py` (NEW)
- `backend/tests/data_platform/test_agent_chat.py`
- `frontend/src/components/AgentChatPanel/__tests__/index.test.tsx`
- `.blueprint/qa/T59/pytest.txt`

## Depends on
- T51, T53

## 功能规格
1. 消息 parts 结构参考 Vercel AI SDK
2. SSE 协议：`data: {"type":"tool","state":"input-streaming",...}\n\n`
3. 审批状态挂起 job 直到收到 `/approve` 或 `/deny`
4. 步骤分隔：`step-start` part 渲染为章节标题
5. 中文加载提示："正在分析..." / "调用工具中..." 而非 "thinking"

## Acceptance
- 4 种 tool 状态各自单测
- SSE 断线自动重连
- 审批面板出现时禁用输入框
- pytest 覆盖 stream + approve 流程

## Verify
```bash
cd backend && pytest tests/data_platform/test_agent_chat.py -v
cd frontend && npm run test -- AgentChatPanel
```

## Commit
`feat(agent-chat): streaming tool parts with approval flow`
