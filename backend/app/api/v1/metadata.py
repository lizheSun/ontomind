"""元数据扫描 / 标准项 / 库概况 / 作业 API."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.metadata_schema import (
    AnnotateJobCreate,
    AnnotateStatsResponse,
    AnnotationBatchReviewRequest,
    AnnotationResponse,
    AnnotationReviewRequest,
    ColumnBindBatchRequest,
    ColumnBindRequest,
    ColumnWorkspaceItem,
    DatabaseBriefCreate,
    DatabaseBriefResponse,
    GlossaryExtractRequest,
    GlossaryTermCreate,
    GlossaryTermResponse,
    GlossaryTermUpdate,
    LlmSettingCreate,
    LlmSettingResponse,
    LlmSettingTestRequest,
    LlmSettingUpdate,
    MetaColumnResponse,
    MetaColumnUpdate,
    MetaScanCreate,
    MetaScanJobResponse,
    MetaStandardCreate,
    MetaStandardResponse,
    MetaStandardUpdate,
    MetaTableResponse,
    MetaTableUpdate,
)
from app.services.annotation_service import AnnotationService
from app.services.glossary_service import GlossaryService
from app.services.llm_settings_service import LlmSettingsService
from app.services.meta_brief_service import MetaBriefService
from app.services.meta_scan_service import MetaScanService
from app.services.meta_standard_service import MetaStandardService

router = APIRouter(prefix="/metadata", tags=["元数据与标注"])


def get_scan_svc(db: Session = Depends(get_db)) -> MetaScanService:
    return MetaScanService(db)


def get_glossary_svc(db: Session = Depends(get_db)) -> GlossaryService:
    return GlossaryService(db)


def get_ann_svc(db: Session = Depends(get_db)) -> AnnotationService:
    return AnnotationService(db)


def get_std_svc(db: Session = Depends(get_db)) -> MetaStandardService:
    return MetaStandardService(db)


def get_brief_svc(db: Session = Depends(get_db)) -> MetaBriefService:
    return MetaBriefService(db)


def get_llm_svc(db: Session = Depends(get_db)) -> LlmSettingsService:
    return LlmSettingsService(db)


def _table_response(table, columns=None) -> MetaTableResponse:
    data = MetaTableResponse.model_validate(table)
    if columns is not None:
        data.columns = [MetaColumnResponse.model_validate(c) for c in columns]
    return data


@router.post("/scans", response_model=MetaScanJobResponse)
def create_scan(
    data: MetaScanCreate,
    svc: MetaScanService = Depends(get_scan_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.create_scan(data)


@router.get("/jobs", response_model=list[MetaScanJobResponse])
def list_jobs(
    source_id: Optional[int] = None,
    database: Optional[str] = None,
    job_kind: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    svc: MetaScanService = Depends(get_scan_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_scans(
        source_id=source_id,
        database=database,
        job_kind=job_kind,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get("/scans", response_model=list[MetaScanJobResponse])
def list_scans(
    source_id: Optional[int] = None,
    database: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    svc: MetaScanService = Depends(get_scan_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_scans(
        source_id=source_id,
        database=database,
        job_kind="scan",
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get("/scans/{job_id}", response_model=MetaScanJobResponse)
def get_scan(
    job_id: int,
    svc: MetaScanService = Depends(get_scan_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.get_scan(job_id)


@router.get("/jobs/{job_id}", response_model=MetaScanJobResponse)
def get_job(
    job_id: int,
    svc: MetaScanService = Depends(get_scan_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.get_scan(job_id)


@router.get("/tables", response_model=list[MetaTableResponse])
def list_tables(
    source_id: Optional[int] = None,
    database: Optional[str] = None,
    keyword: Optional[str] = None,
    domain: Optional[str] = None,
    annotated: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    svc: MetaScanService = Depends(get_scan_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_tables(
        source_id=source_id,
        database=database,
        keyword=keyword,
        domain=domain,
        annotated=annotated,
        limit=limit,
        offset=offset,
    )


@router.get("/tables/{table_id}", response_model=MetaTableResponse)
def get_table(
    table_id: int,
    svc: MetaScanService = Depends(get_scan_svc),
    _user_id: int = Depends(get_current_user_id),
):
    table, columns = svc.get_table_with_columns(table_id)
    return _table_response(table, columns)


@router.put("/tables/{table_id}", response_model=MetaTableResponse)
def update_table(
    table_id: int,
    data: MetaTableUpdate,
    svc: MetaScanService = Depends(get_scan_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.update_table(table_id, data)


@router.put("/columns/{column_id}", response_model=MetaColumnResponse)
def update_column(
    column_id: int,
    data: MetaColumnUpdate,
    svc: MetaScanService = Depends(get_scan_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.update_column(column_id, data)


@router.post("/columns/{column_id}/profile", response_model=MetaColumnResponse)
def profile_column(
    column_id: int,
    svc: MetaScanService = Depends(get_scan_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.profile_one_column(column_id)


@router.get("/workspace/columns", response_model=list[ColumnWorkspaceItem])
def list_workspace_columns(
    source_id: int,
    database: str,
    table_name: Optional[str] = None,
    column_name: Optional[str] = None,
    security_level: Optional[str] = None,
    standard_id: Optional[int] = None,
    bind_status: Optional[str] = None,
    bound: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    svc: MetaStandardService = Depends(get_std_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_workspace_columns(
        source_id=source_id,
        database=database,
        table_name=table_name,
        column_name=column_name,
        security_level=security_level,
        standard_id=standard_id,
        bind_status=bind_status,
        bound=bound,
        limit=limit,
        offset=offset,
    )


@router.get("/standards", response_model=list[MetaStandardResponse])
def list_standards(
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    svc: MetaStandardService = Depends(get_std_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_standards(keyword=keyword, status=status, limit=limit, offset=offset)


@router.post("/standards", response_model=MetaStandardResponse)
def create_standard(
    data: MetaStandardCreate,
    svc: MetaStandardService = Depends(get_std_svc),
    user_id: int = Depends(get_current_user_id),
):
    return svc.create_standard(data, user_id=user_id)


@router.get("/standards/{sid}", response_model=MetaStandardResponse)
def get_standard(
    sid: int,
    svc: MetaStandardService = Depends(get_std_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.get_standard(sid)


@router.put("/standards/{sid}", response_model=MetaStandardResponse)
def update_standard(
    sid: int,
    data: MetaStandardUpdate,
    svc: MetaStandardService = Depends(get_std_svc),
    user_id: int = Depends(get_current_user_id),
):
    return svc.update_standard(sid, data, user_id=user_id)


@router.delete("/standards/{sid}")
def delete_standard(
    sid: int,
    svc: MetaStandardService = Depends(get_std_svc),
    _user_id: int = Depends(get_current_user_id),
):
    svc.delete_standard(sid)
    return {"code": "SUCCESS", "message": "已删除", "data": None}


@router.post("/columns/{column_id}/bind-standard", response_model=ColumnWorkspaceItem)
def bind_standard(
    column_id: int,
    data: ColumnBindRequest,
    svc: MetaStandardService = Depends(get_std_svc),
    user_id: int = Depends(get_current_user_id),
):
    return svc.bind_column(column_id, data, user_id=user_id)


@router.post("/columns/batch-bind-standard", response_model=list[ColumnWorkspaceItem])
def batch_bind_standard(
    data: ColumnBindBatchRequest,
    svc: MetaStandardService = Depends(get_std_svc),
    user_id: int = Depends(get_current_user_id),
):
    return svc.batch_bind(data, user_id=user_id)


@router.delete("/columns/{column_id}/bind-standard")
def unbind_standard(
    column_id: int,
    svc: MetaStandardService = Depends(get_std_svc),
    user_id: int = Depends(get_current_user_id),
):
    svc.unbind_column(column_id, user_id=user_id)
    return {"code": "SUCCESS", "message": "已解绑", "data": None}


@router.get("/briefs", response_model=Optional[DatabaseBriefResponse])
def get_brief(
    source_id: int,
    database: str,
    svc: MetaBriefService = Depends(get_brief_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.get_brief(source_id, database)


@router.post("/briefs", response_model=MetaScanJobResponse)
def create_brief(
    data: DatabaseBriefCreate,
    svc: MetaBriefService = Depends(get_brief_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.create_brief_job(data)


@router.get("/glossary", response_model=list[GlossaryTermResponse])
def list_glossary(
    keyword: Optional[str] = None,
    domain: Optional[str] = None,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    svc: GlossaryService = Depends(get_glossary_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_terms(keyword=keyword, domain=domain, limit=limit, offset=offset)


@router.post("/glossary", response_model=GlossaryTermResponse)
def create_glossary(
    data: GlossaryTermCreate,
    svc: GlossaryService = Depends(get_glossary_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.create_term(data)


@router.put("/glossary/{term_id}", response_model=GlossaryTermResponse)
def update_glossary(
    term_id: int,
    data: GlossaryTermUpdate,
    svc: GlossaryService = Depends(get_glossary_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.update_term(term_id, data)


@router.delete("/glossary/{term_id}")
def delete_glossary(
    term_id: int,
    svc: GlossaryService = Depends(get_glossary_svc),
    _user_id: int = Depends(get_current_user_id),
):
    svc.delete_term(term_id)
    return {"code": "SUCCESS", "message": "已删除", "data": None}


@router.post("/glossary/extract", response_model=list[GlossaryTermResponse])
def extract_glossary(
    data: GlossaryExtractRequest,
    svc: GlossaryService = Depends(get_glossary_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.extract_from_wiki(data.doc_ids, data.mode)


@router.post("/annotate-jobs", response_model=MetaScanJobResponse)
def create_annotate_job(
    data: AnnotateJobCreate,
    svc: AnnotationService = Depends(get_ann_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.create_annotate_job(data)


@router.get("/annotate-jobs/{job_id}", response_model=MetaScanJobResponse)
def get_annotate_job(
    job_id: int,
    svc: AnnotationService = Depends(get_ann_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.get_annotate_job(job_id)


@router.get("/annotations", response_model=list[AnnotationResponse])
def list_annotations(
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    label_kind: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    confidence_min: Optional[float] = None,
    confidence_max: Optional[float] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    svc: AnnotationService = Depends(get_ann_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_annotations(
        target_type=target_type,
        target_id=target_id,
        label_kind=label_kind,
        status=status,
        source=source,
        confidence_min=confidence_min,
        confidence_max=confidence_max,
        limit=limit,
        offset=offset,
    )


@router.post("/annotations/{ann_id}/review", response_model=AnnotationResponse)
def review_annotation(
    ann_id: int,
    data: AnnotationReviewRequest,
    svc: AnnotationService = Depends(get_ann_svc),
    user_id: int = Depends(get_current_user_id),
):
    return svc.review_annotation(
        ann_id, data.action, user_id=user_id, value_override=data.value_override
    )


@router.post("/annotations/batch-review", response_model=list[AnnotationResponse])
def batch_review(
    data: AnnotationBatchReviewRequest,
    svc: AnnotationService = Depends(get_ann_svc),
    user_id: int = Depends(get_current_user_id),
):
    return svc.batch_review(data.ann_ids, data.action, user_id=user_id)


@router.get("/stats", response_model=AnnotateStatsResponse)
def annotate_stats(
    source_id: int,
    database: str,
    svc: AnnotationService = Depends(get_ann_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.annotate_stats(source_id, database)


@router.get("/llm-settings", response_model=list[LlmSettingResponse])
def list_llm_settings(
    svc: LlmSettingsService = Depends(get_llm_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list()


@router.get("/llm-settings/active", response_model=LlmSettingResponse)
def get_active_llm_setting(
    svc: LlmSettingsService = Depends(get_llm_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.get_active()


@router.post("/llm-settings", response_model=LlmSettingResponse)
def create_llm_setting(
    data: LlmSettingCreate,
    svc: LlmSettingsService = Depends(get_llm_svc),
    user_id: int = Depends(get_current_user_id),
):
    return svc.create(data, user_id=user_id)


@router.post("/llm-settings/test")
def test_llm_setting_inline(
    data: LlmSettingTestRequest,
    svc: LlmSettingsService = Depends(get_llm_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.test_inline(data)


@router.put("/llm-settings/{setting_id}", response_model=LlmSettingResponse)
def update_llm_setting(
    setting_id: int,
    data: LlmSettingUpdate,
    svc: LlmSettingsService = Depends(get_llm_svc),
    user_id: int = Depends(get_current_user_id),
):
    return svc.update(setting_id, data, user_id=user_id)


@router.delete("/llm-settings/{setting_id}")
def delete_llm_setting(
    setting_id: int,
    svc: LlmSettingsService = Depends(get_llm_svc),
    _user_id: int = Depends(get_current_user_id),
):
    svc.delete(setting_id)
    return {"code": "SUCCESS", "message": "已删除"}


@router.post("/llm-settings/{setting_id}/apply", response_model=LlmSettingResponse)
def apply_llm_setting(
    setting_id: int,
    svc: LlmSettingsService = Depends(get_llm_svc),
    user_id: int = Depends(get_current_user_id),
):
    return svc.apply(setting_id, user_id=user_id)


@router.post("/llm-settings/{setting_id}/test")
def test_llm_setting_saved(
    setting_id: int,
    svc: LlmSettingsService = Depends(get_llm_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.test_saved(setting_id)
