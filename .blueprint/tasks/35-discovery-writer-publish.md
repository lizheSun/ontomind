# T35 · Discovery service + Writer service + Publish endpoint

## Goal
- `AgentLooperDiscoveryService` — scans `settings.AGENT_CONFIG_PATH` (default `~/.config/opencode/agents/`), parses YAML frontmatter, upserts into `agent_looper_configs` with type=`opencode_native`
- `AgentLooperWriterService` — takes a config, serializes to `.md` frontmatter, writes to `AGENT_CONFIG_PATH/<name>.md` via atomic rename
- `POST /api/v1/agent-looper/discover` — trigger discovery
- `POST /api/v1/agent-looper/configs/{id}/publish` — writes .md to disk

## Files touched
- `backend/app/services/agent_looper_discovery_service.py` (NEW)
- `backend/app/services/agent_looper_writer_service.py` (NEW)
- `backend/app/api/v1/agent_looper/__init__.py` (NEW — aggregator)
- `backend/app/api/v1/agent_looper/discovery.py` (NEW)
- `backend/app/api/v1/agent_looper/configs.py` (NEW — extend with publish endpoint)
- `backend/app/api/v1/router.py` (append)
- `backend/tests/data_platform/test_agent_looper_discovery.py` (NEW)
- `backend/tests/data_platform/test_agent_looper_writer.py` (NEW)
- `.blueprint/qa/T35/pytest.txt`

## Depends on
- T34 (needs AgentLooperConfig model + service)

## Implementation notes

### Discovery service
- `def discover(config_path: Optional[str] = None) -> list[dict]`:
  - Resolve `config_path` or `settings.AGENT_CONFIG_PATH` (expanduser)
  - If path doesn't exist, return empty list — don't fail
  - Walk `*.md` files
  - For each: parse YAML frontmatter (between `---`) using `yaml.safe_load`
  - Extract: `name` (from filename stem), `description`, `mode`, `model`, `temperature`, `steps`, `permission`, and the body text (everything after 2nd `---`)
  - Return list of parsed configs
- `def upsert_discovered(db, configs, user_id) -> int`:
  - For each parsed config: if `agent_looper_configs` has row with `name = stem AND type = 'opencode_native'`, UPDATE it; else INSERT
  - Set `type='opencode_native'`, `is_active=True`, `is_published=True` (it's already on disk)
  - Return count of upserted

### Writer service
- `def publish(config_id, db) -> str`:
  - Load config + latest version
  - Parse `config_json` dict
  - Build YAML frontmatter: `name`, `description`, `mode`, `model`, `temperature`, `steps`, `permission`
  - Only emit fields that opencode understands (NOT loop_strategy, custom_tools, memory_window, resource_bindings, credential_ref, etc.)
  - Body = `config_json.system_prompt`
  - Serialize: `---\n<yaml>\n---\n\n<body>\n`
  - Resolve output path: `AGENT_CONFIG_PATH/<name>.md`
  - Write to `<name>.md.tmp`, then `os.replace(<name>.md.tmp, <name>.md)` (atomic on POSIX)
  - Mark `config.is_published=True`
  - Return path written

### Configs route — extend with publish
- Add `POST /agent-looper/configs/{id}/publish` that calls writer service

### Discovery route — new
- `POST /agent-looper/discover` — calls discovery service, returns upserted count

### Router append
```python
from app.api.v1 import agent_looper
api_router.include_router(agent_looper.router, prefix="/agent-looper", tags=["Agent Looper"])
```

## Verify
```
cd backend
PYTHONPATH=. venv/bin/python -m pytest tests/data_platform/test_agent_looper_discovery.py tests/data_platform/test_agent_looper_writer.py -q --tb=short | tee ../.blueprint/qa/T35/pytest.txt
```

## Commit
`agent: discovery + writer services + publish endpoint`
