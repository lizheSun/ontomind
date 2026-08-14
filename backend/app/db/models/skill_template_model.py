"""Skill 工厂 ORM 模型 — Skill 模板 + 附属文件.

为什么要 skill_files 这张表：
真实世界的优秀 skill 极少是单文件。实测本地 55 个 skill，主流结构是
**渐进披露（Progressive Disclosure）**：

    arkcli-shared/              pdf/
    ├── SKILL.md   ← 常驻上下文  ├── SKILL.md
    └── references/ ← 命中才读   ├── reference.md
        ├── global-flags.md     └── scripts/*.py  ← 9 个脚本
        └── troubleshooting.md

SKILL.md 只放高频规则，稀有细节下沉到 references/，由正文里的路由表指引。
这是把上下文预算当一等公民管理 —— 所以必须支持多文件。

⚠️ OpenCode 的 frontmatter **只认 5 个字段**：
   name / description / license / compatibility / metadata
   其余字段被静默忽略，所以平台不要暴露多余字段给用户填。
"""
from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)

from app.db.models.base import BaseModel


class SkillTemplate(BaseModel):
    """Skill 模板（设计态）。"""

    __tablename__ = "skill_templates"
    __table_args__ = {"comment": "Skill 模板表（OpenCode SKILL.md 设计态）"}

    # ---- OpenCode frontmatter 合法字段 ----
    # name 必须同时满足：正则 ^[a-z0-9]+(-[a-z0-9]+)*$、1-64 字符、**等于目录名**
    name = Column(String(64), nullable=False, unique=True, comment="skill 名（=目录名，小写连字符）")
    # description 是模型选择 skill 的唯一依据，OpenCode 限制 1-1024 字符
    description = Column(String(1024), nullable=False, comment="用途描述（模型选择依据，≤1024）")
    license = Column(String(64), nullable=True, comment="许可证，如 MIT")
    compatibility = Column(String(128), nullable=True, comment="兼容性声明，如 opencode")
    metadata_json = Column(JSON, nullable=True, comment="metadata（string→string 映射）")

    # ---- 正文 ----
    body = Column(Text, nullable=True, comment="SKILL.md 正文（frontmatter 之后的 Markdown）")

    # ---- 平台治理 ----
    display_name = Column(String(128), nullable=True, comment="展示名")
    category = Column(String(64), nullable=True, index=True, comment="分类")
    is_builtin_preset = Column(
        Boolean, nullable=False, default=False, index=True, comment="内置预设（不可删除）",
    )
    source = Column(String(16), nullable=False, default="platform", comment="来源")
    current_version = Column(Integer, nullable=False, default=1, comment="当前版本号")
    created_by_user_id = Column(Integer, nullable=True, comment="创建人")


class SkillFile(BaseModel):
    """Skill 附属文件（references/*.md、scripts/*.py 等）。"""

    __tablename__ = "skill_files"
    __table_args__ = (
        UniqueConstraint("skill_template_id", "rel_path", name="uq_skill_file_path"),
        {"comment": "Skill 附属文件表（支撑渐进披露的多文件结构）"},
    )

    skill_template_id = Column(
        Integer,
        ForeignKey("skill_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属 skill 模板",
    )
    # 相对 skill 目录的路径，如 references/detail.md、scripts/run.py
    # 校验：禁止 .. / 绝对路径 / 与 SKILL.md 重名（见 agent_validate_service）
    rel_path = Column(String(512), nullable=False, comment="相对路径（禁止 .. 与绝对路径）")
    content = Column(Text, nullable=True, comment="文件内容")
    is_executable = Column(
        Boolean, nullable=False, default=False, comment="是否可执行（脚本落盘时给 0o755）",
    )
