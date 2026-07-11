"""数据平台-执行历史（T06 完整列定义）。"""
from sqlalchemy import (
    Column, Integer, Text, DateTime, ForeignKey, JSON, Index, Enum as SAEnum,
)
from app.db.models.base import BaseModel


class DpQueryHistory(BaseModel):
    """数据平台-执行历史：每一次 execute_sync/stream 的落库审计。"""

    __tablename__ = "dp_query_history"
    __table_args__ = (
        Index("ix_dp_query_history_user_started", "user_id", "started_at"),
        {"comment": "数据平台-SQL 执行历史"},
    )

    source_id = Column(
        Integer, ForeignKey("dp_data_sources.id", ondelete="CASCADE"),
        nullable=False, comment="所属数据源",
    )
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, comment="发起用户",
    )
    sql_text = Column(Text, nullable=False, comment="执行的 SQL 文本")
    status = Column(
        SAEnum("running", "success", "error", "canceled", "timeout",
               name="dp_qh_status"),
        nullable=False, comment="执行状态",
    )
    row_count = Column(Integer, nullable=True, comment="返回行数")
    elapsed_ms = Column(Integer, nullable=True, comment="耗时（毫秒）")
    error_message = Column(Text, nullable=True, comment="错误信息")
    columns_json = Column(JSON, nullable=True, comment="列元信息 JSON")
    started_at = Column(DateTime, nullable=False, comment="开始时间")
    finished_at = Column(DateTime, nullable=True, comment="结束时间")
