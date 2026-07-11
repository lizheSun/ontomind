"""dp parse-config TDD: mocked LLM 覆盖 8 条分支（happy / password-strip / dialect
fallback / readonly hint / postgres 缺省 / 422 malformed / 502 LLM error / markdown-fence unwrap）。"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import BusinessException
from app.services.dp_data_source_service import DpDataSourceService


_LLM_PATCH_TARGET = "app.services.llm_config_service.LLMConfigService.chat_completion"


@pytest.mark.asyncio
async def test_parse_config_mysql_env_vars_happy(db):
    svc = DpDataSourceService(db)
    mock_reply = json.dumps({
        "name": "MySQL 业务库", "source_type": "mysql", "dialect": "mysql",
        "host": "10.1.1.1", "port": 3306, "username": "readonly", "password": "",
        "database": "orders", "charset": "utf8mb4", "default_schema": None,
        "description": "订单业务库", "read_only_flag": True,
    })
    with patch(_LLM_PATCH_TARGET, new=AsyncMock(return_value={"content": mock_reply, "model": "test-model"})):
        result = await svc.parse_config(
            "MYSQL_HOST=10.1.1.1\nMYSQL_PORT=3306\nMYSQL_USER=readonly\nMYSQL_DB=orders"
        )
    assert result.parsed["dialect"] == "mysql"
    assert result.parsed["host"] == "10.1.1.1"
    assert result.parsed["port"] == 3306
    assert result.parsed["password"] == ""
    assert result.model_used == "test-model"


@pytest.mark.asyncio
async def test_parse_config_password_always_empty_even_if_llm_returns_one(db):
    svc = DpDataSourceService(db)
    mock_reply = json.dumps({
        "name": "X", "source_type": "mysql", "dialect": "mysql",
        "host": "h", "port": 3306, "username": "u",
        "password": "SUPER_SECRET_LEAK",
        "database": "d", "charset": "utf8mb4", "read_only_flag": True,
    })
    with patch(_LLM_PATCH_TARGET, new=AsyncMock(return_value={"content": mock_reply, "model": "test-model"})):
        result = await svc.parse_config("... maybe includes MYSQL_PASSWORD=xxx ...")
    assert result.parsed["password"] == ""
    assert any("密码字段已被拦截" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_parse_config_dialect_default_when_unknown(db):
    svc = DpDataSourceService(db)
    mock_reply = json.dumps({"name": "?", "host": "h", "database": "d"})
    with patch(_LLM_PATCH_TARGET, new=AsyncMock(return_value={"content": mock_reply, "model": "m"})):
        result = await svc.parse_config("some random text")
    assert result.parsed["dialect"] == "mysql"
    assert any("dialect" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_parse_config_readonly_hint(db):
    svc = DpDataSourceService(db)
    mock_reply = json.dumps({
        "name": "只读副本", "source_type": "mysql", "dialect": "mysql_readonly",
        "host": "readonly.example", "port": 3306, "username": "ro",
        "database": "ro_db", "charset": "utf8mb4", "read_only_flag": True,
    })
    with patch(_LLM_PATCH_TARGET, new=AsyncMock(return_value={"content": mock_reply, "model": "m"})):
        result = await svc.parse_config("生产只读副本，只读用户 ro，库名 ro_db，地址 readonly.example")
    assert result.parsed["dialect"] == "mysql_readonly"


@pytest.mark.asyncio
async def test_parse_config_postgresql_default_port_and_schema(db):
    svc = DpDataSourceService(db)
    mock_reply = json.dumps({
        "name": "PG", "source_type": "postgresql", "dialect": "postgresql",
        "host": "pg.local", "username": "u",
        "database": "analytics", "default_schema": "public",
        "charset": "utf8mb4", "read_only_flag": True,
    })
    with patch(_LLM_PATCH_TARGET, new=AsyncMock(return_value={"content": mock_reply, "model": "m"})):
        result = await svc.parse_config("PG_HOST=pg.local PG_USER=u PG_DB=analytics")
    assert result.parsed["dialect"] == "postgresql"
    assert result.parsed["port"] == 5432
    assert result.parsed["default_schema"] == "public"


@pytest.mark.asyncio
async def test_parse_config_malformed_llm_response_returns_422(db):
    svc = DpDataSourceService(db)
    with patch(_LLM_PATCH_TARGET, new=AsyncMock(return_value={"content": "抱歉我无法解析", "model": "m"})):
        with pytest.raises(BusinessException) as exc:
            await svc.parse_config("noise")
    assert exc.value.code == "DP_PARSE_JSON_ERROR"
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_parse_config_llm_error_returns_502(db):
    svc = DpDataSourceService(db)
    with patch(_LLM_PATCH_TARGET, new=AsyncMock(side_effect=RuntimeError("connection refused"))):
        with pytest.raises(BusinessException) as exc:
            await svc.parse_config("anything")
    assert exc.value.code == "DP_PARSE_LLM_ERROR"
    assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_parse_config_markdown_fence_stripped(db):
    svc = DpDataSourceService(db)
    fenced = "```json\n" + json.dumps({
        "name": "Fenced", "dialect": "mysql", "host": "h", "port": 3306,
        "username": "u", "database": "d", "read_only_flag": True,
    }) + "\n```"
    with patch(_LLM_PATCH_TARGET, new=AsyncMock(return_value={"content": fenced, "model": "m"})):
        result = await svc.parse_config("MYSQL host h port 3306")
    assert result.parsed["name"] == "Fenced"
