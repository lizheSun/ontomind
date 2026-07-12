# T56 · 智能体嵌入框架

## Goal
`<AgentEmbedRunner agentId={id} context={context} onResult={fn} />` React 组件，使用 postMessage 协议与 agent 通信。嵌入到 AIBI 页面（`/application`）与元数据页面（`/data-platform/metadata`）。支持短任务（对话）与长任务（job）。

## Files touched
- `frontend/src/components/AgentEmbedRunner/index.tsx` (NEW)
- `frontend/src/components/AgentEmbedRunner/ChatMode.tsx` (NEW — 短任务)
- `frontend/src/components/AgentEmbedRunner/JobMode.tsx` (NEW — 长任务)
- `frontend/src/components/AgentEmbedRunner/postMessageBridge.ts` (NEW)
- `frontend/src/components/AgentEmbedRunner/types.ts` (NEW — 协议类型)
- `frontend/src/pages/application/aibi/AIBIWorkbench.tsx` (集成)
- `frontend/src/pages/data-platform/metadata/MetadataAnnotator.tsx` (集成)
- `backend/app/services/agent_embed_service.py` (NEW — 桥接调度)
- `backend/app/api/v1/agent_embed.py` (NEW — `POST /agent-embed/{agent_id}/invoke`)
- `frontend/src/components/AgentEmbedRunner/__tests__/index.test.tsx`
- `backend/tests/data_platform/test_agent_embed.py`
- `.blueprint/qa/T56/pytest.txt`

## Depends on
- T51, T55

## postMessage 协议
```
host → embed: { type: "invoke", agentId, input, context, mode: "chat"|"job" }
embed → host: { type: "message" | "tool_call" | "result" | "error", payload }
host → embed: { type: "approve" | "cancel", payload }
```

> 注意：如果是同域同文档（React 组件直接渲染），不需要 postMessage，直接 props 传参即可。
> postMessage 协议仅在 iframe 嵌入场景使用。本 task 采用同域 React 组件方案，不使用 iframe。

## Acceptance
- 组件在两个页面正常运行
- postMessage 协议 5 种事件全部覆盖
- 长任务模式返回 job_id，短任务模式返回同步结果
- pytest 覆盖 invoke / approve / cancel

## Verify
```bash
cd backend && pytest tests/data_platform/test_agent_embed.py -v
cd frontend && npm run test -- AgentEmbedRunner
```

## Commit
`feat(agent-embed): embeddable agent runner with postMessage bridge`
