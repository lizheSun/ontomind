"""Repository 基类 - 提供通用的 CRUD 操作."""
from typing import TypeVar, Generic, Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.db.models.base import BaseModel

# 定义泛型类型
ModelType = TypeVar("ModelType", bound=BaseModel)

class BaseRepository(Generic[ModelType]):
    """Repository 基类 - 封装通用 CRUD 操作"""
    
    def __init__(self, model: type[ModelType], db: Session):
        self.model = model
        self.db = db
    
    def get_by_id(self, id: int) -> Optional[ModelType]:
        """根据 ID 查询"""
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """查询所有记录 - 支持分页"""
        return self.db.query(self.model).offset(skip).limit(limit).all()
    
    def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """创建记录"""
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        self.db.flush()  # 刷新以获取 ID
        return db_obj
    
    def update(self, id: int, obj_in: Dict[str, Any]) -> Optional[ModelType]:
        """更新记录"""
        db_obj = self.get_by_id(id)
        if db_obj:
            for key, value in obj_in.items():
                if hasattr(db_obj, key):
                    setattr(db_obj, key, value)
            self.db.flush()
        return db_obj
    
    def delete(self, id: int) -> bool:
        """删除记录"""
        db_obj = self.get_by_id(id)
        if db_obj:
            self.db.delete(db_obj)
            self.db.flush()
            return True
        return False
    
    def count(self) -> int:
        """统计记录数"""
        return self.db.query(self.model).count()
    
    def exists(self, id: int) -> bool:
        """检查记录是否存在"""
        return self.db.query(self.model).filter(self.model.id == id).first() is not None
