/**
 * 算力调度 API 客户端.
 */
import api from './api';

export interface DockerService {
  id: number;
  name: string;
  slug: string;
  expert_id?: number | null;
  image: string;
  container_name?: string | null;
  container_id?: string | null;
  host: string;
  host_port?: number | null;
  container_port: number;
  opencode_args: string[];
  env: Record<string, string>;
  volumes: { host?: string; container?: string }[];
  status: 'stopped' | 'starting' | 'running' | 'error';
  started_at?: string | null;
  stopped_at?: string | null;
  error_message?: string | null;
  description?: string | null;
  docker_available: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ScheduleTask {
  id: number;
  name: string;
  description?: string | null;
  task_type: string;
  schedule_type: 'manual' | 'once' | 'interval' | 'cron';
  schedule_expr?: string | null;
  docker_service_id?: number | null;
  opencode_config: Record<string, unknown>;
  env: Record<string, string>;
  timeout_seconds: number;
  enabled: boolean;
  status: 'idle' | 'running' | 'paused' | 'disabled';
  last_run_at?: string | null;
  next_run_at?: string | null;
  total_runs: number;
  success_runs: number;
  failed_runs: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface TaskRun {
  id: number;
  task_id: number;
  trigger: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'cancelled' | 'timeout';
  started_at?: string | null;
  finished_at?: string | null;
  duration_ms?: number | null;
  exit_code?: number | null;
  output_summary?: string | null;
  error_message?: string | null;
  opencode_session_id?: string | null;
  created_at?: string | null;
}

export interface TaskLogEntry {
  id: number;
  run_id: number;
  sequence: number;
  level: string;
  message: string;
  created_at?: string | null;
}

const BASE = '/compute';

function unwrap<T>(resp: { data: { code?: string; message?: string; data: T } }): T {
  return resp.data.data;
}

export const computeService = {
  // Docker Services
  listDockerServices: () => api.get(`${BASE}/docker-services`).then((r) => unwrap<DockerService[]>(r)),
  getDockerService: (id: number) => api.get(`${BASE}/docker-services/${id}`).then((r) => unwrap<DockerService>(r)),
  createDockerService: (data: Partial<DockerService>) => api.post(`${BASE}/docker-services`, data).then((r) => unwrap<DockerService>(r)),
  startDockerService: (id: number) => api.post(`${BASE}/docker-services/${id}/start`).then((r) => unwrap<DockerService>(r)),
  stopDockerService: (id: number) => api.post(`${BASE}/docker-services/${id}/stop`).then((r) => unwrap<DockerService>(r)),
  deleteDockerService: (id: number) => api.delete(`${BASE}/docker-services/${id}`).then((r) => unwrap(r)),
  getDockerServiceLogs: (id: number, tail = 200) => api.get(`${BASE}/docker-services/${id}/logs`, { params: { tail } }).then((r) => unwrap<{ logs: string }>(r)),

  // Tasks
  listTasks: () => api.get(`${BASE}/tasks`).then((r) => unwrap<ScheduleTask[]>(r)),
  getTask: (id: number) => api.get(`${BASE}/tasks/${id}`).then((r) => unwrap<ScheduleTask>(r)),
  createTask: (data: Partial<ScheduleTask>) => api.post(`${BASE}/tasks`, data).then((r) => unwrap<ScheduleTask>(r)),
  updateTask: (id: number, data: Partial<ScheduleTask>) => api.patch(`${BASE}/tasks/${id}`, data).then((r) => unwrap<ScheduleTask>(r)),
  deleteTask: (id: number) => api.delete(`${BASE}/tasks/${id}`).then((r) => unwrap(r)),
  toggleTask: (id: number, enabled: boolean) => api.post(`${BASE}/tasks/${id}/toggle`, { enabled }).then((r) => unwrap<ScheduleTask>(r)),
  triggerTask: (id: number) => api.post(`${BASE}/tasks/${id}/trigger`).then((r) => unwrap<TaskRun>(r)),

  // Runs
  listTaskRuns: (taskId: number) => api.get(`${BASE}/tasks/${taskId}/runs`).then((r) => unwrap<TaskRun[]>(r)),
  getRun: (runId: number) => api.get(`${BASE}/runs/${runId}`).then((r) => unwrap<TaskRun>(r)),
  cancelRun: (runId: number) => api.post(`${BASE}/runs/${runId}/cancel`).then((r) => unwrap<TaskRun>(r)),
  getRunLogs: (runId: number, sinceSeq = 0) => api.get(`${BASE}/runs/${runId}/logs`, { params: { since_seq: sinceSeq, limit: 500 } }).then((r) => unwrap<TaskLogEntry[]>(r)),
};