"""dp: 数据平台-执行历史 — 骨架（T04 占位，列由 T06/T07 补完）."""
from app.db.models.base import BaseModel


class DpQueryHistory(BaseModel):
    """数据平台-执行历史（列由后续任务补完）。"""

    __tablename__ = "dp_query_history"
    __table_args__ = {"comment": "数据平台-执行历史"}

    # 列由 T06/T07 补完；BaseModel 已提供 id / created_at / updated_at
