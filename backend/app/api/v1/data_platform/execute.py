"""数据平台-SQL 执行路由：同步 JSON + SSE 流式导出。"""
import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.dp_query_schema import SqlExecuteRequest
from app.services.dp_query_service import DpQueryService

router = APIRouter()


@router.post("/sources/{source_id}/execute", response_model=dict)
async def execute_sync(
    source_id: int,
    payload: SqlExecuteRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """同步执行 SQL，返回全部结果（受 max_rows 截断）."""
    svc = DpQueryService(db)
    result = await svc.execute_sync(
        source_id=source_id,
        sql=payload.sql,
        max_rows=payload.max_rows,
        user_id=user_id,
    )
    return {
        "code": "SUCCESS",
        "message": "执行成功",
        "data": result.model_dump(mode="json"),
    }


@router.get("/sources/{source_id}/execute/stream")
async def execute_stream(
    source_id: int,
    sql: str = Query(..., min_length=1),
    max_rows: int = Query(100_000, ge=1, le=100_000),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """SSE 流式返回 columns / rows / done / error 事件（用于大结果导出）."""
    svc = DpQueryService(db)

    async def event_gen():
        async for evt in svc.execute_stream(
            source_id=source_id,
            sql=sql,
            user_id=user_id,
            max_rows=max_rows,
        ):
            yield {
                "event": evt["event"],
                "data": json.dumps(evt["data"], ensure_ascii=False, default=str),
            }

    return EventSourceResponse(event_gen())
