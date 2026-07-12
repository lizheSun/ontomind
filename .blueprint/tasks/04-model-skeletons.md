# T04 — model skeleton files

## Goal
Create empty SQLAlchemy 2.0 model class stubs (declared but no columns beyond id/created_at/updated_at inherited from `BaseModel`) so downstream tasks can import them in parallel without merge conflicts.

## Files touched
- `backend/app/db/models/dp_data_source_model.py`  (NEW)
- `backend/app/db/models/dp_sql_query_model.py`  (NEW)
- `backend/app/db/models/dp_query_history_model.py`  (NEW)
- `backend/app/db/models/dp_chat_session_model.py`  (NEW)
- `backend/app/db/models/dp_chat_message_model.py`  (NEW)
- `backend/app/db/models/kb_library_model.py`  (NEW)
- `backend/app/db/models/kb_data_asset_model.py`  (NEW)
- `backend/app/db/models/kb_code_repo_model.py`  (NEW)
- `backend/app/db/models/kb_document_model.py`  (NEW)
- `backend/app/db/models/kb_experience_model.py`  (NEW)
- `backend/app/db/models/kb_tag_model.py`  (NEW)

## Depends on
- None

## Implementation notes
- Each file: `from app.db.base import BaseModel` + minimal class inheriting BaseModel + `__tablename__ = "dp_data_sources"` etc.
- NO columns yet beyond inherited — T06/T07 will fill them.
- Do NOT register in `models/__init__.py` yet (T06/T07 does that atomically).

## Acceptance
- `python -c "from app.db.models import dp_data_source_model; print(dp_data_source_model.DpDataSource.__tablename__)"` → `dp_data_sources`.
- 11 new files created.

## Verify
```bash
cd backend && python -c "import importlib; [importlib.import_module(f'app.db.models.{m}') for m in ['dp_data_source_model','dp_sql_query_model','dp_query_history_model','dp_chat_session_model','dp_chat_message_model','kb_library_model','kb_data_asset_model','kb_code_repo_model','kb_document_model','kb_experience_model','kb_tag_model']]; print('ok')"
```
Save to `.blueprint/qa/T04/output.txt`.

## Commit
`dp+kb: scaffold empty SQLAlchemy model stubs`
