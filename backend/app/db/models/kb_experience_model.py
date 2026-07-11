"""kb: 知识库-业务经验 — 骨架（T04 占位，列由 T06/T07 补完）."""
from app.db.models.base import BaseModel


class KbExperience(BaseModel):
    """知识库-业务经验（列由后续任务补完）。"""

    __tablename__ = "kb_experiences"
    __table_args__ = {"comment": "知识库-业务经验"}

    # 列由 T06/T07 补完；BaseModel 已提供 id / created_at / updated_at
