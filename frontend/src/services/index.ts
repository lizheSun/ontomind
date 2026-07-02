import api from './api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');

// ===== 资源管理 =====
export const resourcesAPI = {
  // Instance
  listInstances: (params?: { skip?: number; limit?: number }) =>
    api.get('/resources/instances', { params }),
  getInstance: (id: number) => api.get(`/resources/instances/${id}`),
  createInstance: (data: any) => api.post('/resources/instances', data),
  updateInstance: (id: number, data: any) => api.put(`/resources/instances/${id}`, data),
  deleteInstance: (id: number) => api.delete(`/resources/instances/${id}`),
  heartbeatInstance: (id: number) => api.post(`/resources/instances/${id}/heartbeat`),
  registerLocalInstance: () => api.post('/resources/instances/register-local'),
  scanAgents: (instId: number) => api.post(`/resources/instances/${instId}/scan-agents`),

  // Agent
  listAgents: (params?: { skip?: number; limit?: number }) =>
    api.get('/resources/agents', { params }),
  getAgent: (id: number) => api.get(`/resources/agents/${id}`),
  createAgent: (data: any) => api.post('/resources/agents', data),
  updateAgent: (id: number, data: any) => api.put(`/resources/agents/${id}`, data),
  deleteAgent: (id: number) => api.delete(`/resources/agents/${id}`),
  chatWithAgent: (agentId: number, message: string) =>
    api.post(`/resources/agents/${agentId}/chat`, { message, stream: false }),
  chatWithAgentStream: (agentId: number): string =>
    `${WS_BASE_URL}/resources/agents/${agentId}/chat/stream`,

  // Skill
  listSkills: (params?: { skip?: number; limit?: number }) =>
    api.get('/resources/skills', { params }),
  getSkill: (id: number) => api.get(`/resources/skills/${id}`),
  createSkill: (data: any) => api.post('/resources/skills', data),
  updateSkill: (id: number, data: any) => api.put(`/resources/skills/${id}`, data),
  deleteSkill: (id: number) => api.delete(`/resources/skills/${id}`),
  installSkill: (id: number, instanceId?: number) =>
    api.post(`/resources/skills/${id}/install`, { instance_id: instanceId }),

  // MCP
  listMCPs: (params?: { skip?: number; limit?: number }) =>
    api.get('/resources/mcps', { params }),
  getMCP: (id: number) => api.get(`/resources/mcps/${id}`),
  createMCP: (data: any) => api.post('/resources/mcps', data),
  updateMCP: (id: number, data: any) => api.put(`/resources/mcps/${id}`, data),
  deleteMCP: (id: number) => api.delete(`/resources/mcps/${id}`),
  autoDiscoverMCP: (data: any) => api.post('/resources/mcps/auto-discover', data),

  // AgentRun
  listRuns: (params?: { skip?: number; limit?: number }) =>
    api.get('/resources/runs', { params }),
  getRun: (id: number) => api.get(`/resources/runs/${id}`),
  createRun: (data: any) => api.post('/resources/runs', data),
  stopRun: (id: number) => api.post(`/resources/runs/${id}/stop`),
};

// ===== 项目管理 =====
export const projectsAPI = {
  // Project
  listProjects: (params?: { skip?: number; limit?: number }) =>
    api.get('/projects', { params }),
  getProject: (id: number) => api.get(`/projects/${id}`),
  createProject: (data: any) => api.post('/projects', data),
  updateProject: (id: number, data: any) => api.put(`/projects/${id}`, data),
  deleteProject: (id: number) => api.delete(`/projects/${id}`),

  // Requirements
  listRequirements: (projectId: number, params?: { skip?: number; limit?: number }) =>
    api.get(`/projects/${projectId}/requirements`, { params }),
  createRequirement: (projectId: number, data: any) =>
    api.post(`/projects/${projectId}/requirements`, data),
  updateRequirement: (projectId: number, reqId: number, data: any) =>
    api.put(`/projects/${projectId}/requirements/${reqId}`, data),
  deleteRequirement: (projectId: number, reqId: number) =>
    api.delete(`/projects/${projectId}/requirements/${reqId}`),
  analyzeRequirement: (projectId: number, reqId: number) =>
    api.post(`/projects/${projectId}/requirements/${reqId}/analyze`),
  decomposeRequirement: (projectId: number, reqId: number) =>
    api.post(`/projects/${projectId}/requirements/${reqId}/decompose`),

  // Plans
  listPlans: (projectId: number, params?: { skip?: number; limit?: number }) =>
    api.get(`/projects/${projectId}/plans`, { params }),
  createPlan: (projectId: number, data: any) =>
    api.post(`/projects/${projectId}/plans`, data),
  updatePlan: (projectId: number, planId: number, data: any) =>
    api.put(`/projects/${projectId}/plans/${planId}`, data),
  deletePlan: (projectId: number, planId: number) =>
    api.delete(`/projects/${projectId}/plans/${planId}`),

  // Tasks
  listTasks: (projectId: number, params?: { requirement_id?: number }) =>
    api.get(`/projects/${projectId}/tasks`, { params }),
  createTask: (projectId: number, data: any) =>
    api.post(`/projects/${projectId}/tasks`, data),
  updateTask: (projectId: number, taskId: number, data: any) =>
    api.put(`/projects/${projectId}/tasks/${taskId}`, data),
  moveTask: (projectId: number, taskId: number, data: { status: string; position?: number }) =>
    api.put(`/projects/${projectId}/tasks/${taskId}/move`, data),
  deleteTask: (projectId: number, taskId: number) =>
    api.delete(`/projects/${projectId}/tasks/${taskId}`),

  // Kanban
  getKanban: (projectId: number) =>
    api.get(`/projects/${projectId}/kanban`),
};

// ===== 感知层 =====
export const perceptionAPI = {
  // Data Sources CRUD
  listDataSources: (params?: { skip?: number; limit?: number }) =>
    api.get('/perception/datasources', { params }),
  getDataSource: (id: number) => api.get(`/perception/datasources/${id}`),
  createDataSource: (data: any) => api.post('/perception/datasources', data),
  updateDataSource: (id: number, data: any) => api.put(`/perception/datasources/${id}`, data),
  deleteDataSource: (id: number) => api.delete(`/perception/datasources/${id}`),

  // Auto-configure
  parseConfig: (rawText: string) => api.post('/perception/datasources/parse-config', { raw_text: rawText }),
  autoConfigure: (rawText: string) => api.post('/perception/datasources/auto-configure', { raw_text: rawText }),

  // Test connection
  testConnection: (id: number) => api.post(`/perception/datasources/${id}/test`),

  // Documents
  uploadDocument: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/perception/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  listDocuments: () => api.get('/perception/documents'),
};

// ===== 认知层 =====
export const cognitionAPI = {
  listEntities: () => api.get('/cognition/ontology/entities'),
  listRelations: () => api.get('/cognition/ontology/relations'),
  getGraph: () => api.get('/cognition/ontology/graph'),
  extractOntology: () => api.post('/cognition/ontology/extract'),
  semanticSearch: (q: string) => api.get('/cognition/search/semantic', { params: { q } }),
};

// ===== 决策层 =====
export const decisionAPI = {
  listFeatures: () => api.get('/decision/features'),
  listModels: () => api.get('/decision/models'),
  trainModel: (config: any) => api.post('/decision/models/train', config),
  listStrategies: () => api.get('/decision/strategies'),
  generateStrategies: () => api.post('/decision/strategies/generate'),
};

// ===== 执行层 =====
export const executionAPI = {
  deployStrategy: (id: number) => api.post(`/execution/strategies/${id}/deploy`),
  rollbackStrategy: (id: number) => api.post(`/execution/strategies/${id}/rollback`),
  getMonitorStatus: () => api.get('/execution/monitor/status'),
};

// ===== 应用层 =====
export const applicationAPI = {
  aibiQuery: (query: string) => api.post('/application/aibi/query', { query }),
  listDatasets: () => api.get('/application/dashboard/datasets'),
  listCharts: () => api.get('/application/dashboard/charts'),
};

// ===== 认证 =====
export const authAPI = {
  login: (username: string, password: string) =>
    api.post('/auth/login', new URLSearchParams({ username, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),
};
