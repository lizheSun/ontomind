"""Unified Agent Platform routes."""
from fastapi import APIRouter

from . import agents, deployments, discoveries, nodes

router = APIRouter()
router.include_router(nodes.router, tags=["Agent Platform Nodes"])
router.include_router(discoveries.router, tags=["Agent Platform Discoveries"])
router.include_router(agents.router, prefix="/agents", tags=["Agent Platform Agents"])
router.include_router(
    deployments.router, prefix="/deployments", tags=["Agent Platform Deployments"]
)

__all__ = ["router"]