"""知识库-文档库（T07 完整列定义）。"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, BigInteger
from app.db.models.base import BaseModel


class KbDocument(BaseModel):
    """知识库-文档库：制度/SOP/方案/手册，附件落 UPLOAD_DIR/kb/documents/。"""

    __tablename__ = "kb_documents"
    __table_args__ = {"comment": "知识库-文档库"}

    library_id = Column(
        Integer, ForeignKey("kb_libraries.id"), nullable=False, comment="所属子库",
    )
    title_zh = Column(String(255), nullable=False, comment="文档中文标题")
    filename = Column(String(255), nullable=False, comment="上传原始文件名")
    storage_path = Column(String(512), nullable=False, comment="相对 UPLOAD_DIR 的存储路径")
    mime_type = Column(String(128), nullable=False, comment="MIME 类型")
    size_bytes = Column(BigInteger, nullable=False, comment="文件字节数")
    description_md = Column(Text, nullable=True, comment="描述 markdown")
    tags = Column(JSON, nullable=True, comment="标签数组")
    owner_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, comment="负责人",
    )
    created_by_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, comment="创建者",
    )
