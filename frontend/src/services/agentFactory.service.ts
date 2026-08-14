/** Agent 工厂 API 服务 */
import api from './api';
import type {
  AgentBundle,
  AgentBundleCreate,
  AgentBundleUpdate,
  AgentTemplate,
  AgentTemplateCreate,
  AgentTemplateUpdate,
  AgentVersion,
  Deployment,
  DeployRequest,
  DeployStatus,
  PermissionKeysResponse,
  PresetsResponse,
  PreviewResponse,
  SkillTemplate,
  SkillTemplateCreate,
  SkillTemplateUpdate,
  ValidationResult,
} from '../types/agentFactory';

const B = '/agent-factory';

// ---- 元数据 ----

export async function getPermissionKeys(): Promise<PermissionKeysResponse> {
  const res = await api.get(`${B}/permission-keys`);
  return res.data as PermissionKeysResponse;
}

export async function getPresets(): Promise<PresetsResponse> {
  const res = await api.get(`${B}/presets`);
  return res.data as PresetsResponse;
}

// ---- Agent ----

export async function listAgents(params?: {
  category?: string;
  mode?: string;
  keyword?: string;
}): Promise<AgentTemplate[]> {
  const res = await api.get(`${B}/agents`, { params });
  return res.data as AgentTemplate[];
}

export async function getAgent(id: number): Promise<AgentTemplate> {
  const res = await api.get(`${B}/agents/${id}`);
  return res.data as AgentTemplate;
}

export async function createAgent(data: AgentTemplateCreate): Promise<AgentTemplate> {
  const res = await api.post(`${B}/agents`, data);
  return res.data as AgentTemplate;
}

export async function updateAgent(
  id: number,
  data: AgentTemplateUpdate,
): Promise<AgentTemplate> {
  const res = await api.put(`${B}/agents/${id}`, data);
  return res.data as AgentTemplate;
}

export async function deleteAgent(id: number): Promise<void> {
  await api.delete(`${B}/agents/${id}`);
}

/** 渲染 .md 预览（不落盘）—— 所见即所得 */
export async function previewAgent(id: number): Promise<PreviewResponse> {
  const res = await api.post(`${B}/agents/${id}/preview`);
  return res.data as PreviewResponse;
}

/** 纯校验，不落库 —— 边编辑边提示用 */
export async function validateAgent(
  payload: Record<string, unknown>,
): Promise<ValidationResult> {
  const res = await api.post(`${B}/agents/validate`, payload);
  return res.data as ValidationResult;
}

export async function importAgent(data: {
  content: string;
  name?: string;
  category?: string;
  overwrite?: boolean;
}): Promise<AgentTemplate> {
  const res = await api.post(`${B}/agents/import`, data);
  return res.data as AgentTemplate;
}

export async function listAgentVersions(id: number): Promise<AgentVersion[]> {
  const res = await api.get(`${B}/agents/${id}/versions`);
  return res.data as AgentVersion[];
}

export async function createAgentVersion(
  id: number,
  changeNote?: string,
): Promise<AgentVersion> {
  const res = await api.post(`${B}/agents/${id}/versions`, { change_note: changeNote });
  return res.data as AgentVersion;
}

export async function rollbackAgent(
  id: number,
  version: number,
): Promise<AgentTemplate> {
  const res = await api.post(`${B}/agents/${id}/rollback`, { version });
  return res.data as AgentTemplate;
}

// ---- Skill ----

export async function listSkills(params?: {
  category?: string;
  keyword?: string;
}): Promise<SkillTemplate[]> {
  const res = await api.get(`${B}/skills`, { params });
  return res.data as SkillTemplate[];
}

export async function getSkill(id: number): Promise<SkillTemplate> {
  const res = await api.get(`${B}/skills/${id}`);
  return res.data as SkillTemplate;
}

export async function createSkill(data: SkillTemplateCreate): Promise<SkillTemplate> {
  const res = await api.post(`${B}/skills`, data);
  return res.data as SkillTemplate;
}

export async function updateSkill(
  id: number,
  data: SkillTemplateUpdate,
): Promise<SkillTemplate> {
  const res = await api.put(`${B}/skills/${id}`, data);
  return res.data as SkillTemplate;
}

export async function deleteSkill(id: number): Promise<void> {
  await api.delete(`${B}/skills/${id}`);
}

export async function previewSkill(id: number): Promise<PreviewResponse> {
  const res = await api.post(`${B}/skills/${id}/preview`);
  return res.data as PreviewResponse;
}

// ---- Bundle（Loop 编排方案）----

export async function listBundles(params?: {
  pattern?: string;
  keyword?: string;
}): Promise<AgentBundle[]> {
  const res = await api.get(`${B}/bundles`, { params });
  return res.data as AgentBundle[];
}

export async function getBundle(id: number): Promise<AgentBundle> {
  const res = await api.get(`${B}/bundles/${id}`);
  return res.data as AgentBundle;
}

export async function createBundle(data: AgentBundleCreate): Promise<AgentBundle> {
  const res = await api.post(`${B}/bundles`, data);
  return res.data as AgentBundle;
}

export async function updateBundle(
  id: number,
  data: AgentBundleUpdate,
): Promise<AgentBundle> {
  const res = await api.put(`${B}/bundles/${id}`, data);
  return res.data as AgentBundle;
}

export async function deleteBundle(id: number): Promise<void> {
  await api.delete(`${B}/bundles/${id}`);
}

/** 校验编排方案（含 Loop 拓扑一致性：死引用、无 primary、depth 冲突等） */
export async function validateBundle(id: number): Promise<ValidationResult> {
  const res = await api.post(`${B}/bundles/${id}/validate`);
  return res.data as ValidationResult;
}

/** 全量产物预览 —— 发布前确认到底会写哪些文件 */
export async function previewBundle(id: number): Promise<PreviewResponse> {
  const res = await api.post(`${B}/bundles/${id}/preview`);
  return res.data as PreviewResponse;
}

// ---- 发布 ----

/**
 * 发布到容器（五阶段）。
 * 耗时较长（要重启 opencode 并回读校验，skill 探测还要跑一次 opencode run），
 * 所以放宽 timeout 到 10 分钟。
 */
export async function deployBundle(
  bundleId: number,
  data: DeployRequest,
): Promise<Deployment> {
  const res = await api.post(`${B}/bundles/${bundleId}/deploy`, data, {
    timeout: 600_000,
  });
  return res.data as Deployment;
}

export async function listDeployments(params?: {
  bundle_id?: number;
  node_id?: number;
  container_id?: string;
  status?: DeployStatus;
}): Promise<Deployment[]> {
  const res = await api.get(`${B}/deployments`, { params });
  return res.data as Deployment[];
}

export async function getDeployment(id: number): Promise<Deployment> {
  const res = await api.get(`${B}/deployments/${id}`);
  return res.data as Deployment;
}

/** 重新回读校验（不重写文件、不重启）—— 检测产物漂移 */
export async function reverifyDeployment(id: number): Promise<Deployment> {
  const res = await api.post(`${B}/deployments/${id}/verify`, {}, { timeout: 300_000 });
  return res.data as Deployment;
}

export const agentFactoryService = {
  getPermissionKeys,
  getPresets,
  listAgents,
  getAgent,
  createAgent,
  updateAgent,
  deleteAgent,
  previewAgent,
  validateAgent,
  importAgent,
  listAgentVersions,
  createAgentVersion,
  rollbackAgent,
  listSkills,
  getSkill,
  createSkill,
  updateSkill,
  deleteSkill,
  previewSkill,
  listBundles,
  getBundle,
  createBundle,
  updateBundle,
  deleteBundle,
  validateBundle,
  previewBundle,
  deployBundle,
  listDeployments,
  getDeployment,
  reverifyDeployment,
};
