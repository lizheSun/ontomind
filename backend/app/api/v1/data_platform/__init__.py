"""数据平台聚合路由：sources / execute / saved-queries / history / chat。"""
from fastapi import APIRouter

from . import chat, execute, history, saved_queries, sources

router = APIRouter()
router.include_router(sources.router, prefix="/sources")
router.include_router(execute.router)  # keeps its own /sources/{id}/execute paths
router.include_router(saved_queries.router, prefix="/saved-queries")
router.include_router(history.router, prefix="/history")
router.include_router(chat.router, prefix="/chat")

__all__ = ["router"]
