"""元数据仓库."""
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.repositories.base_repo import BaseRepository
from app.db.models.metadata_model import MetaTable, MetaColumn


class MetaTableRepository(BaseRepository[MetaTable]):
    def __init__(self, db: Session):
        super().__init__(MetaTable, db)

    def get_by_datasource(self, ds_id: int, database: Optional[str] = None) -> List[MetaTable]:
        q = self.db.query(MetaTable).filter(MetaTable.datasource_id == ds_id)
        if database:
            q = q.filter(MetaTable.database_name == database)
        return q.order_by(MetaTable.database_name, MetaTable.table_name).all()

    def find(self, ds_id: int, database: str, table: str) -> Optional[MetaTable]:
        return self.db.query(MetaTable).filter(
            MetaTable.datasource_id == ds_id,
            MetaTable.database_name == database,
            MetaTable.table_name == table,
        ).first()

    def upsert(self, ds_id: int, database: str, table: str, **kwargs) -> MetaTable:
        """插入或更新（按 datasource_id + database + table 唯一）."""
        existing = self.find(ds_id, database, table)
        if existing:
            for k, v in kwargs.items():
                setattr(existing, k, v)
            existing.last_synced_at = datetime.now(timezone.utc)
            existing.sync_status = "synced"
            self.db.flush()
            return existing
        else:
            obj = MetaTable(
                datasource_id=ds_id,
                database_name=database,
                table_name=table,
                last_synced_at=datetime.now(timezone.utc),
                sync_status="synced",
                **kwargs,
            )
            self.db.add(obj)
            self.db.flush()
            return obj


class MetaColumnRepository(BaseRepository[MetaColumn]):
    def __init__(self, db: Session):
        super().__init__(MetaColumn, db)

    def get_by_table(self, table_id: int) -> List[MetaColumn]:
        return self.db.query(MetaColumn).filter(
            MetaColumn.meta_table_id == table_id
        ).order_by(MetaColumn.ordinal_position).all()

    def delete_by_table(self, table_id: int):
        self.db.query(MetaColumn).filter(MetaColumn.meta_table_id == table_id).delete()
        self.db.flush()
