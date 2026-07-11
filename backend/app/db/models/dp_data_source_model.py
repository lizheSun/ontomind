"""dp: 数据平台-数据源 — 骨架（T04 占位，列由 T06/T07 补完）."""
from app.db.models.base import BaseModel


class DpDataSource(BaseModel):
    """数据平台-数据源（列由后续任务补完）。"""

    __tablename__ = "dp_data_sources"
    __table_args__ = {"comment": "数据平台-数据源"}

    # 列由 T06/T07 补完；BaseModel 已提供 id / created_at / updated_at
