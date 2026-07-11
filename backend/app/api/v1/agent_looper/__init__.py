"""Agent Looper 聚合路由：discovery + configs + test。"""
from fastapi import APIRouter

from . import configs, discovery, test as test_route

router = APIRouter()
router.include_router(discovery.router)
router.include_router(configs.router)
router.include_router(test_route.router)

__all__ = ["router"]
