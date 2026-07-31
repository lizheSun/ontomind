"""容器模板 repository."""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.container_template_model import ContainerTemplate
from app.db.repositories.base_repo import BaseRepository


class ContainerTemplateRepository(BaseRepository[ContainerTemplate]):
    def __init__(self, db: Session):
        super().__init__(ContainerTemplate, db)

    def get_by_name(self, name: str) -> Optional[ContainerTemplate]:
        return self.db.query(ContainerTemplate).filter(ContainerTemplate.name == name).first()

    def list_ordered(self, skip: int = 0, limit: int = 200) -> List[ContainerTemplate]:
        return (
            self.db.query(ContainerTemplate)
            .order_by(ContainerTemplate.sort_order.asc(), ContainerTemplate.id.asc())
            .offset(skip).limit(limit).all()
        )
