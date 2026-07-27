/**
 * 算力调度 API 服务 — 节点 / 镜像 / 容器 / 任务 / 运行 / 日志 / OpenCode 本地服务.
 */
import api from './api';
import type {
  ComputeNode,
  ContainerInstance,
  HubImage,
  ImageListItem,
  OpenCodeStatus,
  OpenCodeWebInstance,
  OpenCodeCliRun,
  SchedulerTask,
  TaskRunRecord,
  LogLine,
} from '../pages/compute/types';

interface ApiResponse<T> {
  code: string;
  message: string;
  data: T;
}

// ==========================================================================
// 节点
// ==========================================================================

export async function fetchNodes(): Promise<ComputeNode[]> {
  const { data } = await api.get<ApiResponse<any[]>>('/compute/nodes');
  return (data.data ?? []).map(normalizeNode);
}

export async function createNode(payload: {
  name: string; address: string; conn_type: string;
  ssh_port?: number; ssh_user?: string;
  tls_certs?: string; remark?: string;
}): Promise<ComputeNode> {
  const { data } = await api.post<ApiResponse<any>>('/compute/nodes', payload);
  return normalizeNode(data.data);
}

export async function deleteNode(nodeId: number): Promise<void> {
  await api.delete(`/compute/nodes/${nodeId}`);
}

export async function testNode(nodeId: number): Promise<{ success: boolean; message: string }> {
  const { data } = await api.post<ApiResponse<{ success: boolean; message: string }>>(`/compute/nodes/${nodeId}/test`);
  return data.data;
}

export async function autoMountLocal(): Promise<ComputeNode> {
  const { data } = await api.post<ApiResponse<any>>('/compute/nodes/auto-mount-local');
  return normalizeNode(data.data);
}

// ==========================================================================
// 容器
// ==========================================================================

export async function fetchContainers(nodeId: number): Promise<ContainerInstance[]> {
  const { data } = await api.get<ApiResponse<any[]>>(`/compute/nodes/${nodeId}/containers`);
  return (data.data ?? []).map(normalizeContainer);
}

export async function createContainer(
  nodeId: number,
  payload: {
    name: string; image: string; ports?: string[];
    env_vars?: string[]; volumes?: string[]; expert_slug?: string;
    restart_policy?: string; network?: string; extra_args?: string;
  },
): Promise<ContainerInstance> {
  const { data } = await api.post<ApiResponse<any>>(`/compute/nodes/${nodeId}/containers`, payload);
  return normalizeContainer(data.data);
}

export async function startContainer(nodeId: number, cid: string): Promise<void> {
  await api.post(`/compute/nodes/${nodeId}/containers/${cid}/start`);
}

export async function stopContainer(nodeId: number, cid: string): Promise<void> {
  await api.post(`/compute/nodes/${nodeId}/containers/${cid}/stop`);
}

export async function removeContainer(nodeId: number, cid: string, force = false): Promise<void> {
  await api.delete(`/compute/nodes/${nodeId}/containers/${cid}`, { params: { force } });
}

export async function fetchContainerLogs(
  nodeId: number, cid: string,
  tail = '200', since = '',
): Promise<string> {
  const { data } = await api.get<ApiResponse<string>>(
    `/compute/nodes/${nodeId}/containers/${cid}/logs`,
    { params: { tail, since } },
  );
  return data.data ?? '';
}

// ==========================================================================
// Docker Hub 搜索
// ==========================================================================

export async function searchHubImages(q: string, limit = 15): Promise<HubImage[]> {
  const { data } = await api.get<ApiResponse<HubImage[]>>('/compute/hub-search', {
    params: { q, limit },
  });
  return data.data ?? [];
}

// ==========================================================================
// 调度任务
// ==========================================================================

export interface TaskListParams {
  schedule_type?: string;
  enabled?: boolean;
  search?: string;
  skip?: number; limit?: number;
}

export async function fetchTasks(params: TaskListParams = {}): Promise<SchedulerTask[]> {
  const { data } = await api.get<ApiResponse<any[]>>('/compute/tasks', { params });
  return (data.data ?? []).map(normalizeTask);
}

export async function createTask(payload: {
  name: string; description?: string; command: string;
  log_dir?: string; schedule_type?: string;
  schedule_expr?: string; enabled?: boolean;
}): Promise<SchedulerTask> {
  const { data } = await api.post<ApiResponse<any>>('/compute/tasks', payload);
  return normalizeTask(data.data);
}

export async function getTask(taskId: number): Promise<SchedulerTask> {
  const { data } = await api.get<ApiResponse<any>>(`/compute/tasks/${taskId}`);
  return normalizeTask(data.data);
}

export async function updateTask(
  taskId: number,
  payload: Record<string, unknown>,
): Promise<SchedulerTask> {
  const { data } = await api.patch<ApiResponse<any>>(`/compute/tasks/${taskId}`, payload);
  return normalizeTask(data.data);
}

export async function deleteTask(taskId: number): Promise<void> {
  await api.delete(`/compute/tasks/${taskId}`);
}

export async function toggleTask(taskId: number): Promise<SchedulerTask> {
  const { data } = await api.post<ApiResponse<any>>(`/compute/tasks/${taskId}/toggle`);
  return normalizeTask(data.data);
}

export async function triggerTask(taskId: number): Promise<TaskRunRecord> {
  const { data } = await api.post<ApiResponse<any>>(`/compute/tasks/${taskId}/trigger`);
  return normalizeRun(data.data);
}

// ==========================================================================
// 运行记录
// ==========================================================================

export interface RunListParams {
  task_id?: number;
  status?: string;
  trigger?: string;
  skip?: number; limit?: number;
}

export async function fetchRuns(params: RunListParams = {}): Promise<TaskRunRecord[]> {
  const { data } = await api.get<ApiResponse<any[]>>('/compute/runs', { params });
  return (data.data ?? []).map(normalizeRun);
}

export async function fetchTaskRuns(
  taskId: number, params: { status?: string; trigger?: string; skip?: number; limit?: number } = {},
): Promise<TaskRunRecord[]> {
  const { data } = await api.get<ApiResponse<any[]>>(`/compute/tasks/${taskId}/runs`, { params });
  return (data.data ?? []).map(normalizeRun);
}

export async function cancelRun(runId: number): Promise<TaskRunRecord> {
  const { data } = await api.post<ApiResponse<any>>(`/compute/runs/${runId}/cancel`);
  return normalizeRun(data.data);
}

// ==========================================================================
// 运行日志
// ==========================================================================

export interface RunLogResult {
  lines: LogLine[];
  totalLines: number;
  sinceLine: number;
  runStatus: string;
}

export async function fetchRunLogs(
  runId: number, sinceLine = 0, tail = 500,
): Promise<RunLogResult> {
  const { data } = await api.get<ApiResponse<RunLogResult>>(`/compute/runs/${runId}/logs`, {
    params: { since_line: sinceLine, tail },
  });
  return data.data;
}

// ==========================================================================
// 数据归一化
// ==========================================================================

function normalizeNode(raw: any): ComputeNode {
  return {
    id: raw.id,
    name: raw.name,
    address: raw.address,
    connType: raw.conn_type ?? raw.connType ?? 'local',
    online: raw.online ?? false,
    cpu: raw.cpu ?? '',
    mem: raw.mem ?? '',
    disk: raw.disk ?? '',
    remark: raw.remark ?? undefined,
  };
}

function normalizeContainer(raw: any): ContainerInstance {
  return {
    id: raw.id,
    name: raw.name,
    nodeId: raw.nodeId ?? raw.node_id ?? 0,
    expertSlug: raw.expertSlug ?? raw.expert_slug ?? undefined,
    image: raw.image,
    status: raw.status,
    ports: raw.ports ?? '',
    createdAt: raw.createdAt ?? raw.created_at ?? '',
  };
}

function normalizeTask(raw: any): SchedulerTask {
  return {
    id: raw.id,
    name: raw.name,
    description: raw.description ?? undefined,
    command: raw.command,
    logDir: raw.log_dir ?? raw.logDir ?? '/var/log/ontomind/tasks',
    scheduleType: raw.schedule_type ?? raw.scheduleType ?? 'manual',
    scheduleExpr: raw.schedule_expr ?? raw.scheduleExpr ?? undefined,
    enabled: raw.enabled ?? false,
    status: raw.status ?? 'idle',
    createdAt: raw.created_at ?? raw.createdAt ? new Date(raw.created_at ?? raw.createdAt) : new Date(),
    lastRunAt: raw.last_run_at ?? raw.lastRunAt ? new Date(raw.last_run_at ?? raw.lastRunAt) : undefined,
    nextRunAt: raw.next_run_at ?? raw.nextRunAt ? new Date(raw.next_run_at ?? raw.nextRunAt) : undefined,
    totalRuns: raw.total_runs ?? raw.totalRuns ?? 0,
    successRuns: raw.success_runs ?? raw.successRuns ?? 0,
    failedRuns: raw.failed_runs ?? raw.failedRuns ?? 0,
  };
}

function normalizeRun(raw: any): TaskRunRecord {
  return {
    id: raw.id,
    taskId: raw.task_id ?? raw.taskId,
    trigger: raw.trigger ?? 'manual',
    status: raw.status,
    startedAt: new Date(raw.started_at ?? raw.startedAt),
    finishedAt: raw.finished_at ?? raw.finishedAt ? new Date(raw.finished_at ?? raw.finishedAt) : undefined,
    durationMs: raw.duration_ms ?? raw.durationMs ?? undefined,
    exitCode: raw.exit_code ?? raw.exitCode ?? undefined,
    errorMessage: raw.error_message ?? raw.errorMessage ?? undefined,
    logFile: raw.log_file ?? raw.logFile ?? '',
  };
}

// ====================================================================
// 镜像管理
// ====================================================================

export async function listImages(nodeId: number): Promise<ImageListItem[]> {
  const { data } = await api.get<ApiResponse<ImageListItem[]>>(`/compute/nodes/${nodeId}/images`);
  return data.data;
}

export async function pullImage(nodeId: number, image: string): Promise<any> {
  const { data } = await api.post<ApiResponse<any>>(`/compute/nodes/${nodeId}/images/pull`, { image });
  return data.data;
}

export async function removeImage(nodeId: number, imageName: string): Promise<void> {
  await api.delete(`/compute/nodes/${nodeId}/images/path/${encodeURIComponent(imageName)}`);
}

// ====================================================================
// 本地 OpenCode 服务
// ====================================================================

export async function getOpenCodeStatus(): Promise<OpenCodeStatus> {
  const { data } = await api.get<ApiResponse<OpenCodeStatus>>('/compute/opencode/status');
  return data.data;
}

export async function startOpenCodeWeb(port: number = 4096, corsOrigins: string = 'http://localhost:5173'): Promise<any> {
  const { data } = await api.post<ApiResponse<any>>('/compute/opencode/start-web', { port, cors_origins: corsOrigins });
  return data.data;
}

export async function stopOpenCodeWeb(port: number): Promise<any> {
  const { data } = await api.post<ApiResponse<any>>('/compute/opencode/stop-web', { port });
  return data.data;
}

export async function getOpenCodeWebInstances(): Promise<OpenCodeWebInstance[]> {
  const { data } = await api.get<ApiResponse<OpenCodeWebInstance[]>>('/compute/opencode/web-instances');
  return data.data;
}

export async function runOpenCodeCli(prompt: string, model?: string, timeoutSec: number = 120): Promise<OpenCodeCliRun> {
  const { data } = await api.post<ApiResponse<OpenCodeCliRun>>('/compute/opencode/run-cli', { prompt, model, timeout_sec: timeoutSec });
  return data.data;
}

export async function getOpenCodeRuns(limit: number = 20): Promise<OpenCodeCliRun[]> {
  const { data } = await api.get<ApiResponse<OpenCodeCliRun[]>>('/compute/opencode/runs', { params: { limit } });
  return data.data;
}

export async function getOpenCodeRun(runId: number): Promise<OpenCodeCliRun> {
  const { data } = await api.get<ApiResponse<OpenCodeCliRun>>(`/compute/opencode/runs/${runId}`);
  return data.data;
}
