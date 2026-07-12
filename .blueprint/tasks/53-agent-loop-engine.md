# T53 · Agent Loop 状态机引擎

## Goal
实现 `AgentLoopService`：5 种 loop 策略（single_shot / react / plan_execute / evaluator_optimizer / reflect）+ eval hooks + checkpoint。状态机：`pending → running → evaluating → completed | failed | needs_review`。

## Files touched
- `backend/app/services/agent_loop_service.py` (NEW)
- `backend/app/services/agent_loop/strategies/__init__.py` (NEW)
- `backend/app/services/agent_loop/strategies/single_shot.py` (NEW)
- `backend/app/services/agent_loop/strategies/react.py` (NEW)
- `backend/app/services/agent_loop/strategies/plan_execute.py` (NEW)
- `backend/app/services/agent_loop/strategies/evaluator_optimizer.py` (NEW)
- `backend/app/services/agent_loop/strategies/reflect.py` (NEW)
- `backend/app/services/agent_loop/eval_hook.py` (NEW — 验证器接口)
- `backend/app/services/agent_loop/state_machine.py` (NEW — 状态转换 + 校验)
- `backend/app/services/agent_loop/checkpointer.py` (NEW — DB checkpoint)
- `backend/app/schemas/agent_loop.py` (NEW — LoopState / EvalVerdict enums)
- `backend/tests/data_platform/test_agent_loop.py` (10+ test)
- `.blueprint/qa/T53/pytest.txt`

## Depends on
- T44

## 功能规格
1. `LoopState = pending | running | evaluating | completed | failed | needs_review`
2. Eval Hook 签名：`(context, output) -> {verdict: PASS|REVISE|FAIL, score: 0..1, feedback: str}`
3. `max_iterations` 保护，超限后强制 failed
4. 每次状态变更写入 `agent_run_jobs.steps` JSON 列（checkpoint）
5. 支持从 checkpoint 恢复（`resume(job_id)`）
6. 5 种策略各自 4+ 单元测试

## Acceptance
- 10+ pytest 全部通过
- 状态转换非法路径抛 `IllegalStateTransition`
- checkpoint 序列化 / 反序列化幂等
- eval hook 可注入自定义评估函数

## Verify
```bash
cd backend
pytest tests/data_platform/test_agent_loop.py -v --cov=app.services.agent_loop
```

## Commit
`feat(agent-loop): 5 strategies + eval hooks + checkpoint state machine`
