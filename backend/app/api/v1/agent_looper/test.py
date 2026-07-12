"""Agent Looper 测试端点 (SSE) + 测试历史列表 + Agent Job 管理（T55）。

- `POST /configs/{config_id}/test` — 使用 Agent 的 system_prompt 走一次 LLM，
  SSE 流式返回 text/done/error 事件；每次调用持久化一条 AgentLooperTestRun。
- `POST /test-runs/{config_id}` — 返回该 config 的最近测试历史（POST 兼容平台风格）。
- `GET /test-runs` — GET 变体（query: config_id）。
- `POST/GET/PUT/DELETE /jobs` — Agent 长任务 Job CRUD + 生命周期端点（T55）。
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.api.v1.auth import get_current_user_id
from app.core.exceptions import BusinessException, NotFoundException
from app.db.repositories.agent_looper_repo import AgentLooperTestRunRepository
from app.db.session import get_db
from app.schemas.agent_looper_schema import TestRunRead, TestRunRequest
from app.services.agent_job_service import AgentJobService
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


# ---------------------------------------------------------------------------
# Agent Job endpoints (T55) — ETL-style long-running job management.
# ---------------------------------------------------------------------------


class JobCreateRequest(BaseModel):
    agent_id: int = Field(..., ge=1)
    name: str = Field(..., min_length=1, max_length=256)
    steps: Optional[list[Any]] = None
    input_data: Optional[Any] = None
    total_steps: Optional[int] = Field(default=None, ge=1)


class JobUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=256)
    steps: Optional[list[Any]] = None
    total_steps: Optional[int] = Field(default=None, ge=1)
    input_data: Optional[Any] = None


class JobTransitionRequest(BaseModel):
    action: str = Field(
        ...,
        description="start | pause | resume | complete | fail | cancel | advance_step",
    )
    error_message: Optional[str] = None
    output_data: Optional[Any] = None


def _job_ok(job: dict[str, Any], message: str = "OK") -> dict[str, Any]:
    return {"code": "SUCCESS", "message": message, "data": job}


def _raise_biz(e: BusinessException) -> None:
    raise HTTPException(
        status_code=e.status_code,
        detail={"code": e.code, "message": e.message},
    )


@router.post("/jobs")
async def create_job(
    payload: JobCreateRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Create an Agent Job in `pending` state."""
    svc = AgentJobService(db)
    try:
        job = svc.create(
            agent_id=payload.agent_id,
            name=payload.name,
            user_id=user_id,
            steps=payload.steps,
            input_data=payload.input_data,
            total_steps=payload.total_steps,
        )
    except (BusinessException, NotFoundException) as e:
        _raise_biz(e)
    return _job_ok(job, "Job 已创建")


@router.get("/jobs")
async def list_jobs(
    agent_id: Optional[int] = Query(default=None, ge=1),
    status: Optional[str] = Query(default=None),
    mine: bool = Query(default=True, description="仅返回当前用户创建的 Job"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List jobs with optional filters."""
    svc = AgentJobService(db)
    try:
        jobs = svc.list(
            user_id=user_id if mine else None,
            agent_id=agent_id,
            status=status,
            skip=skip,
            limit=limit,
        )
    except (BusinessException, NotFoundException) as e:
        _raise_biz(e)
    return {"code": "SUCCESS", "message": "OK", "data": jobs}


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    svc = AgentJobService(db)
    try:
        job = svc.get(job_id)
    except (BusinessException, NotFoundException) as e:
        _raise_biz(e)
    return _job_ok(job)


@router.put("/jobs/{job_id}")
async def update_job(
    job_id: int,
    payload: JobUpdateRequest = Body(...),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    svc = AgentJobService(db)
    kw: dict[str, Any] = {}
    if payload.name is not None:
        kw["name"] = payload.name
    if payload.steps is not None:
        kw["steps"] = payload.steps
    if payload.total_steps is not None:
        kw["total_steps"] = payload.total_steps
    # Detect whether input_data was explicitly provided (None is a valid value).
    fields_set = payload.model_fields_set
    if "input_data" in fields_set:
        kw["input_data"] = payload.input_data
        kw["_input_data_set"] = True
    try:
        job = svc.update(job_id, user_id, **kw)
    except (BusinessException, NotFoundException) as e:
        _raise_biz(e)
    return _job_ok(job, "Job 已更新")


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    svc = AgentJobService(db)
    try:
        svc.delete(job_id, user_id)
    except (BusinessException, NotFoundException) as e:
        _raise_biz(e)
    return {"code": "SUCCESS", "message": "Job 已删除", "data": None}


@router.post("/jobs/{job_id}/transition")
async def transition_job(
    job_id: int,
    payload: JobTransitionRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Drive the job through its state machine.

    Supported `action` values: start, pause, resume, complete, fail, cancel,
    advance_step.
    """
    svc = AgentJobService(db)
    action = (payload.action or "").strip().lower()
    try:
        if action == "start":
            job = svc.start(job_id, user_id)
        elif action == "pause":
            job = svc.pause(job_id, user_id)
        elif action == "resume":
            job = svc.resume(job_id, user_id)
        elif action == "complete":
            job = svc.complete(job_id, user_id, output_data=payload.output_data)
        elif action == "fail":
            job = svc.fail(job_id, user_id, error_message=payload.error_message)
        elif action == "cancel":
            job = svc.cancel(job_id, user_id)
        elif action == "advance_step":
            job = svc.advance_step(job_id, user_id)
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "AGENT_JOB_UNKNOWN_ACTION",
                    "message": f"未知 action: {payload.action!r}",
                },
            )
    except (BusinessException, NotFoundException) as e:
        _raise_biz(e)
    return _job_ok(job, f"Job {action} 已执行")
