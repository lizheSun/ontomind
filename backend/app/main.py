"""FastAPI main application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings, validate_production_security
from app.api.v1.router import api_router
from app.core.exceptions import add_exception_handlers
from app.db.session import engine, Base
import app.db.models  # noqa: import all models for table discovery


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup / shutdown lifecycle."""
    validate_production_security()
    # Startup: create tables if not exist (dev convenience)
    Base.metadata.create_all(bind=engine)
    # === OALP v1.0 schema 补丁：已有表加列 ===
    from app.db.session import SessionLocal
    from app.db.schema_patch import apply_oalp_patches
    _session = SessionLocal()
    try:
        changes = apply_oalp_patches(_session)
        if changes:
            from loguru import logger
            logger.info(f"[main.lifespan] OALP schema 补丁已应用: {changes}")
    finally:
        _session.close()
    # === Knowledge Base seed (T07) ===
    from app.db.session import SessionLocal
    from app.db.seed_kb import seed_kb_libraries
    _session = SessionLocal()
    try:
        seed_kb_libraries(_session)
    finally:
        _session.close()
    # === Compute seed：内置容器模板（opencode 等）===
    from app.db.seed_compute import seed_container_templates
    _session = SessionLocal()
    try:
        seed_container_templates(_session)
    finally:
        _session.close()
    # === 专家团 seed（OALP v1.0）：内置 4 个专家 + 演示关系 ===
    from app.services.expert_service import seed_default_experts
    _session = SessionLocal()
    try:
        added = seed_default_experts(_session)
        if added:
            from loguru import logger
            logger.info(f"[main.lifespan] 已 seed {added} 个 OALP 内置专家")
    finally:
        _session.close()
    # === 启动调度器（Compute Scheduling）===
    from app.services.schedule_task_service import _Scheduler
    _Scheduler.start()
    yield
    # Shutdown: cleanup connections
    _Scheduler.stop()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI驱动本体自动构建平台 — 五层架构后端服务",
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
