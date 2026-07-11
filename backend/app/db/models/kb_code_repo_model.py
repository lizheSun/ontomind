"""知识库-代码库（T07 完整列定义）。"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON
from app.db.models.base import BaseModel


class KbCodeRepo(BaseModel):
    """知识库-代码库：内外部 Git 仓库索引。"""

    __tablename__ = "kb_code_repos"
    __table_args__ = {"comment": "知识库-代码库"}

    library_id = Column(
        Integer, ForeignKey("kb_libraries.id"), nullable=False, comment="所属子库",
    )
    title_zh = Column(String(255), nullable=False, comment="仓库中文名")
    repo_url = Column(String(512), nullable=False, comment="Git URL")
    branch = Column(
        String(128), nullable=False, server_default="main", comment="默认分支",
    )
    language = Column(String(32), nullable=True, comment="主语言")
    description_md = Column(Text, nullable=True, comment="描述 markdown")
    tags = Column(JSON, nullable=True, comment="标签数组")
    owner_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, comment="负责人",
    )
    created_by_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, comment="创建者",
    )
