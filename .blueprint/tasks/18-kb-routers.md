# T18 — kb routers + registration

## Goal
Create routers for all knowledge-base endpoints; register with prefix `/knowledge-base`, tag `知识库`.

## Files touched
- `backend/app/api/v1/knowledge_base/libraries.py`  (NEW)
- `backend/app/api/v1/knowledge_base/data_assets.py`  (NEW)
- `backend/app/api/v1/knowledge_base/code_repos.py`  (NEW)
- `backend/app/api/v1/knowledge_base/documents.py`  (NEW — CRUD + upload + download)
- `backend/app/api/v1/knowledge_base/experiences.py`  (NEW)
- `backend/app/api/v1/knowledge_base/tags.py`  (NEW)
- `backend/app/api/v1/knowledge_base/search.py`  (NEW)
- `backend/app/api/v1/knowledge_base/__init__.py`  (NEW)
- `backend/app/api/v1/router.py`  (append)

## Depends on
- T16

## Implementation notes
- All endpoints protected via `Depends(get_current_user_id)`.
- `POST /documents/upload`: `UploadFile`; `POST /documents` for metadata-only.
- `GET /search?q=...&library_code=?` returns grouped results.

## Acceptance
- `curl` to each list endpoint returns 200 empty list (fresh DB).
- Upload endpoint accepts a file and returns row with `storage_path`.

## Verify
```bash
cd backend && uvicorn app.main:app --port 8000 &
sleep 3
TOKEN=$(python scripts/mint_test_token.py)
curl -sS -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/knowledge-base/libraries | tee ../.blueprint/qa/T18/libraries.json
curl -sS -H "Authorization: Bearer $TOKEN" -F "file=@README.md" -F "title_zh=测试文档" http://localhost:8000/api/v1/knowledge-base/documents/upload | tee ../.blueprint/qa/T18/upload.json
kill %1
```

## Commit
`kb: FastAPI routers (libraries/4-sublibs/upload/download/search)`
