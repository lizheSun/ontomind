/**
 * Agent Looper — 4 preset templates (T39).
 *
 * Note: The wizard imports `AgentLooperConfig` / `LoopStrategy` from this file
 * because upstream service (Wave 9 T35-T40 frontend) hasn't shipped the
 * dedicated `types/agentLooper.ts` yet on `blueprint/int-full-w8`. Keeping the
 * types here avoids adding a new type module outside `files_touched`.
 */

export type AgentLooperMode = 'subagent' | 'main';
export type LoopStrategy = 'single_shot' | 'react' | 'plan_execute' | 'reflect';
export type AgentLooperType = 'custom_looper' | 'opencode_native' | 'mcp_agent' | 'imported';

export interface ToolPermissions {
  edit: boolean;
  webfetch: boolean;
  bash: boolean;
  websearch?: boolean;
}

export interface CustomTool {
  name: string;
  description: string;
  params_schema: Record<string, unknown>;
}

export interface Guardrails {
  max_tokens: number;
  max_iterations: number;
  timeout_ms: number;
}

export interface ResourceBindings {
  dp_source_ids?: number[];
  kb_project_ids?: number[];
  metadata_scope?: string | null;
}

export interface AgentLooperConfig {
  mode: AgentLooperMode;
  model: string;
  temperature: number;
  loop_strategy: LoopStrategy;
  system_prompt: string;
  tool_permissions: ToolPermissions;
  custom_tools: CustomTool[];
  memory_window: number;
  guardrails: Guardrails;
  resource_bindings: ResourceBindings | null;
  credential_ref: Record<string, unknown> | null;
}

export interface AgentLooperPreset {
  key: string;
  name: string;
  description: string;
  config: AgentLooperConfig;
}

/** Empty / neutral defaults for a fresh wizard. */
export const EMPTY_CONFIG: AgentLooperConfig = {
  mode: 'subagent',
  model: '',
  temperature: 0.7,
  loop_strategy: 'single_shot',
  system_prompt: '',
  tool_permissions: { edit: false, webfetch: false, bash: false, websearch: false },
  custom_tools: [],
  memory_window: 0,
  guardrails: { max_tokens: 4096, max_iterations: 5, timeout_ms: 30000 },
  resource_bindings: null,
  credential_ref: null,
};

export const PRESETS: AgentLooperPreset[] = [
  {
    key: 'general',
    name: '通用助手',
    description: '面向日常问答、简单分析、代码片段生成的通用 Agent。',
    config: {
      mode: 'subagent',
      model: '',
      temperature: 0.7,
      loop_strategy: 'single_shot',
      system_prompt:
        '你是一个通用 AI 助手，帮助用户解答问题、分析数据、编写代码。请使用中文回答。',
      tool_permissions: { edit: false, webfetch: true, bash: false },
      custom_tools: [],
      memory_window: 0,
      guardrails: { max_tokens: 4096, max_iterations: 5, timeout_ms: 30000 },
      resource_bindings: null,
      credential_ref: null,
    },
  },
  {
    key: 'data_analyst',
    name: '数据分析师',
    description: '使用 SQL 查询数据、分析趋势、总结洞察（只读）。',
    config: {
      mode: 'subagent',
      model: '',
      temperature: 0.3,
      loop_strategy: 'react',
      system_prompt:
        '你是一名数据分析师。使用 SQL 查询数据、分析趋势、生成可视化洞察。\n\n规则：\n1. 只执行 SELECT 查询，不修改数据\n2. 每次查询结果都要总结关键发现\n3. 使用中文回答',
      tool_permissions: { edit: false, webfetch: true, bash: false },
      custom_tools: [
        {
          name: 'execute_sql',
          description: '在数据源上执行 SQL 查询',
          params_schema: { sql: { type: 'string' } },
        },
      ],
      memory_window: 5,
      guardrails: { max_tokens: 8192, max_iterations: 15, timeout_ms: 60000 },
      resource_bindings: { dp_source_ids: [], kb_project_ids: [], metadata_scope: null },
      credential_ref: null,
    },
  },
  {
    key: 'sql_writer',
    name: 'SQL 编写员',
    description: '根据自然语言需求生成高效、安全的 SQL 查询。',
    config: {
      mode: 'subagent',
      model: '',
      temperature: 0.1,
      loop_strategy: 'react',
      system_prompt:
        '你是一名 SQL 专家。根据用户需求编写高效、安全的 SQL 查询。\n\n规则：\n1. 解释你的 SQL 逻辑\n2. 提供优化建议\n3. 使用中文回答',
      tool_permissions: { edit: false, webfetch: false, bash: false },
      custom_tools: [
        {
          name: 'browse_schema',
          description: '浏览数据源的表结构',
          params_schema: {
            database: { type: 'string' },
            table: { type: 'string', optional: true },
          },
        },
      ],
      memory_window: 3,
      guardrails: { max_tokens: 4096, max_iterations: 10, timeout_ms: 30000 },
      resource_bindings: { dp_source_ids: [] },
      credential_ref: null,
    },
  },
  {
    key: 'metadata_reviewer',
    name: '元数据审核员',
    description: '审核表结构 / 字段注释 / 命名规范，给出改进建议。',
    config: {
      mode: 'subagent',
      model: '',
      temperature: 0.2,
      loop_strategy: 'reflect',
      system_prompt:
        '你是一名数据元数据审核专家。审核表结构、字段注释、数据质量，提出改进建议。\n\n规则：\n1. 检查字段注释完整性\n2. 检查命名规范\n3. 检查数据类型合理性\n4. 使用中文回答',
      tool_permissions: { edit: false, webfetch: false, bash: false },
      custom_tools: [],
      memory_window: 10,
      guardrails: { max_tokens: 4096, max_iterations: 20, timeout_ms: 60000 },
      resource_bindings: { metadata_scope: 'all' },
      credential_ref: null,
    },
  },
];

export function findPreset(key: string): AgentLooperPreset | undefined {
  return PRESETS.find((p) => p.key === key);
}
