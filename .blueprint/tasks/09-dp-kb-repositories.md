# T09 — repositories for dp + kb

## Goal
Add repository classes for all 11 models, each extending `BaseRepository[Model]`, with domain-specific query methods.

## Files touched
- `backend/app/db/repositories/dp_data_source_repo.py`  (NEW)
- `backend/app/db/repositories/dp_sql_query_repo.py`  (NEW)
- `backend/app/db/repositories/dp_query_history_repo.py`  (NEW)
- `backend/app/db/repositories/dp_chat_repo.py`  (NEW — sessions + messages)
- `backend/app/db/repositories/kb_library_repo.py`  (NEW)
- `backend/app/db/repositories/kb_data_asset_repo.py`  (NEW)
- `backend/app/db/repositories/kb_code_repo_repo.py`  (NEW)
- `backend/app/db/repositories/kb_document_repo.py`  (NEW)
- `backend/app/db/repositories/kb_experience_repo.py`  (NEW)
- `backend/app/db/repositories/kb_tag_repo.py`  (NEW)

## Depends on
- T06, T07

## Implementation notes
- All repos: `list_by_owner(user_id, ...)`, `get_by_id(id)`, `create(payload)`, `update(id, payload)`, `delete(id)`.
- `dp_query_history_repo`: `list_recent(user_id, source_id, limit=50)`, `create_running(...)`, `mark_success(id, row_count, elapsed_ms, columns_json)`, `mark_error(id, msg)`.
- `dp_chat_repo`: exposes both `list_sessions(user_id)`, `create_session(...)`, `append_message(session_id, role, content, generated_sql?)`, `list_messages(session_id)`.
- KB sub-lib repos share `search_like(q, limit=20)` returning matches on title + description.
- `kb_document_repo.create_with_file(...)` writes file to `UPLOAD_DIR/kb/documents/<uuid>.<ext>` and persists row.

## Acceptance
- `pytest backend/tests/repositories -q` — smoke test each repo with in-memory sqlite or transactional rollback fixture.

## Verify
```bash
cd backend && pytest tests/repositories -q --tb=short | tee ../.blueprint/qa/T09/pytest.txt
```

## Commit
`dp+kb: add repositories with owner-scoped queries and history/chat helpers`
