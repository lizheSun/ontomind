/**
 * Resources API client — canonical entry point after the T45 rename.
 *
 * Canonical route names (`/compute-nodes`, `/mcps`) are exposed alongside
 * the legacy method names (`listInstances`, `createInstance`, ...) so
 * existing components keep compiling while they migrate. Legacy methods
 * delegate to their canonical counterparts.
 */
import api from './api';
import type { Instance, MCPConfig } from '../types/index';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');

// T45 rename: ComputeNode is the canonical name for the former `Instance`.
// The wire shape is unchanged so we alias the type instead of duplicating it.
export type ComputeNode = Instance;
export type MCP = MCPConfig;
export type { Instance, MCPConfig };

export interface PaginationParams {
  skip?: number;
  limit?: number;
}

export const resourcesAPI = {
  // ---- ComputeNode (canonical) ----
  listComputeNodes: (params?: PaginationParams) =>
    api.get('/resources/compute-nodes', { params }),
  getComputeNode: (id: number) => api.get(`/resources/compute-nodes/${id}`),
  createComputeNode: (data: Partial<ComputeNode>) =>
    api.post('/resources/compute-nodes', data),
  updateComputeNode: (id: number, data: Partial<ComputeNode>) =>
    api.put(`/resources/compute-nodes/${id}`, data),
  deleteComputeNode: (id: number) => api.delete(`/resources/compute-nodes/${id}`),
  heartbeatComputeNode: (id: number) =>
    api.post(`/resources/compute-nodes/${id}/heartbeat`),
  registerLocalComputeNode: () =>
    api.post('/resources/compute-nodes/register-local'),
  scanAgentsOnNode: (nodeId: number) =>
    api.post(`/resources/compute-nodes/${nodeId}/scan-agents`),

  // ---- Instance (legacy aliases → delegate to ComputeNode canonical) ----
  listInstances(params?: PaginationParams) {
    return this.listComputeNodes(params);
  },
  getInstance(id: number) {
    return this.getComputeNode(id);
  },
  createInstance(data: Partial<Instance>) {
    return this.createComputeNode(data as Partial<ComputeNode>);
  },
  updateInstance(id: number, data: Partial<Instance>) {
    return this.updateComputeNode(id, data as Partial<ComputeNode>);
  },
  deleteInstance(id: number) {
    return this.deleteComputeNode(id);
  },
  heartbeatInstance(id: number) {
    return this.heartbeatComputeNode(id);
  },
  registerLocalInstance() {
    return this.registerLocalComputeNode();
  },
  scanAgents(instId: number) {
    return this.scanAgentsOnNode(instId);
  },

  // ---- Agent (definition CRUD — table `agents`) ----
  listAgents: (params?: PaginationParams) =>
    api.get('/resources/agents', { params }),
  getAgent: (id: number) => api.get(`/resources/agents/${id}`),
  createAgent: (data: Record<string, unknown>) =>
    api.post('/resources/agents', data),
  updateAgent: (id: number, data: Record<string, unknown>) =>
    api.put(`/resources/agents/${id}`, data),
  deleteAgent: (id: number) => api.delete(`/resources/agents/${id}`),
  chatWithAgent: (agentId: number, message: string) =>
    api.post(`/resources/agents/${agentId}/chat`, { message, stream: false }),
  chatWithAgentStream: (agentId: number): string =>
    `${WS_BASE_URL}/resources/agents/${agentId}/chat/stream`,

  // ---- Skill ----
  listSkills: (params?: PaginationParams) =>
    api.get('/resources/skills', { params }),
  getSkill: (id: number) => api.get(`/resources/skills/${id}`),
  createSkill: (data: Record<string, unknown>) =>
    api.post('/resources/skills', data),
  updateSkill: (id: number, data: Record<string, unknown>) =>
    api.put(`/resources/skills/${id}`, data),
  deleteSkill: (id: number) => api.delete(`/resources/skills/${id}`),
  installSkill: (id: number, instanceId?: number) =>
    api.post(`/resources/skills/${id}/install`, { instance_id: instanceId }),

  // ---- MCP (canonical `/mcps`) ----
  listMCPs: (params?: PaginationParams) =>
    api.get('/resources/mcps', { params }),
  getMCP: (id: number) => api.get(`/resources/mcps/${id}`),
  createMCP: (data: Partial<MCP>) => api.post('/resources/mcps', data),
  updateMCP: (id: number, data: Partial<MCP>) =>
    api.put(`/resources/mcps/${id}`, data),
  deleteMCP: (id: number) => api.delete(`/resources/mcps/${id}`),
  autoDiscoverMCP: (data: Record<string, unknown>) =>
    api.post('/resources/mcps/auto-discover', data),

  // ---- AgentRun ----
  listRuns: (params?: PaginationParams) => api.get('/resources/runs', { params }),
  getRun: (id: number) => api.get(`/resources/runs/${id}`),
  createRun: (data: Record<string, unknown>) => api.post('/resources/runs', data),
  stopRun: (id: number) => api.post(`/resources/runs/${id}/stop`),
};

export default resourcesAPI;
