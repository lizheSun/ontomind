"""Deployment lifecycle REST routes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.agent_platform_schema import (
    DeploymentControlRequest,
    DeploymentCreateRequest,
    DeploymentTransitionRequest,
)
from app.services.agent_platform.deployment import DeploymentService

router = APIRouter()


@router.post("")
def create_deployment(
    payload: DeploymentCreateRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return DeploymentService(db).create(
        payload.agent_version_id,
        payload.environment,
        payload.runtime_config,
        user_id,
    )


@router.get("")
def list_deployments(
    agent_id: int | None = Query(default=None),
    _user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return DeploymentService(db).list(agent_id)


@router.get("/{deployment_id}")
def get_deployment(
    deployment_id: int,
    _user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return DeploymentService(db).get(deployment_id)


@router.post("/{deployment_id}/transition")
def transition_deployment(
    deployment_id: int,
    payload: DeploymentTransitionRequest,
    _user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return DeploymentService(db).transition(
        deployment_id, payload.action, payload.expected_version
    )


@router.post("/{deployment_id}/drain")
def drain_deployment(
    deployment_id: int,
    payload: DeploymentControlRequest,
    _user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return DeploymentService(db).drain(deployment_id, payload.expected_version)


@router.post("/{deployment_id}/force-offline")
def force_offline_deployment(
    deployment_id: int,
    payload: DeploymentControlRequest,
    _user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return DeploymentService(db).force_offline(
        deployment_id, payload.expected_version, payload.reason
    )


@router.post("/{deployment_id}/rollback")
def rollback_deployment(
    deployment_id: int,
    payload: DeploymentControlRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return DeploymentService(db).rollback(
        deployment_id,
        user_id,
        payload.expected_version,
        payload.target_version_id,
    )
