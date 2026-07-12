import { useEffect, useRef, useState } from 'react';
import { agentPlatformEventsUrl } from '../services/agentPlatform.service';
import type { AgentPlatformEvent } from '../pages/agent-platform/types';

export interface EventCursor {
  lastEventId: string;
  lastSequence: number;
  seen: Set<string>;
}

export const createEventCursor = (): EventCursor => ({
  lastEventId: '',
  lastSequence: 0,
  seen: new Set(),
});

export function acceptAgentEvent(cursor: EventCursor, event: AgentPlatformEvent): boolean {
  const key = `${event.run_id}:${event.sequence}`;
  if (cursor.seen.has(key)) return false;
  cursor.seen.add(key);
  cursor.lastSequence = Math.max(cursor.lastSequence, event.sequence);
  cursor.lastEventId = event.id || String(cursor.lastSequence);
  return true;
}

interface ParsedSseMessage {
  id?: string;
  event?: string;
  data: string;
}

export class SseParser {
  private buffer = '';

  push(chunk: string): ParsedSseMessage[] {
    this.buffer += chunk.replace(/\r\n/g, '\n');
    const messages: ParsedSseMessage[] = [];
    let boundary = this.buffer.indexOf('\n\n');
    while (boundary >= 0) {
      const block = this.buffer.slice(0, boundary);
      this.buffer = this.buffer.slice(boundary + 2);
      const parsed = this.parseBlock(block);
      if (parsed) messages.push(parsed);
      boundary = this.buffer.indexOf('\n\n');
    }
    return messages;
  }

  private parseBlock(block: string): ParsedSseMessage | null {
    if (!block || block.startsWith(':')) return null;
    const result: ParsedSseMessage = { data: '' };
    const data: string[] = [];
    for (const line of block.split('\n')) {
      if (!line || line.startsWith(':')) continue;
      const colon = line.indexOf(':');
      const field = colon < 0 ? line : line.slice(0, colon);
      const value = colon < 0 ? '' : line.slice(colon + 1).replace(/^ /, '');
      if (field === 'id') result.id = value;
      else if (field === 'event') result.event = value;
      else if (field === 'data') data.push(value);
    }
    if (!data.length) return null;
    result.data = data.join('\n');
    return result;
  }
}

export interface StreamOptions {
  signal: AbortSignal;
  onEvent: (event: AgentPlatformEvent) => void;
  onState?: (state: 'connecting' | 'open' | 'reconnecting' | 'closed') => void;
  fetchImpl?: typeof fetch;
  retryBaseMs?: number;
  cursor?: EventCursor;
}

const terminalTypes = new Set([
  'run.completed',
  'run.failed',
  'run.needs_review',
  'run.cancelled',
]);

const delay = (milliseconds: number, signal: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    const timer = window.setTimeout(resolve, milliseconds);
    signal.addEventListener(
      'abort',
      () => {
        window.clearTimeout(timer);
        reject(new DOMException('Aborted', 'AbortError'));
      },
      { once: true },
    );
  });

export async function consumeAgentEventStream(
  runId: number,
  options: StreamOptions,
): Promise<void> {
  const request = options.fetchImpl ?? fetch;
  const cursor = options.cursor ?? createEventCursor();
  const decoder = new TextDecoder();
  let attempt = 0;
  let terminal = false;

  while (!options.signal.aborted && !terminal) {
    options.onState?.(attempt === 0 ? 'connecting' : 'reconnecting');
    const headers: Record<string, string> = {
      Accept: 'text/event-stream',
    };
    const token = globalThis.localStorage?.getItem('access_token');
    if (token) headers.Authorization = `Bearer ${token}`;
    if (cursor.lastEventId) headers['Last-Event-ID'] = cursor.lastEventId;

    try {
      const response = await request(agentPlatformEventsUrl(runId), {
        headers,
        signal: options.signal,
      });
      if (!response.ok || !response.body) {
        throw new Error(`SSE 连接失败 (${response.status})`);
      }
      options.onState?.('open');
      attempt = 0;
      const parser = new SseParser();
      const reader = response.body.getReader();
      while (!options.signal.aborted) {
        const { done, value } = await reader.read();
        if (done) break;
        for (const message of parser.push(decoder.decode(value, { stream: true }))) {
          const envelope = JSON.parse(message.data) as Record<string, unknown>;
          const nested =
            envelope.payload && typeof envelope.payload === 'object' && !Array.isArray(envelope.payload)
              ? (envelope.payload as Record<string, unknown>)
              : envelope;
          const sequence = Number(message.id ?? envelope.sequence);
          const event: AgentPlatformEvent = {
            id: message.id,
            run_id: Number(envelope.run_id ?? runId),
            sequence: Number.isFinite(sequence) ? sequence : cursor.lastSequence + 1,
            type: message.event || String(envelope.type || 'message'),
            timestamp: typeof envelope.timestamp === 'string'
              ? envelope.timestamp
              : new Date().toISOString(),
            visibility: typeof envelope.visibility === 'string'
              ? (envelope.visibility as AgentPlatformEvent['visibility'])
              : undefined,
            payload: nested,
          };
          if (!acceptAgentEvent(cursor, event)) continue;
          options.onEvent(event);
          if (terminalTypes.has(event.type)) {
            terminal = true;
            await reader.cancel();
            break;
          }
        }
      }
    } catch (error) {
      if (options.signal.aborted) break;
      if (error instanceof SyntaxError) throw new Error('SSE 事件数据格式无效');
    }

    if (!terminal && !options.signal.aborted) {
      attempt += 1;
      const wait = Math.min((options.retryBaseMs ?? 500) * 2 ** (attempt - 1), 10_000);
      await delay(wait, options.signal);
    }
  }
  options.onState?.('closed');
}

export function useAgentStream(
  runId: number | null,
  onEvent: (event: AgentPlatformEvent) => void,
) {
  const callbackRef = useRef(onEvent);
  const cursorRef = useRef(createEventCursor());
  const [state, setState] = useState<'idle' | 'connecting' | 'open' | 'reconnecting' | 'closed'>(
    'idle',
  );
  const [error, setError] = useState<string | null>(null);
  callbackRef.current = onEvent;

  useEffect(() => {
    cursorRef.current = createEventCursor();
    setError(null);
    if (!runId) {
      setState('idle');
      return;
    }
    const controller = new AbortController();
    void consumeAgentEventStream(runId, {
      signal: controller.signal,
      cursor: cursorRef.current,
      onEvent: (event) => callbackRef.current(event),
      onState: setState,
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) {
        setError(reason instanceof Error ? reason.message : '事件流连接失败');
        setState('closed');
      }
    });
    return () => controller.abort();
  }, [runId]);

  return {
    state,
    error,
    lastSequence: cursorRef.current.lastSequence,
  };
}

export default useAgentStream;
