/**
 * Type definitions for the Agent module (T45 rename from Agent Looper).
 *
 * T45 naming migration:
 *   - `AgentLooperConfig`      → `AgentConfig`
 *   - `AgentLooperConfigRead`  → `AgentConfigRead`
 *   - `AgentLooperVersionRead` → `AgentVersionRead`
 *   - `AgentLooperListEntry`   → `AgentListEntry`
 *   - `AgentLooperTestRunResult` → `AgentTestRunResult`
 *   - `AgentLooperType`        → `AgentType`
 *
 * Legacy `AgentLooper*` names remain exported as aliases via
 * `frontend/src/types/agentLooper.ts` so downstream imports don't break.
 * Wire shape is unchanged — snake_case matches the backend envelope.
 */

export type AgentType =
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

export interface AgentConfig {
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

export interface AgentConfigRead {
  id: number;
  name: string;
  type: AgentType;
  description: string | null;
  current_version_id: number | null;
  active_config_json: AgentConfig | null;
  owner_user_id: number;
  is_active: boolean;
  is_published: boolean;
  settings: Record<string, unknown> | null;
  resource_bindings: ResourceBindings | null;
  credential_ref: CredentialRef | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface AgentVersionRead {
  id: number;
  config_id: number;
  version_number: number;
  config_json: AgentConfig;
  model_snapshot: string | null;
  prompt_snapshot: string | null;
  note: string | null;
  created_by_user_id: number;
  created_at: string | null;
}

export interface AgentListEntry {
  id: number;
  name: string;
  type: AgentType;
  description: string | null;
  is_active: boolean;
  is_published: boolean;
  model: string;
  loop_strategy: LoopStrategy;
  updated_at: string | null;
}

export interface AgentTestRunResult {
  test_run_id: number;
  status: 'success' | 'error' | 'timeout' | 'running';
  output: string | null;
  error: string | null;
  duration_ms: number | null;
}

// --- Backwards-compat aliases (T45 rename) ---------------------------------
// Legacy AgentLooper* names remain exported so existing pages / services keep
// compiling. Prefer the new names in new code.
export type AgentLooperType = AgentType;
export type AgentLooperConfig = AgentConfig;
export type AgentLooperConfigRead = AgentConfigRead;
export type AgentLooperVersionRead = AgentVersionRead;
export type AgentLooperListEntry = AgentListEntry;
export type AgentLooperTestRunResult = AgentTestRunResult;
