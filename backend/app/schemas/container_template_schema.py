"""容器模板校验与响应模型.

ports / env_vars / volumes 在 schema 层为 List[str]，ORM 层存 JSON 字符串。
TemplateResponse 用 field_validator(before) 把 ORM 的 JSON 字符串解析回 list，
不修改原 ORM 对象（避免污染 SQLAlchemy 实例状态）。
"""
import json
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class _TemplateBase(BaseModel):
    name: str = Field(..., max_length=128)
    image: str = Field(..., max_length=256)
    description: Optional[str] = Field(default=None, max_length=512)
    long_description: Optional[str] = Field(default=None)
    icon: Optional[str] = Field(default=None, max_length=64)
    category: Optional[str] = Field(default=None, max_length=64)
    command: Optional[str] = Field(default=None, max_length=512)
    ports: List[str] = Field(default_factory=list)
    env_vars: List[str] = Field(default_factory=list)
    volumes: List[str] = Field(default_factory=list)
    restart_policy: Optional[str] = Field(default=None, pattern=r"^(no|always|on-failure|unless-stopped)$")
    network: Optional[str] = Field(default=None, max_length=64)
    extra_args: Optional[str] = Field(default=None, max_length=512)


class TemplateCreate(_TemplateBase):
    pass


class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=128)
    image: Optional[str] = Field(default=None, max_length=256)
    description: Optional[str] = Field(default=None, max_length=512)
    long_description: Optional[str] = Field(default=None)
    icon: Optional[str] = Field(default=None, max_length=64)
    category: Optional[str] = Field(default=None, max_length=64)
    command: Optional[str] = Field(default=None, max_length=512)
    ports: Optional[List[str]] = None
    env_vars: Optional[List[str]] = None
    volumes: Optional[List[str]] = None
    restart_policy: Optional[str] = Field(default=None, pattern=r"^(no|always|on-failure|unless-stopped)$")
    network: Optional[str] = Field(default=None, max_length=64)
    extra_args: Optional[str] = Field(default=None, max_length=512)


class TemplateResponse(_TemplateBase):
    id: int
    is_builtin: bool = False
    sort_order: int = 0

    model_config = {"from_attributes": True}

    @field_validator("ports", "env_vars", "volumes", mode="before")
    @classmethod
    def _parse_json_array(cls, v):
        """把 ORM 存的 JSON 字符串解析回 list；不修改原对象."""
        if isinstance(v, str):
            if not v:
                return []
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                return []
        if v is None:
            return []
        return v if isinstance(v, list) else []
