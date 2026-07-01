"""AgentRun 业务服务."""
import asyncio
import json
from typing import AsyncGenerator
from sqlalchemy.orm import Session
from app.db.repositories.agent_run_repo import AgentRunRepository
from app.db.repositories.agent_repo import AgentRepository
from app.db.repositories.instance_repo import InstanceRepository
from app.schemas.agent_run_schema import AgentRunCreate, AgentRunUpdate
from app.core.exceptions import ConflictException, NotFoundException


class AgentRunService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AgentRunRepository(db)
        self.agent_repo = AgentRepository(db)
        self.instance_repo = InstanceRepository(db)

    def create(self, data: AgentRunCreate) -> dict:
        run = self.repo.create(data.model_dump())
        self.db.commit()
        return run.to_response_dict()

    def get(self, run_id: int) -> dict:
        run = self.repo.get_by_id(run_id)
        if not run:
            raise NotFoundException(f"运行实例不存在: {run_id}")
        return run.to_response_dict()

    def list(self, skip: int = 0, limit: int = 100) -> list[dict]:
        items = self.repo.get_all(skip, limit)
        return [r.to_response_dict() for r in items]

    def update(self, run_id: int, data: AgentRunUpdate) -> dict:
        run = self.repo.get_by_id(run_id)
        if not run:
            raise NotFoundException(f"运行实例不存在: {run_id}")
        updated = self.repo.update(run_id, data.model_dump(exclude_unset=True))
        self.db.commit()
        return updated.to_response_dict()

    def stop(self, run_id: int) -> dict:
        """停止运行"""
        run = self.repo.get_by_id(run_id)
        if not run:
            raise NotFoundException(f"运行实例不存在: {run_id}")
        # TODO: 实际停止进程/容器
        from datetime import datetime, timezone
        self.repo.update(run_id, {
            "status": "stopped",
            "stopped_at": datetime.now(timezone.utc),
        })
        self.db.commit()
        return run.to_response_dict()

    async def stream_logs(self, run_id: int, db_factory) -> AsyncGenerator[str, None]:
        """WebSocket 实时日志流"""
        db = next(db_factory())
        try:
            run = self.repo.get_by_id(run_id)
            if not run:
                yield json.dumps({"error": f"运行实例不存在: {run_id}"})
                return

            # TODO: 实际对接 Docker logs / SSH tail -f
            # 目前模拟日志流
            mock_logs = [
                "[系统] Agent 正在初始化...",
                "[系统] 正在连接 Instance...",
                "[系统] 环境检查完成",
                "[系统] 正在下载依赖...",
                "[系统] Agent 启动成功",
                "[INFO] Agent 开始处理任务...",
            ]
            for log in mock_logs:
                yield json.dumps({
                    "timestamp": "2025-07-01T09:00:00Z",
                    "level": "info",
                    "message": log,
                })
                await asyncio.sleep(0.5)
        finally:
            db.close()
