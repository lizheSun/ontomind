# T31 · Backend parse-config endpoint

## Goal
New endpoint `POST /api/v1/data-platform/sources/parse-config` — accepts natural-language raw text, returns a parsed `DpDataSourceCreate`-shaped dict (WITHOUT saving). User will review and manually save via existing `POST /sources`.

## Files touched
- `backend/app/services/dp_data_source_service.py` (add class method `parse_config(raw_text: str) -> dict`)
- `backend/app/api/v1/data_platform/sources.py` (add new route)
- `backend/app/schemas/dp_data_source_schema.py` (add `ParseConfigRequest` schema)
- `backend/tests/data_platform/test_dp_parse_config.py` (NEW — mocked LLM tests)
- `.blueprint/qa/T31/pytest.txt`

## Depends on
- None; can run in parallel with T29/T30

## Prompt (from legacy perception.py L127-153 + Wave-8 extensions)

Extend the legacy prompt with:
1. `dialect` output field mapping: `mysql / postgresql / sqlite / mysql_readonly`
2. `read_only_flag: true` default in output JSON
3. `default_schema` field for postgresql
4. Explicit note: **DO NOT extract passwords from raw_text** — always return `password: ""` (user will manually enter)

## Contract

```python
class ParseConfigRequest(BaseModel):
    raw_text: str = Field(..., min_length=1, max_length=10000)

class ParseConfigResult(BaseModel):
    parsed: dict[str, Any]  # DpDataSourceCreate-shaped, password always empty
    model_used: str
    warnings: list[str] = []  # e.g. ["无法识别方言，使用默认 mysql"]
```

## Service method

```python
class DpDataSourceService:
    async def parse_config(self, raw_text: str) -> ParseConfigResult:
        """Parse natural-language config text via LLM. Returns DpDataSourceCreate-shaped dict without password."""
        system_prompt = _PARSE_CONFIG_PROMPT  # module-level constant
        result = await self._llm.chat_completion(
            messages=[{"role":"system","content":system_prompt},{"role":"user","content":raw_text}],
            temperature=0.1, max_tokens=2048,
        )
        content = result["content"].strip()
        # JSON extract with fallback (same regex as legacy L165-172)
        parsed = self._extract_json(content)
        parsed = self._normalize_parsed(parsed)  # alias mapping + coerce port + set password=""
        return ParseConfigResult(parsed=parsed, model_used=result.get("model"), warnings=[])
```

## Tests (TDD)

- `test_parse_config_mysql_env_vars` — happy path, MYSQL_HOST/PORT/DB → dialect=mysql
- `test_parse_config_dialect_default` — text without dialect hint → warnings mention default
- `test_parse_config_password_never_extracted` — even if raw_text contains password, output.parsed.password == ""
- `test_parse_config_readonly_hint` — text mentions "read-only" or "只读" → dialect=mysql_readonly
- `test_parse_config_malformed_llm_response` — LLM returns garbage → 422 with clear message

## Acceptance
- `curl -X POST /api/v1/data-platform/sources/parse-config` with `raw_text=MYSQL_HOST=10.1.1.1...` returns 200 with parsed dict
- password field always empty regardless of input
- 5+ pytest cases pass
- New route protected by `Depends(get_current_user_id)`

## Verify
```
cd backend
PYTHONPATH=. venv/bin/python -m pytest tests/data_platform/test_dp_parse_config.py -q | tee ../.blueprint/qa/T31/pytest.txt
```

## Commit
`dp: parse-config endpoint (LLM-driven natural-language to DpDataSourceCreate)`
