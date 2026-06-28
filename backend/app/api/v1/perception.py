"""感知层 API - 数据源连接器 & 文档管理."""

from fastapi import APIRouter, UploadFile, File

router = APIRouter()


@router.get("/datasources")
async def list_data_sources():
    """获取数据源列表."""
    return {"data_sources": [], "total": 0}


@router.post("/datasources")
async def create_data_source():
    """注册新的数据源连接."""
    return {"message": "create data source - to be implemented"}


@router.get("/datasources/{source_id}")
async def get_data_source(source_id: int):
    """获取数据源详情."""
    return {"source_id": source_id}


@router.delete("/datasources/{source_id}")
async def delete_data_source(source_id: int):
    """删除数据源."""
    return {"message": f"data source {source_id} deleted"}


@router.post("/datasources/{source_id}/sync")
async def sync_data_source(source_id: int):
    """同步数据源元数据."""
    return {"message": f"syncing data source {source_id}"}


@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """上传文档 (PDF/Word/Markdown 等)."""
    return {"filename": file.filename, "size": file.size, "status": "uploaded"}


@router.get("/documents")
async def list_documents():
    """获取文档列表."""
    return {"documents": [], "total": 0}
