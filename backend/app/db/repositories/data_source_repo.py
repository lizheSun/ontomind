"""数据源 Repository — 仅 flush，不 commit。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.data_source_model import DataSource


class DataSourceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[DataSource]:
        return self.db.query(DataSource).order_by(DataSource.id.asc()).all()

    def get(self, source_id: int) -> Optional[DataSource]:
        return self.db.get(DataSource, source_id)

    def get_by_name(self, name: str) -> Optional[DataSource]:
        return self.db.query(DataSource).filter(DataSource.name == name).first()

    def add(self, row: DataSource) -> DataSource:
        self.db.add(row)
        self.db.flush()
        return row

    def delete(self, row: DataSource) -> None:
        self.db.delete(row)
        self.db.flush()
