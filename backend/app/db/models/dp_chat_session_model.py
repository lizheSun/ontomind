"""数据平台-Text2SQL 会话（T06 完整列定义 + T36 agent_looper_config_id）。"""
from sqlalchemy import Column, String, Integer, ForeignKey
from app.db.models.base import BaseModel


class DpChatSession(BaseModel):
    """数据平台-Text2SQL 会话：一次自然语言对话上下文。"""

    __tablename__ = "dp_chat_sessions"
    __table_args__ = {"comment": "数据平台-Text2SQL 会话"}

    name = Column(String(128), nullable=False, comment="会话名称")
    source_id = Column(
        Integer, ForeignKey("dp_data_sources.id", ondelete="CASCADE"),
        nullable=False, comment="所属数据源",
    )
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, comment="发起用户",
    )
    model_config_id = Column(
        Integer, ForeignKey("llm_configs.id"), nullable=True,
        comment="使用的 llm_configs 记录（NULL 走默认）",
    )
    agent_looper_config_id = Column(
        Integer, ForeignKey("agent_looper_configs.id"), nullable=True,
        comment="指定 Agent（优先于 model_config_id）",
    )
