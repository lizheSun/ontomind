# T36 · Test endpoint (SSE) + parseConfig/chat backend integration for agent looper

## Goal
- `POST /api/v1/agent-looper/configs/{id}/test` — SSE stream calling LLMConfigService with agent's system_prompt + model + temperature
- Extend `ParseConfigRequest` + `DpDataSourceService.parse_config` to accept `agent_looper_config_id`
- Extend `SessionCreate` + `DpChatService` to accept `agent_looper_config_id`
- `POST /api/v1/agent-looper/test-runs/{id}` — list test history (with TTL purge)

## Files touched
- `backend/app/api/v1/agent_looper/test.py` (NEW — SSE endpoint + test run persistence)
- `backend/app/schemas/dp_data_source_schema.py` (extend ParseConfigRequest)
- `backend/app/schemas/dp_chat_schema.py` (extend SessionCreate/SessionUpdate/SessionRead)
- `backend/app/services/dp_data_source_service.py` (extend parse_config)
- `backend/app/services/dp_chat_service.py` (extend send_message to use agent_looper)
- `backend/app/scripts/purge_test_runs.py` (NEW — cron-able script)
- `backend/tests/data_platform/test_agent_looper_test.py` (NEW)
- `.blueprint/qa/T36/pytest.txt`

## Depends on
- T34, T35

## Implementation notes

### Test endpoint
```python
@router.post("/configs/{config_id}/test")
async def test_agent_looper(
    config_id: int,
    payload: TestRunRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """模型联通测试 · Prompt 试跑。使用 Agent 的 system_prompt 发送一次 chat_completion，SSE 流式回显。"""
    svc = AgentLooperService(db)
    config = svc.get_by_id(config_id, user_id)
    version = svc.get_version(config.current_version_id)
    config_json = version.config_json if isinstance(version.config_json, dict) else json.loads(version.config_json)
    
    prompt = config_json.get("system_prompt", "")
    model = config_json.get("model", None)
    temperature = config_json.get("temperature", 0.7)
    
    async def event_gen():
        started = time.perf_counter()
        # Record test run
        run = TestRunRepository(db).create(config_id=config_id, version_id=version.id, 
                                            prompt=payload.prompt, user_id=user_id, status="running")
        try:
            llm = LLMConfigService(db)
            # Use the agent's model config — find best match in llm_configs
            # For v1, just use the default active LLM config with the agent's temperature
            result = await llm.chat_completion(
                messages=[{"role": "system", "content": f"{prompt}\n\n用户提示: {payload.prompt}"}],
                temperature=temperature,
                max_tokens=config_json.get("guardrails", {}).get("max_tokens", 2048),
            )
            elapsed = int((time.perf_counter() - started) * 1000)
            response_text = result.get("content", "")
            # Mark success
            TestRunRepository(db).update(run.id, status="success", response=response_text, latency_ms=elapsed)
            # SSE: yield tokens word-by-word for streaming effect
            words = response_text.split(" ")
            for i, w in enumerate(words):
                yield {"event": "text", "data": w + (" " if i < len(words)-1 else "")}
                await asyncio.sleep(0.02)
            yield {"event": "done", "data": json.dumps({"latency_ms": elapsed, "model": result.get("model", "unknown")})}
        except Exception as e:
            TestRunRepository(db).update(run.id, status="error", error=str(e))
            yield {"event": "error", "data": str(e)}
    
    return EventSourceResponse(event_gen())
```

### Extend ParseConfigRequest
```python
class ParseConfigRequest(BaseModel):
    raw_text: str = Field(..., min_length=1, max_length=10000)
    agent_looper_config_id: Optional[int] = Field(None, description="指定解析 Agent（默认=平台 LLM）")
```

### Extend DpDataSourceService.parse_config
Branch on `agent_looper_config_id`: if provided, find the config, get its system_prompt, use it as the system prompt for the LLM call (instead of the default `_PARSE_CONFIG_PROMPT`). If not provided, use existing behavior.

### Extend SessionCreate/SessionRead
```python
class SessionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    source_id: int
    model_config_id: Optional[int] = None
    agent_looper_config_id: Optional[int] = Field(None, description="指定 Agent（优先于 model_config_id）")
```

### Extend DpChatService.send_message
In the system prompt building section (currently L124-129), if `session.agent_looper_config_id` is set, load the config's system_prompt and use it as the system prompt for the LLM call. If both agent_looper_config_id and model_config_id are set, agent_looper wins.

Also add `agent_looper_config_id` to the model's `dp_chat_session_model.py`:
```python
agent_looper_config_id = Column(Integer, ForeignKey("agent_looper_configs.id"), nullable=True, comment="指定 Agent（优先于 model_config_id）")
```

### Test run purge script
```python
"""剧本：清理超过 30 天的测试运行记录。"""
from app.core.config import settings
from app.db.session import SessionLocal
from app.db.models.agent_looper_test_run_model import AgentLooperTestRun
from datetime import datetime, timedelta

def purge_old_test_runs():
    days = settings.AGENT_LOOPER_TEST_RUNS_TTL_DAYS
    cutoff = datetime.utcnow() - timedelta(days=days)
    db = SessionLocal()
    try:
        deleted = db.query(AgentLooperTestRun).filter(AgentLooperTestRun.created_at < cutoff).delete()
        db.commit()
        print(f"Purged {deleted} test runs older than {days} days")
    finally:
        db.close()
```

## Verify
```
cd backend
PYTHONPATH=. venv/bin/python -m pytest tests/data_platform/test_agent_looper_test.py -q --asyncio-mode=auto --tb=short | tee ../.blueprint/qa/T36/pytest.txt
```

## Commit
`agent: test endpoint (SSE) + parseConfig/chat backend integration`
