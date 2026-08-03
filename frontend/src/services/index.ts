/**
 * 通用 API 聚合入口
 *
 * 🗑️ 2026-08-03 两批清理后，这里已无内容可导出。
 *
 * **第一批**（五层业务域 + resources + agent-looper/platform）删除：
 * - `resourcesAPI` / `perceptionAPI` / `cognitionAPI` / `decisionAPI` / `executionAPI`
 *
 * **第二批**（专家团 + 算力调度 + 数据平台 + 知识库 + LLM）删除：
 * - `llmAPI`（LLM 配置整体下线）
 *
 * 当前项目只剩 2 个模块，各自用独立 service：
 * - **AIDE**     → `services/aide.service.ts`
 * - **用户管理** → `services/user.service.ts`
 * - 底层 axios 实例（JWT 拦截 + 网络重试）→ `services/api.ts`
 *
 * 保留本文件是为了不破坏 `import ... from '../../services'` 这类历史路径写法；
 * 新代码请直接 import 具体的 service 文件。
 */
export {};
