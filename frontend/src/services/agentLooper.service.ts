/**
 * Agent Looper API service (Wave 9 W2 T34-T38).
 *
 * Follows the dataPlatform.service.ts / knowledgeBase.service.ts pattern:
 *   - axios via `./api`
 *   - envelope unwrap (expects code === 'SUCCESS')
 *   - explicit snake_case -> typed shape mappers
 *
 * Backend endpoints (planned in T34-T37; may not be merged yet):
 *   GET    /agent-looper/configs
 *   POST   /agent-looper/configs
 *   GET    /agent-looper/configs/{id}
 *   PUT    /agent-looper/configs/{id}
 *   DELETE /agent-looper/configs/{id}
 *   GET    /agent-looper/configs/{id}/versions
 *   POST   /agent-looper/configs/{id}/rollback
 *   POST   /agent-looper/configs/{id}/publish
 *   POST   /agent-looper/configs/{id}/test
 *   POST   /agent-looper/discover
 */

import api from './api';
import type {
  AgentLooperConfig,
  AgentLooperConfigRead,
  AgentLooperListEntry,
  AgentLooperType,
  AgentLooperVersionRead,
  AgentLooperTestRunResult,
  LoopStrategy,
} from '../types/agentLooper';

interface Envelope<T> {
  code: string;
  message: string;
  data: T;
  total?: number;
}

function unwrap<T>(res: { data: Envelope<T> }): T {
  if (res.data?.code !== 'SUCCESS') {
    throw new Error(res.data?.message ?? 'API error');
  }
  return res.data.data;
}

// -- mappers ----------------------------------------------------

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapListEntry(raw: any): AgentLooperListEntry {
  const cfg = raw.active_config_json ?? {};
  return {
    id: raw.id,
    name: raw.name,
    type: raw.type as AgentLooperType,
    description: raw.description ?? null,
    is_active: !!raw.is_active,
    is_published: !!raw.is_published,
    model: cfg.model ?? '',
    loop_strategy: (cfg.loop_strategy ?? 'react') as LoopStrategy,
    updated_at: raw.updated_at ?? null,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapDetail(raw: any): AgentLooperConfigRead {
  return {
    id: raw.id,
    name: raw.name,
    type: raw.type as AgentLooperType,
    description: raw.description ?? null,
    current_version_id: raw.current_version_id ?? null,
    active_config_json: raw.active_config_json ?? null,
    owner_user_id: raw.owner_user_id,
    is_active: !!raw.is_active,
    is_published: !!raw.is_published,
    settings: raw.settings ?? null,
    resource_bindings: raw.resource_bindings ?? null,
    credential_ref: raw.credential_ref ?? null,
    created_at: raw.created_at ?? null,
    updated_at: raw.updated_at ?? null,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapVersion(raw: any): AgentLooperVersionRead {
  return {
    id: raw.id,
    config_id: raw.config_id,
    version_number: raw.version_number,
    config_json: raw.config_json,
    model_snapshot: raw.model_snapshot ?? null,
    prompt_snapshot: raw.prompt_snapshot ?? null,
    note: raw.note ?? null,
    created_by_user_id: raw.created_by_user_id,
    created_at: raw.created_at ?? null,
  };
}

// -- payload types ---------------------------------------------

export interface AgentLooperCreatePayload {
  name: string;
  type?: AgentLooperType;
  description?: string | null;
  config_json: AgentLooperConfig;
  is_active?: boolean;
}

export interface AgentLooperUpdatePayload {
  name?: string;
  description?: string | null;
  config_json?: AgentLooperConfig;
  is_active?: boolean;
  note?: string | null;
}

// -- service ---------------------------------------------------

export const agentLooperService = {
  async list(): Promise<AgentLooperListEntry[]> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const raw = unwrap<any[]>(await api.get('/agent-looper/configs'));
    return (raw ?? []).map(mapListEntry);
  },

  async getById(id: number): Promise<AgentLooperConfigRead> {
    return mapDetail(unwrap(await api.get(`/agent-looper/configs/${id}`)));
  },

  async create(payload: AgentLooperCreatePayload): Promise<AgentLooperConfigRead> {
    return mapDetail(unwrap(await api.post('/agent-looper/configs', payload)));
  },

  async update(
    id: number,
    payload: AgentLooperUpdatePayload,
  ): Promise<AgentLooperConfigRead> {
    return mapDetail(unwrap(await api.put(`/agent-looper/configs/${id}`, payload)));
  },

  async delete(id: number): Promise<void> {
    unwrap(await api.delete(`/agent-looper/configs/${id}`));
  },

  async getVersions(id: number): Promise<AgentLooperVersionRead[]> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const raw = unwrap<any[]>(await api.get(`/agent-looper/configs/${id}/versions`));
    return (raw ?? []).map(mapVersion);
  },

  async rollback(id: number, versionNumber: number): Promise<AgentLooperConfigRead> {
    return mapDetail(
      unwrap(
        await api.post(`/agent-looper/configs/${id}/rollback`, {
          target_version_number: versionNumber,
        }),
      ),
    );
  },

  async publish(id: number): Promise<{ path: string }> {
    return unwrap<{ path: string }>(
      await api.post(`/agent-looper/configs/${id}/publish`),
    );
  },

  async test(id: number, prompt: string): Promise<AgentLooperTestRunResult> {
    return unwrap<AgentLooperTestRunResult>(
      await api.post(`/agent-looper/configs/${id}/test`, { prompt }),
    );
  },

  async discover(): Promise<{ upserted_count: number }> {
    return unwrap<{ upserted_count: number }>(
      await api.post('/agent-looper/discover'),
    );
  },
};

export default agentLooperService;
