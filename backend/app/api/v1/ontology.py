"""本体建模 API."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.ontology_schema import (
    CQCreate,
    CQResponse,
    GraphDataResponse,
    InferRelationsRequest,
    LinkTypeCreate,
    LinkTypeResponse,
    LinkTypeUpdate,
    MappingCreate,
    MappingResponse,
    MappingUpdate,
    MetricCreate,
    MetricResponse,
    MetricUpdate,
    ObjectTypeCreate,
    ObjectTypeResponse,
    ObjectTypeUpdate,
    OntologyBuildJobCreate,
    OntologyBuildJobResponse,
    OntologyCreate,
    OntologyResponse,
    OntologyUpdate,
    OntologyVersionResponse,
    PropertyCreate,
    PropertyResponse,
    PropertyUpdate,
    PublishRequest,
    ReviewRequest,
    RollbackRequest,
)
from app.services.ontology_build_service import OntologyBuildService
from app.services.ontology_cq_service import OntologyCQService
from app.services.ontology_metric_service import OntologyMetricService

router = APIRouter(prefix="/ontology", tags=["本体建模"])


def get_build_svc(db: Session = Depends(get_db)) -> OntologyBuildService:
    return OntologyBuildService(db)


def get_cq_svc(db: Session = Depends(get_db)) -> OntologyCQService:
    return OntologyCQService(db)


def get_metric_svc(db: Session = Depends(get_db)) -> OntologyMetricService:
    return OntologyMetricService(db)


def _job_resp(job) -> OntologyBuildJobResponse:
    return OntologyBuildJobResponse.model_validate(job)


# ---- Ontologies ----

@router.get("/ontologies", response_model=list[OntologyResponse])
def list_ontologies(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_ontologies(limit=limit, offset=offset)


@router.post("/ontologies", response_model=OntologyResponse)
def create_ontology(
    data: OntologyCreate,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.create_ontology(data)


@router.get("/ontologies/{oid}", response_model=OntologyResponse)
def get_ontology(
    oid: int,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.get_ontology(oid)


@router.put("/ontologies/{oid}", response_model=OntologyResponse)
def update_ontology(
    oid: int,
    data: OntologyUpdate,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.update_ontology(oid, data)


@router.delete("/ontologies/{oid}")
def delete_ontology(
    oid: int,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    svc.delete_ontology(oid)
    return {"code": "SUCCESS", "message": "已删除", "data": None}


# ---- Build jobs ----

@router.post("/ontologies/{oid}/build-jobs", response_model=OntologyBuildJobResponse)
def create_build_job(
    oid: int,
    data: OntologyBuildJobCreate,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return _job_resp(svc.create_build_job(oid, data))


@router.get("/build-jobs/{job_id}", response_model=OntologyBuildJobResponse)
def get_build_job(
    job_id: int,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return _job_resp(svc.get_build_job(job_id))


# ---- Object types ----

@router.get("/ontologies/{oid}/object-types", response_model=list[ObjectTypeResponse])
def list_object_types(
    oid: int,
    status: Optional[str] = None,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_object_types(oid, status=status)


@router.post("/ontologies/{oid}/object-types", response_model=ObjectTypeResponse)
def create_object_type(
    oid: int,
    data: ObjectTypeCreate,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.create_object_type(oid, data)


@router.put("/object-types/{ot_id}", response_model=ObjectTypeResponse)
def update_object_type(
    ot_id: int,
    data: ObjectTypeUpdate,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.update_object_type(ot_id, data)


@router.delete("/object-types/{ot_id}")
def delete_object_type(
    ot_id: int,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    svc.delete_object_type(ot_id)
    return {"code": "SUCCESS", "message": "已删除", "data": None}


# ---- Properties ----

@router.get("/object-types/{ot_id}/properties", response_model=list[PropertyResponse])
def list_properties(
    ot_id: int,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_properties(ot_id)


@router.post("/object-types/{ot_id}/properties", response_model=PropertyResponse)
def create_property(
    ot_id: int,
    data: PropertyCreate,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.create_property(ot_id, data)


@router.put("/properties/{prop_id}", response_model=PropertyResponse)
def update_property(
    prop_id: int,
    data: PropertyUpdate,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.update_property(prop_id, data)


@router.delete("/properties/{prop_id}")
def delete_property(
    prop_id: int,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    svc.delete_property(prop_id)
    return {"code": "SUCCESS", "message": "已删除", "data": None}


# ---- Link types ----

@router.get("/ontologies/{oid}/link-types", response_model=list[LinkTypeResponse])
def list_link_types(
    oid: int,
    status: Optional[str] = None,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_link_types(oid, status=status)


@router.post("/ontologies/{oid}/link-types", response_model=LinkTypeResponse)
def create_link_type(
    oid: int,
    data: LinkTypeCreate,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.create_link_type(oid, data)


@router.put("/link-types/{link_id}", response_model=LinkTypeResponse)
def update_link_type(
    link_id: int,
    data: LinkTypeUpdate,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.update_link_type(link_id, data)


@router.delete("/link-types/{link_id}")
def delete_link_type(
    link_id: int,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    svc.delete_link_type(link_id)
    return {"code": "SUCCESS", "message": "已删除", "data": None}


@router.post("/ontologies/{oid}/infer-relations")
def infer_relations(
    oid: int,
    data: InferRelationsRequest,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.infer_relations(oid, data)


# ---- Mappings ----

@router.get("/ontologies/{oid}/mappings", response_model=list[MappingResponse])
def list_mappings(
    oid: int,
    status: Optional[str] = None,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_mappings(oid, status=status)


@router.post("/ontologies/{oid}/mappings", response_model=MappingResponse)
def create_mapping(
    oid: int,
    data: MappingCreate,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.create_mapping(oid, data)


@router.put("/mappings/{mapping_id}", response_model=MappingResponse)
def update_mapping(
    mapping_id: int,
    data: MappingUpdate,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.update_mapping(mapping_id, data)


@router.delete("/mappings/{mapping_id}")
def delete_mapping(
    mapping_id: int,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    svc.delete_mapping(mapping_id)
    return {"code": "SUCCESS", "message": "已删除", "data": None}


# ---- Metrics ----

@router.get("/ontologies/{oid}/metrics", response_model=list[MetricResponse])
def list_metrics(
    oid: int,
    status: Optional[str] = None,
    svc: OntologyMetricService = Depends(get_metric_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_metrics(oid, status=status)


@router.post("/ontologies/{oid}/metrics", response_model=MetricResponse)
def create_metric(
    oid: int,
    data: MetricCreate,
    svc: OntologyMetricService = Depends(get_metric_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.create_metric(oid, data)


@router.post("/ontologies/{oid}/metrics/suggest", response_model=list[MetricResponse])
def suggest_metrics(
    oid: int,
    svc: OntologyMetricService = Depends(get_metric_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.suggest_metrics(oid)


@router.put("/metrics/{metric_id}", response_model=MetricResponse)
def update_metric(
    metric_id: int,
    data: MetricUpdate,
    svc: OntologyMetricService = Depends(get_metric_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.update_metric(metric_id, data)


@router.delete("/metrics/{metric_id}")
def delete_metric(
    metric_id: int,
    svc: OntologyMetricService = Depends(get_metric_svc),
    _user_id: int = Depends(get_current_user_id),
):
    svc.delete_metric(metric_id)
    return {"code": "SUCCESS", "message": "已删除", "data": None}


# ---- CQs ----

@router.get("/ontologies/{oid}/cqs", response_model=list[CQResponse])
def list_cqs(
    oid: int,
    svc: OntologyCQService = Depends(get_cq_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_cqs(oid)


@router.post("/ontologies/{oid}/cqs", response_model=CQResponse)
def create_cq(
    oid: int,
    data: CQCreate,
    svc: OntologyCQService = Depends(get_cq_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.create_cq(oid, data)


@router.post("/ontologies/{oid}/cqs/generate", response_model=list[CQResponse])
def generate_cqs(
    oid: int,
    mode: str = Query("rules"),
    svc: OntologyCQService = Depends(get_cq_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.generate_cqs(oid, mode=mode)


@router.post("/cqs/{cq_id}/verify", response_model=CQResponse)
def verify_cq(
    cq_id: int,
    svc: OntologyCQService = Depends(get_cq_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.verify_cq(cq_id)


@router.post("/ontologies/{oid}/cqs/verify-all")
def verify_all_cqs(
    oid: int,
    svc: OntologyCQService = Depends(get_cq_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.verify_all(oid)


# ---- Review / Graph / Publish / Export ----

@router.post("/ontologies/{oid}/review")
def review_elements(
    oid: int,
    data: ReviewRequest,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.review(oid, data)


@router.get("/ontologies/{oid}/graph", response_model=GraphDataResponse)
def graph_data(
    oid: int,
    focus_key: Optional[str] = None,
    depth: int = Query(2, ge=0, le=10),
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.graph_data(oid, focus_key=focus_key, depth=depth)


@router.post("/ontologies/{oid}/publish", response_model=OntologyVersionResponse)
def publish_version(
    oid: int,
    data: PublishRequest,
    svc: OntologyBuildService = Depends(get_build_svc),
    user_id: int = Depends(get_current_user_id),
):
    return svc.publish_version(oid, data.change_note, user_id)


@router.get("/ontologies/{oid}/versions", response_model=list[OntologyVersionResponse])
def list_versions(
    oid: int,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_versions(oid)


@router.get("/ontologies/{oid}/versions/{version}", response_model=OntologyVersionResponse)
def get_version(
    oid: int,
    version: int,
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.get_version(oid, version)


@router.post("/ontologies/{oid}/rollback", response_model=OntologyVersionResponse)
def rollback_version(
    oid: int,
    data: RollbackRequest,
    svc: OntologyBuildService = Depends(get_build_svc),
    user_id: int = Depends(get_current_user_id),
):
    return svc.rollback_version(oid, data.version, user_id)


@router.get("/ontologies/{oid}/export")
def export_ontology(
    oid: int,
    fmt: str = Query("json", pattern="^(json|jsonld|turtle)$"),
    svc: OntologyBuildService = Depends(get_build_svc),
    _user_id: int = Depends(get_current_user_id),
):
    content = svc.export_ontology(oid, fmt=fmt)
    media = "application/json" if fmt in ("json", "jsonld") else "text/turtle"
    return PlainTextResponse(content, media_type=media)
