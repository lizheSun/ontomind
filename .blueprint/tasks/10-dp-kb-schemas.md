# T10 — Pydantic v2 schemas for dp + kb

## Goal
Create request/response schemas for every endpoint listed in recon. All schemas Pydantic v2 with `model_config = {"from_attributes": True}`. Never expose plaintext or ciphertext password on read schemas.

## Files touched
- `backend/app/schemas/dp_data_source_schema.py`  (NEW)
- `backend/app/schemas/dp_query_schema.py`  (NEW — SqlExecuteRequest, SqlExecuteResponse, SavedQueryRead/Create/Update, QueryHistoryRead)
- `backend/app/schemas/dp_chat_schema.py`  (NEW — SessionCreate/Read, MessageCreate, MessageRead)
- `backend/app/schemas/kb_library_schema.py`  (NEW)
- `backend/app/schemas/kb_data_asset_schema.py`  (NEW)
- `backend/app/schemas/kb_code_repo_schema.py`  (NEW)
- `backend/app/schemas/kb_document_schema.py`  (NEW)
- `backend/app/schemas/kb_experience_schema.py`  (NEW)
- `backend/app/schemas/kb_tag_schema.py`  (NEW)
- `backend/app/schemas/kb_search_schema.py`  (NEW — grouped response)

## Depends on
- T06, T07

## Implementation notes
- `DpDataSourceCreate`: name, source_type, dialect (Literal), host, port, username, password (SecretStr), database, default_schema?, description?, read_only_flag=True.
- `DpDataSourceUpdate`: all optional; `password` optional (empty = keep existing).
- `DpDataSourceRead`: exposes NOTHING password-related; adds `has_password: bool`.
- `SqlExecuteRequest`: sql, max_rows: int = 1000.
- `SqlExecuteResponse`: columns: list[str], rows: list[list[Any]], row_count, elapsed_ms.
- `QueryHistoryRead`: id, sql_text (truncated to 500 chars on list), status, row_count, elapsed_ms, error_message, started_at.
- KB schemas mirror model columns 1:1; `Create` excludes id/timestamps; `Read` includes `tags: list[str]`, `owner_user_id`.
- `KbSearchResult`: `library_code`, `id`, `title`, `snippet`, `score` (LIKE match count).

## Acceptance
- `python -c "from app.schemas import dp_data_source_schema, dp_query_schema, dp_chat_schema, kb_data_asset_schema, kb_code_repo_schema, kb_document_schema, kb_experience_schema, kb_search_schema; print('ok')"`.
- `mypy` (if configured) passes; pydantic v2 semantics respected.

## Verify
```bash
cd backend && python -c "from app.schemas.dp_data_source_schema import DpDataSourceRead; DpDataSourceRead.model_validate({'id':1,'name':'x','source_type':'mysql','dialect':'mysql','database':'d','has_password':True,'created_at':'2025-01-01','updated_at':'2025-01-01','owner_user_id':1,'read_only_flag':True})" | tee ../.blueprint/qa/T10/schema.txt
```

## Commit
`dp+kb: Pydantic v2 schemas (no plaintext password exposure)`
