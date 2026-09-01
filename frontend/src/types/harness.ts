export type PluginId = 'opencode' | 'dsh';

export interface HarnessPlugin {
  id: PluginId;
  label: string;
  available: boolean;
  detail: string;
  binary: string;
}

export interface HarnessSession {
  id: number;
  title: string;
  plugin_id: PluginId;
  plugin_session_id?: string | null;
  workspace_path: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface MessagePart {
  kind: 'text' | 'thinking' | 'execute' | 'error' | 'file';
  text?: string;
  name?: string;
  part_id?: string;
  tool_id?: string;
  tool_name?: string;
  tool_status?: string;
  summary?: string;
  output?: string;
}

export interface UploadedFile {
  name: string;
  rel: string;
  size: number;
}

export interface WorkspaceItem {
  path: string;
  label: string;
  kind: string;
}

export interface WorkspaceList {
  home: string;
  recents: WorkspaceItem[];
}

export interface HarnessMessage {
  id: number;
  session_id: number;
  role: 'user' | 'assistant' | 'system';
  parts: MessagePart[];
  error_text?: string | null;
  created_at?: string | null;
}

export interface StreamChunk {
  kind: 'text' | 'thinking' | 'execute' | 'error' | 'status' | 'meta';
  text?: string;
  delta?: boolean;
  tool_id?: string;
  tool_name?: string;
  tool_status?: string;
  summary?: string;
  output?: string;
  part_id?: string;
  meta?: Record<string, unknown>;
}

export function applyChunk(parts: MessagePart[], ev: StreamChunk): MessagePart[] {
  if (ev.kind === 'status' || ev.kind === 'meta') return parts;
  const next = parts.map((p) => ({ ...p }));
  if (ev.part_id) {
    const idx = next.findIndex((p) => p.part_id === ev.part_id);
    if (idx >= 0) {
      mergePart(next[idx], ev);
      return next;
    }
    next.push(newPart(ev));
    return next;
  }
  if (ev.kind === 'text' || ev.kind === 'thinking') {
    const last = next[next.length - 1];
    if (ev.delta && last && last.kind === ev.kind) {
      last.text = (last.text || '') + (ev.text || '');
      return next;
    }
    next.push({ kind: ev.kind, text: ev.text || '' });
    return next;
  }
  if (ev.kind === 'execute') {
    const idx = ev.tool_id ? next.findIndex((p) => p.kind === 'execute' && p.tool_id === ev.tool_id) : -1;
    if (idx >= 0) {
      mergePart(next[idx], ev);
      return next;
    }
    next.push(newPart(ev));
    return next;
  }
  if (ev.kind === 'error') {
    next.push({ kind: 'error', text: ev.text || '出错了' });
  }
  return next;
}

function newPart(ev: StreamChunk): MessagePart {
  if (ev.kind === 'execute') {
    return {
      kind: 'execute',
      part_id: ev.part_id,
      tool_id: ev.tool_id,
      tool_name: ev.tool_name,
      tool_status: ev.tool_status || 'running',
      summary: ev.summary,
      output: ev.output,
    };
  }
  return { kind: ev.kind as MessagePart['kind'], text: ev.text || '', part_id: ev.part_id };
}

function mergePart(p: MessagePart, ev: StreamChunk) {
  if (ev.kind === 'text' || ev.kind === 'thinking') {
    p.text = ev.delta ? (p.text || '') + (ev.text || '') : ev.text || p.text;
    return;
  }
  if (ev.kind === 'execute') {
    if (ev.tool_name) p.tool_name = ev.tool_name;
    if (ev.tool_status) p.tool_status = ev.tool_status;
    if (ev.summary) p.summary = ev.summary;
    if (ev.output) p.output = ev.output;
  }
}
