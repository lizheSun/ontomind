"""服务层基类 - 提供通用服务方法和事务管理."""
from typing import Generic, TypeVar, Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.db.repositories.base_repo import BaseRepository
from app.db.models.base import BaseModel
from app.core.exceptions import NotFoundException

# 定义泛型类型
ModelType = TypeVar("ModelType", bound=BaseModel)
RepositoryType = TypeVar("RepositoryType", bound=BaseRepository)

class BaseService(Generic[ModelType, RepositoryType]):
    """服务层基类 - 封装通用业务逻辑"""
    
    def __init__(self, db: Session, repository: RepositoryType):
        self.db = db
        self.repository = repository
    
    def get_by_id(self, id: int) -> ModelType:
        """根据 ID 查询 - 如果不存在则抛出异常"""
        obj = self.repository.get_by_id(id)
        if not obj:
            raise NotFoundException(f"ID 为 {id} 的记录不存在")
        return obj
    
    def get_by_id_or_none(self, id: int) -> Optional[ModelType]:
        """根据 ID 查询 - 不存在返回 None"""
        return self.repository.get_by_id(id)
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """查询所有记录 - 支持分页"""
        return self.repository.get_all(skip, limit)
    
    def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """创建记录 - 在事务中"""
        with self.db.begin():
            return self.repository.create(obj_in)
    
    def update(self, id: int, obj_in: Dict[str, Any]) -> ModelType:
        """更新记录 - 在事务中"""
        with self.db.begin():
            obj = self.repository.update(id, obj_in)
            if not obj:
                raise NotFoundException(f"ID 为 {id} 的记录不存在")
            return obj
    
    def delete(self, id: int) -> bool:
        """删除记录 - 在事务中"""
        with self.db.begin():
            if not self.repository.delete(id):
                raise NotFoundException(f"ID 为 {id} 的记录不存在")
            return True
    
    def exists(self, id: int) -> bool:
        """检查记录是否存在"""
        return self.repository.exists(id)
    
    def count(self) -> int:
        """统计记录数"""
        return self.repository.count()
