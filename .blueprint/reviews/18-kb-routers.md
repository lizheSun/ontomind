# T18 Review — kb routers

## Verdict
APPROVE

## Reasoning
- All 8 files + 2-line router.py append match spec; no touching of models/repos/schemas/services (diff confirmed).
- Every endpoint declares `user_id: int = Depends(get_current_user_id)`; envelope `{code,message,data}` uniform; list endpoints carry `total`.
- CRUD coverage complete for data_assets / code_repos / experiences (POST/GET list/GET/{id}/PUT/DELETE). Documents implements POST /upload (File+Form), GET list, GET/{id}, GET/{id}/download (Content-Disposition + Content-Length), PUT, DELETE. libraries + tags read-only; search uses `Query(..., min_length=1)` and returns `KbSearchGrouped.model_dump()`.
- `__init__.py` mounts all 7 sub-routers with kebab-case prefixes (`/libraries`, `/data-assets`, `/code-repos`, `/documents`, `/experiences`, `/tags`, `/search`); `router.py` diff is strictly additive (import + include_router with prefix `/knowledge-base`, tag `知识库`).
- Smoke evidence in `.blueprint/qa/T18/curl.json` proves: libraries → 4 seed rows, empty `q` → 422 with `string_too_short`, no-token → 401, upload → 201 with `data.id=1` and `storage_path=kb/documents/<uuid>.md`, download returns `content-disposition: attachment; filename="..."` + `content-length: 15`.

## Nice-to-haves (non-blocking)
- Task notes hint at a plain `POST /documents` for metadata-only creation; only `POST /documents/upload` is exposed. Reviewer criteria list does not require it and upload path satisfies acceptance — leaving as follow-up if a metadata-only path is later needed by the frontend.
- Consider using `Path(..., ge=1)` on `{id}` params for consistency with `limit` bounds; low-value polish.
