/**
 * Expert (专家团) 前端 service.
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
  skills: string[];
  mcps: string[];
  tools: Record<string, boolean>;
  image?: string | null;
  container_name?: string | null;
  container_id?: string | null;
  host_port?: number | null;
  host: string;
  port: number;
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
  skills?: string[];
  mcps?: string[];
  tools?: Record<string, boolean>;
  image?: string | null;
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
  skills?: string[];
  mcps?: string[];
  tools?: Record<string, boolean>;
  image?: string | null;
  host?: string;
  port?: number;
  sort_order?: number;
}

function unwrap<T>(resp: { data: { code?: string; message?: string; data: T } }): T {
  return resp.data.data;
}

export const expertService = {
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
};