/**
 * OpenCode SDK 薄封装 — 智能数开 Agent 对话。
 * 直连容器 / 本机 opencode serve（需 CORS 放行前端源）。
 *
 * 能力摘要（client）：
 * - session.promptAsync / session.command / session.abort
 * - event.subscribe → message.part.updated（text / reasoning / tool / agent…）
 * - session.status + session.idle（结束 busy）
 * - command.list → `/` 技能/斜杠命令
 * - app.agents → `@agent` 选择
 */
import { createOpencodeClient, type OpencodeClient } from '@opencode-ai/sdk/client';

export type OpencodeEvent = {
  type?: string;
  properties?: Record<string, unknown>;
};

export type OpencodeCommand = {
  name: string;
  description?: string;
  agent?: string;
  template?: string;
};

export type OpencodeAgent = {
  name: string;
  description?: string;
  mode?: string;
  color?: string;
};

export type AssistantPartUpdate =
  | { kind: 'text'; partId: string; text: string }
  | { kind: 'reasoning'; partId: string; text: string }
  | {
      kind: 'tool';
      partId: string;
      tool: string;
      callID?: string;
      status: string;
      title?: string;
      input?: unknown;
      output?: string;
      error?: string;
    }
  | { kind: 'agent'; partId: string; name: string }
  | { kind: 'step-start'; partId: string }
  | { kind: 'step-finish'; partId: string; reason?: string };

export function createServeClient(baseUrl: string, directory?: string): OpencodeClient {
  return createOpencodeClient({
    baseUrl: baseUrl.replace(/\/$/, ''),
    directory,
  });
}

export async function healthCheck(baseUrl: string): Promise<{ ok: boolean; version?: string; error?: string }> {
  try {
    const resp = await fetch(`${baseUrl.replace(/\/$/, '')}/global/health`, {
      method: 'GET',
      mode: 'cors',
    });
    if (!resp.ok) return { ok: false, error: `HTTP ${resp.status}` };
    const body = (await resp.json()) as { healthy?: boolean; version?: string };
    return { ok: Boolean(body.healthy ?? true), version: body.version };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : '探活失败' };
  }
}

export async function createChatSession(
  client: OpencodeClient,
  title = '智能数开',
): Promise<string> {
  const res = await client.session.create({ body: { title } });
  if (res.error || !res.data?.id) {
    throw new Error(
      typeof res.error === 'object' && res.error && 'message' in res.error
        ? String((res.error as { message?: string }).message)
        : '创建 OpenCode session 失败',
    );
  }
  return res.data.id;
}

export async function listCommands(client: OpencodeClient): Promise<OpencodeCommand[]> {
  const res = await client.command.list();
  if (res.error || !res.data) return [];
  return (res.data as OpencodeCommand[]).map((c) => ({
    name: c.name,
    description: c.description,
    agent: c.agent,
    template: c.template,
  }));
}

export async function listAgents(client: OpencodeClient): Promise<OpencodeAgent[]> {
  const res = await client.app.agents();
  if (res.error || !res.data) return [];
  return (res.data as OpencodeAgent[]).map((a) => ({
    name: a.name,
    description: a.description,
    mode: a.mode,
    color: a.color,
  }));
}

export async function promptAsync(
  client: OpencodeClient,
  sessionId: string,
  text: string,
  opts?: { agent?: string; agentMentions?: string[] },
): Promise<void> {
  const parts: Array<
    | { type: 'text'; text: string }
    | { type: 'agent'; name: string; source?: { value: string; start: number; end: number } }
  > = [];

  for (const name of opts?.agentMentions ?? []) {
    parts.push({
      type: 'agent',
      name,
      source: { value: `@${name}`, start: 0, end: name.length + 1 },
    });
  }
  parts.push({ type: 'text', text });

  const res = await client.session.promptAsync({
    path: { id: sessionId },
    body: {
      agent: opts?.agent,
      parts,
    },
  });
  if (res.error) {
    throw new Error(
      typeof res.error === 'object' && res.error && 'message' in res.error
        ? String((res.error as { message?: string }).message)
        : '发送 prompt 失败',
    );
  }
}

export async function runCommand(
  client: OpencodeClient,
  sessionId: string,
  command: string,
  args = '',
  opts?: { agent?: string },
): Promise<void> {
  const res = await client.session.command({
    path: { id: sessionId },
    body: {
      command,
      arguments: args,
      agent: opts?.agent,
    },
  });
  if (res.error) {
    throw new Error(
      typeof res.error === 'object' && res.error && 'message' in res.error
        ? String((res.error as { message?: string }).message)
        : '执行命令失败',
    );
  }
}

export async function abortSession(client: OpencodeClient, sessionId: string): Promise<void> {
  await client.session.abort({ path: { id: sessionId } });
}

/** 订阅 /event，按 session 过滤；返回取消函数 */
export async function subscribeSessionEvents(
  client: OpencodeClient,
  sessionId: string,
  onEvent: (evt: OpencodeEvent) => void,
): Promise<() => void> {
  const result = await client.event.subscribe();
  const stream = result.stream;
  let stopped = false;

  const eventSessionId = (evt: OpencodeEvent): string | undefined => {
    const props = evt.properties ?? {};
    const part = props.part as Record<string, unknown> | undefined;
    const info = props.info as Record<string, unknown> | undefined;
    const status = props.status as Record<string, unknown> | undefined;
    const sid =
      (props.sessionID as string | undefined) ||
      (props.session_id as string | undefined) ||
      (part?.sessionID as string | undefined) ||
      (info?.sessionID as string | undefined) ||
      (status?.sessionID as string | undefined);
    return sid;
  };

  (async () => {
    try {
      for await (const raw of stream) {
        if (stopped) break;
        const evt = raw as OpencodeEvent;
        const sid = eventSessionId(evt);
        // session.idle 可能只有 sessionID；无 sid 的全局事件丢弃
        if (evt.type === 'session.idle') {
          const idleSid = (evt.properties?.sessionID as string | undefined) || sid;
          if (idleSid && idleSid !== sessionId) continue;
          onEvent(evt);
          continue;
        }
        if (sid && sid !== sessionId) continue;
        onEvent(evt);
      }
    } catch {
      /* stream closed */
    }
  })();

  return () => {
    stopped = true;
  };
}

/** 从 SSE 抽取 assistant 相关 part 更新 */
export function extractAssistantParts(
  evt: OpencodeEvent,
  assistantIds: Set<string>,
): AssistantPartUpdate[] {
  const type = String(evt.type || '');
  const props = evt.properties ?? {};
  const out: AssistantPartUpdate[] = [];

  if (type === 'message.updated') {
    const info = props.info as Record<string, unknown> | undefined;
    if (info?.role === 'assistant' && info.id) {
      assistantIds.add(String(info.id));
    }
    return out;
  }

  if (type !== 'message.part.updated') return out;
  const part = props.part as Record<string, unknown> | undefined;
  if (!part) return out;
  const messageId = String(part.messageID || '');
  // 首包可能先于 message.updated；assistant 文本/推理/工具仍收录
  const partType = String(part.type || '');
  const accept =
    !messageId ||
    assistantIds.has(messageId) ||
    partType === 'reasoning' ||
    partType === 'tool' ||
    partType === 'step-start' ||
    partType === 'step-finish';
  if (!accept) return out;
  if (messageId) assistantIds.add(messageId);

  const partId = String(part.id || partType);

  if (partType === 'text') {
    const text = String(part.text || '');
    if (text) out.push({ kind: 'text', partId, text });
    return out;
  }
  if (partType === 'reasoning') {
    const text = String(part.text || '');
    if (text) out.push({ kind: 'reasoning', partId, text });
    return out;
  }
  if (partType === 'tool') {
    const state = (part.state || {}) as Record<string, unknown>;
    out.push({
      kind: 'tool',
      partId,
      tool: String(part.tool || 'tool'),
      callID: part.callID ? String(part.callID) : undefined,
      status: String(state.status || 'pending'),
      title: state.title ? String(state.title) : undefined,
      input: state.input,
      output: state.output != null ? String(state.output) : undefined,
      error: state.error != null ? String(state.error) : undefined,
    });
    return out;
  }
  if (partType === 'agent') {
    out.push({ kind: 'agent', partId, name: String(part.name || '') });
    return out;
  }
  if (partType === 'step-start') {
    out.push({ kind: 'step-start', partId });
    return out;
  }
  if (partType === 'step-finish') {
    out.push({ kind: 'step-finish', partId, reason: part.reason ? String(part.reason) : undefined });
    return out;
  }
  return out;
}

/** @deprecated 用 extractAssistantParts */
export function extractAssistantText(
  evt: OpencodeEvent,
  assistantIds: Set<string>,
): { partId: string; text: string } | null {
  const parts = extractAssistantParts(evt, assistantIds);
  const text = parts.find((p) => p.kind === 'text');
  return text && text.kind === 'text' ? { partId: text.partId, text: text.text } : null;
}

export function isSessionIdle(evt: OpencodeEvent): boolean {
  if (evt.type === 'session.idle') return true;
  if (evt.type !== 'session.status') return false;
  const status = (evt.properties?.status ?? {}) as Record<string, unknown>;
  return String(status.type || '') === 'idle';
}

export function isSessionBusy(evt: OpencodeEvent): boolean {
  if (evt.type !== 'session.status') return false;
  const status = (evt.properties?.status ?? {}) as Record<string, unknown>;
  return String(status.type || '') === 'busy';
}

export function isSessionError(evt: OpencodeEvent): boolean {
  return evt.type === 'session.error';
}

/** 从助手回复中提取首个 sql 代码块 */
export function extractSqlBlock(markdown: string): string | null {
  const match = markdown.match(/```sql\s*([\s\S]*?)```/i);
  if (!match) return null;
  const sql = match[1].trim();
  return sql || null;
}
