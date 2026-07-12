# T01 — backend deps + Fernet + config

## Goal
Install sqlglot / sqlparse / sse-starlette; wire `FERNET_KEY` into `app/core/config.py`; boot guard that logs a loud loguru error when key is missing and short-circuits `dp_data_sources` create/update.

## Files touched
- `backend/requirements.txt`
- `backend/app/core/config.py`
- `backend/app/core/crypto.py`  (NEW)
- `backend/.env.example`

## Depends on
- None

## Implementation notes
- Pin `sqlglot==30.12.0`, `sqlparse==0.5.5`, `sse-starlette==3.4.5`.
- `crypto.py` exposes `encrypt(str) -> str`, `decrypt(str) -> str`, `require_key_or_raise()` using `MultiFernet` if `FERNET_KEY` contains commas.
- On import, if key missing set module flag `ENCRYPTION_DISABLED = True` and `logger.error` a Chinese-tagged message.

## Acceptance
- `pip install -r backend/requirements.txt` succeeds.
- `python -c "from app.core.crypto import encrypt, decrypt; import os; os.environ.setdefault('FERNET_KEY', 'x'*44); print(decrypt(encrypt('hi')))"` prints `hi`.
- `python -c "from app.core import crypto; crypto.ENCRYPTION_DISABLED"` prints True when key missing.

## Verify
```bash
cd backend && pip install -r requirements.txt
python -c "from app.core.crypto import encrypt, decrypt; import os; os.environ['FERNET_KEY']='XX...44chars...'; print(decrypt(encrypt('hi')))"
# → hi
```
Save stdout to `.blueprint/qa/T01/output.txt`.

## Commit
`deps: add sqlglot/sqlparse/sse-starlette + Fernet crypto module`
