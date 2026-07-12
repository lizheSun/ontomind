"""Credential repository."""
from sqlalchemy.orm import Session

from app.db.models.credential_model import Credential
from app.db.repositories.base_repo import BaseRepository


class CredentialRepository(BaseRepository[Credential]):
    def __init__(self, db: Session):
        super().__init__(Credential, db)

    def get_by_name(self, name: str) -> Credential | None:
        return self.db.query(Credential).filter(Credential.name == name).first()

    def name_exists(self, name: str, exclude_id: int | None = None) -> bool:
        query = self.db.query(Credential).filter(Credential.name == name)
        if exclude_id is not None:
            query = query.filter(Credential.id != exclude_id)
        return query.first() is not None


__all__ = ["CredentialRepository"]
