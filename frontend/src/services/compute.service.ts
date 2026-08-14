/** 算力管理 API 服务 */
import api from './api';
import type {
  ComputeNode,
  ComputeNodeCreate,
  ComputeNodeUpdate,
  ConnectionTestResult,
  ImageInfo,
  ImagePullResponse,
  ContainerInfo,
  ContainerCreateData,
  ContainerLogs,
  ContainerInspectData,
  ContainerUpdateRequest,
  ContainerExecRequest,
  ContainerExecResponse,
  ContainerExecLogsResponse,
  CommandTemplate,
  ContainerPreset,
  ShellDetectResult,
  AideContainerSource,
  ContainerServiceInfo,
  ContainerServiceCreate,
  ServiceRefreshResult,
  ServiceLaunchRequest,
} from '../types/compute';

function toCamelNode(node: Record<string, unknown>): ComputeNode {
  return {
    id: node.id as number,
    name: node.name as string,
    description: node.description as string | undefined,
    host: node.host as string,
    port: node.port as number,
    username: node.username as string,
    authType: node.auth_type as string,
    isLocal: node.is_local as boolean,
    status: node.status as string,
    lastCheckedAt: node.last_checked_at as string | undefined,
    createdAt: node.created_at as string | undefined,
    updatedAt: node.updated_at as string | undefined,
  };
}

// ---- 节点 ----

export async function getLocalNode(): Promise<ComputeNode> {
  const res = await api.get('/compute/nodes/local');
  return toCamelNode(res.data);
}

export async function listNodes(): Promise<ComputeNode[]> {
  const res = await api.get('/compute/nodes');
  return (res.data as Record<string, unknown>[]).map(toCamelNode);
}

export async function getNode(nodeId: number): Promise<ComputeNode> {
  const res = await api.get(`/compute/nodes/${nodeId}`);
  return toCamelNode(res.data);
}

export async function createNode(data: ComputeNodeCreate): Promise<ComputeNode> {
  const res = await api.post('/compute/nodes', data);
  return toCamelNode(res.data);
}

export async function updateNode(
  nodeId: number,
  data: ComputeNodeUpdate,
): Promise<ComputeNode> {
  const res = await api.put(`/compute/nodes/${nodeId}`, data);
  return toCamelNode(res.data);
}

export async function deleteNode(nodeId: number): Promise<void> {
  await api.delete(`/compute/nodes/${nodeId}`);
}

export async function testNodeConnection(
  nodeId: number,
): Promise<ConnectionTestResult> {
  const res = await api.post(`/compute/nodes/${nodeId}/test`);
  return {
    success: res.data.success,
    message: res.data.message,
    nodeId: res.data.node_id,
  };
}

// ---- 镜像 ----

export async function listImages(nodeId: number): Promise<ImageInfo[]> {
  const res = await api.get(`/compute/nodes/${nodeId}/images`);
  return res.data as ImageInfo[];
}

/** 拉取镜像（长耗时，前端需放宽 timeout） */
export async function pullImage(
  nodeId: number,
  image: string,
): Promise<ImagePullResponse> {
  const res = await api.post(
    `/compute/nodes/${nodeId}/images/pull`,
    { image },
    { timeout: 900_000 },
  );
  return res.data as ImagePullResponse;
}

// ---- 容器 ----

export async function listContainers(
  nodeId: number,
  all = false,
): Promise<ContainerInfo[]> {
  const res = await api.get(`/compute/nodes/${nodeId}/containers`, {
    params: { all },
  });
  return res.data as ContainerInfo[];
}

export async function createContainer(
  nodeId: number,
  data: ContainerCreateData,
): Promise<ContainerInfo> {
  // 创建可能触发镜像拉取，需要长 timeout（后端上限 900s）
  const res = await api.post(`/compute/nodes/${nodeId}/containers`, data, {
    timeout: 920_000,
  });
  return res.data as ContainerInfo;
}

export async function startContainer(
  nodeId: number,
  containerId: string,
): Promise<ContainerInfo> {
  const res = await api.post(
    `/compute/nodes/${nodeId}/containers/${containerId}/start`,
  );
  return res.data as ContainerInfo;
}

export async function stopContainer(
  nodeId: number,
  containerId: string,
): Promise<ContainerInfo> {
  const res = await api.post(
    `/compute/nodes/${nodeId}/containers/${containerId}/stop`,
  );
  return res.data as ContainerInfo;
}

export async function restartContainer(
  nodeId: number,
  containerId: string,
): Promise<ContainerInfo> {
  const res = await api.post(
    `/compute/nodes/${nodeId}/containers/${containerId}/restart`,
  );
  return res.data as ContainerInfo;
}

export async function removeContainer(
  nodeId: number,
  containerId: string,
  force = false,
): Promise<void> {
  await api.delete(`/compute/nodes/${nodeId}/containers/${containerId}`, {
    params: { force },
  });
}

export async function getContainerLogs(
  nodeId: number,
  containerId: string,
  tail = 100,
): Promise<ContainerLogs> {
  const res = await api.get(
    `/compute/nodes/${nodeId}/containers/${containerId}/logs`,
    { params: { tail } },
  );
  return res.data as ContainerLogs;
}

export async function inspectContainer(
  nodeId: number,
  containerId: string,
): Promise<ContainerInspectData> {
  const res = await api.get(
    `/compute/nodes/${nodeId}/containers/${containerId}/inspect`,
  );
  return res.data as ContainerInspectData;
}

// ---- 容器修改 ----

export async function updateContainer(
  nodeId: number,
  containerId: string,
  data: ContainerUpdateRequest,
): Promise<ContainerInfo> {
  const res = await api.put(
    `/compute/nodes/${nodeId}/containers/${containerId}`,
    data,
    { timeout: 920_000 },
  );
  return res.data as ContainerInfo;
}

// ---- shell 探测 ----

/** 探测容器内可用 shell，控制台据此自动选择（避免硬编码 /bin/bash 直接失败） */
export async function detectShells(
  nodeId: number,
  containerId: string,
): Promise<ShellDetectResult> {
  const res = await api.get(
    `/compute/nodes/${nodeId}/containers/${containerId}/shells`,
  );
  return res.data as ShellDetectResult;
}

// ---- 容器预设 ----

export async function listContainerPresets(): Promise<ContainerPreset[]> {
  const res = await api.get('/compute/container-presets');
  return res.data as ContainerPreset[];
}

// ---- 快速命令 ----

export async function listCommandTemplates(): Promise<CommandTemplate[]> {
  const res = await api.get('/compute/command-templates');
  return res.data as CommandTemplate[];
}

export async function execContainerCommand(
  nodeId: number,
  containerId: string,
  data: ContainerExecRequest,
): Promise<ContainerExecResponse> {
  const res = await api.post(
    `/compute/nodes/${nodeId}/containers/${containerId}/exec`,
    data,
  );
  return res.data as ContainerExecResponse;
}

export async function getExecLogs(
  nodeId: number,
  containerId: string,
  execId: string,
): Promise<ContainerExecLogsResponse> {
  const res = await api.get(
    `/compute/nodes/${nodeId}/containers/${containerId}/exec/${execId}`,
  );
  return res.data as ContainerExecLogsResponse;
}

// ---- 容器服务登记（container_services） ----

/**
 * 列出已登记的容器服务。
 * @param refresh true 时后端会先回探真实状态再返回（慢但准）
 */
export async function listContainerServices(
  nodeId?: number,
  refresh = false,
): Promise<ContainerServiceInfo[]> {
  const res = await api.get('/compute/services', {
    params: { ...(nodeId ? { node_id: nodeId } : {}), refresh },
    timeout: refresh ? 180_000 : 30_000,
  });
  return res.data as ContainerServiceInfo[];
}

/** 批量回探所有服务状态并写回 DB */
export async function refreshContainerServices(
  nodeId?: number,
): Promise<ServiceRefreshResult> {
  const res = await api.post(
    '/compute/services/refresh',
    {},
    { params: nodeId ? { node_id: nodeId } : {}, timeout: 180_000 },
  );
  return res.data as ServiceRefreshResult;
}

/** 扫描容器，把现实中已在跑但 DB 未登记的服务补录进来 */
export async function discoverContainerServices(
  nodeId?: number,
): Promise<ServiceRefreshResult> {
  const res = await api.post(
    '/compute/services/discover',
    {},
    { params: nodeId ? { node_id: nodeId } : {}, timeout: 240_000 },
  );
  return res.data as ServiceRefreshResult;
}

/** 在容器内一键启动 opencode 服务（强制绑 0.0.0.0）并登记 */
export async function launchContainerService(
  nodeId: number,
  containerId: string,
  data: ServiceLaunchRequest,
): Promise<ContainerServiceInfo> {
  const res = await api.post(
    `/compute/nodes/${nodeId}/containers/${containerId}/services/launch`,
    data,
    { timeout: 180_000 },
  );
  return res.data as ContainerServiceInfo;
}

/** 手工登记一个已在容器内运行的服务 */
export async function registerContainerService(
  nodeId: number,
  containerId: string,
  data: ContainerServiceCreate,
): Promise<ContainerServiceInfo> {
  const res = await api.post(
    `/compute/nodes/${nodeId}/containers/${containerId}/services`,
    data,
    { timeout: 60_000 },
  );
  return res.data as ContainerServiceInfo;
}

/** 回探单个服务 */
export async function refreshContainerService(
  serviceId: number,
): Promise<ContainerServiceInfo> {
  const res = await api.post(`/compute/services/${serviceId}/refresh`, {}, {
    timeout: 60_000,
  });
  return res.data as ContainerServiceInfo;
}

/** 停掉容器内该服务进程（保留登记） */
export async function stopContainerService(
  serviceId: number,
): Promise<ContainerServiceInfo> {
  const res = await api.post(`/compute/services/${serviceId}/stop`, {}, {
    timeout: 90_000,
  });
  return res.data as ContainerServiceInfo;
}

/** 删除服务登记（不影响容器内进程） */
export async function deleteContainerService(serviceId: number): Promise<void> {
  await api.delete(`/compute/services/${serviceId}`);
}

// ---- AIDE 容器源 ----

export async function listAideSources(
  nodeId?: number,
  refresh = false,
): Promise<AideContainerSource[]> {
  const res = await api.get('/compute/aide-sources', {
    params: { ...(nodeId ? { node_id: nodeId } : {}), refresh },
    timeout: refresh ? 180_000 : 30_000,
  });
  return res.data as AideContainerSource[];
}

/** 构建容器终端的 WebSocket URL */
export function getContainerConsoleUrl(
  nodeId: number,
  containerId: string,
  cmd = '/bin/bash',
): string {
  const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
  return (
    base.replace(/^http/, 'ws') +
    `/compute/nodes/${nodeId}/containers/${containerId}/console` +
    `?cmd=${encodeURIComponent(cmd)}`
  );
}

/** 命名空间导出，方便 import * as computeService 使用 */
export const computeService = {
  getLocalNode,
  listNodes,
  getNode,
  createNode,
  updateNode,
  deleteNode,
  testNodeConnection,
  listImages,
  pullImage,
  listContainers,
  createContainer,
  startContainer,
  stopContainer,
  restartContainer,
  removeContainer,
  getContainerLogs,
  inspectContainer,
  updateContainer,
  detectShells,
  listContainerPresets,
  listCommandTemplates,
  execContainerCommand,
  getExecLogs,
  listAideSources,
  listContainerServices,
  refreshContainerServices,
  discoverContainerServices,
  launchContainerService,
  registerContainerService,
  refreshContainerService,
  stopContainerService,
  deleteContainerService,
  consoleUrl: getContainerConsoleUrl,
};
