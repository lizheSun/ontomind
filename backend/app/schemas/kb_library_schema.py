"""知识库-子库定义 Schema（只读，无编辑接口）。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


LibraryCode = Literal["data_asset", "code_repo", "document", "experience"]


class KbLibraryRead(BaseModel):
    id: int
    code: LibraryCode
    name_zh: str
    icon: str
    description: Optional[str] = None
    sort_order: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
