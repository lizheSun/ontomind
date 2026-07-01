"""Skill 校验模型."""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class SkillBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    skill_type: str = Field(..., description="docker / mcp / script / api")
    docker_image: Optional[str] = Field(None, max_length=256)
    entrypoint: Optional[str] = Field(None, max_length=2000)
    install_cmd: Optional[str] = Field(None, max_length=2000)
    parameters_schema: Optional[Dict[str, Any]] = Field(None, description="参数 JSON Schema")
    output_schema: Optional[Dict[str, Any]] = Field(None, description="输出 JSON Schema")
    env_vars: Optional[Dict[str, Any]] = Field(None, description="环境变量")
    description: Optional[str] = Field(None, max_length=2000)
    tags: Optional[List[str]] = Field(None, description="标签")
    icon: Optional[str] = Field(None, max_length=128)
    is_active: bool = Field(True)


class SkillCreate(SkillBase):
    pass


class SkillUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    skill_type: Optional[str] = None
    docker_image: Optional[str] = Field(None, max_length=256)
    entrypoint: Optional[str] = Field(None, max_length=2000)
    install_cmd: Optional[str] = Field(None, max_length=2000)
    parameters_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    env_vars: Optional[Dict[str, Any]] = None
    description: Optional[str] = Field(None, max_length=2000)
    tags: Optional[List[str]] = None
    icon: Optional[str] = Field(None, max_length=128)
    is_active: Optional[bool] = None


class SkillResponse(SkillBase):
    id: int
    is_installed: bool = False
    installed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


class SkillInstallRequest(BaseModel):
    """一键安装请求"""
    instance_id: Optional[int] = Field(None, description="指定安装到的 Instance ID")
