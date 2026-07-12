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

/**
 * Onboarding metadata attached to presets / SOP templates for the Template
 * Library page (T60). Every field is optional so old consumers keep working;
 * TemplateLibrary uses whichever fields exist and falls back to sensible
 * defaults.
 */
export type OnboardingDifficulty = 'beginner' | 'intermediate' | 'advanced';

export interface OnboardingMeta {
  /** Grouping tag: 数据 / 分析 / 治理 / 知识库 / 通用 …… */
  category: string;
  /** Short one-line pitch, rendered under the template title. */
  pitch: string;
  /** Difficulty badge (beginner ≈ 零学习曲线可直接用). */
  difficulty: OnboardingDifficulty;
  /** ~5 分钟 / ~15 分钟 / ~30 分钟 —— rough time-to-value hint. */
  timeToValue?: string;
  /** Ordered onboarding steps shown as "quick start" checklist. */
  quickStart: string[];
  /** Freeform searchable tags (e.g. "SQL", "只读", "评审"). */
  tags: string[];
}

export interface AgentLooperPreset {
  key: string;
  name: string;
  description: string;
  config: AgentLooperConfig;
  /** Optional onboarding metadata (T60). */
  onboarding?: OnboardingMeta;
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
    onboarding: {
      category: '通用',
      pitch: '零配置即可开箱聊天，适合首次体验 Agent Loop。',
      difficulty: 'beginner',
      timeToValue: '~2 分钟',
      quickStart: [
        '点击「使用此模板」进入向导',
        '在向导第 1 步选择任意可用模型',
        '直接点「保存并运行」开始对话',
      ],
      tags: ['入门', '通用', '问答'],
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
    onboarding: {
      category: '数据分析',
      pitch: '接入数据源即可对话式跑 SQL，全流程只读安全。',
      difficulty: 'beginner',
      timeToValue: '~5 分钟',
      quickStart: [
        '绑定至少 1 个 dp_source（感知层 → 数据源）',
        '在向导第 3 步保留默认 execute_sql 工具',
        '进入 Agent Job 页面直接提问业务问题',
      ],
      tags: ['SQL', '数据分析', '只读', 'ReAct'],
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
    onboarding: {
      category: '数据分析',
      pitch: '低温度、专注写 SQL 的助手，适合 BI 开发者。',
      difficulty: 'intermediate',
      timeToValue: '~10 分钟',
      quickStart: [
        '绑定目标数据源（用于 browse_schema）',
        '在系统提示里追加你的方言约束（MySQL / Doris 等）',
        '首轮以「查一下……」开始验证 schema 命中率',
      ],
      tags: ['SQL', '生成', '低温度'],
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
    onboarding: {
      category: '数据治理',
      pitch: '巡检字段注释 / 命名 / 类型，自动出改进建议。',
      difficulty: 'intermediate',
      timeToValue: '~15 分钟',
      quickStart: [
        '在向导第 4 步把 metadata_scope 缩到具体库或分级',
        '首次运行前用 SOP「元数据治理巡检」串起来',
        '把审核报告投递给对应责任人',
      ],
      tags: ['治理', '元数据', 'Reflect', '审核'],
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
  /** Optional onboarding metadata (T60). */
  onboarding?: OnboardingMeta;
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
    onboarding: {
      category: '感知层',
      pitch: '新数据源接入的默认工作流，含质量报告和验收通知。',
      difficulty: 'beginner',
      timeToValue: '~10 分钟',
      quickStart: [
        '在 SOP 编辑器点「使用此模板」',
        '把 s2 的工具指向具体的连通性检查任务',
        '发布 SOP 并跑一次演练',
      ],
      tags: ['数据源', '接入', '感知层'],
    },
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
    onboarding: {
      category: '运维',
      pitch: '一条链路把告警 → 定位 → 修复 → 复盘串起来。',
      difficulty: 'intermediate',
      timeToValue: '~20 分钟',
      quickStart: [
        '把 s1 接入实际告警通道（Webhook / IM）',
        '在 s3 补全人工介入判定条件',
        '每次事故后回填 runbook 长期沉淀',
      ],
      tags: ['告警', '事故', 'Condition'],
    },
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
    onboarding: {
      category: '决策层',
      pitch: '模型上线标准动作，含灰度和条件回滚。',
      difficulty: 'advanced',
      timeToValue: '~30 分钟',
      quickStart: [
        '把 s2 指定为安全 / 合规负责人',
        '在 s3 绑定实际的灰度部署工具',
        '在 s5 定义回滚阈值',
      ],
      tags: ['模型', '发布', '灰度', 'Condition'],
    },
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
    onboarding: {
      category: '数据治理',
      pitch: '周期性巡检，产出治理工单并派单到人。',
      difficulty: 'intermediate',
      timeToValue: '~15 分钟',
      quickStart: [
        '在 s1 定义拉取范围（最近 7 天 / 特定库）',
        '把 s2 挂到「元数据审核员」预设 Agent 上',
        '在 s4 配置责任人推送通道',
      ],
      tags: ['治理', '元数据', '巡检'],
    },
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
    onboarding: {
      category: '知识库',
      pitch: '通用文档入库四步走：分块 → 向量化 → 入库 → 发布。',
      difficulty: 'beginner',
      timeToValue: '~10 分钟',
      quickStart: [
        '选择目标知识库项目',
        '把 s2 指向平台默认分块工具',
        '首次运行完成后在应用层验证检索',
      ],
      tags: ['知识库', '向量', 'RAG'],
    },
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

export type TemplateKind = 'agent' | 'sop';

export interface TemplateLibraryEntry {
  kind: TemplateKind;
  key: string;
  name: string;
  description: string;
  onboarding: OnboardingMeta;
}

const DEFAULT_ONBOARDING: OnboardingMeta = {
  category: '其他',
  pitch: '暂未提供简介，进入后可自行编辑。',
  difficulty: 'intermediate',
  quickStart: [],
  tags: [],
};

export function getTemplateLibraryEntries(): TemplateLibraryEntry[] {
  const agentEntries: TemplateLibraryEntry[] = PRESETS.map((p) => ({
    kind: 'agent',
    key: p.key,
    name: p.name,
    description: p.description,
    onboarding: p.onboarding ?? DEFAULT_ONBOARDING,
  }));
  const sopEntries: TemplateLibraryEntry[] = SOP_TEMPLATES.map((t) => ({
    kind: 'sop',
    key: t.key,
    name: t.name,
    description: t.description,
    onboarding: t.onboarding ?? DEFAULT_ONBOARDING,
  }));
  return [...agentEntries, ...sopEntries];
}

export const DIFFICULTY_LABELS: Record<OnboardingDifficulty, string> = {
  beginner: '零学习曲线',
  intermediate: '进阶',
  advanced: '高级',
};

