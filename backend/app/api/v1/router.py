"""API v1 route aggregation."""

from fastapi import APIRouter

from app.api.v1 import perception, cognition, decision, execution, application, auth, users, llm, resources, projects

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])
api_router.include_router(llm.router, prefix="/llm", tags=["LLM 配置"])
api_router.include_router(resources.router, prefix="/resources", tags=["资源管理"])
api_router.include_router(projects.router, prefix="/projects", tags=["项目管理"])
api_router.include_router(perception.router, prefix="/perception", tags=["感知层"])
api_router.include_router(cognition.router, prefix="/cognition", tags=["认知层"])
api_router.include_router(decision.router, prefix="/decision", tags=["决策层"])
api_router.include_router(execution.router, prefix="/execution", tags=["执行层"])
api_router.include_router(application.router, prefix="/application", tags=["应用层"])
