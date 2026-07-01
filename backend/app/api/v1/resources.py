"""资源管理 API — Instance / Agent / Skill / MCP / AgentRun."""
import json
import asyncio
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.instance_service import InstanceService
from app.services.agent_service import AgentService
from app.services.skill_service import SkillService
from app.services.mcp_service import MCPService
from app.services.agent_run_service import AgentRunService

from app.schemas.instance_schema import InstanceCreate, InstanceUpdate
from app.schemas.agent_schema import AgentCreate, AgentUpdate
from app.schemas.skill_schema import SkillCreate, SkillUpdate, SkillInstallRequest
from app.schemas.mcp_schema import MCPCreate, MCPUpdate, MCPAutoDiscoverRequest
from app.schemas.agent_run_schema import AgentRunCreate, AgentRunUpdate

router = APIRouter()

# ==================== Instance 计算节点 ====================


@router.get("/instances")
def list_instances(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    svc = InstanceService(db)
    return {"code": "SUCCESS", "data": svc.list(skip, limit)}


@router.post("/instances")
def create_instance(data: InstanceCreate, db: Session = Depends(get_db)):
    svc = InstanceService(db)
    return {"code": "SUCCESS", "message": "创建成功", "data": svc.create(data)}


@router.get("/instances/{inst_id}")
def get_instance(inst_id: int, db: Session = Depends(get_db)):
    svc = InstanceService(db)
    return {"code": "SUCCESS", "data": svc.get(inst_id)}


@router.put("/instances/{inst_id}")
def update_instance(inst_id: int, data: InstanceUpdate, db: Session = Depends(get_db)):
    svc = InstanceService(db)
    return {"code": "SUCCESS", "message": "更新成功", "data": svc.update(inst_id, data)}


@router.delete("/instances/{inst_id}")
def delete_instance(inst_id: int, db: Session = Depends(get_db)):
    svc = InstanceService(db)
    svc.delete(inst_id)
    return {"code": "SUCCESS", "message": "删除成功"}


@router.post("/instances/{inst_id}/heartbeat")
def heartbeat_instance(inst_id: int, db: Session = Depends(get_db)):
    """手动标记心跳"""
    from app.db.repositories.instance_repo import InstanceRepository
    InstanceRepository(db).update_heartbeat(inst_id)
    return {"code": "SUCCESS", "message": "心跳已刷新"}


# ==================== Agent 智能体定义 ====================


@router.get("/agents")
def list_agents(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    svc = AgentService(db)
    return {"code": "SUCCESS", "data": svc.list(skip, limit)}


@router.post("/agents")
def create_agent(data: AgentCreate, db: Session = Depends(get_db)):
    svc = AgentService(db)
    return {"code": "SUCCESS", "message": "创建成功", "data": svc.create(data)}


@router.get("/agents/{agent_id}")
def get_agent(agent_id: int, db: Session = Depends(get_db)):
    svc = AgentService(db)
    return {"code": "SUCCESS", "data": svc.get(agent_id)}


@router.put("/agents/{agent_id}")
def update_agent(agent_id: int, data: AgentUpdate, db: Session = Depends(get_db)):
    svc = AgentService(db)
    return {"code": "SUCCESS", "message": "更新成功", "data": svc.update(agent_id, data)}


@router.delete("/agents/{agent_id}")
def delete_agent(agent_id: int, db: Session = Depends(get_db)):
    svc = AgentService(db)
    svc.delete(agent_id)
    return {"code": "SUCCESS", "message": "删除成功"}


# ==================== Skill 技能模块 ====================


@router.get("/skills")
def list_skills(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    svc = SkillService(db)
    return {"code": "SUCCESS", "data": svc.list(skip, limit)}


@router.post("/skills")
def create_skill(data: SkillCreate, db: Session = Depends(get_db)):
    svc = SkillService(db)
    return {"code": "SUCCESS", "message": "创建成功", "data": svc.create(data)}


@router.get("/skills/{skill_id}")
def get_skill(skill_id: int, db: Session = Depends(get_db)):
    svc = SkillService(db)
    return {"code": "SUCCESS", "data": svc.get(skill_id)}


@router.put("/skills/{skill_id}")
def update_skill(skill_id: int, data: SkillUpdate, db: Session = Depends(get_db)):
    svc = SkillService(db)
    return {"code": "SUCCESS", "message": "更新成功", "data": svc.update(skill_id, data)}


@router.delete("/skills/{skill_id}")
def delete_skill(skill_id: int, db: Session = Depends(get_db)):
    svc = SkillService(db)
    svc.delete(skill_id)
    return {"code": "SUCCESS", "message": "删除成功"}


@router.post("/skills/{skill_id}/install")
def install_skill(skill_id: int, body: SkillInstallRequest = None, db: Session = Depends(get_db)):
    """一键安装技能到指定 Instance"""
    instance_id = body.instance_id if body else None
    svc = SkillService(db)
    return {"code": "SUCCESS", "message": "安装成功", "data": svc.install(skill_id, instance_id)}


# ==================== MCP 工具/服务 ====================


@router.get("/mcps")
def list_mcps(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    svc = MCPService(db)
    return {"code": "SUCCESS", "data": svc.list(skip, limit)}


@router.post("/mcps")
def create_mcp(data: MCPCreate, db: Session = Depends(get_db)):
    svc = MCPService(db)
    return {"code": "SUCCESS", "message": "创建成功", "data": svc.create(data)}


@router.get("/mcps/{mcp_id}")
def get_mcp(mcp_id: int, db: Session = Depends(get_db)):
    svc = MCPService(db)
    return {"code": "SUCCESS", "data": svc.get(mcp_id)}


@router.put("/mcps/{mcp_id}")
def update_mcp(mcp_id: int, data: MCPUpdate, db: Session = Depends(get_db)):
    svc = MCPService(db)
    return {"code": "SUCCESS", "message": "更新成功", "data": svc.update(mcp_id, data)}


@router.delete("/mcps/{mcp_id}")
def delete_mcp(mcp_id: int, db: Session = Depends(get_db)):
    svc = MCPService(db)
    svc.delete(mcp_id)
    return {"code": "SUCCESS", "message": "删除成功"}


@router.post("/mcps/auto-discover")
async def auto_discover_mcp(data: MCPAutoDiscoverRequest, db: Session = Depends(get_db)):
    """从任意 API + LLM 自动发现生成 MCP 配置"""
    svc = MCPService(db)
    result = await svc.auto_discover(
        api_url=data.api_url,
        method=data.method,
        headers=data.headers,
        request_body_example=data.request_body_example,
        response_body_example=data.response_body_example,
        description_text=data.description_text,
    )
    return result


# ==================== AgentRun 运行时 ====================


@router.get("/runs")
def list_runs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    svc = AgentRunService(db)
    return {"code": "SUCCESS", "data": svc.list(skip, limit)}


@router.post("/runs")
def create_run(data: AgentRunCreate, db: Session = Depends(get_db)):
    svc = AgentRunService(db)
    return {"code": "SUCCESS", "message": "启动成功", "data": svc.create(data)}


@router.get("/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db)):
    svc = AgentRunService(db)
    return {"code": "SUCCESS", "data": svc.get(run_id)}


@router.put("/runs/{run_id}")
def update_run(run_id: int, data: AgentRunUpdate, db: Session = Depends(get_db)):
    svc = AgentRunService(db)
    return {"code": "SUCCESS", "message": "更新成功", "data": svc.update(run_id, data)}


@router.post("/runs/{run_id}/stop")
def stop_run(run_id: int, db: Session = Depends(get_db)):
    svc = AgentRunService(db)
    return {"code": "SUCCESS", "message": "已停止", "data": svc.stop(run_id)}


# ==================== WebSocket 实时日志 ====================


@router.websocket("/runs/{run_id}/logs")
async def stream_run_logs(websocket: WebSocket, run_id: int):
    """WebSocket 实时推送 AgentRun 日志"""
    await websocket.accept()
    try:
        from app.db.session import SessionLocal
        svc = AgentRunService(SessionLocal())

        async for log_entry in svc.stream_logs(run_id, SessionLocal):
            await websocket.send_text(log_entry)

        await websocket.close()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_text(json.dumps({"error": str(e)}))
        await websocket.close()
