"""Requirement service — CRUD + Agent analysis + decomposition."""
import json
from sqlalchemy.orm import Session
from app.db.repositories.requirement_repo import RequirementRepository
from app.db.repositories.task_repo import TaskRepository
from app.schemas.project_schema import RequirementCreate, RequirementUpdate
from app.core.exceptions import NotFoundException


ANALYZE_PROMPT = """你是一个资深技术需求评审专家。请对以下需求进行严格打分分析。

需求信息：
- 标题: {title}
- 类型: {req_type}
- 优先级: {priority}
- 描述: {description}
- 验收标准: {acceptance_criteria}
- 影响范围: {impact_scope}

请按以下维度评分（1-10分），输出 JSON 格式：
{{
  "score_clarity": <需求清晰度>,
  "score_feasibility": <技术可行性>,
  "score_value": <业务价值>,
  "score_total": <综合评分(加权平均)>,
  "passed": <true/false, 综合>=5 则通过>,
  "comment": "<评审意见，100字内>"
}}

只输出 JSON，不要其他内容。"""

DECOMPOSE_PROMPT = """你是一个资深任务拆解专家。请将以下需求拆解为可执行的开发任务。

需求信息：
- 标题: {title}
- 描述: {description}
- 验收标准: {acceptance_criteria}

请拆解为 3-8 个任务，每个任务包含：title（简洁标题）、description（任务描述）、priority（P0/P1/P2/P3）、estimated_hours（预估工时小时数）、assignee_agent_type（建议分配的Agent类型，如 openclaw/harness/custom）。

输出 JSON 数组格式：
[
  {{"title": "...", "description": "...", "priority": "P1", "estimated_hours": 4, "assignee_agent_type": "harness"}},
  ...
]

只输出 JSON 数组，不要其他内容。"""


class RequirementService:
    def __init__(self, db: Session):
        self.repo = RequirementRepository(db)
        self.task_repo = TaskRepository(db)
        self.db = db

    def list_by_project(self, project_id: int, skip: int = 0, limit: int = 200):
        return self.repo.list_by_project(project_id, skip, limit)

    def get(self, rid: int):
        obj = self.repo.get(rid)
        if not obj:
            raise NotFoundException(f"需求不存在: {rid}")
        return obj

    def create(self, data: RequirementCreate):
        return self.repo.create(data.model_dump())

    def update(self, rid: int, data: RequirementUpdate):
        self.get(rid)
        return self.repo.update(rid, data.model_dump(exclude_unset=True))

    def delete(self, rid: int):
        self.get(rid)
        self.repo.delete(rid)

    async def analyze(self, rid: int) -> dict:
        """调用 Agent 评审需求，自动打分"""
        req = self.get(rid)

        prompt = ANALYZE_PROMPT.format(
            title=req.title,
            req_type=req.req_type,
            priority=req.priority,
            description=req.description or "无",
            acceptance_criteria=req.acceptance_criteria or "无",
            impact_scope=req.impact_scope or "无",
        )

        result = await self._call_llm(prompt, max_tokens=1024)

        try:
            analysis = json.loads(result["content"])
        except (json.JSONDecodeError, KeyError):
            raise RuntimeError(f"Agent 评审解析失败: {result.get('content', '')[:200]}")

        update_data = {
            "score_clarity": float(analysis.get("score_clarity", 0)),
            "score_feasibility": float(analysis.get("score_feasibility", 0)),
            "score_value": float(analysis.get("score_value", 0)),
            "score_total": float(analysis.get("score_total", 0)),
            "review_comment": str(analysis.get("comment", "")),
            "status": "passed" if analysis.get("passed", False) else "rejected",
        }
        updated = self.repo.update(rid, update_data)
        return {
            "requirement": updated,
            "analysis": analysis,
        }

    async def decompose(self, rid: int) -> dict:
        """调用 Agent 拆解需求为 Task"""
        req = self.get(rid)

        if req.status not in ("passed", "in_progress"):
            raise RuntimeError("只有已通过的需求才能拆解")

        prompt = DECOMPOSE_PROMPT.format(
            title=req.title,
            description=req.description or "无",
            acceptance_criteria=req.acceptance_criteria or "无",
        )

        result = await self._call_llm(prompt, max_tokens=2048)

        try:
            tasks_raw = json.loads(result["content"])
            if not isinstance(tasks_raw, list):
                raise ValueError("返回不是数组")
        except (json.JSONDecodeError, KeyError, ValueError):
            raise RuntimeError(f"任务拆解解析失败: {result.get('content', '')[:200]}")

        # 批量创建 Task
        created = []
        for i, t in enumerate(tasks_raw):
            task_data = {
                "project_id": req.project_id,
                "requirement_id": rid,
                "title": str(t.get("title", f"Task-{i+1}")),
                "description": str(t.get("description", "")),
                "priority": str(t.get("priority", "P2")),
                "status": "todo",
                "estimated_hours": float(t.get("estimated_hours", 2)),
                "assignee_agent_type": str(t.get("assignee_agent_type", "")),
                "position": i,
            }
            created.append(task_data)

        tasks = self.task_repo.batch_create(created)

        # 标记需求为已拆解
        self.repo.update(rid, {"is_decomposed": True, "status": "in_progress"})

        return {"tasks": tasks, "count": len(tasks)}

    async def _call_llm(self, prompt: str, max_tokens: int = 1024) -> dict:
        """调用默认 LLM"""
        from app.services.llm_config_service import LLMConfigService
        llm_svc = LLMConfigService(self.db)
        return await llm_svc.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=max_tokens,
        )
