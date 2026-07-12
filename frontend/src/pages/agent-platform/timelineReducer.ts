import type { AgentChatMessage, AgentChatPart } from '../../components/common/AgentChatPanel';
import type {
  AgentPlatformEvent,
  RunStatus,
  RunTimelineState,
  TimelineEntry,
} from './types';

export const initialTimelineState = (): RunTimelineState => ({
  runId: null,
  status: null,
  messages: [],
  entries: [],
  seen: {},
  lastSequence: 0,
});

const text = (value: unknown): string =>
  typeof value === 'string' ? value : value == null ? '' : JSON.stringify(value);

const payloadId = (event: AgentPlatformEvent, prefix: string): string =>
  text(event.payload.message_id ?? event.payload.step_id ?? event.payload.tool_call_id ??
    event.payload.subagent_run_id ?? event.payload.eval_id) || `${prefix}-${event.sequence}`;

function upsertMessage(
  messages: AgentChatMessage[],
  id: string,
  updater: (message: AgentChatMessage) => AgentChatMessage,
): AgentChatMessage[] {
  const index = messages.findIndex((message) => message.id === id);
  if (index < 0) {
    return [
      ...messages,
      updater({
        id,
        role: 'assistant',
        parts: [],
        createdAt: Date.now(),
        streaming: true,
      }),
    ];
  }
  return messages.map((message, current) => (current === index ? updater(message) : message));
}

function updatePart(
  parts: AgentChatPart[],
  partId: string,
  create: () => AgentChatPart,
  update: (part: AgentChatPart) => AgentChatPart,
): AgentChatPart[] {
  const index = parts.findIndex((part) => part.id === partId);
  if (index < 0) return [...parts, create()];
  return parts.map((part, current) => (current === index ? update(part) : part));
}

function applyMessageEvent(
  messages: AgentChatMessage[],
  event: AgentPlatformEvent,
): AgentChatMessage[] {
  const messageId = payloadId(event, 'message');
  const partId = text(event.payload.part_id) || `${messageId}-text`;

  if (event.type === 'message.started') {
    return upsertMessage(messages, messageId, (message) => ({
      ...message,
      role: (event.payload.role as AgentChatMessage['role']) || 'assistant',
      createdAt: Date.parse(event.timestamp) || Date.now(),
      streaming: true,
    }));
  }
  if (event.type === 'message.delta') {
    const delta = text(event.payload.delta ?? event.payload.text ?? event.payload.content);
    return upsertMessage(messages, messageId, (message) => ({
      ...message,
      streaming: true,
      parts: updatePart(
        message.parts,
        partId,
        () => ({ kind: 'text', id: partId, text: delta, streaming: true }),
        (part) =>
          part.kind === 'text'
            ? { ...part, text: part.text + delta, streaming: true }
            : part,
      ),
    }));
  }
  return upsertMessage(messages, messageId, (message) => ({
    ...message,
    streaming: false,
    parts: message.parts.map((part) =>
      part.kind === 'text' ? { ...part, streaming: false } : part,
    ),
  }));
}

const toolStatus = (eventType: string): Extract<AgentChatPart, { kind: 'tool' }>['status'] => {
  if (eventType === 'tool.awaiting_approval' || eventType === 'approval.requested') {
    return 'awaiting-approval';
  }
  if (eventType === 'tool.approved' || eventType === 'approval.approved') return 'approved';
  if (eventType === 'tool.rejected' || eventType === 'approval.rejected') return 'rejected';
  if (eventType === 'tool.started') return 'running';
  if (eventType === 'tool.completed') return 'success';
  if (eventType === 'tool.failed') return 'error';
  return 'pending';
};

function applyToolEvent(
  messages: AgentChatMessage[],
  event: AgentPlatformEvent,
): AgentChatMessage[] {
  const messageId = text(event.payload.message_id) || `run-${event.run_id}-assistant`;
  const partId =
    text(event.payload.approval_id ?? event.payload.tool_call_id) ||
    payloadId(event, 'tool');
  return upsertMessage(messages, messageId, (message) => ({
    ...message,
    parts: updatePart(
      message.parts,
      partId,
      () => ({
        kind: 'tool',
        id: partId,
        toolName: text(event.payload.tool_name) || 'tool',
        args: event.payload.arguments ?? event.payload.args,
        result: event.payload.result,
        error: text(event.payload.error) || undefined,
        status: toolStatus(event.type),
        requiresApproval:
          Boolean(event.payload.requires_approval) ||
          event.type === 'tool.awaiting_approval' ||
          event.type === 'approval.requested',
      }),
      (part) =>
        part.kind === 'tool'
          ? {
              ...part,
              status: toolStatus(event.type),
              result: event.payload.result ?? part.result,
              error: text(event.payload.error) || part.error,
            }
          : part,
    ),
  }));
}

function entryFromEvent(event: AgentPlatformEvent): TimelineEntry | null {
  const type = event.type;
  let category: TimelineEntry['category'] | null = null;
  if (type === 'thinking_summary' || type === 'thinking.summary') category = 'thinking';
  else if (type.startsWith('step.') || type.startsWith('run.step.')) category = 'step';
  else if (type.startsWith('tool.') || type.startsWith('approval.')) category = 'tool';
  else if (type.startsWith('subagent.')) category = 'subagent';
  else if (type.startsWith('eval.') || type === 'run.evaluation') category = 'eval';
  else if (type.startsWith('run.')) category = 'run';
  if (!category) return null;

  const failed = type.endsWith('.failed') || type === 'run.failed';
  const completed = type.endsWith('.completed') || type === 'eval.result';
  const warning = type.includes('awaiting') || type.includes('revision') || type.includes('needs_review');
  const status: TimelineEntry['status'] = failed
    ? 'error'
    : completed
      ? 'success'
      : warning
        ? 'warning'
        : type.endsWith('.started') || category === 'thinking'
          ? 'running'
          : 'pending';
  const name = text(
    event.payload.title ??
      event.payload.name ??
      event.payload.step_name ??
      event.payload.role ??
      event.payload.tool_name ??
      event.payload.agent_name ??
      event.payload.eval_name,
  );
  const labels: Record<TimelineEntry['category'], string> = {
    thinking: '思考摘要',
    step: '执行步骤',
    tool: '工具调用',
    subagent: '子 Agent',
    eval: 'Eval',
    run: 'Run',
  };
  const keyByCategory: Record<TimelineEntry['category'], unknown> = {
    thinking: event.payload.summary_id,
    step: event.payload.step_id ?? event.payload.step_sequence,
    tool: event.payload.tool_call_id ?? event.payload.approval_id,
    subagent: event.payload.subagent_run_id,
    eval: event.payload.eval_id,
    run: event.run_id,
  };
  return {
    key: text(keyByCategory[category]) || `${category}-${event.sequence}`,
    eventType: type,
    category,
    title: name ? `${labels[category]} · ${name}` : labels[category],
    summary: text(
      event.payload.summary ??
        event.payload.thinking_summary ??
        event.payload.output ??
        event.payload.feedback ??
        event.payload.message ??
        event.payload.error,
    ) || undefined,
    status,
    sequence: event.sequence,
    timestamp: event.timestamp,
    payload: event.payload,
  };
}

function upsertEntry(entries: TimelineEntry[], next: TimelineEntry): TimelineEntry[] {
  const index = entries.findIndex(
    (entry) => entry.category === next.category && entry.key === next.key,
  );
  if (index < 0) return [...entries, next].sort((a, b) => a.sequence - b.sequence);
  return entries
    .map((entry, current) =>
      current === index
        ? {
            ...entry,
            ...next,
            summary: next.summary ?? entry.summary,
            payload: { ...entry.payload, ...next.payload },
          }
        : entry,
    )
    .sort((a, b) => a.sequence - b.sequence);
}

const runStatusFromEvent = (type: string): RunStatus | null => {
  const value = type.startsWith('run.') ? type.slice(4) : '';
  const known: RunStatus[] = [
    'pending', 'running', 'needs_review', 'completed', 'failed', 'cancelled',
  ];
  if (value === 'created') return 'pending';
  if (value === 'started' || value === 'resumed') return 'running';
  return known.includes(value as RunStatus) ? (value as RunStatus) : null;
};

export function reduceTimeline(
  state: RunTimelineState,
  event: AgentPlatformEvent,
): RunTimelineState {
  const dedupeKey = `${event.run_id}:${event.sequence}`;
  if (state.seen[dedupeKey]) return state;

  let messages = state.messages;
  if (event.type.startsWith('message.')) messages = applyMessageEvent(messages, event);
  if (event.type.startsWith('tool.') || event.type.startsWith('approval.')) {
    messages = applyToolEvent(messages, event);
  }
  // 兜底：若只有 run.completed 而没有 message.*，用 final_output 合成助手气泡
  if (event.type === 'run.completed') {
    const output = event.payload.output;
    const finalOutput =
      output && typeof output === 'object' && !Array.isArray(output)
        ? text((output as Record<string, unknown>).final_output)
        : text(event.payload.final_output);
    const hasAssistantText = messages.some(
      (item) =>
        item.role === 'assistant' &&
        item.parts.some((part) => part.kind === 'text' && part.text.trim()),
    );
    if (finalOutput && !hasAssistantText) {
      const messageId = `fallback-${event.run_id}`;
      messages = [
        ...messages,
        {
          id: messageId,
          role: 'assistant',
          createdAt: Date.parse(event.timestamp) || Date.now(),
          streaming: false,
          parts: [{ kind: 'text', id: `${messageId}-text`, text: finalOutput }],
        },
      ];
    }
  }

  const nextEntry = entryFromEvent(event);
  const nextStatus = runStatusFromEvent(event.type);
  return {
    ...state,
    runId: event.run_id,
    status: nextStatus ?? state.status,
    messages,
    entries: nextEntry ? upsertEntry(state.entries, nextEntry) : state.entries,
    seen: { ...state.seen, [dedupeKey]: true },
    lastSequence: Math.max(state.lastSequence, event.sequence),
  };
}

export function appendUserMessage(
  state: RunTimelineState,
  id: string,
  content: string,
): RunTimelineState {
  return {
    ...state,
    messages: [
      ...state.messages,
      {
        id,
        role: 'user',
        createdAt: Date.now(),
        parts: [{ kind: 'text', id: `${id}-text`, text: content }],
      },
    ],
  };
}
