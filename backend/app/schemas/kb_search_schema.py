"""知识库-跨子库聚合搜索 Schema。"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


LibraryCode = Literal["data_asset", "code_repo", "document", "experience"]


class KbSearchResult(BaseModel):
    library_code: LibraryCode
    id: int
    title: str
    snippet: Optional[str] = None
    score: float = 1.0


class KbSearchGrouped(BaseModel):
    data_asset: list[KbSearchResult] = []
    code_repo: list[KbSearchResult] = []
    document: list[KbSearchResult] = []
    experience: list[KbSearchResult] = []
