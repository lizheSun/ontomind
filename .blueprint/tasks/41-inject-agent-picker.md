# T41 · Inject AgentPicker into SmartAddModal + ChatTab

## Goal
Replace the static "平台 LLM" behavior in SmartAddModal and ChatTab with the shared `<AgentPicker>` component from T40.

## Files touched
- `frontend/src/pages/data-platform/components/SmartAddModal.tsx` (add AgentPicker + pass agent_looper_config_id to parseConfig)
- `frontend/src/pages/data-platform/tabs/ChatTab.tsx` (add AgentPicker + pass to createSession)
- `frontend/src/services/dataPlatform.service.ts` (extend parseConfig, createSession signatures)
- `.blueprint/qa/T41/vitest.txt`

## Depends on
- T40 (AgentPicker component exists)

## Implementation
- SmartAddModal: add `AgentPicker` with `includePlatformLlm` above the TextArea; pass `agent_looper_config_id` to the `parseConfig` call
- ChatTab: add `AgentPicker` in the header row between the title and the session Dropdown; thread `agent_looper_config_id` into `createSession`
- dataPlatform.service.ts: extend `parseConfig` to accept optional `agentLooperConfigId`; extend `createSession` to accept optional `agentLooperConfigId`

## Verify
```
cd frontend
npx vitest run --reporter=verbose 2>&1 | tail -20
```
Expect 32+ tests.

## Commit
`ui: inject AgentPicker into SmartAddModal + ChatTab`
