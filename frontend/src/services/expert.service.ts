/**
 * Expert (专家团) 前端 service — OALP v1.0
 */
import api from './api';

export interface Expert {
  id: number;
  name: string;
  slug: string;
  avatar?: string | null;
  description?: string | null;
  role?: string | null;
  sop?: string | null;
  provider?: string | null;
  model?: string | null;
  temperature?: string | null;
  top_p?: string | null;
  mode: 'primary' | 'subagent' | 'all';
  subagent_depth: number;
  max_steps?: number | null;
  system_prompt?: string | null;
  permission: Record<string, any>;
  hooks: any[];
  evals: any[];
  version: number;
  skills: string[];
  mcps: string[];
  tools: Record<string, boolean>;
  image?: string | null;
  container_template_id?: number | null;
  container_name?: string | null;
  container_id?: string | null;
  host_port?: number | null;
  host: string;
  port: number;
  bind_skills_to_container: boolean;
  status: 'online' | 'offline' | 'error';
  agent_file_path?: string | null;
  started_at?: string | null;
  stopped_at?: string | null;
  error_message?: string | null;
  sort_order: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ExpertCreatePayload {
  name: string;
  slug: string;
  avatar?: string | null;
  description?: string | null;
  role?: string | null;
  sop?: string | null;
  provider?: string | null;
  model?: string | null;
  temperature?: string | null;
  top_p?: string | null;
  mode?: 'primary' | 'subagent' | 'all';
  subagent_depth?: number;
  max_steps?: number | null;
  system_prompt?: string | null;
  permission?: Record<string, any>;
  hooks?: any[];
  evals?: any[];
  skills?: string[];
  mcps?: string[];
  tools?: Record<string, boolean>;
  image?: string | null;
  container_template_id?: number | null;
  bind_skills_to_container?: boolean | null;
  host?: string;
  port?: number;
  sort_order?: number;
}

export interface ExpertUpdatePayload {
  name?: string;
  avatar?: string | null;
  description?: string | null;
  role?: string | null;
  sop?: string | null;
  provider?: string | null;
  model?: string | null;
  temperature?: string | null;
  top_p?: string | null;
  mode?: 'primary' | 'subagent' | 'all';
  subagent_depth?: number;
  max_steps?: number | null;
  system_prompt?: string | null;
  permission?: Record<string, any>;
  hooks?: any[];
  evals?: any[];
  skills?: string[];
  mcps?: string[];
  tools?: Record<string, boolean>;
  image?: string | null;
  container_template_id?: number | null;
  bind_skills_to_container?: boolean | null;
  host?: string;
  port?: number;
  sort_order?: number;
}

export interface ExpertAutoDraftResp {
  name: string;
  slug: string;
  avatar: string;
  description: string;
  role: string;
  sop: string;
  provider: string;
  model: string;
  temperature: string;
  skills: string[];
  mcps: string[];
  tools: Record<string, boolean>;
  permission: Record<string, any>;
}

export interface AgentRelation {
  id: number;
  parent_expert_id: number;
  parent_slug?: string | null;
  parent_name?: string | null;
  child_expert_id: number;
  child_slug?: string | null;
  child_name?: string | null;
  relation: 'delegate' | 'fan_out' | 'review';
  condition?: string | null;
  sort_order: number;
  created_at?: string | null;
}

export interface DeployContainerResp {
  expert: Expert;
  container: {
    id: string;
    name: string;
    node_id: number;
    node_name: string;
    image: string;
    host_port: number;
    container_port: number;
    url: string;
    healthy: boolean;
    status: string;
  };
}

export interface DiscoveredSkill {
  name: string;
  source_path: string;
  source_dir: string;
  description: string;
  frontmatter: Record<string, any>;
  body_length: number;
  is_loaded: boolean;
}

export interface DiscoveredMCP {
  name: string;
  type: string;
  enabled: boolean;
  command?: string[] | null;
  url?: string | null;
  description?: string;
}

export interface LocalAgent {
  slug: string;
  path: string;
  description: string;
  mode: string;
  model?: string | null;
  permission: Record<string, any>;
  body_length: number;
}

function unwrap<T>(resp: { data: { code?: string; message?: string; data: T } }): T {
  return resp.data.data;
}

function unwrapRaw<T>(resp: { data: T }): T {
  return resp.data;
}

export const expertService = {
  // ---- Expert ----
  list: () => api.get('/experts').then((r) => unwrap<Expert[]>(r)),
  get: (id: number) => api.get(`/experts/${id}`).then((r) => unwrap<Expert>(r)),
  create: (data: ExpertCreatePayload) =>
    api.post('/experts', data).then((r) => unwrap<Expert>(r)),
  update: (id: number, data: ExpertUpdatePayload) =>
    api.patch(`/experts/${id}`, data).then((r) => unwrap<Expert>(r)),
  remove: (id: number) => api.delete(`/experts/${id}`).then((r) => unwrap(r)),
  start: (id: number) =>
    api.post(`/experts/${id}/start`).then((r) => unwrap<Expert>(r)),
  stop: (id: number) =>
    api.post(`/experts/${id}/stop`).then((r) => unwrap<Expert>(r)),
  seed: () =>
    api.post('/experts/seed').then((r) => unwrap<{ added: number }>(r)),
  clone: (id: number, new_slug: string, new_name?: string) =>
    api.post(`/experts/${id}/clone`, { new_slug, new_name }).then((r) => unwrap<Expert>(r)),
  autoDraft: (description: string) =>
    api.post('/experts/auto-draft', { description }).then(unwrapRaw<ExpertAutoDraftResp>),

  // ---- Relations ----
  listRelations: () =>
    api.get('/experts/relations/all').then((r) => unwrap<AgentRelation[]>(r)),
  listRelationsFor: (parentId: number) =>
    api.get(`/experts/${parentId}/relations`).then((r) => unwrap<AgentRelation[]>(r)),
  createRelation: (data: {
    parent_expert_id: number;
    child_expert_id: number;
    relation?: 'delegate' | 'fan_out' | 'review';
    condition?: string;
    sort_order?: number;
  }) => api.post('/experts/relations', data).then((r) => unwrap<AgentRelation>(r)),
  deleteRelation: (id: number) =>
    api.delete(`/experts/relations/${id}`).then((r) => unwrap(r)),

  // ---- Deploy container ----
  deployContainer: (id: number, data: {
    node_id: number;
    container_template_id?: number;
    host_port?: number;
    extra_env?: Record<string, string>;
    auto_start?: boolean;
  }) => api.post(`/experts/${id}/deploy-container`, data).then((r) => unwrap<DeployContainerResp>(r)),

  // ---- Skill/MCP discovery ----
  discoverSkills: () =>
    api.get('/experts/skill-mcp/skills/discover').then((r) => unwrap<DiscoveredSkill[]>(r)),
  loadSkills: () =>
    api.post('/experts/skill-mcp/skills/load-from-opencode').then((r) => unwrap<{ added: number; updated: number }>(r)),
  uploadSkillFolder: (file: File, overwrite = false) => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('overwrite', String(overwrite));
    return api.post('/experts/skill-mcp/skills/upload-folder', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => unwrap<{ added: number; updated: number; skipped: number; errors: string[] }>(r));
  },
  summarizeSkill: (id: number) =>
    api.post(`/experts/skill-mcp/skills/${id}/summarize`).then(unwrapRaw<any>),

  discoverMCPs: () =>
    api.get('/experts/skill-mcp/mcps/discover').then((r) => unwrap<DiscoveredMCP[]>(r)),
  loadMCPs: () =>
    api.post('/experts/skill-mcp/mcps/load-from-opencode').then((r) => unwrap<{ added: number; updated: number }>(r)),
  summarizeMCP: (id: number) =>
    api.post(`/experts/skill-mcp/mcps/${id}/summarize`).then(unwrapRaw<any>),

  listLocalAgents: () =>
    api.get('/experts/skill-mcp/agents/list-local').then((r) => unwrap<LocalAgent[]>(r)),
};
