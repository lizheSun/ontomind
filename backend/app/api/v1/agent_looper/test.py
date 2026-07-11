"""Agent Looper 测试端点 (SSE) + 测试历史列表。

- `POST /configs/{config_id}/test` — 使用 Agent 的 system_prompt 走一次 LLM，
  SSE 流式返回 text/done/error 事件；每次调用持久化一条 AgentLooperTestRun。
- `POST /test-runs/{config_id}` — 返回该 config 的最近测试历史（POST 兼容平台风格）。
- `GET /test-runs` — GET 变体（query: config_id）。
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.api.v1.auth import get_current_user_id
from app.core.exceptions import BusinessException, NotFoundException
from app.db.repositories.agent_looper_repo import AgentLooperTestRunRepository
from app.db.session import get_db
from app.schemas.agent_looper_schema import TestRunRead, TestRunRequest
from app.services.agent_looper_service import AgentLooperService
from app.services.llm_config_service import LLMConfigService

router = APIRouter()


@router.post("/configs/{config_id}/test")
async def test_agent_looper(
    config_id: int,
    payload: TestRunRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """模型联通测试 · Prompt 试跑。SSE：text*, done | error。"""
    svc = AgentLooperService(db)
    try:
        config, version, config_json = svc.get_current_config_dict(config_id, user_id)
    except (BusinessException, NotFoundException) as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"code": e.code, "message": e.message},
        )

    system_prompt = config_json.get("system_prompt", "") if isinstance(config_json, dict) else ""
    temperature = float(config_json.get("temperature", 0.7)) if isinstance(config_json, dict) else 0.7
    max_tokens_default = 2048
    guardrails = config_json.get("guardrails", {}) if isinstance(config_json, dict) else {}
    if isinstance(guardrails, dict):
        try:
            max_tokens = int(guardrails.get("max_tokens", max_tokens_default))
        except (TypeError, ValueError):
            max_tokens = max_tokens_default
    else:
        max_tokens = max_tokens_default

    version_id = version.id if version is not None else None
    run_repo = AgentLooperTestRunRepository(db)
    run = run_repo.create(
        config_id=config_id,
        version_id=version_id,
        prompt=payload.prompt,
        user_id=user_id,
        status="running",
    )
    run_id = run.id

    llm = LLMConfigService(db)

    async def event_gen():
        started = time.perf_counter()
        try:
            result = await llm.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": f"{system_prompt}\n\n用户提示: {payload.prompt}"
                        if system_prompt
                        else payload.prompt,
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            elapsed = int((time.perf_counter() - started) * 1000)
            response_text = ""
            model_used = "unknown"
            if isinstance(result, dict):
                response_text = result.get("content", "") or ""
                model_used = result.get("model") or "unknown"
            else:
                response_text = str(result)

            run_repo.update(
                run_id,
                status="success",
                response=response_text,
                latency_ms=elapsed,
            )

            # SSE: split by whitespace, preserve spaces
            words = response_text.split(" ")
            for i, w in enumerate(words):
                token = w + (" " if i < len(words) - 1 else "")
                yield {"event": "text", "data": token}
                await asyncio.sleep(0)  # 让出事件循环
            yield {
                "event": "done",
                "data": json.dumps(
                    {
                        "latency_ms": elapsed,
                        "model": model_used,
                        "run_id": run_id,
                    },
                    ensure_ascii=False,
                ),
            }
        except Exception as e:  # noqa: BLE001
            err = str(e)[:512]
            try:
                run_repo.update(run_id, status="error", error=err)
            except Exception:  # noqa: BLE001
                pass
            yield {"event": "error", "data": err}

    return EventSourceResponse(event_gen())


def _to_read(row) -> dict[str, Any]:
    return TestRunRead.model_validate(row).model_dump(mode="json")


@router.post("/test-runs/{config_id}")
async def list_test_runs(
    config_id: int,
    limit: int = Query(50, ge=1, le=500),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """列出指定 Agent 的最近测试运行记录。"""
    svc = AgentLooperService(db)
    try:
        svc.get_by_id(config_id, user_id)  # owner 校验
    except (BusinessException, NotFoundException) as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"code": e.code, "message": e.message},
        )
    rows = AgentLooperTestRunRepository(db).list_by_config(config_id, limit=limit)
    return {
        "code": "SUCCESS",
        "message": "OK",
        "data": [_to_read(r) for r in rows],
    }


@router.get("/test-runs")
async def list_test_runs_get(
    config_id: int = Query(..., ge=1),
    limit: int = Query(50, ge=1, le=500),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """GET 变体。"""
    return await list_test_runs(config_id, limit, user_id, db)
