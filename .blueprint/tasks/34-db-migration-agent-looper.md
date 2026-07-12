# T34 · DB migration + AgentLooperService CRUD + version management

## Goal
3 new tables + service class with CRUD, version chain, soft-delete.

## Files touched
- `backend/app/db/models/agent_looper_config_model.py` (NEW)
- `backend/app/db/models/agent_looper_version_model.py` (NEW)
- `backend/app/db/models/agent_looper_test_run_model.py` (NEW)
- `backend/app/db/models/__init__.py` (append imports)
- `backend/app/db/repositories/agent_looper_repo.py` (NEW — ConfigRepo + VersionRepo + TestRunRepo)
- `backend/app/services/agent_looper_service.py` (NEW — CRUD + version chain + rollback)
- `backend/app/schemas/agent_looper_schema.py` (NEW — Create/Update/Read/VersionRead)
- `backend/app/core/config.py` (add AGENT_CONFIG_PATH, AGENT_LOOPER_TEST_RUNS_TTL settings)
- `backend/tests/data_platform/test_agent_looper_service.py` (NEW — 10+ tests)
- `.blueprint/qa/T34/pytest.txt`

## Depends on
- None

## Implementation notes

### Models (3 files)

**agent_looper_config_model.py**:
```python
class AgentLooperConfig(BaseModel):
    __tablename__ = "agent_looper_configs"
    name = Column(String(128), nullable=False)  # unique per owner
    type = Column(String(32), nullable=False, server_default="custom_looper", comment="custom_looper/opencode_native/mcp_agent/imported")
    description = Column(Text, nullable=True)
    current_version_id = Column(Integer, ForeignKey("agent_looper_versions.id"), nullable=True)
    active_config_json = Column(Text, nullable=True, comment="LONGTEXT: full JSON schema")
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="1")
    is_published = Column(Boolean, nullable=False, server_default="0")
    settings = Column(JSON, nullable=True, comment="path overrides etc")
    resource_bindings = Column(JSON, nullable=True)
    credential_ref = Column(JSON, nullable=True, comment="{credential_type: dp_source, credential_id: int}")
```

**agent_looper_version_model.py**:
```python
class AgentLooperVersion(BaseModel):
    __tablename__ = "agent_looper_versions"
    __table_args__ = (Index("ix_agent_looper_versions_config_id_version", "config_id", "version_number", unique=True),)
    config_id = Column(Integer, ForeignKey("agent_looper_configs.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False, server_default="1")
    config_json = Column(Text, nullable=False, comment="LONGTEXT: full snapshot")
    model_snapshot = Column(String(256), nullable=True)
    prompt_snapshot = Column(Text, nullable=True)
    note = Column(String(256), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
```

**agent_looper_test_run_model.py**:
```python
class AgentLooperTestRun(BaseModel):
    __tablename__ = "agent_looper_test_runs"
    config_id = Column(Integer, ForeignKey("agent_looper_configs.id", ondelete="CASCADE"), nullable=False)
    version_id = Column(Integer, ForeignKey("agent_looper_versions.id"), nullable=True)
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    status = Column(String(32), nullable=False, server_default="running")
    error = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # created_at from BaseModel used for TTL purge
```

### Config additions

Add to `Settings` class:
```python
AGENT_CONFIG_PATH: str = "~/.config/opencode/agents"
AGENT_LOOPER_TEST_RUNS_TTL_DAYS: int = 30
```

### Service

`AgentLooperService`:
- `create(payload, user_id) -> AgentLooperConfigRead` — creates config + first version (version_number=1), sets `current_version_id`
- `get_by_id(id) -> AgentLooperConfigRead` — includes current version's config_json
- `list_by_owner(user_id, type=None, is_active=None) -> list[]`
- `update(id, payload, user_id) -> AgentLooperConfigRead` — creates NEW version row (version_number++), updates `current_version_id`, updates `active_config_json`
- `rollback(id, target_version_number, user_id) -> AgentLooperConfigRead` — copies that version's config_json into a NEW version row (version_number = max+1), updates `current_version_id`
- `soft_delete(id, user_id)`
- `get_version_history(config_id) -> list[VersionRead]`
- Version number auto-increment: `SELECT COALESCE(MAX(version_number), 0) + 1 FROM agent_looper_versions WHERE config_id = :id`
- On create, config_json = active_config_json = the full schema JSON
- On update, config_json = new full snapshot, active_config_json updated to match

### Tests (10+ cases)
- Create config → version 1 present, current_version_id set
- Update config → version 2 present, current_version_id updated
- Rollback to version 1 → version 3 created with version 1's config_json
- list_by_owner filters by user
- Soft-delete hides from list
- Non-owner cannot update/delete/rollback
- Version history returns ordered rows
- Default type=custom_looper applied
- `is_published` flag works
- Resource bindings stored correctly

## Verify
```
cd backend
PYTHONPATH=. venv/bin/python -m pytest tests/data_platform/test_agent_looper_service.py -q --tb=short | tee ../.blueprint/qa/T34/pytest.txt
```

## Commit
`agent: DB migration + AgentLooperService CRUD + version management`
