"""发布记录 ORM 模型 — Bundle → Docker 容器的发布审计.

发布五阶段（每阶段可观测，status 逐步推进）：

    ① resolve    解析 bundle → 全量产物清单（含 sha256）
    ② validate   再校验一次（DB 可能被手改过）
    ③ write      内存 tar 原子上传（本地 put_archive / 远程 tar+base64 over SSH）
    ④ reload     重启容器内 opencode 服务
    ⑤ verify     回读 GET /agent 逐项比对；skill 用 opencode run 探测

⚠️ 为什么必须重启（实测结论，见 PRD §2.5）：
   - `PATCH /config` 返回 200 但 agent **不出现在 GET /agent**，且不落盘 → 不可用
   - 写 opencode.jsonc 后不重启也**不热感知**
   - 唯一可靠路径：写文件（为真）+ 重启（生效）+ GET /agent（校验）
   重启会中断进行中的会话，所以发布请求必须带 restart_confirmed。

⚠️ 为什么不用 GET /api/skill 做 skill 校验（实测结论）：
   该端点在 skill 明确可用时仍返回 data: []，不可信。
   改用容器内 `opencode run "列出可用 skills"` 作为权威判据。
"""
import enum

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)

from app.db.models.base import BaseModel


class DeployScope(str, enum.Enum):
    """产物写入范围。"""

    GLOBAL = "global"     # /root/.config/opencode/ —— 对该容器所有项目生效
    PROJECT = "project"   # /workspace/.opencode/  —— 只对该项目生效


class DeployStatus(str, enum.Enum):
    """发布状态机。"""

    PENDING = "pending"
    VALIDATING = "validating"
    WRITING = "writing"
    RELOADING = "reloading"
    VERIFYING = "verifying"
    SUCCESS = "success"     # 全部产物写入且回读一致
    PARTIAL = "partial"     # 写入成功但回读有差异（如某 agent 未被识别）
    FAILED = "failed"       # 中途失败


class Deployment(BaseModel):
    """发布记录。"""

    __tablename__ = "deployments"
    __table_args__ = {"comment": "Bundle 发布记录表（含产物清单与回读校验结果）"}

    # ---- 发布对象 ----
    bundle_id = Column(
        Integer,
        ForeignKey("agent_bundles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="发布的 bundle",
    )
    bundle_name = Column(String(128), nullable=False, comment="bundle 名快照")
    bundle_version = Column(Integer, nullable=False, default=1, comment="发布时的 bundle 版本")

    # ---- 发布目标 ----
    node_id = Column(
        Integer,
        ForeignKey("compute_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="目标算力节点",
    )
    node_name = Column(String(128), nullable=False, comment="节点名快照")
    container_id = Column(String(64), nullable=False, index=True, comment="目标容器 ID")
    container_name = Column(String(255), nullable=False, comment="容器名快照")
    scope = Column(
        String(16), nullable=False, default=DeployScope.GLOBAL.value,
        comment="范围: global / project",
    )
    target_dir = Column(String(512), nullable=False, comment="容器内目标目录")

    # ---- 执行结果 ----
    status = Column(
        String(16), nullable=False, default=DeployStatus.PENDING.value,
        index=True, comment="状态",
    )
    # 产物清单：[{path, sha256, bytes, skipped}]，用于幂等判断与漂移检测
    artifacts_json = Column(JSON, nullable=True, comment="产物清单（含 sha256，用于幂等与漂移检测）")
    # 回读校验：{agents:[{name, expected, actual, match}], skills:[...], summary:{...}}
    verify_json = Column(JSON, nullable=True, comment="回读校验结果（期望 vs 容器实际）")
    restart_used = Column(
        Boolean, nullable=False, default=False, comment="是否重启了容器内服务",
    )
    error_detail = Column(Text, nullable=True, comment="失败原因（可执行的中文提示）")
    duration_ms = Column(Integer, nullable=True, comment="总耗时")
    deployed_by_user_id = Column(Integer, nullable=True, comment="发布人")
