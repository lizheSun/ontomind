"""Project & Requirement & Plan & Task schemas."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


# ===== Project =====

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    key: str = Field(..., min_length=2, max_length=16, pattern=r"^[A-Z0-9]+$")
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=8)
    color: Optional[str] = Field(None, max_length=7)

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = None
    status: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=8)
    color: Optional[str] = Field(None, max_length=7)


# ===== Requirement =====

class RequirementCreate(BaseModel):
    project_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=256)
    req_type: str = Field(default="feature", pattern=r"^(feature|bug|improvement|performance)$")
    priority: str = Field(default="P2", pattern=r"^P[0-3]$")
    description: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    impact_scope: Optional[str] = None
    related_modules: Optional[list[str]] = None

class RequirementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=256)
    req_type: Optional[str] = Field(None, pattern=r"^(feature|bug|improvement|performance)$")
    priority: Optional[str] = Field(None, pattern=r"^P[0-3]$")
    status: Optional[str] = None
    description: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    impact_scope: Optional[str] = None
    related_modules: Optional[list[str]] = None


# ===== Plan =====

class PlanCreate(BaseModel):
    project_id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=256)
    plan_type: str = Field(default="sprint", pattern=r"^(sprint|release|milestone)$")
    goal: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class PlanUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=256)
    plan_type: Optional[str] = Field(None, pattern=r"^(sprint|release|milestone)$")
    goal: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None


# ===== Task =====

class TaskCreate(BaseModel):
    project_id: Optional[int] = None
    plan_id: Optional[int] = None
    requirement_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    status: str = Field(default="todo", pattern=r"^(todo|in_progress|review|done)$")
    priority: str = Field(default="P2", pattern=r"^P[0-3]$")
    assignee_agent_type: Optional[str] = None
    assignee_agent_id: Optional[int] = None
    estimated_hours: Optional[float] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=256)
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = Field(None, pattern=r"^P[0-3]$")
    assignee_agent_type: Optional[str] = None
    assignee_agent_id: Optional[int] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    plan_id: Optional[int] = None  # allow moving task between plans

class TaskMove(BaseModel):
    """Move task between kanban columns."""
    status: str = Field(..., pattern=r"^(todo|in_progress|review|done)$")
    position: Optional[int] = None
