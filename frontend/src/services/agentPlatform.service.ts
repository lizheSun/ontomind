import api from './api';
import type {
  AgentRun,
  AgentSession,
  AgentStudioConfig,
  AgentSummary,
  ComputeNode,
  DiscoveryDecision,
  DiscoveryItem,
  NodeInventory,
  RunStatus,
} from '../pages/agent-platform/types';

const ROOT = '/agent-platform';
type Raw = Record<string, unknown>;

interface Envelope<T> {
  code?: string;
  message?: string;
  data: T;
}

export function unwrapAgentPlatformResponse<T>(response: { data: T | Envelope<T> }): T {
  const body = response.data as Envelope<T>;
  if (body && typeof body === 'object' && 'data' in body) {
    if (body.code && body.code !== 'SUCCESS') {
      throw new Error(body.message || 'Agent Platform API 请求失败');
    }
    return body.data;
  }
  return response.data as T;
}

const number = (value: unknown): number => Number(value);
const nullableNumber = (value: unknown): number | null =>
  value == null ? null : Number(value);
const string = (value: unknown): string => String(value ?? '');
const nullableString = (value: unknown): string | null =>
  value == null ? null : String(value);
const object = (value: unknown): Record<string, unknown> =>
  value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};

export function mapAgentRow(raw: Raw): AgentSummary {
  return {
    id: number(raw.id),
    name: string(raw.name),
    type: string(raw.type),
    description: nullableString(raw.description),
    is_active: Boolean(raw.is_active),
    is_published: Boolean(raw.is_published),
    version: number(raw.version),
    current_version_id: nullableNumber(raw.current_version_id),
    owner_user_id: nullableNumber(raw.owner_user_id),
    created_at: nullableString(raw.created_at),
    updated_at: nullableString(raw.updated_at),
  };
}

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

export function mapAgentVersionRow(raw: Raw): AgentVersion {
  return {
    id: number(raw.id),
    agent_id: number(raw.agent_id),
    version_number: number(raw.version_number),
    config: object(raw.config) as unknown as AgentStudioConfig,
    config_hash: string(raw.config_hash),
    note: nullableString(raw.note),
    created_by_user_id: nullableNumber(raw.created_by_user_id),
    created_at: nullableString(raw.created_at),
    updated_at: nullableString(raw.updated_at),
  };
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

export function mapAgentCreateRow(raw: Raw): AgentCreateResult {
  return {
    ...mapAgentRow(raw),
    latest_version: mapAgentVersionRow(object(raw.latest_version)),
  };
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

export function mapNodeRow(raw: Raw): ComputeNode {
  const connection = object(raw.connection);
  return {
    id: number(raw.id),
    name: string(raw.name),
    hostname: nullableString(raw.hostname),
    platform: nullableString(raw.platform),
    platform_raw: nullableString(raw.platform_raw),
    ip: nullableString(raw.ip),
    status: string(raw.status),
    labels: raw.labels == null ? null : object(raw.labels),
    connection: {
      id: number(connection.id),
      connector_type: connection.connector_type === 'ssh' ? 'ssh' : 'local',
      address: nullableString(connection.address),
      port: nullableNumber(connection.port),
      username: nullableString(connection.username),
      host_key_algorithm: nullableString(connection.host_key_algorithm),
      host_key_fingerprint: nullableString(connection.host_key_fingerprint),
      managed_roots: Array.isArray(connection.managed_roots)
        ? connection.managed_roots.map(String)
        : [],
      enabled: Boolean(connection.enabled),
      has_credential: Boolean(connection.has_credential),
    },
    created_at: nullableString(raw.created_at),
    updated_at: nullableString(raw.updated_at),
  };
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

export function mapDiscoveryRunRow(raw: Raw): DiscoveryRun {
  return {
    id: number(raw.id),
    node_id: number(raw.node_id),
    provider_type: string(raw.provider_type),
    status: string(raw.status),
    summary: raw.summary == null ? null : object(raw.summary),
    error_code: nullableString(raw.error_code),
    error_message: nullableString(raw.error_message),
  };
}

export function mapDiscoveryItemRow(raw: Raw): DiscoveryItem {
  return {
    id: number(raw.id),
    discovery_run_id: number(raw.discovery_run_id),
    resource_type: raw.resource_type as DiscoveryItem['resource_type'],
    external_key: string(raw.external_key),
    source_path: nullableString(raw.source_path),
    status: raw.status as DiscoveryItem['status'],
    decision: raw.decision as DiscoveryDecision,
    diff: raw.diff,
    platform_resource_id: nullableNumber(raw.platform_resource_id),
    remote_snapshot: object(raw.remote_snapshot),
    platform_snapshot: raw.platform_snapshot == null ? null : object(raw.platform_snapshot),
  };
}

export interface Deployment {
  id: number;
  agent_id: number;
  agent_version_id: number;
  environment: string;
  status: 'draft' | 'deploying' | 'active' | 'failed' | 'stopped';
  runtime_config: Record<string, unknown>;
  status_version: number;
  deployed_at: string | null;
  stopped_at: string | null;
  created_by_user_id: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export function mapDeploymentRow(raw: Raw): Deployment {
  return {
    id: number(raw.id),
    agent_id: number(raw.agent_id),
    agent_version_id: number(raw.agent_version_id),
    environment: string(raw.environment),
    status: raw.status as Deployment['status'],
    runtime_config: object(raw.runtime_config),
    status_version: number(raw.status_version),
    deployed_at: nullableString(raw.deployed_at),
    stopped_at: nullableString(raw.stopped_at),
    created_by_user_id: nullableNumber(raw.created_by_user_id),
    created_at: nullableString(raw.created_at),
    updated_at: nullableString(raw.updated_at),
  };
}

export interface AgentMessage {
  id: number;
  session_id: number;
  sequence: number;
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  message_metadata: Record<string, unknown>;
  created_at: string | null;
}

export interface AgentSessionDetail extends AgentSession {
  messages: AgentMessage[];
}

export function mapSessionRow(raw: Raw): AgentSession {
  return {
    id: number(raw.id),
    agent_id: number(raw.agent_id),
    deployment_id: nullableNumber(raw.deployment_id),
    owner_user_id: nullableNumber(raw.owner_user_id),
    title: nullableString(raw.title),
    status: string(raw.status),
    session_metadata: object(raw.session_metadata),
    created_at: nullableString(raw.created_at),
    updated_at: nullableString(raw.updated_at),
  };
}

export function mapMessageRow(raw: Raw): AgentMessage {
  return {
    id: number(raw.id),
    session_id: number(raw.session_id),
    sequence: number(raw.sequence),
    role: raw.role as AgentMessage['role'],
    content: string(raw.content),
    message_metadata: object(raw.message_metadata),
    created_at: nullableString(raw.created_at),
  };
}

export function mapRunRow(raw: Raw): AgentRun {
  return {
    id: number(raw.id),
    agent_id: nullableNumber(raw.agent_id),
    agent_version_id: nullableNumber(raw.agent_version_id),
    deployment_id: nullableNumber(raw.deployment_id),
    session_id: nullableNumber(raw.session_id),
    run_name: string(raw.run_name),
    status: raw.status as RunStatus,
    strategy: raw.strategy as AgentRun['strategy'],
    input: raw.input == null ? null : object(raw.input),
    output: raw.output == null ? null : object(raw.output),
    state_version: number(raw.state_version),
    started_at: nullableString(raw.started_at),
    completed_at: nullableString(raw.completed_at),
    error_message: nullableString(raw.error_message),
    created_at: nullableString(raw.created_at),
    updated_at: nullableString(raw.updated_at),
  };
}

export interface Approval {
  id: number;
  run_id: number;
  status: string;
  lock_version: number;
  tool_name: string;
}

export const agentPlatformService = {
  async listAgents(): Promise<AgentSummary[]> {
    const rows = unwrapAgentPlatformResponse<Raw[]>(await api.get(`${ROOT}/agents`));
    return rows.map(mapAgentRow);
  },
  async getAgent(agentId: number): Promise<AgentSummary> {
    return mapAgentRow(
      unwrapAgentPlatformResponse<Raw>(await api.get(`${ROOT}/agents/${agentId}`)),
    );
  },
  async createAgent(payload: AgentCreatePayload): Promise<AgentCreateResult> {
    return mapAgentCreateRow(
      unwrapAgentPlatformResponse<Raw>(await api.post(`${ROOT}/agents`, payload)),
    );
  },
  async listAgentVersions(agentId: number): Promise<AgentVersion[]> {
    const rows = unwrapAgentPlatformResponse<Raw[]>(
      await api.get(`${ROOT}/agents/${agentId}/versions`),
    );
    return rows.map(mapAgentVersionRow);
  },
  async createAgentVersion(
    agentId: number,
    payload: { config: AgentStudioConfig; note?: string | null },
  ): Promise<AgentVersion> {
    return mapAgentVersionRow(
      unwrapAgentPlatformResponse<Raw>(
        await api.post(`${ROOT}/agents/${agentId}/versions`, payload),
      ),
    );
  },
  async publishAgentVersion(agentId: number, versionId: number): Promise<AgentVersion> {
    return mapAgentVersionRow(
      unwrapAgentPlatformResponse<Raw>(
        await api.post(`${ROOT}/agents/${agentId}/versions/${versionId}/publish`),
      ),
    );
  },

  async listSessions(): Promise<AgentSession[]> {
    const rows = unwrapAgentPlatformResponse<Raw[]>(await api.get(`${ROOT}/sessions`));
    return rows.map(mapSessionRow);
  },
  async createSession(payload: {
    agent_id: number;
    deployment_id?: number | null;
    title?: string;
    metadata?: Record<string, unknown>;
  }): Promise<AgentSession> {
    return mapSessionRow(
      unwrapAgentPlatformResponse<Raw>(
        await api.post(`${ROOT}/sessions`, { metadata: {}, ...payload }),
      ),
    );
  },
  async getSession(sessionId: number): Promise<AgentSessionDetail> {
    const raw = unwrapAgentPlatformResponse<Raw>(
      await api.get(`${ROOT}/sessions/${sessionId}`),
    );
    return {
      ...mapSessionRow(raw),
      messages: Array.isArray(raw.messages)
        ? raw.messages.map((row) => mapMessageRow(object(row)))
        : [],
    };
  },
  async sendMessage(
    sessionId: number,
    content: string,
  ): Promise<{ message_id: number; run_id: number; message: AgentMessage; run: AgentRun }> {
    const raw = unwrapAgentPlatformResponse<Raw>(
      await api.post(
        `${ROOT}/sessions/${sessionId}/messages`,
        {
          role: 'user',
          content,
          metadata: {},
        },
        // OpenCode CLI 可能需要较长时间
        { timeout: 180000 },
      ),
    );
    return {
      message_id: number(raw.message_id),
      run_id: number(raw.run_id),
      message: mapMessageRow(object(raw.message)),
      run: mapRunRow(object(raw.run)),
    };
  },
  /** @deprecated 使用 sendMessage，会自动创建并执行 Run */
  async addMessage(sessionId: number, content: string): Promise<AgentMessage> {
    const result = await this.sendMessage(sessionId, content);
    return result.message;
  },

  async createRun(payload: {
    agent_version_id: number;
    deployment_id?: number | null;
    session_id?: number | null;
    strategy?: 'single_shot' | 'evaluator_optimizer';
    input: Record<string, unknown>;
  }): Promise<AgentRun> {
    return mapRunRow(
      unwrapAgentPlatformResponse<Raw>(
        await api.post(`${ROOT}/runs`, { strategy: 'single_shot', ...payload }),
      ),
    );
  },
  async listRuns(): Promise<AgentRun[]> {
    const rows = unwrapAgentPlatformResponse<Raw[]>(await api.get(`${ROOT}/runs`));
    return rows.map(mapRunRow);
  },
  async getRun(runId: number): Promise<AgentRun> {
    return mapRunRow(
      unwrapAgentPlatformResponse<Raw>(await api.get(`${ROOT}/runs/${runId}`)),
    );
  },
  async controlRun(runId: number, action: 'start' | 'cancel'): Promise<AgentRun> {
    return mapRunRow(
      unwrapAgentPlatformResponse<Raw>(
        await api.post(`${ROOT}/runs/${runId}/control`, { action }),
      ),
    );
  },
  async getApproval(approvalId: number): Promise<Approval> {
    const raw = unwrapAgentPlatformResponse<Raw>(
      await api.get(`${ROOT}/approvals/${approvalId}`),
    );
    return {
      id: number(raw.id),
      run_id: number(raw.run_id),
      status: string(raw.status),
      lock_version: number(raw.lock_version),
      tool_name: string(raw.tool_name),
    };
  },
  async decideApproval(
    approvalId: number,
    decision: 'approve' | 'reject',
    expectedVersion: number,
    reason?: string,
  ): Promise<Approval> {
    const raw = unwrapAgentPlatformResponse<Raw>(
      await api.post(`${ROOT}/approvals/${approvalId}/decision`, {
        decision,
        expected_version: expectedVersion,
        reason,
      }),
    );
    return {
      id: number(raw.id),
      run_id: number(raw.run_id),
      status: string(raw.status),
      lock_version: number(raw.lock_version),
      tool_name: string(raw.tool_name),
    };
  },

  async listNodes(): Promise<ComputeNode[]> {
    const rows = unwrapAgentPlatformResponse<Raw[]>(await api.get(`${ROOT}/nodes`));
    return rows.map(mapNodeRow);
  },
  async registerLocalNode(): Promise<ComputeNode> {
    return mapNodeRow(
      unwrapAgentPlatformResponse<Raw>(await api.post(`${ROOT}/nodes/register-local`)),
    );
  },
  async getNodeInventory(nodeId: number, refresh = false): Promise<NodeInventory> {
    return unwrapAgentPlatformResponse<NodeInventory>(
      await api.get(`${ROOT}/nodes/${nodeId}/inventory`, { params: { refresh } }),
    );
  },
  async createNode(payload: NodeCreatePayload): Promise<ComputeNode> {
    return mapNodeRow(
      unwrapAgentPlatformResponse<Raw>(await api.post(`${ROOT}/nodes`, payload)),
    );
  },
  async testNodeConnection(nodeId: number): Promise<Record<string, unknown>> {
    return unwrapAgentPlatformResponse(
      await api.post(`${ROOT}/nodes/${nodeId}/connection-tests`),
    );
  },
  async startDiscovery(nodeId: number): Promise<DiscoveryRun> {
    return mapDiscoveryRunRow(
      unwrapAgentPlatformResponse<Raw>(
        await api.post(`${ROOT}/nodes/${nodeId}/discoveries`, {
          provider_type: 'opencode',
        }),
      ),
    );
  },
  async getDiscovery(discoveryId: number): Promise<DiscoveryRun> {
    return mapDiscoveryRunRow(
      unwrapAgentPlatformResponse<Raw>(
        await api.get(`${ROOT}/discoveries/${discoveryId}`),
      ),
    );
  },
  async listDiscoveryItems(discoveryId: number): Promise<DiscoveryItem[]> {
    const rows = unwrapAgentPlatformResponse<Raw[]>(
      await api.get(`${ROOT}/discoveries/${discoveryId}/items`),
    );
    return rows.map(mapDiscoveryItemRow);
  },
  async decideDiscoveryItem(
    discoveryId: number,
    itemId: number,
    decision: Exclude<DiscoveryDecision, 'pending'>,
  ): Promise<DiscoveryItem> {
    return mapDiscoveryItemRow(
      unwrapAgentPlatformResponse<Raw>(
        await api.post(`${ROOT}/discoveries/${discoveryId}/items/${itemId}/decisions`, {
          decision,
        }),
      ),
    );
  },
  async applyDiscovery(discoveryId: number, itemIds?: number[]) {
    return unwrapAgentPlatformResponse<{
      run_id: number;
      applied: Array<{ item_id: number; resource_id: number }>;
      skipped: number;
    }>(
      await api.post(`${ROOT}/discoveries/${discoveryId}/apply`, {
        item_ids: itemIds ?? null,
      }),
    );
  },

  async listDeployments(agentId?: number): Promise<Deployment[]> {
    const rows = unwrapAgentPlatformResponse<Raw[]>(
      await api.get(`${ROOT}/deployments`, { params: { agent_id: agentId } }),
    );
    return rows.map(mapDeploymentRow);
  },
  async createDeployment(payload: {
    agent_version_id: number;
    environment: string;
    runtime_config: Record<string, unknown>;
  }): Promise<Deployment> {
    return mapDeploymentRow(
      unwrapAgentPlatformResponse<Raw>(
        await api.post(`${ROOT}/deployments`, payload),
      ),
    );
  },
  async transitionDeployment(
    deploymentId: number,
    action: 'start' | 'activate' | 'fail' | 'stop',
    expectedVersion?: number,
  ): Promise<Deployment> {
    return mapDeploymentRow(
      unwrapAgentPlatformResponse<Raw>(
        await api.post(`${ROOT}/deployments/${deploymentId}/transition`, {
          action,
          expected_version: expectedVersion,
        }),
      ),
    );
  },
};

export function agentPlatformEventsUrl(runId: number): string {
  const configured = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
  return `${configured.replace(/\/$/, '')}${ROOT}/runs/${runId}/events`;
}

export default agentPlatformService;
