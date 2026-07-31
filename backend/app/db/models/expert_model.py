"""专家/Expert 数据模型 — OALP v1.0.

一个专家 = 一份 opencode agent Markdown 定义（写到 ~/.config/opencode/agent/{slug}.md）
       + opencode_config 快照（provider / model / skills / mcps）
       + 可选 Docker 容器

字段对照（OALP = OntoMind Agent Loop Protocol，对齐 opencode agents.md 协议）：
  mode/subagent_depth/max_steps/permission_json/hooks_json/evals_json
  详见 docs/AGENT_LOOP_PROTOCOL.md（手稿已落 HANDOFF.md §6）。
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text

from app.db.models.base import BaseModel


class Expert(BaseModel):
    __tablename__ = "experts"

    name = Column(String(128), nullable=False, comment="专家显示名称")
    slug = Column(String(64), nullable=False, unique=True, comment="唯一标识 / opencode agent 名")
    avatar = Column(String(256), nullable=True, comment="emoji 或 URL")
    description = Column(Text, nullable=True, comment="一句话描述")
    role = Column(Text, nullable=True, comment="角色定位（写进 agent md 顶部）")
    sop = Column(Text, nullable=True, comment="SOP / 工作流程说明（写进 agent md 底部）")

    # 模型
    provider = Column(String(64), nullable=True, comment="opencode providerID，如 agent-plan")
    model = Column(String(128), nullable=True, comment="opencode modelID")
    temperature = Column(String(16), nullable=True, comment="采样温度（字符串以便存 null）")
    top_p = Column(String(16), nullable=True, comment="top_p 采样（字符串以便存 null）")

    # 能力
    skills = Column(JSON, nullable=False, default=list, comment="Skill 名称数组")
    mcps = Column(JSON, nullable=False, default=list, comment="MCP 名称数组")
    tools = Column(JSON, nullable=False, default=dict, comment="工具开关，如 {read:true, write:true}")

    # === OALP v1.0 新增字段（向后兼容，旧记录自动 default） ===
    mode = Column(String(16), nullable=False, server_default="subagent",
                  comment="primary|subagent|all（对齐 opencode agent.mode）")
    subagent_depth = Column(Integer, nullable=False, server_default="1",
                            comment="最大子 agent 嵌套深度（1=primary→subagent，2=再嵌套一层）")
    max_steps = Column(Integer, nullable=True,
                       comment="最大循环步数（对齐 opencode agent.steps）")
    system_prompt = Column(Text, nullable=True,
                           comment="完整 system prompt（frontmatter 之外的 Markdown body）")
    permission_json = Column(JSON, nullable=False, default=dict,
                             comment="permission 全集：edit/bash/task/skill/webfetch 等")
    hooks_json = Column(JSON, nullable=False, default=list,
                        comment="plugin refs：tool.execute.before/after/session.idle/...")
    evals_json = Column(JSON, nullable=False, default=list,
                        comment="用户只读展示的 eval hooks（本期不连 judge，仅展示）")
    version = Column(Integer, nullable=False, server_default="1",
                     comment="乐观锁版本号，create_all 加列时默认为 1")

    # Docker 部署（可选，当前 mock 模式为空）
    image = Column(String(256), nullable=True, comment="Docker 镜像名")
    container_template_id = Column(Integer, ForeignKey("container_templates.id", ondelete="SET NULL"),
                                   nullable=True, comment="绑定的容器模板")
    container_name = Column(String(128), nullable=True, comment="Docker 容器名")
    container_id = Column(String(64), nullable=True, comment="Docker 容器 ID")
    host_port = Column(Integer, nullable=True, comment="本机映射端口")
    bind_skills_to_container = Column(Boolean, nullable=False, server_default="1",
                                      comment="容器拉起时是否注入 skill/mcp 文件")

    # opencode 服务端点
    host = Column(String(64), nullable=False, server_default="127.0.0.1")
    port = Column(Integer, nullable=False, server_default="4096")

    # 状态
    status = Column(String(20), nullable=False, server_default="offline")
    agent_file_path = Column(String(512), nullable=True, comment="生成的 agent md 文件绝对路径")
    started_at = Column(DateTime(timezone=True), nullable=True)
    stopped_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    sort_order = Column(Integer, nullable=False, server_default="0")
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


__all__ = ["Expert"]
