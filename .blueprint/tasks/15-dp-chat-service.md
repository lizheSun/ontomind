# T15 — dp chat service (text-to-SQL)

## Goal
`DpChatService` manages chat sessions, calls `llm_config_service.chat_completion` to translate user prompt + schema summary into SQL, returns preview SQL to user without executing; `apply_message` runs the previewed SQL through the SAME guard + query service pipeline.

## Files touched
- `backend/app/services/dp_chat_service.py`  (NEW)
- `backend/tests/data_platform/test_dp_chat_service.py`  (NEW — TDD w/ mocked LLM)

## Depends on
- T09, T10, T14

## Implementation notes
- `create_session(source_id, model_config_id?, name?, user_id)`.
- `list_sessions(user_id)` / `get_session(id, user_id)` / `list_messages(session_id, user_id)`.
- `send_message(session_id, content, user_id, stream: bool) -> MessageRead | AsyncIterator`:
  - Persist user message.
  - Build system prompt: role=SQL analyst, dialect=..., schema summary (first 30 tables' names + top columns).
  - Call `llm_config_service.chat_completion(messages, config_id, temperature=0.1, max_tokens=800)`.
  - Extract SQL from ```sql``` fenced block; strip; store on assistant message `generated_sql`.
  - Return assistant message OR yield SSE `token` events + final `sql` event when stream.
- `apply_message(session_id, message_id, user_id) -> SqlExecuteResponse`:
  - Load assistant message; ensure `generated_sql`.
  - Delegate to `dp_query_service.execute_sync(...)`.
  - Set `executed=True`.

## Acceptance
- Tests: mocked LLM returns fenced SQL → parsed; malicious SQL from LLM (`DROP TABLE users`) → guard rejects on apply; non-owner cannot apply.

## Verify
```bash
cd backend && pytest tests/data_platform/test_dp_chat_service.py -q --tb=short | tee ../.blueprint/qa/T15/pytest.txt
```

## Commit
`dp: chat service (text-to-SQL preview + guarded apply)`
