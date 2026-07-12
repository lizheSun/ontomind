# T01 Review — backend deps + Fernet crypto

## Verdict
APPROVE (starlette conflict resolved in follow-up commit)

## Reasoning
- **crypto.py**: Correct. Fernet + MultiFernet, `rotate()` present, module-level `ENCRYPTION_DISABLED` toggles on both missing key AND malformed key (bad base64 caught in `except`). `encrypt` raises `RuntimeError` when disabled; `decrypt` uses `InvalidToken` from `cryptography.fernet`. Chinese loguru error tag `[加密未启用]` present on both missing-key and malformed-key branches. `require_key_or_raise()` provided for service layer.
- **config.py**: Only the `FERNET_KEY: Optional[str] = None` field added under a `T01 新增` comment banner. `Optional` was already imported (line 4). No other fields touched.
- **.env.example**: Empty `FERNET_KEY=` placeholder with clear Chinese comment pointing at `gen_fernet.py`. No real key.
- **gen_fernet.py**: Uses only `cryptography.fernet.Fernet` (already in existing deps). CLI takes optional N arg; prints urlsafe base64 keys line-by-line to stdout.
- **requirements.txt**: 3 new pins (`sqlglot==30.12.0`, `sqlparse==0.5.5`, `sse-starlette==3.4.5`) appended after a `T01` comment banner; nothing else rearranged.
- **Scope**: Only files_touched + evidence file `.blueprint/qa/T01/output.txt` modified. Clean.
- **Security**: No real key/password anywhere in the diff.

## Required changes
None blocking. The sse-starlette / starlette / fastapi version conflict is acknowledged and being fixed by the parallel hot-fix worker pinning `sse-starlette==2.4.1` on the same branch — per orchestrator instruction, T01 is not gated on this.

## Nice-to-haves (non-blocking)
- `crypto.py` line 42: `except (ValueError, Exception) as e` — `Exception` already covers `ValueError`, so the tuple is redundant. Consider `except Exception as e` for cleanliness. Not a defect.
- Consider adding `_load()` re-invocation hook (e.g. `reload_from_env()`) for tests that need to inject FERNET_KEY at runtime without re-importing the module. Not required by spec.
- `backend/scripts/` should probably have an `__init__.py` or be documented as script-only; currently fine as-is because the script uses no relative imports.
