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


@router.post("/instances/register-local")
def register_local_instance(db: Session = Depends(get_db)):
    """一键添加本地服务器为计算节点，自动检测主机名/OS/CPU/内存"""
    import platform
    import os as _os
    import socket
    import subprocess

    from app.db.models.instance_model import Instance

    hostname = platform.node()
    svc = InstanceService(db)

    # 检查是否已注册
    existing = db.query(Instance).filter(Instance.name == hostname).first()
    if existing:
        return {"code": "SUCCESS", "message": "本地服务器已存在", "data": existing.to_response_dict()}

    # 检测系统信息
    try:
        cpu = _os.cpu_count() or 1
    except Exception:
        cpu = None

    try:
        mem_bytes = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"]).decode().strip())
        memory_mb = mem_bytes // (1024 * 1024)
    except Exception:
        try:
            # Linux fallback
            mem_bytes = _os.sysconf("SC_PAGE_SIZE") * _os.sysconf("SC_PHYS_PAGES")
            memory_mb = mem_bytes // (1024 * 1024)
        except Exception:
            memory_mb = None

    try:
        system = platform.system()
        os_map = {"Darwin": "macOS", "Linux": "Linux", "Windows": "Windows"}
        os_name = os_map.get(system, system)
    except Exception:
        os_name = None

    try:
        ip = socket.gethostbyname(hostname)
    except Exception:
        ip = "127.0.0.1"

    data = InstanceCreate(
        name=hostname,
        host=ip,
        port=22,
        instance_type="physical",
        protocol="ssh",
        os=os_name,
        cpu_cores=cpu,
        memory_mb=memory_mb,
        description="本地开发服务器（自动注册）",
    )
    result = svc.create(data)
    # 本地服务器注册后直接设为 online（不需要等心跳）
    from app.db.models.instance_model import Instance
    inst = db.query(Instance).filter(Instance.id == result["id"]).first()
    if inst:
        inst.status = "online"
        from datetime import datetime, timezone
        inst.last_heartbeat = datetime.now(timezone.utc)
        db.commit()
        result["status"] = "online"
        result["last_heartbeat"] = inst.last_heartbeat.isoformat()

    # 自动扫描本地 Agent
    from app.services.agent_discovery import discover_agents
    discovery = discover_agents(ip, instance_id=result["id"])
    agents_data = [
        {
            "agent_type": a.agent_type,
            "label": a.label,
            "icon": a.icon,
            "port": a.port,
            "host": a.host,
            "health_url": a.health_url,
            "is_healthy": a.is_healthy,
            "version": a.version,
            "process_name": a.process_name,
            "error": a.error,
        }
        for a in discovery.agents
    ]
    return {
        "code": "SUCCESS",
        "message": f"本地服务器已添加，发现 {len(agents_data)} 个 Agent",
        "data": result,
        "discovered_agents": agents_data,
        "total_ports_scanned": discovery.total_ports_scanned,
    }


# ==================== Agent 发现 ====================


@router.post("/instances/{inst_id}/scan-agents")
def scan_agents(inst_id: int, db: Session = Depends(get_db)):
    """
    扫描指定计算节点上的 Agent 服务，并将健康的 Agent 自动添加到 Agent 表。

    通过端口扫描 + HTTP 健康检查 + 进程检测（仅本机）来发现：
    - OpenClaw（端口 3000/8080/8000/7860）
    - OpenCode（端口 5173/3000/8080/8787）
    - Harness（端口 3000/8080/4000）

    返回每个 Agent 的可用性和版本信息，健康的 Agent 会自动注册到数据库。
    """
    from app.db.models.instance_model import Instance
    from app.db.models.agent_model import Agent
    from app.services.agent_discovery import discover_agents

    inst = db.query(Instance).filter(Instance.id == inst_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="实例不存在")

    host = inst.host
    discovery = discover_agents(host, instance_id=inst_id)

    # 自动将健康的 Agent 注册到数据库
    auto_registered: list[dict] = []
    for a in discovery.agents:
        if not a.is_healthy:
            continue

        # CLI 模式优先命名，HTTP 模式用端口
        if a.cli_command:
            agent_name = a.label
        elif a.port > 0:
            agent_name = f"{a.label}-{a.port}"
        else:
            agent_name = f"{a.label}-proc"

        # 检查是否已存在（按名称）
        existing = db.query(Agent).filter(Agent.name == agent_name).first()
        if existing:
            # 更新版本和 entrypoint
            updated = False
            if a.version and existing.version != a.version:
                existing.version = a.version
                updated = True
            if a.cli_command and existing.entrypoint != a.cli_command:
                existing.entrypoint = a.cli_command
                updated = True
            if a.port > 0 and existing.ports != [a.port]:
                existing.ports = [a.port]
                updated = True
            if updated:
                db.commit()
            auto_registered.append({"id": existing.id, "name": existing.name, "action": "updated"})
            continue

        # 确定 entrypoint: CLI 命令路径 或 HTTP URL
        if a.cli_command:
            entrypoint = a.cli_command
        elif a.port > 0:
            entrypoint = f"http://{a.host}:{a.port}"
        else:
            entrypoint = a.process_name or ""

        # 将 agent_name (OpenClaw 的 testagent 等) 存到 env_template 里
        env_template = {"agent_name": a.agent_name} if a.agent_name else None

        new_agent = Agent(
            name=agent_name,
            agent_type=a.agent_type,
            version=a.version or "latest",
            runtime="binary",
            entrypoint=entrypoint,
            docker_image=None,
            env_template=env_template,
            config_template=None,
            ports=[a.port] if a.port > 0 else None,
            volume_mounts=None,
            resource_limit=None,
            skill_ids=None,
            description=f"自动发现: {a.label} ({a.interaction_mode}) — {'CLI: ' + a.cli_command if a.cli_command else f'{a.host}:{a.port}'}（来自节点 {inst.name}）",
            is_active=True,
        )
        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)
        auto_registered.append({"id": new_agent.id, "name": new_agent.name, "action": "created"})

    agents_data = [
        {
            "agent_type": a.agent_type,
            "label": a.label,
            "icon": a.icon,
            "port": a.port,
            "host": a.host,
            "health_url": a.health_url,
            "is_healthy": a.is_healthy,
            "version": a.version,
            "process_name": a.process_name,
            "error": a.error,
            "cli_command": a.cli_command,
            "interaction_mode": a.interaction_mode,
            "agent_name": a.agent_name,
        }
        for a in discovery.agents
    ]
    return {
        "code": "SUCCESS",
        "data": {
            "instance_id": inst_id,
            "host": host,
            "agents": agents_data,
            "total_ports_scanned": discovery.total_ports_scanned,
            "errors": discovery.errors,
            "auto_registered": auto_registered,
        },
    }


# ==================== WebSocket 实时 Agent 交互 ====================


@router.websocket("/agents/{agent_id}/chat/stream")
async def stream_agent_chat(websocket: WebSocket, agent_id: int):
    """
    WebSocket 实时流式 Agent 交互。

    前端发送: {"message": "你好"}
    后端实时推送事件:
      {"type":"status","content":"正在执行 CLI..."}
      {"type":"thinking","content":"让我想想..."}
      {"type":"text","content":"回复内容"}
      {"type":"error","content":"错误信息"}
      {"type":"tool_use","tool":"read_file","input":{...}}
      {"type":"done","exit_code":0}
    """
    import os as _os
    import re as _re
    import subprocess as _sp
    import asyncio as _aio

    from app.db.models.agent_model import Agent
    from app.db.session import SessionLocal
    from app.services.agent_discovery import KNOWN_AGENTS

    await websocket.accept()

    try:
        # 等待前端发消息
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)
            message = payload.get("message", "").strip()
            if not message:
                await websocket.send_text(json.dumps({"type": "error", "content": "消息不能为空"}))
                continue

            db = SessionLocal()
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                await websocket.send_text(json.dumps({"type": "error", "content": "Agent 不存在"}))
                db.close()
                continue

            entrypoint = (agent.entrypoint or "").strip()
            if not entrypoint:
                await websocket.send_text(json.dumps({"type": "error", "content": "Agent 未配置 entrypoint"}))
                db.close()
                continue

            is_http = entrypoint.startswith("http://") or entrypoint.startswith("https://")

            if is_http:
                # HTTP 模式暂不支持流式，回退提示
                await websocket.send_text(json.dumps({"type": "error", "content": "HTTP 模式暂不支持流式，请使用 CLI 模式"}))
                db.close()
                continue

            # ============ CLI 流式模式 ============
            cli_path = entrypoint.split()[0]
            extra_args = entrypoint.split()[1:] if len(entrypoint.split()) > 1 else []

            agent_info = KNOWN_AGENTS.get(agent.agent_type, {})
            cli_chat_args = agent_info.get("cli_chat_args", ["{msg}"])

            # 获取 agent_name（从 env_template 里取，OpenClaw 需要 --agent 参数）
            agent_name = ""
            if agent.env_template and isinstance(agent.env_template, dict):
                agent_name = agent.env_template.get("agent_name", "")

            # 如果配置了 cli_list_agents_args 但没存 agent_name，自动获取
            if not agent_name and agent_info.get("cli_list_agents_args"):
                from app.services.agent_discovery import _get_first_agent_name
                agent_name = _get_first_agent_name(cli_path, agent_info["cli_list_agents_args"]) or ""

            args = [arg.replace("{msg}", message).replace("{agent_name}", agent_name) for arg in cli_chat_args]

            env = {**_os.environ, "NO_COLOR": "1", "TERM": "dumb"}
            cli_env = agent_info.get("cli_env", {})
            env.update(cli_env)

            full_cmd = [cli_path] + extra_args + args
            cmd_display = f"{cli_path} {' '.join(args[:3])}"

            await websocket.send_text(json.dumps({
                "type": "status",
                "content": f"⚡ 执行: {cmd_display}..."
            }))

            # 启动子进程，流式读取 stdout
            try:
                proc = await _aio.create_subprocess_exec(
                    *full_cmd,
                    stdout=_sp.PIPE,
                    stderr=_sp.PIPE,
                    env=env,
                )
            except FileNotFoundError:
                await websocket.send_text(json.dumps({"type": "error", "content": f"CLI 命令不存在: {cli_path}"}))
                db.close()
                continue

            ansi_escape = _re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')

            # 流式读取 stdout 行
            stdout_buffer = []
            async for raw_line in proc.stdout:
                line = raw_line.decode(errors="ignore").rstrip("\n\r")
                line_clean = ansi_escape.sub("", line).strip()
                if not line_clean:
                    continue
                stdout_buffer.append(line_clean)

                # 尝试解析为 JSON 事件
                parsed = False
                try:
                    evt = json.loads(line_clean)
                    parsed = True
                    evt_type = evt.get("type", "")

                    if evt_type in ("text", "message"):
                        content = evt.get("content", "")
                        if content:
                            await websocket.send_text(json.dumps({"type": "text", "content": content}))
                    elif evt_type == "thinking":
                        content = evt.get("content", "")
                        if content:
                            await websocket.send_text(json.dumps({"type": "thinking", "content": content}))
                    elif evt_type == "reasoning":
                        content = evt.get("content", "")
                        if content:
                            await websocket.send_text(json.dumps({"type": "thinking", "content": content}))
                    elif evt_type == "tool_use":
                        await websocket.send_text(json.dumps({
                            "type": "tool_use",
                            "tool": evt.get("tool", evt.get("name", "unknown")),
                            "input": evt.get("input", {}),
                        }))
                    elif evt_type == "tool_result":
                        await websocket.send_text(json.dumps({
                            "type": "tool_result",
                            "tool": evt.get("tool", ""),
                            "output": str(evt.get("output", evt.get("content", "")))[:2000],
                        }))
                    elif evt_type == "status":
                        await websocket.send_text(json.dumps({"type": "status", "content": evt.get("content", "")}))
                    elif evt_type == "error":
                        err_data = evt.get("error", {})
                        if isinstance(err_data, dict):
                            err_msg = err_data.get("data", {}).get("message") or err_data.get("message", str(err_data))
                        else:
                            err_msg = str(err_data)
                        await websocket.send_text(json.dumps({"type": "error", "content": err_msg}))
                    elif evt_type == "session":
                        await websocket.send_text(json.dumps({"type": "session", "session_id": evt.get("sessionID", evt.get("session_id", ""))}))
                    else:
                        # 未知事件类型，原样转发
                        await websocket.send_text(json.dumps({"type": evt_type or "raw", "content": json.dumps(evt, ensure_ascii=False)[:2000]}))
                except (json.JSONDecodeError, ValueError):
                    pass

                # 如果不是 JSON，作为 raw text 推送（可能有用的日志/输出）
                if not parsed:
                    # 过滤掉无用的进度行
                    if any(skip in line_clean.lower() for skip in ["%", "downloading", "loading"]):
                        continue
                    await websocket.send_text(json.dumps({"type": "log", "content": line_clean[:1000]}))

            # 等待进程结束
            exit_code = await proc.wait()

            # 读取 stderr
            stderr_data = b""
            if proc.stderr:
                stderr_data = await proc.stderr.read()
            stderr_text = ansi_escape.sub("", stderr_data.decode(errors="ignore")).strip()

            # 如果 stdout 是整体 JSON（OpenClaw 多行格式），buffer 里有多行
            # 尝试整体解析
            if stdout_buffer and exit_code == 0:
                full_stdout = "\n".join(stdout_buffer)
                # 检查是否还没解析出 text 事件（OpenClaw 的多行 JSON 会被逐行推送为 log）
                # 尝试整体解析
                try:
                    data = json.loads(full_stdout)
                    result_obj = data.get("result", {})
                    payloads = result_obj.get("payloads", [])
                    if payloads:
                        for p in payloads:
                            text = p.get("text", "")
                            if text:
                                await websocket.send_text(json.dumps({"type": "text", "content": text}))
                    status = data.get("status", "")
                    if status == "error":
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "content": f"OpenClaw 状态错误: {data.get('summary', 'unknown')}"
                        }))
                    meta = result_obj.get("meta", {})
                    agent_meta = meta.get("agentMeta", {})
                    if agent_meta:
                        await websocket.send_text(json.dumps({
                            "type": "meta",
                            "model": agent_meta.get("model", ""),
                            "provider": agent_meta.get("provider", ""),
                            "session_id": agent_meta.get("sessionId", ""),
                            "duration_ms": meta.get("durationMs", 0),
                        }))
                except (json.JSONDecodeError, ValueError):
                    pass  # 已经逐行推送过了

            await websocket.send_text(json.dumps({
                "type": "done",
                "exit_code": exit_code,
                **({"stderr": stderr_text[:1000]} if stderr_text else {}),
            }))

            db.close()
            # 单次问答完成，关闭连接
            break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"type": "error", "content": f"服务器异常: {e}"}))
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@router.post("/agents/{agent_id}/chat")
def chat_with_agent(agent_id: int, payload: dict, db: Session = Depends(get_db)):
    """
    与 Agent 交互测试：向 Agent 发送消息并获取响应。

    支持两种交互模式:
    1. CLI 模式 — entrypoint 是可执行命令路径（如 /usr/local/bin/openclaw）
       执行: <command> -p "<message>" 或 <command> "<message>"
    2. HTTP 模式 — entrypoint 是 URL（如 http://127.0.0.1:8000）
       POST 到 /v1/chat/completions, /chat, /api/chat 等端点

    请求体: { "message": "你好" }
    """
    import json as _json
    import urllib.request as _urlreq
    import subprocess as _subprocess
    import shlex as _shlex
    import tempfile

    from app.db.models.agent_model import Agent

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")

    message = payload.get("message", "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="消息不能为空")

    entrypoint = (agent.entrypoint or "").strip()
    if not entrypoint:
        raise HTTPException(status_code=400, detail="Agent 未配置 entrypoint，无法交互")

    # 判断交互模式: 如果 entrypoint 以 http 开头 → HTTP 模式，否则 → CLI 模式
    is_http = entrypoint.startswith("http://") or entrypoint.startswith("https://")

    # ============ CLI 模式 ============
    if not is_http:
        from app.services.agent_discovery import KNOWN_AGENTS

        cli_path = entrypoint.split()[0]
        extra_args = entrypoint.split()[1:] if len(entrypoint.split()) > 1 else []

        # 根据 agent_type 获取 CLI 交互参数模板（参照 multica）
        agent_info = KNOWN_AGENTS.get(agent.agent_type, {})
        cli_chat_args = agent_info.get("cli_chat_args", ["{msg}"])

        # 替换 {msg} 占位符
        args = [arg.replace("{msg}", message) for arg in cli_chat_args]

        # 构建环境变量（参照 multica: OPENCODE_PERMISSION 等）
        import os as _os
        env = {**_os.environ, "NO_COLOR": "1", "TERM": "dumb"}
        cli_env = agent_info.get("cli_env", {})
        env.update(cli_env)

        try:
            full_cmd = [cli_path] + extra_args + args
            result = _subprocess.run(
                full_cmd,
                capture_output=True, text=True, timeout=120,
                env=env,
            )
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            cmd_display = f"{cli_path} {' '.join(args[:2])}"

            # 清理 ANSI 转义码
            import re as _re
            ansi_escape = _re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
            stdout_clean = ansi_escape.sub('', stdout).strip()

            if not stdout_clean:
                return {
                    "code": "ERROR",
                    "message": f"CLI 无输出 (exit={result.returncode})。stderr: {stderr[:500] or '(空)'}",
                    "data": {"agent_id": agent_id, "cli_path": cli_path, "command": cmd_display, "stderr": stderr[:1000]},
                }

            # ---- 解析输出，参照 multica 的事件流模式 ----
            # OpenCode (--format json): 每行一个 JSON 事件，提取 type=text 的 content
            # OpenClaw (--json): 整体一个多行 JSON，提取 result.payloads[].text
            # 通用 fallback: 纯文本

            response_text = None

            # 1. 先尝试整体解析为单个 JSON（OpenClaw 格式: 多行格式化 JSON）
            try:
                data = _json.loads(stdout_clean)
                # OpenClaw 格式: {"status":"ok","result":{"payloads":[{"text":"..."}]}}
                result_obj = data.get("result", {})
                payloads = result_obj.get("payloads", [])
                if payloads:
                    text_parts = [p.get("text", "") for p in payloads if p.get("text")]
                    if text_parts:
                        response_text = "\n".join(text_parts)

                # 检查错误状态
                status = data.get("status", "")
                if status == "error" and not response_text:
                    return {
                        "code": "ERROR",
                        "message": f"Agent 返回错误: {data.get('summary', 'unknown')}",
                        "data": {"agent_id": agent_id, "agent_name": agent.name, "mode": "cli", "command": cmd_display, "raw_status": status},
                    }

                # 通用 JSON 字段
                if not response_text:
                    for key in ["response", "reply", "output", "message", "answer", "text", "result", "content"]:
                        val = data.get(key)
                        if val and isinstance(val, str):
                            response_text = val
                            break
                        elif val and isinstance(val, dict):
                            # 嵌套 result
                            for sub_key in ["text", "content", "message", "output"]:
                                sub_val = val.get(sub_key)
                                if sub_val and isinstance(sub_val, str):
                                    response_text = sub_val
                                    break
                            if response_text:
                                break
            except _json.JSONDecodeError:
                pass

            # 2. 尝试逐行解析 JSONL（opencode 事件流格式）
            if not response_text:
                lines = [l.strip() for l in stdout_clean.split('\n') if l.strip()]
                json_lines = []
                for line in lines:
                    try:
                        json_lines.append(_json.loads(line))
                    except _json.JSONDecodeError:
                        continue

                if json_lines:
                    text_parts = []
                    error_parts = []
                    for evt in json_lines:
                        evt_type = evt.get("type", "")
                        if evt_type in ("text", "message"):
                            content = evt.get("content", "")
                            if content:
                                text_parts.append(content)
                        elif evt_type == "error":
                            err_data = evt.get("error", {})
                            if isinstance(err_data, dict):
                                err_msg = err_data.get("data", {}).get("message") or err_data.get("message", str(err_data))
                            else:
                                err_msg = str(err_data)
                            error_parts.append(err_msg)

                    if text_parts:
                        response_text = "\n".join(text_parts)
                    elif error_parts:
                        return {
                            "code": "ERROR",
                            "message": f"Agent 返回错误: {'; '.join(error_parts)}",
                            "data": {"agent_id": agent_id, "agent_name": agent.name, "mode": "cli", "command": cmd_display, "errors": error_parts},
                        }

            # Fallback: 如果 JSON 解析失败，用清理后的纯文本
            if not response_text:
                response_text = stdout_clean[:8000]

            # 判断是否是错误响应
            is_error = "Error:" in response_text or "error" in response_text.lower()[:50]

            return {
                "code": "ERROR" if is_error else "SUCCESS",
                "data": {
                    "agent_id": agent_id,
                    "agent_name": agent.name,
                    "mode": "cli",
                    "command": cmd_display,
                    "response": response_text[:8000],
                    **({"warning": f"exit_code={result.returncode}"} if result.returncode != 0 else {}),
                },
                **({"message": "Agent 执行返回错误"} if is_error else {}),
            }
        except _subprocess.TimeoutExpired:
            return {
                "code": "ERROR",
                "message": "CLI 命令执行超时（120s），可能是 Agent 需要交互式输入或等待模型响应",
                "data": {"agent_id": agent_id, "cli_path": cli_path, "command": f"{cli_path} {' '.join(args[:2])}"},
            }
        except FileNotFoundError:
            return {
                "code": "ERROR",
                "message": f"CLI 命令不存在: {cli_path}",
                "data": {"agent_id": agent_id, "cli_path": cli_path},
            }
        except Exception as e:
            return {
                "code": "ERROR",
                "message": f"CLI 执行异常: {e}",
                "data": {"agent_id": agent_id, "cli_path": cli_path},
            }

    # ============ HTTP 模式 ============
    base_url = entrypoint.rstrip("/")
    chat_endpoints = [
        "/v1/chat/completions",
        "/chat",
        "/api/chat",
        "/api/v1/chat",
        "/v1/chat",
    ]

    openai_body = _json.dumps({
        "model": agent.name,
        "messages": [{"role": "user", "content": message}],
        "stream": False,
        "max_tokens": 2000,
    }).encode("utf-8")

    simple_body = _json.dumps({
        "message": message,
        "input": message,
        "query": message,
    }).encode("utf-8")

    last_error = None
    for endpoint in chat_endpoints:
        url = f"{base_url}{endpoint}"
        for body in [openai_body, simple_body]:
            try:
                req = _urlreq.Request(url, data=body, method="POST")
                req.add_header("Content-Type", "application/json")
                req.add_header("User-Agent", "OntoMind-AgentChat/1.0")
                resp = _urlreq.urlopen(req, timeout=30)
                resp_body = resp.read().decode(errors="ignore")[:10000]

                try:
                    data = _json.loads(resp_body)
                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0].get("message", {}).get("content", "")
                        if content:
                            return {
                                "code": "SUCCESS",
                                "data": {
                                    "agent_id": agent_id,
                                    "agent_name": agent.name,
                                    "mode": "http",
                                    "endpoint": endpoint,
                                    "response": content,
                                },
                            }
                    for key in ["response", "reply", "output", "message", "answer", "text", "result"]:
                        if key in data and data[key]:
                            return {
                                "code": "SUCCESS",
                                "data": {
                                    "agent_id": agent_id,
                                    "agent_name": agent.name,
                                    "mode": "http",
                                    "endpoint": endpoint,
                                    "response": str(data[key]),
                                },
                            }
                    if isinstance(data, str) and data:
                        return {
                            "code": "SUCCESS",
                            "data": {
                                "agent_id": agent_id,
                                "agent_name": agent.name,
                                "mode": "http",
                                "endpoint": endpoint,
                                "response": data,
                            },
                        }
                except _json.JSONDecodeError:
                    if resp_body.strip():
                        return {
                            "code": "SUCCESS",
                            "data": {
                                "agent_id": agent_id,
                                "agent_name": agent.name,
                                "mode": "http",
                                "endpoint": endpoint,
                                "response": resp_body[:2000],
                            },
                        }
            except Exception as e:
                last_error = str(e)
                continue

    return {
        "code": "ERROR",
        "message": f"无法连接到 Agent 或未找到可用的 chat 端点。最后错误: {last_error}",
        "data": {
            "agent_id": agent_id,
            "base_url": base_url,
            "tried_endpoints": chat_endpoints,
        },
    }


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
