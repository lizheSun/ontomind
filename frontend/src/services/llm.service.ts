import api from './api';

export interface LLMConfig {
  id: number;
  name: string;
  provider: 'openai' | 'anthropic';
  base_url: string;
  api_key: string;
  model_name: string;
  description?: string;
  is_active: boolean;
  extra_headers?: string;
  extra_body?: string;
  timeout: string;
  max_retries: string;
  created_at?: string;
  updated_at?: string;
}

export interface LLMConfigCreate {
  name: string;
  provider: string;
  base_url: string;
  api_key: string;
  model_name: string;
  description?: string;
  is_active?: boolean;
  extra_headers?: string;
  extra_body?: string;
  timeout?: string;
  max_retries?: string;
}

export interface LLMConfigUpdate {
  name?: string;
  provider?: string;
  base_url?: string;
  api_key?: string;
  model_name?: string;
  description?: string;
  is_active?: boolean;
  extra_headers?: string;
  extra_body?: string;
  timeout?: string;
  max_retries?: string;
}

export interface LLMChatRequest {
  messages: { role: string; content: string }[];
  config_id?: number;
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
}

export interface LLMChatResponse {
  content: string;
  model: string;
  usage?: Record<string, number>;
}

export const llmService = {
  listConfigs: async (params?: { skip?: number; limit?: number }) => {
    const res = await api.get('/llm', { params });
    return res.data;
  },

  getConfig: async (id: number) => {
    const res = await api.get(`/llm/${id}`);
    return res.data;
  },

  createConfig: async (data: LLMConfigCreate) => {
    const res = await api.post('/llm', data);
    return res.data;
  },

  updateConfig: async (id: number, data: LLMConfigUpdate) => {
    const res = await api.put(`/llm/${id}`, data);
    return res.data;
  },

  deleteConfig: async (id: number) => {
    const res = await api.delete(`/llm/${id}`);
    return res.data;
  },

  chat: async (data: LLMChatRequest) => {
    const res = await api.post('/llm/chat', data);
    return res.data;
  },

  getActiveConfig: async () => {
    const res = await api.get('/llm/active/info');
    return res.data;
  },
};

export default llmService;
