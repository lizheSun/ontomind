"""DataOps API — 数据源 / 元数据 / 样例查询."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.dataops_schema import (
    ConnectionTestRequest,
    ConnectionTestResponse,
    DataSourceCreate,
    DataSourceResponse,
    DataSourceUpdate,
    ExecuteSqlRequest,
    ExecuteSqlResponse,
    SampleQueryRequest,
    SampleQueryResponse,
)
from app.services.dataops_service import DataOpsService

router = APIRouter(prefix="/dataops", tags=["DataOps"])


def get_svc(db: Session = Depends(get_db)) -> DataOpsService:
    return DataOpsService(db)


@router.get("/sources", response_model=list[DataSourceResponse])
def list_sources(
    svc: DataOpsService = Depends(get_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_sources()


@router.post("/sources", response_model=DataSourceResponse)
def create_source(
    data: DataSourceCreate,
    svc: DataOpsService = Depends(get_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.create_source(data)


@router.get("/sources/{source_id}", response_model=DataSourceResponse)
def get_source(
    source_id: int,
    svc: DataOpsService = Depends(get_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.get_source(source_id)


@router.put("/sources/{source_id}", response_model=DataSourceResponse)
def update_source(
    source_id: int,
    data: DataSourceUpdate,
    svc: DataOpsService = Depends(get_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.update_source(source_id, data)


@router.delete("/sources/{source_id}")
def delete_source(
    source_id: int,
    svc: DataOpsService = Depends(get_svc),
    _user_id: int = Depends(get_current_user_id),
):
    svc.delete_source(source_id)
    return {"code": "SUCCESS", "message": "已删除", "data": None}


@router.post("/sources/test", response_model=ConnectionTestResponse)
def test_connection(
    data: ConnectionTestRequest,
    svc: DataOpsService = Depends(get_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.test_connection(data)


@router.get("/sources/{source_id}/databases")
def list_databases(
    source_id: int,
    svc: DataOpsService = Depends(get_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return {"code": "SUCCESS", "data": svc.list_databases(source_id)}


@router.get("/sources/{source_id}/tables")
def list_tables(
    source_id: int,
    database: str = Query(..., min_length=1),
    svc: DataOpsService = Depends(get_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return {"code": "SUCCESS", "data": svc.list_tables(source_id, database)}


@router.get("/sources/{source_id}/columns")
def list_columns(
    source_id: int,
    database: str = Query(..., min_length=1),
    table: str = Query(..., min_length=1),
    svc: DataOpsService = Depends(get_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return {"code": "SUCCESS", "data": svc.list_columns(source_id, database, table)}


@router.post("/sources/{source_id}/sample", response_model=SampleQueryResponse)
def sample_rows(
    source_id: int,
    data: SampleQueryRequest,
    svc: DataOpsService = Depends(get_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.sample(
        source_id,
        database=data.database,
        table=data.table,
        limit=data.limit,
    )


@router.post("/sources/{source_id}/execute", response_model=ExecuteSqlResponse)
def execute_sql(
    source_id: int,
    data: ExecuteSqlRequest,
    svc: DataOpsService = Depends(get_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.execute_sql(
        source_id,
        sql=data.sql,
        database=data.database,
        max_rows=data.max_rows,
    )
