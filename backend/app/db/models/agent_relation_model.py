"""多 Agent 协同关系表 — 主 Agent 调子 Agent 的拓扑.

对齐 opencode `permission.task` 规则：
- parent_expert 通过 `permission.task` glob 允许/拒绝调用 child_expert
- 关系本身不强制约束（permission.task 才是真正的执行闸门），但提供：
  1. UI 可视化（关系图 / 树）
  2. 自动生成 `permission.task` 规则（sync_to_opencode 时合并）
  3. 反环检测（DFS）

relation 语义：
- delegate : 主 agent 把任务委派给子 agent
- fan_out  : 主 agent 并行调多个子 agent
- review   : 主 agent 让子 agent 评审自己的产物
"""
from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.db.models.base import BaseModel


class AgentRelation(BaseModel):
    __tablename__ = "agent_relations"
    __table_args__ = (
        UniqueConstraint("parent_expert_id", "child_expert_id", name="uq_agent_rel_parent_child"),
        {"comment": "多 Agent 协同关系（主→子 调用拓扑）"},
    )

    parent_expert_id = Column(
        Integer, ForeignKey("experts.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="主 agent（调用方）",
    )
    child_expert_id = Column(
        Integer, ForeignKey("experts.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="子 agent（被调用方）",
    )
    relation = Column(
        String(32), nullable=False, server_default="delegate",
        comment="delegate|fan_out|review",
    )
    condition = Column(Text, nullable=True, comment="何时触发（自然语言描述，给 LLM 看）")
    sort_order = Column(Integer, nullable=False, server_default="0")


def detect_cycle(db: Session, parent_id: int, child_id: int) -> bool:
    """DFS 检查加入 (parent_id→child_id) 后是否会成环."""
    if parent_id == child_id:
        return True
    # 构造邻接表
    rows = db.query(AgentRelation).all()
    adj: dict[int, list[int]] = {}
    for r in rows:
        adj.setdefault(r.parent_expert_id, []).append(r.child_expert_id)
    # 加入候选边后再 DFS
    adj.setdefault(parent_id, []).append(child_id)
    visited: set[int] = set()

    def dfs(node: int) -> bool:
        if node in visited:
            return False
        visited.add(node)
        for nxt in adj.get(node, []):
            if nxt == parent_id:  # 回到起点 = 环
                return True
            if dfs(nxt):
                return True
        return False

    return dfs(child_id)


def assert_no_cycle(db: Session, parent_id: int, child_id: int) -> None:
    if detect_cycle(db, parent_id, child_id):
        raise BusinessException(
            f"加入关系 (parent={parent_id} → child={child_id}) 会形成环",
            code="AGENT_RELATION_CYCLE",
        )


__all__ = ["AgentRelation", "assert_no_cycle"]
