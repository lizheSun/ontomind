/** Agent 工厂类型定义.
 *
 * 字段与后端 app/schemas/agent_factory_schema.py 一一对应。
 * 关键约束（来自 OpenCode，见 docs/PRD-agent-skill-platform.md）：
 * - 权限只有 15 个合法键，写错会被 OpenCode 静默忽略 → 平台在保存前拦截
 * - Skill frontmatter 只认 5 个字段，其余忽略
 * - agent name = 落盘文件名；skill name = 落盘目录名，都必须唯一
 */

// ---- 权限 ----

export type PermissionAction = 'allow' | 'ask' | 'deny';

/** 简写动作 或 glob→动作 映射 */
export type PermissionRule = PermissionAction | Record<string, PermissionAction>;

export type PermissionConfig = Record<string, PermissionRule>;

export interface PermissionKeyMeta {
  key: string;
  /** 该键管哪些工具 */
  gates: string;
  /** 是否支持 glob 细粒度配置 */
  glob: boolean;
  label: string;
}

export interface PermissionKeysResponse {
  keys: string[];
  glob_capable: string[];
  actions: PermissionAction[];
  meta: PermissionKeyMeta[];
  notes: string[];
}

// ---- 校验 ----

export interface ValidationIssue {
  /** info = 配置合法，仅说明「会发生什么」 */
  level: 'error' | 'warning' | 'info';
  field: string;
  message: string;
}

export interface ValidationResult {
  ok: boolean;
  issues: ValidationIssue[];
}

// ---- Agent ----

export type AgentMode = 'subagent' | 'primary' | 'all';

export interface AgentTemplate {
  id: number;
  /** = 落盘文件名 <name>.md，不可修改 */
  name: string;
  display_name?: string | null;
  /** primary 据此判断何时委派该 subagent */
  description: string;
  mode: AgentMode;
  model?: string | null;
  prompt?: string | null;
  temperature?: number | null;
  top_p?: number | null;
  steps?: number | null;
  permission_json?: PermissionConfig | null;
  options_json?: Record<string, unknown> | null;
  color?: string | null;
  hidden: boolean;
  disable: boolean;
  category?: string | null;
  is_builtin_preset: boolean;
  source: string;
  current_version: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export type AgentTemplateCreate = Omit<
  AgentTemplate,
  'id' | 'is_builtin_preset' | 'source' | 'current_version' | 'created_at' | 'updated_at'
>;

export type AgentTemplateUpdate = Partial<Omit<AgentTemplateCreate, 'name'>>;

export interface AgentVersion {
  id: number;
  agent_template_id: number;
  version: number;
  snapshot_json: Record<string, unknown>;
  change_note?: string | null;
  created_at?: string | null;
}

// ---- Skill ----

export interface SkillFileItem {
  /** 相对 skill 目录，如 references/detail.md；禁止 .. 与绝对路径 */
  rel_path: string;
  content: string;
  is_executable: boolean;
}

export interface SkillTemplate {
  id: number;
  /** = 落盘目录名，OpenCode 要求与 frontmatter name 一致 */
  name: string;
  /** 模型选择该 skill 的唯一依据，≤1024 */
  description: string;
  license?: string | null;
  compatibility?: string | null;
  metadata_json?: Record<string, string> | null;
  body?: string | null;
  display_name?: string | null;
  category?: string | null;
  files: SkillFileItem[];
  is_builtin_preset: boolean;
  source: string;
  current_version: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export type SkillTemplateCreate = Omit<
  SkillTemplate,
  'id' | 'is_builtin_preset' | 'source' | 'current_version' | 'created_at' | 'updated_at'
>;

export type SkillTemplateUpdate = Partial<Omit<SkillTemplateCreate, 'name'>>;

// ---- Bundle（Loop 编排方案）----

export type BundlePattern =
  | 'single'
  | 'plan-build'
  | 'orchestrator-workers'
  | 'research-loop'
  | 'review-loop'
  | 'pipeline'
  | 'custom';

export type MemberType = 'agent' | 'skill';
export type MemberRole = 'primary' | 'subagent' | 'skill';

export interface BundleMemberItem {
  member_type: MemberType;
  agent_template_id?: number | null;
  skill_template_id?: number | null;
  role: MemberRole;
  skill_permission?: PermissionAction | null;
  /**
   * subagent 在**本方案内**的被委派权限。
   * 存在 bundle_members 而非 agent 模板 —— 否则一个方案的授权会污染
   * 共享同一模板的其它方案。空 = 继承模板的 permission.task。
   */
  task_permission?: PermissionAction | null;
  sort_order: number;
}

/** 委派权限的来源 */
export type TaskSource = 'bundle' | 'template' | 'default';

export interface BundleMember extends BundleMemberItem {
  id: number;
  /** 冗余字段，前端展示与拓扑图用 */
  member_name?: string | null;
  member_description?: string | null;
  member_mode?: string | null;
  /** 最终生效的委派动作（后端按 覆盖 > 模板 > 默认 算出） */
  effective_task?: PermissionAction | null;
  /** 该动作是哪来的 */
  task_source?: TaskSource | null;
  /** 人类可读的溯源说明，如 `orchestrator 模板规则 "*": deny 命中` */
  task_source_detail?: string | null;
}

export interface AgentBundle {
  id: number;
  name: string;
  description?: string | null;
  pattern: BundlePattern;
  /** 必须是 primary，否则 OpenCode fallback 到 build */
  default_agent?: string | null;
  /** 0=禁止派生 / 1=默认 / 2=允许再嵌一层 */
  subagent_depth?: number | null;
  global_permission_json?: PermissionConfig | null;
  topology_json?: Record<string, unknown> | null;
  members: BundleMember[];
  is_builtin_preset: boolean;
  current_version: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AgentBundleCreate {
  name: string;
  description?: string;
  pattern: BundlePattern;
  default_agent?: string;
  subagent_depth?: number;
  global_permission_json?: PermissionConfig;
  topology_json?: Record<string, unknown>;
  members: BundleMemberItem[];
}

export type AgentBundleUpdate = Partial<AgentBundleCreate>;

// ---- 渲染预览 ----

export interface RenderedArtifact {
  path: string;
  content: string;
  sha256: string;
  bytes: number;
  is_executable: boolean;
}

export interface PreviewResponse {
  artifacts: RenderedArtifact[];
  validation: ValidationResult;
  tree: string[];
}

// ---- 发布 ----

export type DeployScope = 'global' | 'project';

export type DeployStatus =
  | 'pending'
  | 'validating'
  | 'writing'
  | 'reloading'
  | 'verifying'
  | 'success'
  | 'partial'
  | 'failed';

export interface DeployRequest {
  node_id: number;
  container_id: string;
  scope: DeployScope;
  /** 必须 true：发布需重启容器内 opencode，会中断进行中的会话 */
  restart_confirmed: boolean;
  prune: boolean;
}

export interface DeployArtifactEntry {
  path: string;
  sha256: string;
  bytes: number;
  skipped: boolean;
}

export interface DeployArtifacts {
  files: DeployArtifactEntry[];
  written: number;
  skipped: number;
  pruned: string[];
}

export interface VerifyItem {
  kind: 'agent' | 'skill';
  name: string;
  match: boolean;
  expected?: Record<string, unknown> | null;
  actual?: Record<string, unknown> | null;
  detail?: string | null;
}

export interface VerifyResult {
  items: VerifyItem[];
  reload: {
    restarted?: boolean;
    kind?: string;
    port?: number;
    listening?: boolean;
    control_url?: string | null;
    reason?: string | null;
  };
  summary: {
    total: number;
    matched: number;
    mismatched: string[];
    all_match: boolean;
    agent_probe_error?: string | null;
    skill_probe_error?: string | null;
  };
}

export interface Deployment {
  id: number;
  bundle_id: number;
  bundle_name: string;
  bundle_version: number;
  node_id: number;
  node_name: string;
  container_id: string;
  container_name: string;
  scope: DeployScope;
  target_dir: string;
  status: DeployStatus;
  artifacts_json?: DeployArtifacts | null;
  verify_json?: VerifyResult | null;
  restart_used: boolean;
  error_detail?: string | null;
  duration_ms?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
}

// ---- 预设 ----

export interface BundlePresetInfo {
  name: string;
  pattern: BundlePattern;
  description?: string;
  default_agent?: string;
  subagent_depth?: number;
  agents: string[];
  skills: string[];
}

export interface AgentPresetInfo {
  name: string;
  display_name?: string;
  description: string;
  mode?: string;
  category?: string;
}

export interface SkillPresetInfo {
  name: string;
  display_name?: string;
  description: string;
  category?: string;
  files: string[];
}

export interface PresetsResponse {
  bundles: BundlePresetInfo[];
  agents: AgentPresetInfo[];
  skills: SkillPresetInfo[];
}

// ---- 展示映射 ----

export const deployStatusColor: Record<DeployStatus, string> = {
  pending: '#8c8c8c',
  validating: '#1890ff',
  writing: '#1890ff',
  reloading: '#faad14',
  verifying: '#1890ff',
  success: '#52c41a',
  partial: '#faad14',
  failed: '#ff4d4f',
};

export const deployStatusLabel: Record<DeployStatus, string> = {
  pending: '排队中',
  validating: '校验中',
  writing: '写入中',
  reloading: '重启中',
  verifying: '校验中',
  success: '成功',
  partial: '部分成功',
  failed: '失败',
};

export const bundlePatternLabel: Record<BundlePattern, string> = {
  single: '单体',
  'plan-build': '先规划后执行',
  'orchestrator-workers': '编排者与专家团',
  'research-loop': '深度调研环',
  'review-loop': '实现与评审环',
  pipeline: '顺序流水线',
  custom: '自定义',
};

export const agentModeLabel: Record<AgentMode, string> = {
  primary: '主对话',
  subagent: '子代理',
  all: '两者皆可',
};
