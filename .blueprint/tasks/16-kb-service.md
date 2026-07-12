# T16 — kb service (4 sub-libs CRUD + upload + search)

## Goal
`KbService` handles CRUD for data-assets / code-repos / documents / experiences, tag pool management, document upload/download, and aggregated cross-library `LIKE` search.

## Files touched
- `backend/app/services/kb_service.py`  (NEW)
- `backend/tests/knowledge_base/test_kb_service.py`  (NEW — TDD)

## Depends on
- T09, T10

## Implementation notes
- `list_libraries()` returns 4 rows ordered by `order`.
- For each sub-lib expose `list_*(owner_only=False, tag=None, q=None)`, `create_*`, `update_*`, `delete_*`.
- `upload_document(file: UploadFile, meta, user_id) -> KbDocumentRead`:
  - Persist file to `UPLOAD_DIR/kb/documents/<uuid>.<ext>` (create dir if absent).
  - `mime_type = file.content_type`, `size_bytes = file.size`.
  - Persist row.
- `download_document(id, user_id) -> FileResponse`.
- `search_all(q, library_code?, limit=20) -> {"data_asset":[...], "code_repo":[...], "document":[...], "experience":[...]}` via per-repo `search_like`.

## Acceptance
- Tests: CRUD each sublib, tag reuse, upload persists file + row (asserted with tmp UPLOAD_DIR), download returns file bytes, search returns grouped results.

## Verify
```bash
cd backend && pytest tests/knowledge_base/test_kb_service.py -q --tb=short | tee ../.blueprint/qa/T16/pytest.txt
```

## Commit
`kb: service (4-sublib CRUD + upload/download + aggregated search)`
