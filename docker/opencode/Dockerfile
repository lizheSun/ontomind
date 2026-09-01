# OpenCode Server 容器镜像
#
# 设计要点：
# - opencode CLI 通过 npm 安装（opencode-ai 是薄 wrapper，会拉对应平台的 native binary）
# - agent / skill 定义通过 volume 挂载进来，不烤进镜像（方便热更新）
# - API Key 一律运行时 `-e` 注入，**绝不写进镜像层**
# - 默认 `opencode serve --hostname 0.0.0.0 --port 4096`，容器外由宿主端口映射访问

FROM node:22-slim

# opencode 运行时依赖：git（部分 tool 需要）、ca-certificates（HTTPS）、ripgrep（grep tool）
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        ca-certificates \
        ripgrep \
        curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 opencode CLI
# 版本可通过 build-arg 覆盖：docker build --build-arg OPENCODE_VERSION=1.18.4 .
ARG OPENCODE_VERSION=latest
RUN npm install -g opencode-ai@${OPENCODE_VERSION} \
    && npm cache clean --force

# 工作目录 —— opencode 会把这里当作 project root（find/grep tool 的作用域）
WORKDIR /workspace

# opencode 配置目录（挂载点）
# - /root/.config/opencode/agent/*.md  → 专家 agent 定义
# - /root/.config/opencode/skills/*    → skill 定义
# - /root/.config/opencode/opencode.json → provider / mcp 配置
RUN mkdir -p /root/.config/opencode/agent /root/.config/opencode/skills

# ── 运行时环境变量（全部留空，由 docker run -e 注入）─────────────
# 火山方舟 Agent Plan
ENV ARK_API_KEY=""
ENV ARK_BASE_URL="https://ark.cn-beijing.volces.com/api/plan/v3"
# 其他常见 provider（按需）
ENV ANTHROPIC_API_KEY=""
ENV OPENAI_API_KEY=""
ENV ZHIPU_API_KEY=""
# opencode server 监听参数
ENV OPENCODE_PORT="4096"
ENV OPENCODE_HOSTNAME="0.0.0.0"
# CORS 白名单（逗号分隔，entrypoint 会展开成多个 --cors）
ENV OPENCODE_CORS=""
# 可选：给 server 加 basic auth
ENV OPENCODE_SERVER_PASSWORD=""

EXPOSE 4096

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:${OPENCODE_PORT}/global/health || exit 1

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["serve"]
