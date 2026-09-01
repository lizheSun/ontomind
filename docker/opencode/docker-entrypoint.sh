#!/usr/bin/env bash
# OpenCode 容器入口脚本
#
# 职责：
# 1. 若挂载了 opencode.json 就直接用；否则根据环境变量生成一份最小 provider 配置
# 2. 组装 `opencode serve` 参数（port / hostname / cors）
# 3. exec 交出 PID 1，保证信号能正确传递（docker stop 优雅退出）

set -euo pipefail

CONFIG_DIR="/root/.config/opencode"
CONFIG_FILE="${CONFIG_DIR}/opencode.json"

log() { echo "[entrypoint] $*" >&2; }

# ── 1. 生成 provider 配置（仅当未挂载 opencode.json 时）──────────────
if [[ ! -f "${CONFIG_FILE}" ]]; then
  log "未检测到 ${CONFIG_FILE}，根据环境变量生成最小配置"

  # 用 node 生成 JSON，避免手写字符串拼接出错
  node <<'NODE'
const fs = require('fs');
const path = '/root/.config/opencode/opencode.json';

const cfg = { $schema: 'https://opencode.ai/config.json', provider: {} };

// 火山方舟 Agent Plan（OpenAI 兼容）
if (process.env.ARK_API_KEY) {
  cfg.provider['agent-plan'] = {
    npm: '@ai-sdk/openai-compatible',
    name: 'ARK Agent Plan',
    options: {
      baseURL: process.env.ARK_BASE_URL || 'https://ark.cn-beijing.volces.com/api/plan/v3',
      apiKey: process.env.ARK_API_KEY,
    },
    models: {
      'ark-code-latest': { name: 'ARK Code Latest' },
    },
  };
  cfg.model = 'agent-plan/ark-code-latest';
}

if (process.env.ANTHROPIC_API_KEY) {
  cfg.provider.anthropic = { options: { apiKey: process.env.ANTHROPIC_API_KEY } };
}
if (process.env.OPENAI_API_KEY) {
  cfg.provider.openai = { options: { apiKey: process.env.OPENAI_API_KEY } };
}
if (process.env.ZHIPU_API_KEY) {
  cfg.provider.zai = {
    npm: '@ai-sdk/openai-compatible',
    name: 'Z.AI',
    options: {
      baseURL: 'https://api.z.ai/api/paas/v4',
      apiKey: process.env.ZHIPU_API_KEY,
    },
  };
}

if (Object.keys(cfg.provider).length === 0) {
  console.error('[entrypoint] 警告：未注入任何 API Key，opencode 将无可用 provider');
}

fs.writeFileSync(path, JSON.stringify(cfg, null, 2));
console.error(`[entrypoint] 已生成配置，provider: ${Object.keys(cfg.provider).join(', ') || '(空)'}`);
NODE
else
  log "使用挂载的 ${CONFIG_FILE}"
fi

# ── 2. 报告 agent / skill 挂载情况 ───────────────────────────────
AGENT_COUNT=$(find "${CONFIG_DIR}/agent" -maxdepth 1 -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
SKILL_COUNT=$(find "${CONFIG_DIR}/skills" -maxdepth 1 -type d 2>/dev/null | tail -n +2 | wc -l | tr -d ' ')
log "已加载 agent: ${AGENT_COUNT} 个，skill: ${SKILL_COUNT} 个"

# ── 3. 组装 serve 参数 ──────────────────────────────────────────
if [[ "${1:-}" == "serve" ]]; then
  shift
  ARGS=(serve --port "${OPENCODE_PORT:-4096}" --hostname "${OPENCODE_HOSTNAME:-0.0.0.0}")

  # CORS：逗号分隔展开成多个 --cors
  if [[ -n "${OPENCODE_CORS:-}" ]]; then
    IFS=',' read -ra ORIGINS <<< "${OPENCODE_CORS}"
    for origin in "${ORIGINS[@]}"; do
      trimmed="$(echo "${origin}" | xargs)"
      [[ -n "${trimmed}" ]] && ARGS+=(--cors "${trimmed}")
    done
  fi

  # 追加调用方额外传入的参数
  ARGS+=("$@")

  log "启动: opencode ${ARGS[*]}"
  exec opencode "${ARGS[@]}"
fi

# 非 serve 子命令直接透传（方便 docker run <image> --version 之类调试）
log "透传执行: opencode $*"
exec opencode "$@"
