# 02 — Frontend Runtime 调研

## TL;DR
- `node_modules/` 143 条目已装，vite/react/antd/typescript 版本合法。
- `cd frontend && npm run dev`，5173 端口。
- 硬要求：Node ≥ 20.19 或 ≥ 22.12（vite 8）。
- `.env` 指 `http://localhost:8000/api/v1`。

## 关键点
- Scripts `frontend/package.json:6-11`
- Env 使用 `frontend/src/services/api.ts:4`, `services/index.ts:3-4`
- Vite config 极简，无 proxy/alias/port
- Dockerfile: node:20-alpine + npm install + npm run dev -- --host 0.0.0.0

## 坑
1. Node <20.19 会被 vite 8 拒
2. 无 vite proxy → 依赖 backend CORS
3. WS URL 由 `http→ws` 替换派生
