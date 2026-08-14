/** Skill 平台类型定义。

字段与 backend/app/schemas/skill_platform_schema.py 对应。
双平面设计：执行平面（SKILL.md 5 字段） + 治理平面（MySQL 全量配置）。
*/
export type SkillKind = 'prompt' | 'api' | 'flow';
export type RiskLevel = 'low' | 'medium' | 'high';
export type Lifecycle = 'draft' | 'testing' | 'canary' | 'released' | 'frozen' | 'archived';
export type ParamDirection = 'in' | 'out';
export type ParamSource = 'dialog' | 'context' | 'system' | 'const';
export type MaskRule = 'none' | 'phone' | 'idcard' | 'bankcard' | 'email' | 'all' | 'custom';
export type AuthType = 'none' | 'bearer' | 'ak_sk' | 'api_key' | 'basic';
export type FallbackMode = 'none' | 'static' | 'skill' | 'prompt';
export type FlowNodeType = 'start' | 'skill' | 'branch' | 'loop' | 'end';

export interface SkillMetaPayload {
  skill_kind: SkillKind;
  name_zh?: string;
  name_en?: string;
  biz_tags: string[];
  risk_level: RiskLevel;
  owner?: string;
  owner_email?: string;
  biz_line?: string;
  qps_limit?: number;
  session_call_limit?: number;
  lifecycle: Lifecycle;
  lifecycle_note?: string;
}

export interface SkillParamPayload {
  name: string;
  title?: string;
  description?: string;
  data_type: string;
  required: boolean;
  default_value?: string;
  enum_values: string[];
  regex_pattern?: string;
  min_val?: number;
  max_val?: number;
  source?: ParamSource;
  context_key?: string;
  const_value?: string;
  mask_rule: MaskRule;
  mask_pattern?: string;
  filtered: boolean;
  write_to_context: boolean;
  context_write_key?: string;
  sort_order: number;
}

export interface SkillParamResponse extends SkillParamPayload {
  id: number;
  direction: ParamDirection;
}

export interface FewShot {
  input: string;
  output: string;
}

export interface ExecPromptPayload {
  system_prompt?: string;
  few_shots: FewShot[];
  output_constraint?: string;
  output_format: 'text' | 'json' | 'markdown';
  temperature?: number;
  max_tokens?: number;
}

export interface ParamMappingItem {
  param: string;
  location: 'query' | 'body' | 'header' | 'path';
  field: string;
}

export interface ExecApiPayload {
  http_method: string;
  url_test?: string;
  url_staging?: string;
  url_prod?: string;
  headers: Record<string, string>;
  auth_type: AuthType;
  secret_ref?: string;
  param_mappings: ParamMappingItem[];
  timeout_ms: number;
  retry_times: number;
  retry_backoff_ms: number;
  success_path?: string;
  success_value?: string;
  data_path?: string;
}

export interface ErrorMapItem {
  match: string;
  scene: 'param' | 'network' | 'service';
  user_msg: string;
  suggest?: string;
}

export interface SkillPolicyPayload {
  timeout_ms?: number;
  retry_times?: number;
  circuit_threshold?: number;
  circuit_window_sec: number;
  circuit_min_calls: number;
  circuit_cooldown_sec: number;
  fallback_mode: FallbackMode;
  fallback_payload?: string;
  error_maps: ErrorMapItem[];
  allowed_agents: string[];
  allowed_roles: string[];
  require_confirm: boolean;
  confirm_prompt?: string;
  account_whitelist: string[];
  account_blacklist: string[];
  ctx_read_keys: string[];
  ctx_write_keys: string[];
  session_isolation: string;
}

export interface SkillFileItem {
  rel_path: string;
  content: string;
  is_executable: boolean;
}

export interface ValidationIssue {
  level: 'error' | 'warning' | 'info';
  field: string;
  message: string;
  module?: string;
}

export interface SkillValidation {
  ok: boolean;
  issues: ValidationIssue[];
}

export interface SkillFullResponse {
  id: number;
  name: string;
  description: string;
  license?: string;
  compatibility?: string;
  metadata_json?: Record<string, string>;
  body?: string;
  display_name?: string;
  category?: string;
  files: SkillFileItem[];
  current_version: number;
  is_builtin_preset: boolean;
  meta: SkillMetaPayload;
  params_in: SkillParamResponse[];
  params_out: SkillParamResponse[];
  exec_prompt: ExecPromptPayload | null;
  exec_api: ExecApiPayload | null;
  exec_flow: { nodes: FlowNodePayload[] } | null;
  policy: SkillPolicyPayload | null;
  validation: SkillValidation | null;
  created_at?: string;
  updated_at?: string;
}

export interface SkillListItem {
  id: number;
  name: string;
  description: string;
  display_name?: string;
  skill_kind: SkillKind;
  risk_level: RiskLevel;
  lifecycle: Lifecycle;
  biz_line?: string;
  owner?: string;
  current_version: number;
  file_count: number;
  param_in_count: number;
  param_out_count: number;
  is_builtin_preset: boolean;
  updated_at?: string;
}

export interface FlowNodePayload {
  node_key: string;
  node_type: FlowNodeType;
  label?: string;
  ref_skill_id?: number;
  condition_expr?: string;
  loop_config?: Record<string, unknown>;
  var_mappings: Record<string, string>;
  next_keys: string[];
  on_fail_next?: string;
  pos_x?: number;
  pos_y?: number;
  sort_order: number;
}

export interface SkillVersionResponse {
  id: number;
  skill_template_id: number;
  version: number;
  change_note?: string;
  lifecycle_at_snapshot?: string;
  canary_json?: { mode: 'percent' | 'whitelist'; percent: number; accounts: string[] };
  created_by_name?: string;
  created_at?: string;
}

export interface SkillAuditResponse {
  id: number;
  skill_name: string;
  action: string;
  field_path?: string;
  summary?: string;
  operator_name?: string;
  created_at?: string;
}

export interface ExportedFile {
  path: string;
  content: string;
  sha256: string;
  bytes: number;
  is_executable: boolean;
  plane: 'data' | 'control';
}

export interface SkillExportResponse {
  skill_name: string;
  scope: string;
  files: ExportedFile[];
  tree: string[];
  validation: SkillValidation;
  control_plane_note: string;
}

export interface ParamDebugResult {
  ok: boolean;
  fields: { name: string; ok: boolean; value: unknown; message?: string }[];
  json_schema: Record<string, unknown>;
}

export const SKILL_KIND_OPTIONS = [
  { value: 'prompt', label: 'Prompt 推理型', desc: '靠系统提示词让模型直接推理，无外部调用' },
  { value: 'api', label: 'API 调用型', desc: '调用后端接口取数或执行动作，需配鉴权' },
  { value: 'flow', label: '编排组合型', desc: '按流程图编排多个原子 Skill，支持分支/循环' },
];

export const LIFECYCLE_LABEL: Record<Lifecycle, string> = {
  draft: '草稿', testing: '测试', canary: '灰度', released: '正式', frozen: '冻结', archived: '归档',
};

export const RISK_COLOR: Record<RiskLevel, string> = {
  low: 'green', medium: 'orange', high: 'red',
};

export const LIFECYCLE_COLOR: Record<Lifecycle, string> = {
  draft: 'default', testing: 'blue', canary: 'orange', released: 'green', frozen: 'purple', archived: 'default',
};