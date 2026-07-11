/**
 * Type definitions for the Agent Looper module (Wave 9 W2 T34-T38).
 *
 * Mirrors the backend schemas defined in
 *   backend/app/schemas/agent_looper.py (planned in T34-T37).
 *
 * Field names stay in snake_case to match the wire format from the backend
 * envelope — no automatic camelCase mapping is applied for config bodies.
 */

export type AgentLooperType =
  | 'custom_looper'
  | 'opencode_native'
  | 'mcp_agent'
  | 'imported';

export type LoopStrategy = 'single_shot' | 'react' | 'plan_execute' | 'reflect';

export interface ToolPermissionMap {
  edit?: boolean;
  webfetch?: boolean;
  bash?: boolean;
  websearch?: boolean;
}

export interface CustomToolDef {
  name: string;
  description: string;
  params_schema?: Record<string, unknown>;
}

export interface Guardrails {
  max_tokens?: number;
  max_iterations?: number;
  timeout_ms?: number;
}

export interface ResourceBindings {
  dp_source_ids?: number[];
  kb_project_ids?: number[];
  metadata_scope?: string | null;
}

export interface CredentialRef {
  credential_type: 'dp_source' | 'inline';
  credential_id?: number | null;
}

export interface AgentLooperConfig {
  name: string;
  description: string;
  mode: 'subagent' | 'primary' | 'all';
  model: string;
  temperature: number;
  loop_strategy: LoopStrategy;
  system_prompt: string;
  tool_permissions: ToolPermissionMap;
  custom_tools: CustomToolDef[];
  memory_window: number;
  guardrails: Guardrails;
  resource_bindings: ResourceBindings | null;
  credential_ref: CredentialRef | null;
  provider: string | null;
  api_base: string | null;
  context_files: string[];
  spawnable_agents: string[];
  disabled: boolean;
}

export interface AgentLooperConfigRead {
  id: number;
  name: string;
  type: AgentLooperType;
  description: string | null;
  current_version_id: number | null;
  active_config_json: AgentLooperConfig | null;
  owner_user_id: number;
  is_active: boolean;
  is_published: boolean;
  settings: Record<string, unknown> | null;
  resource_bindings: ResourceBindings | null;
  credential_ref: CredentialRef | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface AgentLooperVersionRead {
  id: number;
  config_id: number;
  version_number: number;
  config_json: AgentLooperConfig;
  model_snapshot: string | null;
  prompt_snapshot: string | null;
  note: string | null;
  created_by_user_id: number;
  created_at: string | null;
}

export interface AgentLooperListEntry {
  id: number;
  name: string;
  type: AgentLooperType;
  description: string | null;
  is_active: boolean;
  is_published: boolean;
  model: string;
  loop_strategy: LoopStrategy;
  updated_at: string | null;
}

export interface AgentLooperTestRunResult {
  test_run_id: number;
  status: 'success' | 'error' | 'timeout' | 'running';
  output: string | null;
  error: string | null;
  duration_ms: number | null;
}
