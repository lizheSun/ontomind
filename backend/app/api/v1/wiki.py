"""Wiki 知识库 API."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.wiki_schema import (
    WikiDocumentCreate,
    WikiDocumentListItem,
    WikiDocumentResponse,
    WikiDocumentUpdate,
    WikiDocumentVersionResponse,
    WikiFetchUrlRequest,
    WikiImportRequest,
    WikiRollbackRequest,
    WikiSpaceCreate,
    WikiSpaceResponse,
    WikiSpaceUpdate,
)
from app.services.wiki_service import WikiService

router = APIRouter(prefix="/wiki", tags=["Wiki 知识库"])


def get_svc(db: Session = Depends(get_db)) -> WikiService:
    return WikiService(db)


@router.get("/spaces", response_model=list[WikiSpaceResponse])
def list_spaces(svc: WikiService = Depends(get_svc), _user_id: int = Depends(get_current_user_id)):
    return svc.list_spaces()


@router.post("/spaces", response_model=WikiSpaceResponse)
def create_space(
    data: WikiSpaceCreate,
    svc: WikiService = Depends(get_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.create_space(data)


@router.get("/spaces/{space_id}", response_model=WikiSpaceResponse)
def get_space(space_id: int, svc: WikiService = Depends(get_svc), _user_id: int = Depends(get_current_user_id)):
    return svc.get_space(space_id)


@router.put("/spaces/{space_id}", response_model=WikiSpaceResponse)
def update_space(
    space_id: int,
    data: WikiSpaceUpdate,
    svc: WikiService = Depends(get_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.update_space(space_id, data)


@router.delete("/spaces/{space_id}")
def delete_space(space_id: int, svc: WikiService = Depends(get_svc), _user_id: int = Depends(get_current_user_id)):
    svc.delete_space(space_id)
    return {"code": "SUCCESS", "message": "已删除", "data": None}


@router.get("/documents", response_model=list[WikiDocumentListItem])
def list_documents(
    space_id: Optional[int] = None,
    keyword: Optional[str] = None,
    tag: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    svc: WikiService = Depends(get_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_documents(
        space_id=space_id, keyword=keyword, tag=tag, status=status, limit=limit, offset=offset
    )


@router.post("/documents", response_model=WikiDocumentResponse)
def create_document(
    data: WikiDocumentCreate,
    svc: WikiService = Depends(get_svc),
    user_id: int = Depends(get_current_user_id),
):
    return svc.create_document(data, user_id)


@router.get("/documents/{doc_id}", response_model=WikiDocumentResponse)
def get_document(doc_id: int, svc: WikiService = Depends(get_svc), _user_id: int = Depends(get_current_user_id)):
    return svc.get_document(doc_id)


@router.put("/documents/{doc_id}", response_model=WikiDocumentResponse)
def update_document(
    doc_id: int,
    data: WikiDocumentUpdate,
    svc: WikiService = Depends(get_svc),
    user_id: int = Depends(get_current_user_id),
):
    return svc.update_document(doc_id, data, user_id)


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: int, svc: WikiService = Depends(get_svc), _user_id: int = Depends(get_current_user_id)):
    svc.delete_document(doc_id)
    return {"code": "SUCCESS", "message": "已删除", "data": None}


@router.get("/documents/{doc_id}/versions", response_model=list[WikiDocumentVersionResponse])
def list_versions(doc_id: int, svc: WikiService = Depends(get_svc), _user_id: int = Depends(get_current_user_id)):
    return svc.list_versions(doc_id)


@router.post("/documents/{doc_id}/rollback", response_model=WikiDocumentResponse)
def rollback_document(
    doc_id: int,
    data: WikiRollbackRequest,
    svc: WikiService = Depends(get_svc),
    user_id: int = Depends(get_current_user_id),
):
    return svc.rollback_document(doc_id, data.version, user_id)


@router.post("/import", response_model=WikiDocumentResponse)
def import_document(
    data: WikiImportRequest,
    svc: WikiService = Depends(get_svc),
    user_id: int = Depends(get_current_user_id),
):
    return svc.import_document(data, user_id)


@router.post("/fetch-url")
def fetch_url(
    data: WikiFetchUrlRequest,
    svc: WikiService = Depends(get_svc),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.fetch_url(data.url)
