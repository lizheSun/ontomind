# T55 · 长任务 Job 管理

## Goal
`agent_run_jobs` 表 + `AgentJobService`。状态机：`pending → running → paused → completed | failed | cancelled`。前端仪表盘 ETL 风格任务列表 + 详情页（步骤展开 / 日志 / 重试 / 取消）。

## Files touched
- `backend/app/services/agent_job_service.py` (NEW)
- `backend/app/schemas/agent_job.py` (NEW)
- `backend/app/api/v1/agent_jobs.py` (NEW — CRUD + start/pause/resume/cancel/retry)
- `backend/app/services/agent_job/scheduler.py` (NEW — asyncio 任务调度器)
- `frontend/src/pages/agent-jobs/index.tsx` (NEW — 列表仪表盘)
- `frontend/src/pages/agent-jobs/JobDetail.tsx` (NEW — 步骤展开)
- `frontend/src/pages/agent-jobs/components/JobStatusBadge.tsx` (NEW)
- `frontend/src/pages/agent-jobs/components/JobStepTimeline.tsx` (NEW)
- `frontend/src/pages/agent-jobs/components/JobActions.tsx` (NEW)
- `frontend/src/services/agentJobService.ts` (NEW)
- `frontend/src/routes.tsx` (`/agent-jobs`, `/agent-jobs/:id`)
- `backend/tests/data_platform/test_agent_job.py`
- `frontend/src/pages/agent-jobs/__tests__/index.test.tsx`
- `.blueprint/qa/T55/pytest.txt`

## Depends on
- T44, T53

## 功能规格
1. Job 记录：`agent_id / status / progress_pct / started_at / finished_at / steps (JSON) / error / result / input`
2. Scheduler 使用 asyncio.Task，最大并发 20（可配）
3. pause 保存 checkpoint，resume 从 checkpoint 继续
4. retry 复用 input 创建新 job
5. 仪表盘：状态过滤 / 时间排序 / 关键字搜索

## Acceptance
- Job CRUD + 5 种状态转换全部 pytest 覆盖
- 前端列表支持 WebSocket 实时刷新（fallback: poll 5s）
- 详情页步骤时间线可折叠 / 展开
- 取消 job 立即释放 asyncio.Task
- 后端重启后，running 状态的任务自动标记为 failed（orphaned 恢复）

## Verify
```bash
cd backend && pytest tests/data_platform/test_agent_job.py -v
cd frontend && npm run test -- agent-jobs
curl -X POST http://localhost:8000/api/v1/agent-jobs -d '{"agent_id":1,"input":{"q":"..."}}'
```

## Commit
`feat(agent-jobs): long-task job management with etl-style dashboard`
