import api from './api';
import type {
  HarnessMessage,
  HarnessPlugin,
  HarnessSession,
  PluginId,
  StreamChunk,
  UploadedFile,
  WorkspaceList,
} from '../types/harness';

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function readError(res: Response, fallback: string): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: { message?: string }; message?: string };
    return body.detail?.message || body.message || fallback;
  } catch {
    return fallback;
  }
}

export const harnessService = {
  async listPlugins(): Promise<HarnessPlugin[]> {
    const res = await api.get('/harness/plugins');
    return Array.isArray(res.data) ? (res.data as HarnessPlugin[]) : [];
  },

  async listSessions(): Promise<HarnessSession[]> {
    const res = await api.get('/harness/sessions');
    return Array.isArray(res.data) ? (res.data as HarnessSession[]) : [];
  },

  async getSession(id: number): Promise<HarnessSession> {
    const res = await api.get(`/harness/sessions/${id}`);
    return res.data as HarnessSession;
  },

  async createSession(
    pluginId: PluginId,
    opts?: { title?: string; workspace_path?: string },
  ): Promise<HarnessSession> {
    const res = await api.post('/harness/sessions', {
      plugin_id: pluginId,
      title: opts?.title,
      workspace_path: opts?.workspace_path || undefined,
    });
    return res.data as HarnessSession;
  },

  async updateSession(
    id: number,
    data: { title?: string; plugin_id?: PluginId; workspace_path?: string },
  ): Promise<HarnessSession> {
    const res = await api.patch(`/harness/sessions/${id}`, data);
    return res.data as HarnessSession;
  },

  async deleteSession(id: number): Promise<void> {
    await api.delete(`/harness/sessions/${id}`);
  },

  async listMessages(sessionId: number): Promise<HarnessMessage[]> {
    const res = await api.get(`/harness/sessions/${sessionId}/messages`);
    return res.data as HarnessMessage[];
  },

  async listWorkspaces(): Promise<WorkspaceList> {
    const res = await api.get('/harness/workspaces');
    return res.data as WorkspaceList;
  },

  async optimizePrompt(text: string, pluginId: PluginId): Promise<string> {
    const res = await api.post('/harness/prompt/optimize', { text, plugin_id: pluginId });
    return (res.data as { text: string }).text;
  },

  async uploadFiles(sessionId: number, files: File[]): Promise<UploadedFile[]> {
    const fd = new FormData();
    for (const f of files) fd.append('files', f);
    const res = await fetch(`${BASE}/harness/sessions/${sessionId}/files`, {
      method: 'POST',
      headers: authHeaders(),
      body: fd,
    });
    if (!res.ok) throw new Error(await readError(res, `上传失败 (${res.status})`));
    return (await res.json()) as UploadedFile[];
  },

  async *sendMessage(
    sessionId: number,
    content: string,
    pluginId: PluginId,
    signal?: AbortSignal,
    attachments: string[] = [],
  ): AsyncGenerator<StreamChunk> {
    const res = await fetch(`${BASE}/harness/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders(),
      },
      body: JSON.stringify({ content, plugin_id: pluginId, attachments }),
      signal,
    });
    if (!res.ok) throw new Error(await readError(res, `发送失败 (${res.status})`));
    if (!res.body) return;
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const blocks = buf.split('\n\n');
      buf = blocks.pop() ?? '';
      for (const block of blocks) {
        const ev = parseSseBlock(block);
        if (ev === 'done') return;
        if (ev) yield ev;
      }
    }
  },
};

function parseSseBlock(block: string): StreamChunk | 'done' | null {
  let event = 'message';
  const dataLines: string[] = [];
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
  }
  if (event === 'done') return 'done';
  if (!dataLines.length) return null;
  try {
    return JSON.parse(dataLines.join('\n')) as StreamChunk;
  } catch {
    return null;
  }
}
