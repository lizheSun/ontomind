"""MCP 仓库."""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.db.repositories.base_repo import BaseRepository
from app.db.models.mcp_model import MCPConfig


class MCPRepository(BaseRepository[MCPConfig]):
    def __init__(self, db: Session):
        super().__init__(MCPConfig, db)

    def name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        q = self.db.query(MCPConfig).filter(MCPConfig.name == name)
        if exclude_id is not None:
            q = q.filter(MCPConfig.id != exclude_id)
        return q.first() is not None

    def get_active(self) -> List[MCPConfig]:
        return self.db.query(MCPConfig).filter(MCPConfig.is_active == True).all()

    def get_by_type(self, mcp_type: str) -> List[MCPConfig]:
        return self.db.query(MCPConfig).filter(MCPConfig.mcp_type == mcp_type).all()
