/**
 * OpenCode server client — 直接封 fetch 调 opencode HTTP API.
 *
 * 为什么不直接用 `@opencode-ai/sdk`：
 * 1) SDK 就是 openapi 生成的 fetch wrapper，本模块 100% 与之等价；
 * 2) 避免生产构建依赖 opencode 私有包链路；
 * 3) 类型定义放在 ./types.ts，跟 SDK 的 `types.gen.ts` 语义一致。
 *
 * 想切回 SDK：把本文件里 `oc.*` 函数改成 SDK 的 `client.session.*` 即可，签名匹配。
 */
import type {
  OcAgent,
  OcCommand,
  OcConfig,
  OcHealth,
  OcMcpStatusMap,
  OcMessagesEnvelope,
  OcPermissionResponse,
  OcPromptBody,
  OcSession,
} from './types';

const DEFAULT_URL: string =
  (import.meta as unknown as { env?: Record<string, string> }).env
    ?.VITE_OPENCODE_URL || 'http://127.0.0.1:4096';

const LOCAL_OVERRIDE_KEY = 'ontomind_opencode_url';

export function opencodeBaseUrl(): string {
  try {
    const override = localStorage.getItem(LOCAL_OVERRIDE_KEY);
    if (override) return override;
  } catch { /* SSR */ }
  return DEFAULT_URL;
}

/** 内部：普通 JSON fetch，抛错时带上后端消息。 */
async function req<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const url = `${opencodeBaseUrl()}${path}`;
  const resp = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers || {}),
    },
  });
  if (!resp.ok) {
    let msg = `${resp.status} ${resp.statusText}`;
    try {
      const j = await resp.json();
      if (j?.error?.message) msg = j.error.message;
    } catch {
      /* ignore */
    }
    throw new Error(`opencode ${init.method || 'GET'} ${path}: ${msg}`);
  }
  if (resp.status === 204) return undefined as unknown as T;
  return (await resp.json()) as T;
}

// ============================================================
// Global
// ============================================================
export function health(): Promise<OcHealth> {
  return req<OcHealth>('/global/health');
}

// ============================================================
// Sessions
// ============================================================
export function listSessions(): Promise<OcSession[]> {
  return req<OcSession[]>('/session');
}

export function createSession(body: { title?: string; parentID?: string } = {}) {
  return req<OcSession>('/session', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function getSession(id: string) {
  return req<OcSession>(`/session/${encodeURIComponent(id)}`);
}

export function deleteSession(id: string) {
  return req<boolean>(`/session/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
}

export function updateSession(id: string, body: { title?: string }) {
  return req<OcSession>(`/session/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
}

export function abortSession(id: string) {
  return req<boolean>(`/session/${encodeURIComponent(id)}/abort`, {
    method: 'POST',
  });
}

export function revertMessage(id: string, messageID: string, partID?: string) {
  return req<boolean>(`/session/${encodeURIComponent(id)}/revert`, {
    method: 'POST',
    body: JSON.stringify({ messageID, partID }),
  });
}

export function unrevertSession(id: string) {
  return req<boolean>(`/session/${encodeURIComponent(id)}/unrevert`, {
    method: 'POST',
  });
}

// ============================================================
// Messages
// ============================================================
export function listMessages(
  id: string,
  limit?: number,
): Promise<OcMessagesEnvelope[]> {
  const q = limit ? `?limit=${limit}` : '';
  return req<OcMessagesEnvelope[]>(
    `/session/${encodeURIComponent(id)}/message${q}`,
  );
}

/** 阻塞式发送消息，返回最终 assistant message. */
export function sendPrompt(id: string, body: OcPromptBody) {
  return req<OcMessagesEnvelope>(`/session/${encodeURIComponent(id)}/message`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/** 非阻塞发送（204 No Content），后续靠 SSE 收 delta. */
export async function sendPromptAsync(id: string, body: OcPromptBody) {
  const url = `${opencodeBaseUrl()}/session/${encodeURIComponent(id)}/prompt_async`;
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!resp.ok && resp.status !== 204) {
    throw new Error(`opencode POST prompt_async: ${resp.status}`);
  }
}

// ============================================================
// Permissions
// ============================================================
export function respondPermission(
  sessionId: string,
  permissionID: string,
  response: OcPermissionResponse,
  remember: boolean = false,
) {
  return req<boolean>(
    `/session/${encodeURIComponent(sessionId)}/permissions/${encodeURIComponent(permissionID)}`,
    {
      method: 'POST',
      body: JSON.stringify({ response, remember }),
    },
  );
}

// ============================================================
// Files / Search
// ============================================================
export function findFiles(query: string, opts: {
  type?: 'file' | 'directory';
  limit?: number;
} = {}) {
  const params = new URLSearchParams({ query });
  if (opts.type) params.set('type', opts.type);
  if (opts.limit) params.set('limit', String(opts.limit));
  return req<string[]>(`/find/file?${params.toString()}`);
}

export function readFile(path: string) {
  return req<{ type: string; content: string }>(
    `/file/content?path=${encodeURIComponent(path)}`,
  );
}

// ============================================================
// Config / Provider / Agents / Commands / MCP
// ============================================================
export function getConfig(): Promise<OcConfig> {
  return req<OcConfig>('/config');
}

export function patchConfig(patch: Partial<OcConfig> & Record<string, unknown>) {
  return req<OcConfig>('/config', {
    method: 'PATCH',
    body: JSON.stringify(patch),
  });
}

export function listProviders() {
  return req<{
    providers: {
      id: string;
      name: string;
      models: Record<string, { id?: string; name?: string; family?: string; providerID?: string }>;
    }[];
    default: Record<string, string>;
  }>('/config/providers');
}

export function listAgents(): Promise<OcAgent[]> {
  return req<OcAgent[]>('/agent');
}

export function listCommands(): Promise<OcCommand[]> {
  return req<OcCommand[]>('/command');
}

export function mcpStatus(): Promise<OcMcpStatusMap> {
  return req<OcMcpStatusMap>('/mcp');
}

// ============================================================
// SSE Event Stream
// ============================================================
/**
 * 订阅 opencode 全局事件流 (Server-Sent Events).
 * 用法：
 *   const es = subscribeEvents((evt) => { ... });
 *   // ... es.close();
 */
export function subscribeEvents(
  onEvent: (evt: OcEvent) => void,
  onError?: (err: Event) => void,
): EventSource {
  const es = new EventSource(`${opencodeBaseUrl()}/event`);
  es.onmessage = (msg) => {
    try {
      const parsed = JSON.parse(msg.data) as OcEvent;
      onEvent(parsed);
    } catch (err) {
      // 忽略非 JSON 心跳
      // eslint-disable-next-line no-console
      console.warn('[opencode] bad SSE payload', err);
    }
  };
  if (onError) es.onerror = onError;
  return es;
}

// 复用 event 类型
import type { OcEvent } from './types';
