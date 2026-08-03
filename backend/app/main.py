"""FastAPI main application entry point.

当前形态（2026-08-03 深度精简后）：
- **AIDE** — iframe 嵌入 opencode Web UI（前端默认落地页）
- **用户管理** — 用户 / 角色 / 权限 / 审计
- 后端只有 3 个路由域：`/api/v1/{auth, users, opencode}`，4 张数据表
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings, validate_production_security
from app.api.v1.router import api_router
from app.core.exceptions import add_exception_handlers
from app.db.session import engine, Base
import app.db.models  # noqa: F401 — import all models for table discovery


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup / shutdown lifecycle."""
    validate_production_security()
    # 建表（dev 便利）：只剩 users / roles / user_roles / audit_logs
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Agent 工作平台 — AIDE（opencode Web UI 嵌入）+ 用户管理",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
add_exception_handlers(app)

# Register API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"name": settings.APP_NAME, "version": settings.APP_VERSION, "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
