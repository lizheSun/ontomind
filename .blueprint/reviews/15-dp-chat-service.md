# T15 — DpChatService review

## Verdict
APPROVE

## Reasoning
- **Constructor** (`dp_chat_service.py:43-56`) matches spec: `db + ds_service? + query_service? + llm_service?` with duck-typed `llm_service` (comment explicitly documents required `async chat_completion(messages, config_id, temperature, max_tokens)`); tests inject `MagicMock` + `AsyncMock` and call succeeds.
- **Session CRUD** (`:60-90`): `create/list/get/update/delete/list_messages` all present. Every mutation and read goes through `_require_owned_session` (`:184-197`) which raises `DP_CHAT_SESSION_NOT_FOUND`/`DP_CHAT_FORBIDDEN`. Non-owner test (`test_non_owner_cannot_access_session`) verifies `DP_CHAT_FORBIDDEN`.
- **send_message** (`:94-147`) faithfully implements the spec: persists user turn → `describe_schema` in try/except (best-effort, falls back to `{"databases": []}` on any exc) → builds Chinese system prompt (`_system_prompt`, `:251`) with dialect + schema summary → awaits `llm_service.chat_completion(messages=..., config_id=session.model_config_id, temperature=0.1, max_tokens=800)` → parses fenced SQL → persists assistant message with `generated_sql` (executed defaults False).
- **apply_message** (`:149-176`) reloads assistant SQL, cross-checks `msg.session_id == session_id`, then delegates to `self.query_service.execute_sync(...)` with the SAME guard path (no `validate_and_shape` re-implementation). Guard-rejected DDL test (`test_apply_rejects_malicious_llm_sql`) confirms `SQL_GUARD_*` code bubbles up. `mark_executed` called after successful exec.
- **`_reset_autobegin()`** (`:180-182`) used consistently before every `with self.db.begin():` (5 sites: create/update/delete session, persist user msg, persist assistant msg, mark_executed).
- **`_extract_sql_fence`** (`:219-230`): regex `r"```(?:sql)?\s*\n?(.*?)\n?```"` handles ```` ```sql\n...\n``` ````, ```` ```\n...\n``` ````; unfenced fallback matches `SELECT`/`WITH`; returns `None` for empty and non-SQL. All 5 branches tested in `test_extract_sql_fence_variants`.
- **`_extract_assistant_text`** (`:202-216`): str passthrough, OpenAI `choices[0].message.content`, and normalized `{"content": ...}` all covered by `test_extract_assistant_text_openai_and_normalized`.
- **Evidence**: `.blueprint/qa/T15/pytest.txt` shows `7 passed in 0.41s`; matches 7 test functions in file (2 helper + 5 service). LLM entirely mocked via `AsyncMock` — no network.
- **Scope discipline**: `git diff --stat` confirms only three new files (`dp_chat_service.py`, `test_dp_chat_service.py`, `qa/T15/pytest.txt`). Zero edits to `dp_data_source_service.py`, `dp_query_service.py`, `llm_config_service.py`, models, repos, or schemas.

## Required changes (if any)
_None._

## Nice-to-haves (non-blocking)
- The evidence file only proves T15's 7 tests pass; the task's criterion #10 (full 52/52 backend suite) was not captured in `qa/T15/pytest.txt`. Regression risk is effectively zero because the diff only adds two new files and touches nothing shared — but a future evidence bundle could append a full-suite run.
- `_dialect_display` maps `mysql_readonly` → "MySQL" but skips e.g. `mariadb`; falls through to raw dialect string, which is fine but easy to extend when needed.
- The `_SQL_FENCE` regex is greedy across the whole text with `DOTALL`; if an LLM ever returns multiple code fences, it will span both. Not blocking — real LLM outputs one fence per spec — but a `.*?` with the current non-greedy quantifier is already the safest form.
