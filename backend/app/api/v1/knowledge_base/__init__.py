"""知识库聚合路由：libraries / 4 子库 / tags / search。"""
from fastapi import APIRouter

from . import code_repos, data_assets, documents, experiences, libraries, search, tags

router = APIRouter()
router.include_router(libraries.router, prefix="/libraries")
router.include_router(data_assets.router, prefix="/data-assets")
router.include_router(code_repos.router, prefix="/code-repos")
router.include_router(documents.router, prefix="/documents")
router.include_router(experiences.router, prefix="/experiences")
router.include_router(tags.router, prefix="/tags")
router.include_router(search.router, prefix="/search")

__all__ = ["router"]
