"""算力调度种子：幂等 upsert 内置容器模板.

由 main.py 的 lifespan 在 Base.metadata.create_all 之后调用一次。
"""
from __future__ import annotations

import json

from loguru import logger
from sqlalchemy.orm import Session

from app.db.models.container_template_model import ContainerTemplate

_OPENCODE_LONG_DESC = """\
## smanx/opencode — OpenCode Web (Docker)

一个开箱即用的 OpenCode Web 容器镜像：基于 Ubuntu，通过官方安装脚本安装 opencode，容器启动后默认在 **0.0.0.0:4096** 运行 `opencode web`。

### 运行
```bash
docker run -itd --name opencode -p 4096:4096 \\
  -v opencode-config:/root/.config/opencode \\
  -v opencode-data:/root/.local/share/opencode \\
  smanx/opencode
```

挂载当前项目目录作为工作区：
```bash
docker run -itd --name opencode -p 4096:4096 \\
  -v opencode-config:/root/.config/opencode \\
  -v opencode-data:/root/.local/share/opencode \\
  -v "$(pwd)":/workspace \\
  smanx/opencode
```

### 持久化目录
| 目录 | 说明 |
|------|------|
| `/root/.config/opencode` | 配置（opencode.jsonc） |
| `/root/.local/share/opencode` | 数据（auth.json、opencode.db、log/、storage/） |
| `/root/.local/state/opencode` | 状态（可选） |
| `/root/.cache/opencode` | 缓存（可选） |

### 环境变量
- `OPENCODE_HOSTNAME=0.0.0.0` — 监听地址
- `OPENCODE_PORT=4096` — 监听端口
- `OPENCODE_CORS=<origin>` — CORS 白名单，可逗号分隔多个
- `OPENCODE_MDNS=true` — 启用 mDNS
- `OPENCODE_LOG_LEVEL=INFO` — 日志级别（DEBUG/INFO/WARN/ERROR）
- `OPENCODE_SERVER_USERNAME` / `OPENCODE_SERVER_PASSWORD` — 认证凭据

### Web 参数
镜像名后面的参数会原样转发给 `opencode web`：
- `--port <number>` / `--hostname <string>`
- `--cors <origin>`（可多次传入）
- `--mdns` / `--mdns-domain <string>`
- `--log-level <level>` / `--print-logs`

### API 信息
- Base URL: `https://openai.good.hidns.vip/v1`
- API Key: 镜像内置公开共享 Key，仅供测试使用

启动后浏览器访问：**http://localhost:4096**
"""

_SEEDS: list[dict] = [
    {
        "name": "OpenCode",
        "image": "smanx/opencode",
        "description": "OpenCode Web 容器镜像 — 基于 Ubuntu，开箱即用。默认在 4096 端口提供 opencode web 服务，支持 CORS / 认证 / mDNS。",
        "long_description": _OPENCODE_LONG_DESC,
        "icon": "RocketOutlined",
        "category": "devtool",
        "command": "opencode web --port 4096 --cors http://localhost:5173 --cors http://localhost:3000 --log-level INFO",
        "ports": ["4096:4096"],
        "env_vars": [
            "OPENCODE_HOSTNAME=0.0.0.0",
            "OPENCODE_PORT=4096",
            "OPENCODE_CORS=http://localhost:5173,http://localhost:3000",
            "OPENCODE_LOG_LEVEL=INFO",
        ],
        "volumes": [
            "opencode-config:/root/.config/opencode",
            "opencode-data:/root/.local/share/opencode",
        ],
        "restart_policy": "unless-stopped",
        "is_builtin": True,
        "sort_order": 1,
    },
    {
        # OALP v1.0: 专家团专用模板。
        # 区别于通用 OpenCode 模板：
        #   1. 默认命令用 `opencode serve`（不是 web），便于 SDK 直连
        #   2. 端口/挂载由 deploy_expert_container() 在运行时精确注入：
        #      - agent/{slug}.md → /root/.config/opencode/agent/{slug}.md (ro)
        #      - skills/         → /root/.config/opencode/skills (ro)
        #      - opencode.json   → /root/.config/opencode/opencode.json (ro)
        "name": "opencode-agent",
        "image": "smanx/opencode",
        "description": "OALP 专家团容器模板 — 拉起 opencode serve，自动挂载专家 agent.md + skills + opencode.json。",
        "long_description": (
            "## opencode-agent — 专家团容器化部署\n\n"
            "为 OntoMind「专家团」功能定制的容器模板：\n\n"
            "1. **基础镜像**：`smanx/opencode`（与通用 OpenCode 模板一致）\n"
            "2. **启动命令**：`opencode serve`（不是 web，SDK 可直连）\n"
            "3. **端口**：4096（容器内）→ 自动分配空闲主机端口（部署时）\n"
            "4. **关键挂载**（部署时由后端精确注入，不要手动改）：\n"
            "   - `{agent_dir}` → `/root/.config/opencode/agent` (ro)\n"
            "   - `{skill_dir}` → `/root/.config/opencode/skills` (ro)\n"
            "   - `{cfg}/opencode.json` → `/root/.config/opencode/opencode.json` (ro)\n"
            "5. **opencode CLI 兼容性**：≥ 1.17\n\n"
            "使用方式：在专家团页面点「部署为容器」→ 选本节点 → 自动起容器 + 健康检查。\n"
        ),
        "icon": "ExperimentOutlined",
        "category": "agent",
        "command": "opencode serve --port 4096 --hostname 0.0.0.0",
        "ports": ["4096:4096"],
        "env_vars": [
            "OPENCODE_HOSTNAME=0.0.0.0",
            "OPENCODE_PORT=4096",
            "OPENCODE_CORS=http://localhost:5173,http://127.0.0.1:5173",
            "OPENCODE_LOG_LEVEL=INFO",
        ],
        "volumes": [
            # 模板里只放占位说明；部署时由 deploy_expert_container 替换为 bind mount
            "opencode-agent-data:/root/.local/share/opencode",
        ],
        "restart_policy": "unless-stopped",
        "is_builtin": True,
        "sort_order": 2,
    },
]


def _try_set(obj: object, attr: str, value) -> None:
    """安全地 setattr（向前兼容：列不存在时跳过并日志警告）."""
    try:
        setattr(obj, attr, value)
    except Exception as e:
        logger.warning(f"[compute-seed] 设置 {attr} 失败（列可能还没迁移？）: {e}")


def seed_container_templates(session: Session) -> None:
    """幂等地写入内置容器模板。已存在则更新 long_description / image / command 等关键字段。"""
    for row in _SEEDS:
        existing = (
            session.query(ContainerTemplate)
            .filter(ContainerTemplate.name == row["name"])
            .first()
        )
        data = dict(row)
        for f in ("ports", "env_vars", "volumes"):
            data[f] = json.dumps(data.get(f) or [], ensure_ascii=False)

        if existing is None:
            session.add(ContainerTemplate(**data))
            logger.info(f"[compute-seed] 新增容器模板 name={row['name']}")
        else:
            # 更新关键字段（让内置模板配置保持最新）
            _try_set(existing, "image", data["image"])
            _try_set(existing, "description", data["description"])
            _try_set(existing, "long_description", data.get("long_description"))
            _try_set(existing, "icon", data["icon"])
            _try_set(existing, "category", data["category"])
            _try_set(existing, "command", data["command"])
            _try_set(existing, "ports", data["ports"])
            _try_set(existing, "env_vars", data["env_vars"])
            _try_set(existing, "volumes", data["volumes"])
            _try_set(existing, "restart_policy", data["restart_policy"])
            logger.info(f"[compute-seed] 更新容器模板 name={row['name']}")
    session.commit()
