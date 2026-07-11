"""Agent Looper 聚合路由：discovery + configs（含 publish endpoint）。"""
from fastapi import APIRouter

from . import configs, discovery

router = APIRouter()
router.include_router(discovery.router)
router.include_router(configs.router)

__all__ = ["router"]
