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

export type SOPStepKind =
  | 'agent'
  | 'tool'
  | 'human'
  | 'condition'
  | 'notify';

export interface SOPStep {
  /** Stable id (usually `s1`, `s2` …). */
  id: string;
  /** Step title / short goal. */
  title: string;
  /** Optional longer description or prompt. */
  detail?: string;
  /** Step kind — decides the icon and downstream compiler. */
  kind: SOPStepKind;
  /** DAG deps: ids of upstream steps that must complete first. */
  depends_on: string[];
}

export interface SOPTemplate {
  key: string;
  name: string;
  description: string;
  steps: SOPStep[];
}

/** 5 preset SOP templates — cover the platform's common scenarios. */
export const SOP_TEMPLATES: SOPTemplate[] = [
  {
    key: 'data_onboarding',
    name: '数据源接入 SOP',
    description: '新数据源从连接到落表的标准接入流程。',
    steps: [
      { id: 's1', title: '收集连接信息', kind: 'human', depends_on: [] },
      { id: 's2', title: '测试连通性', kind: 'tool', depends_on: ['s1'] },
      { id: 's3', title: '抽取元数据', kind: 'agent', depends_on: ['s2'] },
      { id: 's4', title: '生成质量报告', kind: 'agent', depends_on: ['s3'] },
      { id: 's5', title: '通知负责人验收', kind: 'notify', depends_on: ['s4'] },
    ],
  },
  {
    key: 'incident_response',
    name: '数据异常告警响应',
    description: '数据质量或链路告警后的排查、修复、复盘流程。',
    steps: [
      { id: 's1', title: '接收告警并分级', kind: 'agent', depends_on: [] },
      { id: 's2', title: '定位受影响任务', kind: 'tool', depends_on: ['s1'] },
      { id: 's3', title: '判断是否需人工介入', kind: 'condition', depends_on: ['s2'] },
      { id: 's4', title: '执行修复动作', kind: 'agent', depends_on: ['s3'] },
      { id: 's5', title: '复盘并沉淀 runbook', kind: 'human', depends_on: ['s4'] },
    ],
  },
  {
    key: 'model_release',
    name: '模型发布 SOP',
    description: '离线模型 → 灰度 → 全量的标准发布流程。',
    steps: [
      { id: 's1', title: '离线效果评估', kind: 'agent', depends_on: [] },
      { id: 's2', title: '安全 & 合规审查', kind: 'human', depends_on: ['s1'] },
      { id: 's3', title: '灰度部署', kind: 'tool', depends_on: ['s2'] },
      { id: 's4', title: '监控关键指标', kind: 'agent', depends_on: ['s3'] },
      { id: 's5', title: '全量放量或回滚', kind: 'condition', depends_on: ['s4'] },
    ],
  },
  {
    key: 'metadata_governance',
    name: '元数据治理巡检',
    description: '周期性巡检字段注释 / 命名规范 / 数据分级。',
    steps: [
      { id: 's1', title: '拉取近期新增元数据', kind: 'tool', depends_on: [] },
      { id: 's2', title: '规则扫描', kind: 'agent', depends_on: ['s1'] },
      { id: 's3', title: '生成治理工单', kind: 'agent', depends_on: ['s2'] },
      { id: 's4', title: '推送责任人', kind: 'notify', depends_on: ['s3'] },
    ],
  },
  {
    key: 'kb_ingestion',
    name: '知识库文档入库',
    description: '文档上传 → 分块 → 向量化 → 索引发布。',
    steps: [
      { id: 's1', title: '接收上传文件', kind: 'human', depends_on: [] },
      { id: 's2', title: '解析并分块', kind: 'tool', depends_on: ['s1'] },
      { id: 's3', title: '生成向量', kind: 'agent', depends_on: ['s2'] },
      { id: 's4', title: '写入向量库', kind: 'tool', depends_on: ['s3'] },
      { id: 's5', title: '发布可检索索引', kind: 'notify', depends_on: ['s4'] },
    ],
  },
];

/**
 * Naive natural-language → SOP compiler.
 *
 * Rules:
 * - Split input on newlines / 中文和英文分号 / 句号 / 顿号-style separators.
 * - Trim numeric or bullet prefixes (`1.`、`一、`、`- `、`* `).
 * - Detect kind by keyword heuristics (工具/tool → tool, 人工/审核 → human, etc.).
 * - Chain steps sequentially (each new step depends on the previous one) —
 *   downstream editor can adjust the DAG.
 *
 * The compiler is deliberately conservative: unknown lines still become
 * `agent` steps so the user has something to edit rather than a blank canvas.
 */
export function compileSOPFromNaturalLanguage(input: string): SOPStep[] {
  if (!input.trim()) return [];

  const rawLines = input
    .split(/[\n\r]+|(?<=[。；;])\s*/g)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);

  const bulletPrefix =
    /^\s*(?:[0-9]+[.)、]|[一二三四五六七八九十]+[、.)]|[-*•●·]|Step\s*\d+[:：]?)\s*/i;

  const steps: SOPStep[] = [];
  let idx = 0;
  for (const line of rawLines) {
    const cleaned = line.replace(bulletPrefix, '').trim();
    if (!cleaned) continue;
    idx += 1;
    const id = `s${idx}`;
    const kind = detectStepKind(cleaned);
    steps.push({
      id,
      title: cleaned.slice(0, 60),
      detail: cleaned.length > 60 ? cleaned : undefined,
      kind,
      depends_on: idx === 1 ? [] : [`s${idx - 1}`],
    });
  }
  return steps;
}

function detectStepKind(text: string): SOPStepKind {
  const t = text.toLowerCase();
  if (/(人工|审核|确认|approve|review|manual)/.test(text) || /human|approve/.test(t)) {
    return 'human';
  }
  if (/(通知|告警|推送|发邮件|发消息|notify|alert|email|message)/.test(text) || /notify/.test(t)) {
    return 'notify';
  }
  if (/(如果|若|判断|条件|is\s+it|whether|when)/i.test(text) || /condition|if/.test(t)) {
    return 'condition';
  }
  if (/(调用|执行|运行|抓取|同步|上传|下载|部署|api|sql|http)/i.test(text) || /tool|call|exec/.test(t)) {
    return 'tool';
  }
  return 'agent';
}

