"""Unified Agent Platform routes."""
from fastapi import APIRouter

from . import agents, approvals, deployments, discoveries, nodes, runs, sessions

router = APIRouter()
router.include_router(nodes.router, tags=["Agent Platform Nodes"])
router.include_router(discoveries.router, tags=["Agent Platform Discoveries"])
router.include_router(agents.router, prefix="/agents", tags=["Agent Platform Agents"])
router.include_router(
    deployments.router, prefix="/deployments", tags=["Agent Platform Deployments"]
)
router.include_router(sessions.router, prefix="/sessions", tags=["Agent Platform Sessions"])
router.include_router(runs.router, prefix="/runs", tags=["Agent Platform Runs"])
router.include_router(approvals.router, prefix="/approvals", tags=["Agent Platform Approvals"])

__all__ = ["router"]
