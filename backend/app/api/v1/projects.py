"""项目管理 API — Project / Requirement / Plan / Task / Kanban."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.repositories.plan_repo import PlanRepository
from app.services.project_service import ProjectService
from app.services.requirement_service import RequirementService
from app.services.llm_config_service import LLMConfigService

from app.schemas.project_schema import (
    ProjectCreate, ProjectUpdate,
    RequirementCreate, RequirementUpdate,
    PlanCreate, PlanUpdate,
    TaskCreate, TaskUpdate, TaskMove,
)

router = APIRouter()

# ==================== Project ====================


@router.get("")
def list_projects(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    svc = ProjectService(db)
    return {"code": "SUCCESS", "data": svc.list(skip, limit)}


@router.post("")
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    svc = ProjectService(db)
    return {"code": "SUCCESS", "message": "创建成功", "data": svc.create(data)}


@router.get("/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):
    svc = ProjectService(db)
    return {"code": "SUCCESS", "data": svc.get(project_id)}


@router.put("/{project_id}")
def update_project(project_id: int, data: ProjectUpdate, db: Session = Depends(get_db)):
    svc = ProjectService(db)
    return {"code": "SUCCESS", "message": "更新成功", "data": svc.update(project_id, data)}


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    svc = ProjectService(db)
    svc.delete(project_id)
    return {"code": "SUCCESS", "message": "删除成功"}


# ==================== Requirement ====================


@router.get("/{project_id}/requirements")
def list_requirements(project_id: int, skip: int = 0, limit: int = 200, db: Session = Depends(get_db)):
    svc = RequirementService(db)
    return {"code": "SUCCESS", "data": svc.list_by_project(project_id, skip, limit)}


@router.post("/{project_id}/requirements")
def create_requirement(project_id: int, data: RequirementCreate, db: Session = Depends(get_db)):
    data.project_id = project_id
    svc = RequirementService(db)
    return {"code": "SUCCESS", "message": "创建成功", "data": svc.create(data)}


@router.put("/{project_id}/requirements/{req_id}")
def update_requirement(project_id: int, req_id: int, data: RequirementUpdate, db: Session = Depends(get_db)):
    svc = RequirementService(db)
    return {"code": "SUCCESS", "message": "更新成功", "data": svc.update(req_id, data)}


@router.delete("/{project_id}/requirements/{req_id}")
def delete_requirement(project_id: int, req_id: int, db: Session = Depends(get_db)):
    svc = RequirementService(db)
    svc.delete(req_id)
    return {"code": "SUCCESS", "message": "删除成功"}


@router.post("/{project_id}/requirements/{req_id}/analyze")
async def analyze_requirement(project_id: int, req_id: int, db: Session = Depends(get_db)):
    """Agent 自动评审需求并打分"""
    try:
        svc = RequirementService(db)
        return {"code": "SUCCESS", "message": "评审完成", "data": await svc.analyze(req_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/requirements/{req_id}/decompose")
async def decompose_requirement(project_id: int, req_id: int, db: Session = Depends(get_db)):
    """Agent 拆解需求为 Task"""
    try:
        svc = RequirementService(db)
        return {"code": "SUCCESS", "message": "拆解完成", "data": await svc.decompose(req_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Plan ====================


@router.get("/{project_id}/plans")
def list_plans(project_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    repo = PlanRepository(db)
    return {"code": "SUCCESS", "data": repo.list_by_project(project_id, skip, limit)}


@router.post("/{project_id}/plans")
def create_plan(project_id: int, data: PlanCreate, db: Session = Depends(get_db)):
    data.project_id = project_id
    repo = PlanRepository(db)
    return {"code": "SUCCESS", "message": "创建成功", "data": repo.create(data.model_dump())}


@router.put("/{project_id}/plans/{plan_id}")
def update_plan(project_id: int, plan_id: int, data: PlanUpdate, db: Session = Depends(get_db)):
    repo = PlanRepository(db)
    return {"code": "SUCCESS", "message": "更新成功", "data": repo.update(plan_id, data.model_dump(exclude_unset=True))}


@router.delete("/{project_id}/plans/{plan_id}")
def delete_plan(project_id: int, plan_id: int, db: Session = Depends(get_db)):
    repo = PlanRepository(db)
    repo.delete(plan_id)
    return {"code": "SUCCESS", "message": "删除成功"}


# ==================== Task ====================


from app.db.repositories.task_repo import TaskRepository


@router.get("/{project_id}/tasks")
def list_tasks(project_id: int, requirement_id: int = None, skip: int = 0, limit: int = 500, db: Session = Depends(get_db)):
    repo = TaskRepository(db)
    if requirement_id:
        return {"code": "SUCCESS", "data": repo.list_by_requirement(requirement_id)}
    return {"code": "SUCCESS", "data": repo.list_by_project(project_id, skip, limit)}


@router.post("/{project_id}/tasks")
def create_task(project_id: int, data: TaskCreate, db: Session = Depends(get_db)):
    data.project_id = project_id
    repo = TaskRepository(db)
    return {"code": "SUCCESS", "message": "创建成功", "data": repo.create(data.model_dump())}


@router.put("/{project_id}/tasks/{task_id}")
def update_task(project_id: int, task_id: int, data: TaskUpdate, db: Session = Depends(get_db)):
    repo = TaskRepository(db)
    return {"code": "SUCCESS", "message": "更新成功", "data": repo.update(task_id, data.model_dump(exclude_unset=True))}


@router.put("/{project_id}/tasks/{task_id}/move")
def move_task(project_id: int, task_id: int, data: TaskMove, db: Session = Depends(get_db)):
    """移动任务到看板不同列"""
    repo = TaskRepository(db)
    update_data = {"status": data.status}
    if data.position is not None:
        update_data["position"] = data.position
    return {"code": "SUCCESS", "message": "已移动", "data": repo.update(task_id, update_data)}


@router.delete("/{project_id}/tasks/{task_id}")
def delete_task(project_id: int, task_id: int, db: Session = Depends(get_db)):
    repo = TaskRepository(db)
    repo.delete(task_id)
    return {"code": "SUCCESS", "message": "删除成功"}


# ==================== Kanban ====================


@router.get("/{project_id}/kanban")
def get_kanban(project_id: int, db: Session = Depends(get_db)):
    """获取项目的敏捷看板数据"""
    repo = TaskRepository(db)
    return {"code": "SUCCESS", "data": repo.get_kanban(project_id)}
