"""容器模板服务 — CRUD + 内置模板保护.

事务边界只在 Service 层：flush + commit（遵循项目规范，禁用 with db.begin()）。
"""
import json
import logging
from typing import List

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException, NotFoundException
from app.db.models.container_template_model import ContainerTemplate
from app.db.repositories.container_template_repo import ContainerTemplateRepository
from app.schemas.container_template_schema import (
    TemplateCreate, TemplateResponse, TemplateUpdate,
)

logger = logging.getLogger(__name__)

_JSON_FIELDS = ("ports", "env_vars", "volumes")


def _to_orm_dict(payload: TemplateCreate) -> dict:
    """把 schema 的 List[str] 字段序列化为 JSON 字符串（完整 dump）."""
    data = payload.model_dump()
    for f in _JSON_FIELDS:
        data[f] = json.dumps(data.get(f) or [], ensure_ascii=False)
    return data


def _to_orm_dict_partial(payload: TemplateUpdate) -> dict:
    """部分更新：仅序列化显式提供的字段."""
    data = payload.model_dump(exclude_unset=True)
    for f in _JSON_FIELDS:
        if f in data:
            data[f] = json.dumps(data[f] or [], ensure_ascii=False)
    return data


class ContainerTemplateService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ContainerTemplateRepository(db)

    def list_templates(self) -> List[TemplateResponse]:
        items = self.repo.list_ordered()
        return [TemplateResponse.model_validate(it) for it in items]

    def get_template(self, template_id: int) -> TemplateResponse:
        t = self.repo.get_by_id(template_id)
        if not t:
            raise NotFoundException(f"模板 ID={template_id} 不存在")
        return TemplateResponse.model_validate(t)

    def create_template(self, payload: TemplateCreate) -> TemplateResponse:
        if self.repo.get_by_name(payload.name):
            raise BusinessException(f"模板 '{payload.name}' 已存在", code="TEMPLATE_NAME_CONFLICT")
        t = ContainerTemplate(**_to_orm_dict(payload), is_builtin=False)
        self.db.add(t)
        self.db.flush()
        self.db.commit()
        logger.info(f"创建容器模板: {t.name}")
        return TemplateResponse.model_validate(t)

    def update_template(self, template_id: int, payload: TemplateUpdate) -> TemplateResponse:
        t = self.repo.get_by_id(template_id)
        if not t:
            raise NotFoundException(f"模板 ID={template_id} 不存在")
        # 内置模板保护：不允许改名
        if t.is_builtin and payload.name is not None and payload.name != t.name:
            raise BusinessException("内置模板不允许改名", code="BUILTIN_PROTECTED")
        data = _to_orm_dict_partial(payload)
        if "name" in data and data["name"] != t.name:
            if self.repo.get_by_name(data["name"]):
                raise BusinessException(f"模板 '{data['name']}' 已存在", code="TEMPLATE_NAME_CONFLICT")
        for k, v in data.items():
            setattr(t, k, v)
        self.db.flush()
        self.db.commit()
        return TemplateResponse.model_validate(t)

    def delete_template(self, template_id: int) -> None:
        t = self.repo.get_by_id(template_id)
        if not t:
            raise NotFoundException(f"模板 ID={template_id} 不存在")
        if t.is_builtin:
            raise BusinessException("内置模板不允许删除", code="BUILTIN_PROTECTED")
        self.db.delete(t)
        self.db.flush()
        self.db.commit()
        logger.info(f"删除容器模板: {t.name}")
