import { create } from 'zustand';
import { harnessService } from '../services/harness.service';
import {
  applyChunk,
  type HarnessMessage,
  type HarnessPlugin,
  type HarnessSession,
  type PluginId,
  type UploadedFile,
  type WorkspaceList,
} from '../types/harness';

const PLUGIN_KEY = 'om-chat-plugin';
const WS_KEY = 'om-chat-workspace';
const MAX_ATTACH = 12;
const MAX_FILE = 12 * 1024 * 1024;

function readPlugin(): PluginId {
  try {
    const v = localStorage.getItem(PLUGIN_KEY);
    if (v === 'opencode' || v === 'dsh') return v;
  } catch {
    /* ignore */
  }
  return 'opencode';
}

function readWorkspace(): string {
  try {
    return localStorage.getItem(WS_KEY) || '';
  } catch {
    return '';
  }
}

function isManagedWorkspace(path: string): boolean {
  return path.includes('/.ontomind/harness/') || path.includes('\\.ontomind\\harness\\');
}

function persistWorkspace(path: string) {
  try {
    if (!path || isManagedWorkspace(path)) return;
    localStorage.setItem(WS_KEY, path);
  } catch {
    /* ignore */
  }
}

function errMsg(e: unknown, fallback: string): string {
  const ax = e as { response?: { data?: { message?: string } }; message?: string; name?: string };
  return ax.response?.data?.message || (e instanceof Error ? e.message : fallback);
}

interface ChatState {
  plugins: HarnessPlugin[];
  sessions: HarnessSession[];
  activeId: number | null;
  messages: HarnessMessage[];
  pluginId: PluginId;
  workspacePath: string;
  workspaces: WorkspaceList | null;
  attachments: UploadedFile[];
  statusText: string;
  streaming: boolean;
  uploading: boolean;
  loading: boolean;
  error: string;

  loadPlugins: () => Promise<void>;
  loadSessions: () => Promise<void>;
  loadWorkspaces: () => Promise<void>;
  select: (id: number | null) => Promise<void>;
  createAndSelect: (pluginId?: PluginId) => Promise<HarnessSession>;
  remove: (id: number) => Promise<void>;
  setPluginId: (id: PluginId) => void;
  switchPlugin: (id: PluginId) => Promise<void>;
  setWorkspace: (path: string) => Promise<void>;
  uploadFiles: (files: File[]) => Promise<void>;
  removeAttachment: (rel: string) => void;
  send: (content: string) => Promise<void>;
  stop: () => void;
}

let abort: AbortController | null = null;

function upsertSession(list: HarnessSession[], sess: HarnessSession): HarnessSession[] {
  const rest = list.filter((x) => x.id !== sess.id);
  return [sess, ...rest];
}

export const useChatStore = create<ChatState>((set, get) => ({
  plugins: [],
  sessions: [],
  activeId: null,
  messages: [],
  pluginId: readPlugin(),
  workspacePath: readWorkspace(),
  workspaces: null,
  attachments: [],
  statusText: '',
  streaming: false,
  uploading: false,
  loading: false,
  error: '',

  loadPlugins: async () => {
    try {
      const plugins = await harnessService.listPlugins();
      set({ plugins });
      const { pluginId } = get();
      const cur = plugins.find((p) => p.id === pluginId);
      if (cur && !cur.available) {
        const fallback = plugins.find((p) => p.available);
        if (fallback) {
          try {
            localStorage.setItem(PLUGIN_KEY, fallback.id);
          } catch {
            /* ignore */
          }
          set({ pluginId: fallback.id });
        }
      }
    } catch {
      /* 侧栏探活失败不挡页面 */
    }
  },

  loadSessions: async () => {
    try {
      const sessions = await harnessService.listSessions();
      set({ sessions });
    } catch {
      /* ignore */
    }
  },

  loadWorkspaces: async () => {
    try {
      const workspaces = await harnessService.listWorkspaces();
      set({ workspaces });
    } catch {
      /* ignore */
    }
  },

  select: async (id) => {
    abort?.abort();
    set({
      activeId: id,
      messages: [],
      error: '',
      statusText: '',
      streaming: false,
      attachments: [],
    });
    if (id == null) {
      set({ workspacePath: readWorkspace() });
      return;
    }
    set({ loading: true });
    try {
      let sess = get().sessions.find((s) => s.id === id) ?? null;
      if (!sess) {
        sess = await harnessService.getSession(id);
        set((s) => ({ sessions: upsertSession(s.sessions, sess!) }));
      }
      const messages = await harnessService.listMessages(id);
      if (sess.workspace_path) persistWorkspace(sess.workspace_path);
      set({
        messages,
        loading: false,
        pluginId: sess.plugin_id,
        workspacePath: sess.workspace_path || get().workspacePath,
      });
    } catch (e) {
      set({ loading: false, error: errMsg(e, '加载消息失败') });
    }
  },

  createAndSelect: async (pluginId) => {
    try {
      const pid = pluginId ?? get().pluginId;
      const current = get().workspacePath.trim();
      const ws = current && !isManagedWorkspace(current) ? current : readWorkspace();
      const sess = await harnessService.createSession(pid, {
        workspace_path: ws && !isManagedWorkspace(ws) ? ws : undefined,
      });
      persistWorkspace(sess.workspace_path);
      set((s) => ({
        sessions: upsertSession(s.sessions, sess),
        pluginId: pid,
        workspacePath: sess.workspace_path,
        error: '',
      }));
      await get().select(sess.id);
      return sess;
    } catch (e) {
      set({ error: errMsg(e, '无法创建会话（后端未响应？）') });
      throw e;
    }
  },

  remove: async (id) => {
    await harnessService.deleteSession(id);
    const { activeId } = get();
    set((s) => ({ sessions: s.sessions.filter((x) => x.id !== id) }));
    if (activeId === id) await get().select(null);
  },

  setPluginId: (id) => {
    try {
      localStorage.setItem(PLUGIN_KEY, id);
    } catch {
      /* ignore */
    }
    set({ pluginId: id });
  },

  switchPlugin: async (id) => {
    get().setPluginId(id);
    const { activeId } = get();
    if (activeId == null) return;
    try {
      const sess = await harnessService.updateSession(activeId, { plugin_id: id });
      set((s) => ({ sessions: upsertSession(s.sessions, sess) }));
    } catch (e) {
      set({ error: errMsg(e, '切换助手失败') });
    }
  },

  setWorkspace: async (path) => {
    const next = path.trim();
    persistWorkspace(next);
    set({ workspacePath: next, error: '' });
    const { activeId } = get();
    if (!next || activeId == null) return;
    try {
      const sess = await harnessService.updateSession(activeId, { workspace_path: next });
      persistWorkspace(sess.workspace_path);
      set((s) => ({
        sessions: upsertSession(s.sessions, sess),
        workspacePath: sess.workspace_path,
      }));
    } catch (e) {
      set({ error: errMsg(e, '工作区无效') });
      throw e;
    }
  },

  uploadFiles: async (files) => {
    if (!files.length || get().streaming) return;
    const oversized = files.find((f) => f.size > MAX_FILE);
    if (oversized) {
      set({ error: `${oversized.name} 超过 12MB` });
      return;
    }
    set({ uploading: true, error: '' });
    try {
      let { activeId } = get();
      if (activeId == null) {
        const sess = await get().createAndSelect();
        activeId = sess.id;
      }
      const uploaded = await harnessService.uploadFiles(activeId, files);
      set((s) => ({
        uploading: false,
        attachments: [...s.attachments, ...uploaded].slice(0, MAX_ATTACH),
      }));
    } catch (e) {
      set({ uploading: false, error: errMsg(e, '上传失败') });
    }
  },

  removeAttachment: (rel) => {
    set((s) => ({ attachments: s.attachments.filter((a) => a.rel !== rel) }));
  },

  send: async (content) => {
    const files = get().attachments;
    const text = content.trim() || (files.length ? '请结合附件处理。' : '');
    if (!text || get().streaming) return;
    let { activeId, pluginId } = get();
    if (activeId == null) {
      const sess = await get().createAndSelect(pluginId);
      activeId = sess.id;
    }
    abort?.abort();
    abort = new AbortController();
    const userMsg: HarnessMessage = {
      id: Date.now(),
      session_id: activeId,
      role: 'user',
      parts: [
        { kind: 'text', text },
        ...files.map((f) => ({ kind: 'file' as const, name: f.name, text: f.rel })),
      ],
    };
    const draftId = -Date.now();
    const draft: HarnessMessage = { id: draftId, session_id: activeId, role: 'assistant', parts: [] };
    set((s) => ({
      messages: [...s.messages, userMsg, draft],
      attachments: [],
      streaming: true,
      statusText: '',
      error: '',
    }));
    try {
      for await (const ev of harnessService.sendMessage(
        activeId,
        text,
        pluginId,
        abort.signal,
        files.map((f) => f.rel),
      )) {
        if (ev.kind === 'status') {
          set({ statusText: ev.text || '' });
          continue;
        }
        if (ev.kind === 'meta') continue;
        set((s) => ({
          messages: s.messages.map((m) =>
            m.id === draftId ? { ...m, parts: applyChunk(m.parts, ev) } : m,
          ),
          statusText: ev.kind === 'text' || ev.kind === 'thinking' ? '' : s.statusText,
        }));
      }
      const messages = await harnessService.listMessages(activeId);
      await get().loadSessions();
      set({ messages, streaming: false, statusText: '' });
    } catch (e) {
      if ((e as { name?: string }).name === 'AbortError') {
        set({ streaming: false, statusText: '' });
        return;
      }
      set({
        streaming: false,
        statusText: '',
        error: errMsg(e, '发送失败'),
      });
    }
  },

  stop: () => {
    abort?.abort();
    abort = null;
    set({ streaming: false, statusText: '' });
  },
}));
