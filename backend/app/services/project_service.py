"""Project service — CRUD."""
from sqlalchemy.orm import Session
from app.db.repositories.project_repo import ProjectRepository
from app.schemas.project_schema import ProjectCreate, ProjectUpdate
from app.core.exceptions import ConflictException, NotFoundException


class ProjectService:
    def __init__(self, db: Session):
        self.repo = ProjectRepository(db)

    def list(self, skip: int = 0, limit: int = 50):
        return self.repo.list(skip, limit)

    def get(self, pid: int):
        obj = self.repo.get(pid)
        if not obj:
            raise NotFoundException(f"项目不存在: {pid}")
        return obj

    def create(self, data: ProjectCreate):
        if self.repo.get_by_key(data.key):
            raise ConflictException(f"项目标识 {data.key} 已存在")
        return self.repo.create(data.model_dump())

    def update(self, pid: int, data: ProjectUpdate):
        self.get(pid)
        return self.repo.update(pid, data.model_dump(exclude_unset=True))

    def delete(self, pid: int):
        self.get(pid)
        self.repo.delete(pid)
