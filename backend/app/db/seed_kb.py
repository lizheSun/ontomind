"""知识库子库种子函数：幂等 upsert 4 条 kb_libraries 行。

由 main.py 的 lifespan 在 Base.metadata.create_all 之后调用一次。
"""
from __future__ import annotations

from loguru import logger
from sqlalchemy.orm import Session

from app.db.models.kb_library_model import KbLibrary


_SEEDS: list[dict] = [
    {"code": "data_asset", "name_zh": "数据资产",
     "icon": "DatabaseOutlined",
     "description": "按业务域整理的数据资产目录", "sort_order": 1},
    {"code": "code_repo", "name_zh": "代码库",
     "icon": "GithubOutlined",
     "description": "内外部代码仓库索引", "sort_order": 2},
    {"code": "document", "name_zh": "文档库",
     "icon": "FileTextOutlined",
     "description": "制度、SOP、方案与手册", "sort_order": 3},
    {"code": "experience", "name_zh": "业务经验库",
     "icon": "BulbOutlined",
     "description": "一线业务经验沉淀", "sort_order": 4},
]


def seed_kb_libraries(session: Session) -> None:
    """幂等地写入 4 条子库记录。已存在则跳过（按 code 唯一约束）。"""
    for row in _SEEDS:
        existing = (
            session.query(KbLibrary).filter(KbLibrary.code == row["code"]).first()
        )
        if existing is None:
            session.add(KbLibrary(**row))
            logger.info(f"[kb-seed] 新增子库 code={row['code']} name={row['name_zh']}")
    session.commit()
