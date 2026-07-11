"""Agent Looper API 聚合路由（T35 discovery/writer + T36 test 一并挂载）。"""
from fastapi import APIRouter

from app.api.v1.agent_looper import test as test_route

router = APIRouter()
router.include_router(test_route.router)

# NOTE: T35 会追加 discovery/configs 子路由；此处兼容单独运行 T36 时也可工作。
try:
    from app.api.v1.agent_looper import discovery as _discovery
    router.include_router(_discovery.router)
except Exception:  # pragma: no cover - T35 未合并时静默
    pass

try:
    from app.api.v1.agent_looper import configs as _configs
    router.include_router(_configs.router)
except Exception:  # pragma: no cover
    pass
