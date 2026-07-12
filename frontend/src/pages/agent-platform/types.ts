import type { AgentChatMessage, AgentChatPart } from '../../components/common/AgentChatPanel';

export type RunStatus =
  | 'pending'
  | 'running'
  | 'needs_review'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface AgentPlatformEvent {
  id?: string;
  run_id: number;
  sequence: number;
  type: string;
  timestamp: string;
  visibility?: 'user' | 'builder' | 'admin';
  payload: Record<string, unknown>;
}

export interface TimelineEntry {
  key: string;
  eventType: string;
  category: 'thinking' | 'step' | 'tool' | 'subagent' | 'eval' | 'run';
  title: string;
  summary?: string;
  status: 'pending' | 'running' | 'success' | 'error' | 'warning';
  sequence: number;
  timestamp: string;
  payload: Record<string, unknown>;
}

export interface RunTimelineState {
  runId: number | null;
  status: RunStatus | null;
  messages: AgentChatMessage[];
  entries: TimelineEntry[];
  seen: Record<string, true>;
  lastSequence: number;
}

export interface AgentSummary {
  id: number;
  name: string;
  type: string;
  description: string | null;
  is_active: boolean;
  is_published: boolean;
  version: number;
  current_version_id: number | null;
  owner_user_id: number | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AgentSession {
  id: number;
  agent_id: number;
  deployment_id: number | null;
  owner_user_id: number | null;
  title: string | null;
  status: string;
  session_metadata: Record<string, unknown>;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AgentRun {
  id: number;
  agent_id: number | null;
  agent_version_id: number | null;
  deployment_id: number | null;
  session_id: number | null;
  run_name: string;
  status: RunStatus;
  strategy: 'single_shot' | 'evaluator_optimizer' | null;
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
  state_version: number;
  started_at?: string | null;
  completed_at?: string | null;
  error_message?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface NodeConnection {
  id: number;
  connector_type: 'local' | 'ssh';
  address: string | null;
  port: number | null;
  username: string | null;
  host_key_algorithm: string | null;
  host_key_fingerprint: string | null;
  managed_roots: string[];
  enabled: boolean;
  has_credential: boolean;
}

export interface ComputeNode {
  id: number;
  name: string;
  hostname: string | null;
  platform: string | null;
  platform_raw?: string | null;
  ip: string | null;
  status: string;
  labels: Record<string, unknown> | null;
  connection: NodeConnection;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface OpenCodeContainer {
  id: string;
  container_type: 'opencode';
  name: string;
  status: 'running' | 'stopped' | 'not_installed';
  cli_path: string | null;
  version: string | null;
  managed_roots: string[];
  config_path: string | null;
  config_preview: Record<string, unknown> | null;
  node_id: number;
  node_name: string;
  hostname: string | null;
}

export interface InventoryResource {
  resource_type: 'agent' | 'skill' | 'mcp' | 'runtime' | string;
  external_key: string;
  source_path: string | null;
  status: string;
  decision?: DiscoveryDecision | 'platform';
  origin: 'discovered' | 'platform' | 'both';
  location: string;
  platform_resource_id: number | null;
  remote_snapshot: Record<string, unknown>;
  platform_snapshot?: Record<string, unknown> | null;
}

export interface NodeInventory {
  node: ComputeNode;
  latest_discovery: {
    id: number;
    status: string;
    summary: Record<string, unknown> | null;
    error_message: string | null;
  } | null;
  containers: OpenCodeContainer[];
  resources: {
    agents: InventoryResource[];
    skills: InventoryResource[];
    mcps: InventoryResource[];
  };
  hierarchy_label: string;
}

export type DiscoveryDecision =
  | 'pending'
  | 'import'
  | 'link'
  | 'keep_platform'
  | 'ignore'
  | 'external';

export interface DiscoveryItem {
  id: number;
  discovery_run_id: number;
  resource_type: 'runtime' | 'agent' | 'skill' | 'mcp';
  external_key: string;
  source_path: string | null;
  status: 'new' | 'matched' | 'changed' | 'missing' | 'unsupported' | 'error';
  decision: DiscoveryDecision;
  diff: unknown;
  platform_resource_id: number | null;
  remote_snapshot: Record<string, unknown>;
  platform_snapshot: Record<string, unknown> | null;
}

export interface AgentStudioConfig {
  objective: {
    name: string;
    problem: string;
    success_criteria: string[];
    exclusions: string[];
  };
  role: {
    system_prompt: string;
    output_format: string;
  };
  model: {
    model_id: string;
    temperature: number;
    context_policy: string;
  };
  capabilities: {
    skill_ids: string[];
    mcp_ids: string[];
  };
  runtime: {
    node_id: number | null;
    container_id: string | null;
    managed_root: string | null;
    config_path: string | null;
  };
  collaboration: {
    mode: 'single' | 'sequential' | 'router' | 'parallel' | 'evaluator_optimizer';
    participants: Array<{ agent_id: string; role: string }>;
  };
  loop: {
    strategy: string;
    max_iterations: number;
    timeout_seconds: number;
    sop: Array<{ key: string; instruction: string }>;
  };
  hooks: Array<{ event: string; action_id: string; failure_policy: 'continue' | 'block' }>;
  eval_bindings: Array<{
    suite_id: string;
    required: boolean;
    threshold: number;
  }>;
  guardrails: {
    tool_approval: 'always' | 'risk_based' | 'never';
    max_tool_calls: number;
    forbidden_actions: string[];
    pii_redaction: boolean;
  };
  release: {
    change_summary: string;
  };
}

export const defaultStudioConfig = (): AgentStudioConfig => ({
  objective: {
    name: '',
    problem: '',
    success_criteria: ['给出可追溯的结论'],
    exclusions: [],
  },
  role: {
    system_prompt:
      '你是 OntoMind 团队助手。基于用户目标完成任务，输出清晰、可验证的结果；不确定时主动说明假设与边界。',
    output_format: 'Markdown · 结论 / 证据 / 建议',
  },
  model: {
    model_id: 'doubao-seed-1-6-250615',
    temperature: 0.2,
    context_policy: 'session',
  },
  capabilities: { skill_ids: [], mcp_ids: [] },
  runtime: { node_id: null, container_id: null, managed_root: null, config_path: null },
  collaboration: { mode: 'single', participants: [] },
  loop: {
    strategy: 'react',
    max_iterations: 8,
    timeout_seconds: 90,
    sop: [{ key: 'execute', instruction: '理解目标、执行任务并给出结构化结论' }],
  },
  hooks: [],
  eval_bindings: [],
  guardrails: {
    tool_approval: 'risk_based',
    max_tool_calls: 10,
    forbidden_actions: ['destructive_write', 'credential_export', 'force_push_main'],
    pii_redaction: true,
  },
  release: { change_summary: '初始草稿' },
});

/** @deprecated 使用 defaultStudioConfig */
export const emptyStudioConfig = defaultStudioConfig;

export function normalizeStudioConfig(config: AgentStudioConfig): AgentStudioConfig {
  const defaults = defaultStudioConfig();
  return {
    objective: {
      ...defaults.objective,
      ...config.objective,
      success_criteria: config.objective.success_criteria.some(Boolean)
        ? config.objective.success_criteria
        : defaults.objective.success_criteria,
    },
    role: {
      ...defaults.role,
      ...config.role,
      system_prompt: config.role.system_prompt.trim() || defaults.role.system_prompt,
      output_format: config.role.output_format.trim() || defaults.role.output_format,
    },
    model: {
      ...defaults.model,
      ...config.model,
      model_id: config.model.model_id.trim() || defaults.model.model_id,
    },
    capabilities: { ...defaults.capabilities, ...config.capabilities },
    runtime: { ...defaults.runtime, ...config.runtime },
    collaboration: { ...defaults.collaboration, ...config.collaboration },
    loop: {
      ...defaults.loop,
      ...config.loop,
      sop: config.loop.sop.length ? config.loop.sop : defaults.loop.sop,
    },
    hooks: config.hooks.length ? config.hooks : defaults.hooks,
    eval_bindings: config.eval_bindings.length ? config.eval_bindings : defaults.eval_bindings,
    guardrails: {
      ...defaults.guardrails,
      ...config.guardrails,
      forbidden_actions: config.guardrails.forbidden_actions.length
        ? config.guardrails.forbidden_actions
        : defaults.guardrails.forbidden_actions,
    },
    release: {
      ...defaults.release,
      ...config.release,
      change_summary: config.release.change_summary.trim() || defaults.release.change_summary,
    },
  };
}

export type TimelineChatPart = AgentChatPart;
