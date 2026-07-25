import api from './api';
import type {
  AgentStudioConfig,
  AgentSummary,
  ComputeNode,
  DiscoveryDecision,
  DiscoveryItem,
  NodeInventory,
} from '../pages/agent-platform/types';

const ROOT = '/agent-platform';
type Raw = Record<string, unknown>;

interface Envelope<T> {
  code?: string;
  message?: string;
  data: T;
}

function unwrap<T>(resp: { data: T | Envelope<T> }): T {
  const body = resp.data as Envelope<T>;
  if (body && typeof body === 'object' && 'data' in body) {
    if (body.code && body.code !== 'SUCCESS') throw new Error(body.message || '请求失败');
    return body.data;
  }
  return resp.data as T;
}

// ── shared payload / view models ────────────────────────────
export interface AgentVersion {
  id: number;
  agent_id: number;
  version_number: number;
  config: AgentStudioConfig;
  config_hash: string;
  note: string | null;
  created_by_user_id: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface AgentCreatePayload {
  name: string;
  type: string;
  description?: string | null;
  config: AgentStudioConfig;
  version_note?: string | null;
}

export interface AgentCreateResult extends AgentSummary {
  latest_version: AgentVersion;
}

export interface NodeConnectionCreatePayload {
  connector_type: 'local' | 'ssh';
  address?: string | null;
  port?: number | null;
  username?: string | null;
  password?: string | null;
  private_key?: string | null;
  host_key_algorithm?: string | null;
  host_key_fingerprint?: string | null;
  managed_roots: string[];
  connect_timeout_seconds?: number;
  command_timeout_seconds?: number;
  max_concurrency?: number;
}

export interface NodeCreatePayload {
  name: string;
  hostname?: string | null;
  platform?: string | null;
  labels?: Record<string, unknown> | null;
  connection: NodeConnectionCreatePayload;
}

export interface DiscoveryRun {
  id: number;
  node_id: number;
  provider_type: string;
  status: string;
  summary: Record<string, unknown> | null;
  error_code: string | null;
  error_message: string | null;
}

// ── service ─────────────────────────────────────────────────
export const agentPlatformService = {
  // Agents
  getAgent: (id: number) => api.get<Raw>(`${ROOT}/agents/${id}`).then((r) => unwrap<AgentSummary>(r as unknown as { data: Envelope<AgentSummary> })),
  listAgents: () =>
    api.get(`${ROOT}/agents`).then((r) => unwrap<AgentSummary[]>(r as unknown as { data: Envelope<AgentSummary[]> })),
  createAgent: (data: AgentCreatePayload) =>
    api.post(`${ROOT}/agents`, data).then((r) => unwrap<AgentCreateResult>(r as unknown as { data: Envelope<AgentCreateResult> })),
  createAgentVersion: (agentId: number, data: { config: AgentStudioConfig; note?: string | null }) =>
    api.post(`${ROOT}/agents/${agentId}/versions`, data).then((r) => unwrap<AgentVersion>(r as unknown as { data: Envelope<AgentVersion> })),
  listAgentVersions: (agentId: number) =>
    api.get(`${ROOT}/agents/${agentId}/versions`).then((r) => unwrap<AgentVersion[]>(r as unknown as { data: Envelope<AgentVersion[]> })),
  publishAgentVersion: (agentId: number, versionId: number) =>
    api.post(`${ROOT}/agents/${agentId}/versions/${versionId}/publish`).then((r) => unwrap<AgentVersion>(r as unknown as { data: Envelope<AgentVersion> })),

  // Nodes
  listNodes: () =>
    api.get(`${ROOT}/nodes`).then((r) => unwrap<ComputeNode[]>(r as unknown as { data: Envelope<ComputeNode[]> })),
  getNodeInventory: (nodeId: number, refresh?: boolean) =>
    api.get(`${ROOT}/nodes/${nodeId}/inventory`, { params: { refresh } }).then((r) => unwrap<NodeInventory>(r as unknown as { data: Envelope<NodeInventory> })),
  createNode: (data: NodeCreatePayload) =>
    api.post(`${ROOT}/nodes`, data).then((r) => unwrap<ComputeNode>(r as unknown as { data: Envelope<ComputeNode> })),
  registerLocalNode: () =>
    api.post(`${ROOT}/nodes/register-local`).then((r) => unwrap<ComputeNode>(r as unknown as { data: Envelope<ComputeNode> })),

  // Discovery
  startDiscovery: (nodeId: number) =>
    api.post(`${ROOT}/discoveries`, { node_id: nodeId }).then((r) => unwrap<DiscoveryRun>(r as unknown as { data: Envelope<DiscoveryRun> })),
  listDiscoveryItems: (runId: number) =>
    api.get(`${ROOT}/discoveries/${runId}/items`).then((r) => unwrap<DiscoveryItem[]>(r as unknown as { data: Envelope<DiscoveryItem[]> })),
  decideDiscoveryItem: (itemId: number, decision: DiscoveryDecision) =>
    api.post(`${ROOT}/discovery-items/${itemId}/decide`, { decision }).then((r) => unwrap<DiscoveryItem>(r as unknown as { data: Envelope<DiscoveryItem> })),
  applyDiscovery: (discoveryId: number, importIds: number[]) =>
    api.post(`${ROOT}/discoveries/${discoveryId}/apply`, { import_ids: importIds }).then((r) => unwrap<{ imported: number }>(r as unknown as { data: Envelope<{ imported: number }> })),
};

export default agentPlatformService;