"""Docker service repository."""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.docker_service_model import DockerService
from app.db.repositories.base_repo import BaseRepository


class DockerServiceRepository(BaseRepository[DockerService]):
    def __init__(self, db: Session):
        super().__init__(DockerService, db)

    def get_by_slug(self, slug: str) -> Optional[DockerService]:
        return self.db.query(DockerService).filter(DockerService.slug == slug).first()

    def list_ordered(self, skip: int = 0, limit: int = 200) -> List[DockerService]:
        return (
            self.db.query(DockerService)
            .order_by(DockerService.id.asc())
            .offset(skip).limit(limit).all()
        )