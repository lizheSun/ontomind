"""文档（document）CRUD + multipart 上传 + 二进制下载。"""
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user_id
from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.schemas.kb_document_schema import (
    KbDocumentMetaCreate,
    KbDocumentRead,
    KbDocumentUpdate,
)
from app.services.kb_service import KbService

router = APIRouter()


@router.get("", response_model=dict)
async def list_documents(
    owner_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    docs = KbService(db).list_documents(
        user_id=user_id, owner_only=owner_only, skip=skip, limit=limit
    )
    data = [d.model_dump(mode="json") for d in docs]
    return {"code": "SUCCESS", "message": "操作成功", "data": data, "total": len(data)}


@router.post("/upload", response_model=dict, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title_zh: str = Form(...),
    library_id: int = Form(...),
    description_md: str | None = Form(None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    meta = KbDocumentMetaCreate(
        title_zh=title_zh,
        library_id=library_id,
        description_md=description_md,
        tags=None,
    )
    doc = await KbService(db).upload_document(file=file, meta=meta, user_id=user_id)
    return {"code": "SUCCESS", "message": "上传成功", "data": doc.model_dump(mode="json")}


@router.get("/{id}", response_model=dict)
async def get_document(
    id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    svc = KbService(db)
    row = svc.doc_repo.get_by_id(id)
    if row is None:
        raise NotFoundException(
            message=f"文档 id={id} 不存在",
            code="KB_DOC_NOT_FOUND",
        )
    return {
        "code": "SUCCESS",
        "message": "操作成功",
        "data": KbDocumentRead.model_validate(row).model_dump(mode="json"),
    }


@router.get("/{id}/download")
async def download_document(
    id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    row, contents = KbService(db).get_document_bytes(id)
    return Response(
        content=contents,
        media_type=row.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{row.filename}"',
            "Content-Length": str(len(contents)),
        },
    )


@router.put("/{id}", response_model=dict)
async def update_document(
    id: int,
    payload: KbDocumentUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    doc = KbService(db).update_document(id, payload, user_id=user_id)
    return {
        "code": "SUCCESS",
        "message": "文档更新成功",
        "data": doc.model_dump(mode="json"),
    }


@router.delete("/{id}", response_model=dict)
async def delete_document(
    id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    KbService(db).delete_document(id, user_id=user_id)
    return {"code": "SUCCESS", "message": "文档删除成功", "data": None}
