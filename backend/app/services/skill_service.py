"""Skill 业务服务."""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.repositories.skill_repo import SkillRepository
from app.schemas.skill_schema import SkillCreate, SkillUpdate
from app.core.exceptions import ConflictException, NotFoundException


class SkillService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SkillRepository(db)

    def create(self, data: SkillCreate) -> dict:
        if self.repo.name_exists(data.name):
            raise ConflictException("技能名称已存在", code="SKILL_NAME_EXISTS")
        skill = self.repo.create(data.model_dump())
        self.db.commit()
        return skill.to_response_dict()

    def get(self, skill_id: int) -> dict:
        skill = self.repo.get_by_id(skill_id)
        if not skill:
            raise NotFoundException(f"技能不存在: {skill_id}")
        return skill.to_response_dict()

    def list(self, skip: int = 0, limit: int = 100) -> list[dict]:
        items = self.repo.get_all(skip, limit)
        return [s.to_response_dict() for s in items]

    def update(self, skill_id: int, data: SkillUpdate) -> dict:
        skill = self.repo.get_by_id(skill_id)
        if not skill:
            raise NotFoundException(f"技能不存在: {skill_id}")
        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data and update_data["name"] != skill.name:
            if self.repo.name_exists(update_data["name"], exclude_id=skill_id):
                raise ConflictException("技能名称已存在", code="SKILL_NAME_EXISTS")
        updated = self.repo.update(skill_id, update_data)
        self.db.commit()
        return updated.to_response_dict()

    def delete(self, skill_id: int) -> bool:
        if not self.repo.delete(skill_id):
            raise NotFoundException(f"技能不存在: {skill_id}")
        self.db.commit()
        return True

    def install(self, skill_id: int, instance_id: int = None) -> dict:
        """一键安装技能"""
        skill = self.repo.get_by_id(skill_id)
        if not skill:
            raise NotFoundException(f"技能不存在: {skill_id}")
        # TODO: 实际执行安装（Docker pull + run / pip install 等）
        # 目前先标记为已安装
        self.repo.update(skill_id, {
            "is_installed": True,
            "installed_at": datetime.now(timezone.utc),
        })
        self.db.commit()
        return skill.to_response_dict()
