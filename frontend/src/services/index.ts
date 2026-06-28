import api from './api';

// ===== 感知层 =====
export const perceptionAPI = {
  listDataSources: () => api.get('/perception/datasources'),
  createDataSource: (data: any) => api.post('/perception/datasources', data),
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
