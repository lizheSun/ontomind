/**
 * OpenCode 对话工作台的全局 store.
 *
 * 数据流：
 *   opencode HTTP → hooks/*.ts → 本 store → components/*.tsx
 *   opencode SSE  → useEventStream → dispatchEvent(evt) → 本 store
 *
 * 只保存 UI 需要的最小状态；opencode session 元数据以 opencode server 为准，
 * store 只做前端渲染层缓存与增量合并。
 */
import { create } from 'zustand';
import type {
  OcEvent,
  OcMessagesEnvelope,
  OcMessageInfo,
  OcPart,
  OcPermission,
  OcSession,
} from '../types';

export interface ModelRef {
  providerID: string;
  modelID: string;
}

const SS_AGENT_KEY = 'oc:currentAgent';
const SS_MODEL_KEY = 'oc:currentModel';
const SS_EXPERT_KEY = 'oc:currentExpertId';
const SS_SYSTEM_KEY = 'oc:currentSystemPrompt';

function loadAgent(): string {
  if (typeof window === 'undefined') return 'build';
  return window.sessionStorage.getItem(SS_AGENT_KEY) || 'build';
}
function loadModel(): ModelRef | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.sessionStorage.getItem(SS_MODEL_KEY);
    if (!raw) return null;
    const j = JSON.parse(raw) as ModelRef;
    return j && j.providerID && j.modelID ? j : null;
  } catch {
    return null;
  }
}
function loadExpertId(): number | null {
  if (typeof window === 'undefined') return null;
  const raw = window.sessionStorage.getItem(SS_EXPERT_KEY);
  const n = raw ? Number(raw) : NaN;
  return Number.isFinite(n) ? n : null;
}
function loadSystemPrompt(): string | null {
  if (typeof window === 'undefined') return null;
  return window.sessionStorage.getItem(SS_SYSTEM_KEY);
}
function saveAgent(a: string): void {
  try { window.sessionStorage.setItem(SS_AGENT_KEY, a); } catch { /* ignore */ }
}
function saveModel(m: ModelRef | null): void {
  try {
    if (m) window.sessionStorage.setItem(SS_MODEL_KEY, JSON.stringify(m));
    else window.sessionStorage.removeItem(SS_MODEL_KEY);
  } catch { /* ignore */ }
}
function saveExpertId(id: number | null): void {
  try {
    if (id == null) window.sessionStorage.removeItem(SS_EXPERT_KEY);
    else window.sessionStorage.setItem(SS_EXPERT_KEY, String(id));
  } catch { /* ignore */ }
}
function saveSystemPrompt(sp: string | null): void {
  try {
    if (!sp) window.sessionStorage.removeItem(SS_SYSTEM_KEY);
    else window.sessionStorage.setItem(SS_SYSTEM_KEY, sp);
  } catch { /* ignore */ }
}

export interface OpencodeState {
  // --- 元数据 ---
  serverReady: boolean;                       // /global/health & SSE 连通
  serverBaseUrl: string;
  version?: string;

  // --- 会话 ---
  sessions: OcSession[];
  activeSessionId: string | null;

  // --- 消息（按 sessionId 分桶）---
  messagesBySession: Record<string, OcMessagesEnvelope[]>;

  // --- 流式状态 ---
  streaming: boolean;                         // 当前会话是否在跑

  // --- 权限请求队列 ---
  pendingPermissions: OcPermission[];

  // --- 错误提示 ---
  lastError: string | null;

  // --- Agent / Model 选择（发消息时会用）---
  currentAgent: string;                       // 默认 "build"；也可切到 "plan" 等 primary agent
  currentModel: ModelRef | null;              // null = 用 opencode server 的 default
  currentExpertId: number | null;             // 当前选中的专家 id（null=本地）
  currentSystemPrompt: string | null;         // 当前专家的角色 prompt（选专家时注入）

  // --- Actions ---
  setServerStatus(ready: boolean, version?: string, baseUrl?: string): void;
  setSessions(list: OcSession[]): void;
  upsertSession(s: OcSession): void;
  removeSession(id: string): void;
  setActiveSession(id: string | null): void;
  setMessages(sessionId: string, list: OcMessagesEnvelope[]): void;
  setStreaming(v: boolean): void;
  dispatchEvent(evt: OcEvent): void;
  removePermission(permissionID: string): void;
  setError(msg: string | null): void;
  setCurrentAgent(name: string): void;
  setCurrentModel(m: ModelRef | null): void;
  setCurrentExpert(expertId: number | null, systemPrompt?: string | null): void;
  reset(): void;
}

export const useOpencodeStore = create<OpencodeState>((set, get) => ({
  serverReady: false,
  serverBaseUrl: '',
  version: undefined,
  sessions: [],
  activeSessionId: null,
  messagesBySession: {},
  streaming: false,
  pendingPermissions: [],
  lastError: null,
  currentAgent: loadAgent(),
  currentModel: loadModel(),
  currentExpertId: loadExpertId(),
  currentSystemPrompt: loadSystemPrompt(),

  setServerStatus(ready, version, baseUrl) {
    set({
      serverReady: ready,
      version: version ?? get().version,
      serverBaseUrl: baseUrl ?? get().serverBaseUrl,
    });
  },

  setCurrentAgent(name) {
    saveAgent(name);
    set({ currentAgent: name });
  },

  setCurrentModel(m) {
    saveModel(m);
    set({ currentModel: m });
  },

  setCurrentExpert(expertId, systemPrompt) {
    saveExpertId(expertId);
    saveSystemPrompt(systemPrompt ?? null);
    set({
      currentExpertId: expertId,
      currentSystemPrompt: systemPrompt ?? null,
    });
  },

  setSessions(list) {
    set({ sessions: list });
  },

  upsertSession(s) {
    const list = get().sessions;
    const idx = list.findIndex((x) => x.id === s.id);
    if (idx < 0) {
      set({ sessions: [s, ...list] });
    } else {
      const next = [...list];
      next[idx] = { ...next[idx], ...s };
      set({ sessions: next });
    }
  },

  removeSession(id) {
    const { sessions, activeSessionId, messagesBySession } = get();
    const nextMsgs = { ...messagesBySession };
    delete nextMsgs[id];
    set({
      sessions: sessions.filter((s) => s.id !== id),
      messagesBySession: nextMsgs,
      activeSessionId: activeSessionId === id ? null : activeSessionId,
    });
  },

  setActiveSession(id) {
    set({ activeSessionId: id });
  },

  setMessages(sessionId, list) {
    set({
      messagesBySession: { ...get().messagesBySession, [sessionId]: list },
    });
  },

  setStreaming(v) {
    set({ streaming: v });
  },

  removePermission(permissionID) {
    set({
      pendingPermissions: get().pendingPermissions.filter(
        (p) => p.id !== permissionID,
      ),
    });
  },

  setError(msg) {
    set({ lastError: msg });
  },

  dispatchEvent(evt) {
    const state = get();
    // v1.17+ 事件都在 properties 里，注意 sessionID/messageID 可能在 properties 顶层
    // 而 message/part 对象本身不一定重复带这两个字段。做兼容处理.
    switch (evt.type) {
      case 'server.connected':
        set({ serverReady: true });
        break;

      case 'message.updated': {
        const props = evt.properties as {
          sessionID?: string;
          info: OcMessageInfo & { sessionID?: string };
        };
        const info = props.info;
        const sid = info.sessionID || props.sessionID;
        if (!sid) break;
        const bucket = state.messagesBySession[sid] ?? [];
        const idx = bucket.findIndex((m) => m.info.id === info.id);
        let next: OcMessagesEnvelope[];
        if (idx < 0) {
          next = [...bucket, { info: { ...info, sessionID: sid }, parts: [] }];
        } else {
          next = [...bucket];
          next[idx] = {
            ...next[idx],
            info: { ...next[idx].info, ...info, sessionID: sid },
          };
        }
        set({
          messagesBySession: { ...state.messagesBySession, [sid]: next },
          streaming: info.role === 'assistant' && !info.time?.completed
            ? true
            : state.streaming,
        });
        break;
      }

      case 'message.part.updated': {
        const props = evt.properties as {
          sessionID?: string;
          part: OcPart & { sessionID?: string; messageID?: string };
        };
        const part = props.part;
        const sid = part.sessionID || props.sessionID;
        const mid = part.messageID;
        if (!sid || !mid) break;
        const bucket = state.messagesBySession[sid] ?? [];
        const idx = bucket.findIndex((m) => m.info.id === mid);
        if (idx < 0) break;
        const msg = bucket[idx];
        const pid = (part as { id?: string }).id;
        const partIdx = pid
          ? msg.parts.findIndex((p) => (p as { id?: string }).id === pid)
          : -1;
        let nextParts: OcPart[];
        if (partIdx < 0) {
          nextParts = [...msg.parts, part as OcPart];
        } else {
          nextParts = [...msg.parts];
          nextParts[partIdx] = { ...nextParts[partIdx], ...part } as OcPart;
        }
        const next = [...bucket];
        next[idx] = { ...msg, parts: nextParts };
        set({
          messagesBySession: { ...state.messagesBySession, [sid]: next },
          streaming: true,
        });
        break;
      }

      // v1.17+ 增量事件：文本 delta 拼接到指定 part
      case 'message.part.delta': {
        const props = evt.properties as {
          sessionID: string;
          messageID: string;
          partID: string;
          field: string;
          delta: string;
        };
        const { sessionID: sid, messageID: mid, partID, field, delta } = props;
        if (!sid || !mid || !partID || typeof delta !== 'string') break;
        const bucket = state.messagesBySession[sid] ?? [];
        const idx = bucket.findIndex((m) => m.info.id === mid);
        if (idx < 0) break;
        const msg = bucket[idx];
        const partIdx = msg.parts.findIndex((p) => (p as { id?: string }).id === partID);
        if (partIdx < 0) break;
        const oldPart = msg.parts[partIdx] as Record<string, unknown>;
        const oldVal = (oldPart[field] as string | undefined) ?? '';
        const nextParts = [...msg.parts];
        nextParts[partIdx] = { ...oldPart, [field]: oldVal + delta } as OcPart;
        const next = [...bucket];
        next[idx] = { ...msg, parts: nextParts };
        set({
          messagesBySession: { ...state.messagesBySession, [sid]: next },
          streaming: true,
        });
        break;
      }

      case 'message.removed': {
        const { sessionID, messageID } = evt.properties as { sessionID: string; messageID: string };
        const bucket = state.messagesBySession[sessionID] ?? [];
        set({
          messagesBySession: {
            ...state.messagesBySession,
            [sessionID]: bucket.filter((m) => m.info.id !== messageID),
          },
        });
        break;
      }

      case 'session.updated': {
        const props = evt.properties as { info: OcSession };
        state.upsertSession(props.info);
        break;
      }

      case 'session.deleted': {
        const props = evt.properties as { info?: OcSession; sessionID?: string };
        const sid = props.info?.id || props.sessionID;
        if (sid) state.removeSession(sid);
        break;
      }

      case 'session.error': {
        const err = (evt.properties as { error?: { message?: string } })?.error;
        set({ lastError: err?.message || 'opencode session 报错', streaming: false });
        break;
      }

      // 空闲：全局无正在跑的 session
      case 'session.idle':
      case 'idle':
        set({ streaming: false });
        break;

      // 全局忙碌事件（v1.17）
      case 'busy':
        set({ streaming: true });
        break;

      // 单会话状态（v1.17）
      case 'session.status': {
        const status = (evt.properties as { status?: { type?: string } })?.status;
        if (status?.type === 'idle') set({ streaming: false });
        else if (status?.type === 'busy') set({ streaming: true });
        break;
      }

      case 'permission.updated': {
        const perm = evt.properties as OcPermission;
        if (!state.pendingPermissions.find((p) => p.id === perm.id)) {
          set({ pendingPermissions: [...state.pendingPermissions, perm] });
        }
        break;
      }

      case 'permission.replied': {
        const permissionID = (evt.properties as { permissionID: string }).permissionID;
        state.removePermission(permissionID);
        break;
      }

      default:
        // 静默丢弃未知事件（心跳、diff 等）
        break;
    }
  },

  reset() {
    set({
      sessions: [],
      activeSessionId: null,
      messagesBySession: {},
      streaming: false,
      pendingPermissions: [],
      lastError: null,
    });
  },
}));
