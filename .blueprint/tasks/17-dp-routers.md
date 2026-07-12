# T17 — dp routers + registration

## Goal
Create routers for all data-platform endpoints per recon URL list; register in `api/v1/router.py` with prefix `/data-platform`, Chinese tag `数据平台`.

## Files touched
- `backend/app/api/v1/data_platform/sources.py`  (NEW)
- `backend/app/api/v1/data_platform/execute.py`  (NEW — sync + stream)
- `backend/app/api/v1/data_platform/saved_queries.py`  (NEW)
- `backend/app/api/v1/data_platform/history.py`  (NEW)
- `backend/app/api/v1/data_platform/chat.py`  (NEW — sessions + messages + apply, SSE)
- `backend/app/api/v1/data_platform/__init__.py`  (NEW — aggregates sub-routers)
- `backend/app/api/v1/router.py`  (append include)

## Depends on
- T13, T14, T15

## Implementation notes
- Every endpoint: `Depends(get_current_user_id)`.
- Envelope returned via existing global `BusinessException` handler.
- SSE endpoints use `EventSourceResponse` from `sse-starlette`; media_type `text/event-stream`.
- `POST /sources/{id}/execute` sync JSON; `GET /sources/{id}/execute/stream?sql=<urlenc>&max_rows=100000` SSE.
- Chat send: `POST /chat/sessions/{sid}/messages` with `?stream=true` toggles SSE.

## Acceptance
- `curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/data-platform/sources` returns 200 + envelope.
- Without token → 401.
- OpenAPI docs at `/docs` show all endpoints under tag `数据平台`.

## Verify
```bash
cd backend && uvicorn app.main:app --port 8000 &
sleep 3
TOKEN=$(python scripts/mint_test_token.py)
curl -sS -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/data-platform/sources | tee ../.blueprint/qa/T17/curl.json
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:8000/api/v1/data-platform/sources | tee -a ../.blueprint/qa/T17/curl.json  # → 401
kill %1
```

## Commit
`dp: FastAPI routers (sources/execute/history/saved/chat + SSE)`
