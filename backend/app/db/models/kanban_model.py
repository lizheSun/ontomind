"""任务看板 ORM：kanban_boards / kanban_columns / kanban_tasks。

列位置（column）与执行状态（run_status）正交：拖列不改运行态。
任务可选绑定 harness_sessions，点卡片进统一会话。
"""
from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text

from app.db.models.base import BaseModel


class KanbanBoard(BaseModel):
    __tablename__ = "kanban_boards"
    __table_args__ = {"comment": "任务看板"}

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False, default="默认看板")
    icon = Column(String(32), nullable=True)
    color = Column(String(20), nullable=True)
    position = Column(Integer, nullable=False, default=0)


class KanbanColumn(BaseModel):
    __tablename__ = "kanban_columns"
    __table_args__ = {"comment": "看板列"}

    board_id = Column(
        Integer, ForeignKey("kanban_boards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(128), nullable=False)
    icon = Column(String(32), nullable=True)
    color = Column(String(20), nullable=True)
    position = Column(Integer, nullable=False, default=0)
    collapsed = Column(Boolean, nullable=False, default=False)


class KanbanTask(BaseModel):
    __tablename__ = "kanban_tasks"
    __table_args__ = {"comment": "看板任务（可绑定统一会话）"}

    board_id = Column(
        Integer, ForeignKey("kanban_boards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    column_id = Column(
        Integer, ForeignKey("kanban_columns.id", ondelete="SET NULL"), nullable=True, index=True
    )
    session_id = Column(
        Integer, ForeignKey("harness_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title = Column(String(256), nullable=False, default="新任务")
    plugin_id = Column(String(32), nullable=False, default="opencode")
    run_status = Column(String(16), nullable=False, default="pending")
    position = Column(Integer, nullable=False, default=0)
    summary = Column(Text, nullable=True)
