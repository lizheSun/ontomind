"""Compute node business service (formerly Instance).

T45 naming migration: `Instance → ComputeNode`.

Public API (canonical):
    - ComputeNodeService

Backwards-compat aliases (legacy imports keep working):
    - InstanceService  = ComputeNodeService

Note: the persistence layer still uses the `Instance` ORM model /
`InstanceRepository` / `InstanceCreate`/`InstanceUpdate` schemas, because
T44 introduced a separate `ComputeNode` model for the container platform.
Only the *service* facade is renamed here — the DTOs are unchanged.
"""
from sqlalchemy.orm import Session
from app.db.repositories.instance_repo import InstanceRepository
from app.schemas.instance_schema import InstanceCreate, InstanceUpdate
from app.core.exceptions import ConflictException, NotFoundException


class ComputeNodeService:
    """CRUD service for compute nodes (legacy: `Instance`).

    The underlying storage still lives in the `instances` table via
    `InstanceRepository`. Renaming the facade is a compatible rename —
    consumers that import `InstanceService` from this module get the same
    object via the backwards-compat alias below.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = InstanceRepository(db)

    def create(self, data: InstanceCreate) -> dict:
        if self.repo.name_exists(data.name):
            raise ConflictException("计算节点名称已存在", code="COMPUTE_NODE_NAME_EXISTS")
        inst = self.repo.create(data.model_dump())
        self.db.commit()
        return inst.to_response_dict()

    def get(self, inst_id: int) -> dict:
        inst = self.repo.get_by_id(inst_id)
        if not inst:
            raise NotFoundException(f"计算节点不存在: {inst_id}")
        return inst.to_response_dict()

    def list(self, skip: int = 0, limit: int = 100) -> list[dict]:
        items = self.repo.get_all(skip, limit)
        return [i.to_response_dict() for i in items]

    def update(self, inst_id: int, data: InstanceUpdate) -> dict:
        inst = self.repo.get_by_id(inst_id)
        if not inst:
            raise NotFoundException(f"计算节点不存在: {inst_id}")
        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data and update_data["name"] != inst.name:
            if self.repo.name_exists(update_data["name"], exclude_id=inst_id):
                raise ConflictException(
                    "计算节点名称已存在", code="COMPUTE_NODE_NAME_EXISTS"
                )
        updated = self.repo.update(inst_id, update_data)
        self.db.commit()
        return updated.to_response_dict()

    def delete(self, inst_id: int) -> bool:
        if not self.repo.delete(inst_id):
            raise NotFoundException(f"计算节点不存在: {inst_id}")
        self.db.commit()
        return True


# --- Backwards-compat aliases (do NOT remove until Wave 12) ---
# Older code paths still import `InstanceService` from this module.
InstanceService = ComputeNodeService
