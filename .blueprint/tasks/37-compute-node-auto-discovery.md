# T37 · Compute node auto-discovery (default-load local machine)

## Goal
Extend existing `POST /api/v1/resources/instances/register-local` to auto-discover the local machine as a compute node AND auto-scan opencode agents. Also auto-discover Agent Looper configs from disk.

## Files touched
- `backend/app/api/v1/resources.py` (extend register-local endpoint)
- `backend/app/services/agent_looper_discovery_service.py` (already has scan — reuse)
- `frontend/src/pages/resources/index.tsx` (add "计算节点" section to InstancesPanel showing local machine)
- `frontend/src/services/index.ts` (add resourcesAPI.registerLocal() if not already)
- `backend/tests/data_platform/test_compute_node.py` (NEW)
- `.blueprint/qa/T37/pytest.txt`

## Depends on
- T35 (discovery service)

## Implementation notes
- The existing `POST /api/v1/resources/instances/register-local` already exists (resources.py:L64-158). It registers the local host and auto-discovers agents via `discover_agents`. I need to extend it to also call `AgentLooperDiscoveryService.upsert_discovered` after scanning agents.
- On the frontend InstancesPanel, add a "本地节点" card at the top of the list, showing hostname, platform, and agent count. This card is auto-inserted on page load by calling `register-local` on mount.
- `resourcesAPI.registerLocal()` is already in `services/index.ts` (L7-8) — just call it.

## Verify
```
cd backend
PYTHONPATH=. venv/bin/python -m pytest tests/data_platform/test_compute_node.py -q --tb=short | tee ../.blueprint/qa/T37/pytest.txt
```

## Commit
`agent: compute node auto-discovery (register-local + agent looper scan)`
