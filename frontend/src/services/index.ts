import api from './api';

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

  // Agent
  listAgents: (params?: { skip?: number; limit?: number }) =>
    api.get('/resources/agents', { params }),
  getAgent: (id: number) => api.get(`/resources/agents/${id}`),
  createAgent: (data: any) => api.post('/resources/agents', data),
  updateAgent: (id: number, data: any) => api.put(`/resources/agents/${id}`, data),
  deleteAgent: (id: number) => api.delete(`/resources/agents/${id}`),

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
