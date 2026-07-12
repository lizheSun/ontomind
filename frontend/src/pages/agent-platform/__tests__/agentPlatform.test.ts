import { describe, expect, it, vi } from 'vitest';
import {
  acceptAgentEvent,
  consumeAgentEventStream,
  createEventCursor,
  SseParser,
} from '../../../hooks/useAgentStream';
import { emptyStudioConfig, normalizeStudioConfig } from '../types';
import type { AgentPlatformEvent, DiscoveryItem } from '../types';
import {
  availableDiscoveryDecisions,
  evaluateDraftSave,
  evaluateStudioCompleteness,
  resolveDiscoveryDecision,
} from '../domain';
import { initialTimelineState, reduceTimeline } from '../timelineReducer';

const event = (
  sequence: number,
  type: string,
  payload: Record<string, unknown> = {},
): AgentPlatformEvent => ({
  run_id: 'run-1',
  sequence,
  type,
  timestamp: '2026-07-12T10:00:00Z',
  payload,
});

describe('run event reducer', () => {
  it('按 run+sequence 去重并聚合消息、工具和统一 timeline', () => {
    let state = initialTimelineState();
    const events = [
      event(1, 'run.started'),
      event(2, 'message.started', { message_id: 'm1' }),
      event(3, 'message.delta', { message_id: 'm1', delta: '你好' }),
      event(4, 'thinking_summary', { summary: '先确认目标' }),
      event(5, 'step.started', { step_id: 's1', step_name: '检索' }),
      event(6, 'tool.awaiting_approval', {
        message_id: 'm1',
        tool_call_id: 'approval-1',
        tool_name: 'knowledge.search',
        arguments: { query: '目标' },
      }),
      event(7, 'subagent.started', { subagent_run_id: 'child-1', agent_name: '审核员' }),
      event(8, 'eval.result', { eval_id: 'eval-1', eval_name: '一致性', summary: '通过' }),
    ];
    for (const item of events) state = reduceTimeline(state, item);
    const duplicate = reduceTimeline(state, events[7]);

    expect(duplicate).toBe(state);
    expect(state.status).toBe('running');
    expect(state.messages[0].parts).toEqual([
      expect.objectContaining({ kind: 'text', text: '你好' }),
      expect.objectContaining({
        kind: 'tool',
        id: 'approval-1',
        status: 'awaiting-approval',
      }),
    ]);
    expect(state.entries.map((item) => item.category)).toEqual([
      'run',
      'thinking',
      'step',
      'tool',
      'subagent',
      'eval',
    ]);
  });
});

describe('SSE stream', () => {
  it('解析跨 chunk 的 SSE 消息', () => {
    const parser = new SseParser();
    expect(parser.push('id: 1\nevent: step.started\nda')).toEqual([]);
    expect(parser.push('ta: {"sequence":1}\n\n')).toEqual([
      { id: '1', event: 'step.started', data: '{"sequence":1}' },
    ]);
  });

  it('按 run+sequence 去重', () => {
    const cursor = createEventCursor();
    expect(acceptAgentEvent(cursor, event(1, 'run.started'))).toBe(true);
    expect(acceptAgentEvent(cursor, event(1, 'run.started'))).toBe(false);
    expect(cursor.lastEventId).toBe('1');
  });

  it('断线重连携带 Last-Event-ID，并过滤补发重复事件', async () => {
    const encode = (value: string) => new TextEncoder().encode(value);
    const response = (body: string) => ({
      ok: true,
      status: 200,
      body: new ReadableStream({
        start(controller) {
          controller.enqueue(encode(body));
          controller.close();
        },
      }),
    }) as Response;
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response(`id: 1\nevent: run.started\ndata: ${JSON.stringify(event(1, 'run.started'))}\n\n`))
      .mockResolvedValueOnce(response(
        `id: 1\nevent: run.started\ndata: ${JSON.stringify(event(1, 'run.started'))}\n\n` +
        `id: 2\nevent: run.completed\ndata: ${JSON.stringify(event(2, 'run.completed'))}\n\n`,
      ));
    const received: AgentPlatformEvent[] = [];
    await consumeAgentEventStream('run-1', {
      signal: new AbortController().signal,
      fetchImpl: fetchMock,
      retryBaseMs: 1,
      onEvent: (item) => received.push(item),
    });

    expect(received.map((item) => item.sequence)).toEqual([1, 2]);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1][1].headers['Last-Event-ID']).toBe('1');
  });

  it('解析后端事件信封中的嵌套 payload', async () => {
    const encode = (value: string) => new TextEncoder().encode(value);
    const envelope = {
      run_id: 9,
      sequence: 3,
      type: 'message.delta',
      timestamp: '2026-07-12T10:00:00Z',
      visibility: 'user',
      payload: { message_id: 'a1', delta: '你好' },
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      body: new ReadableStream({
        start(controller) {
          controller.enqueue(encode(`id: 3\nevent: message.delta\ndata: ${JSON.stringify(envelope)}\n\n`));
          controller.enqueue(encode(`id: 4\nevent: run.completed\ndata: ${JSON.stringify({
            ...envelope,
            sequence: 4,
            type: 'run.completed',
            payload: { status: 'completed', output: { final_output: '你好' } },
          })}\n\n`));
          controller.close();
        },
      }),
    } as Response);
    const received: AgentPlatformEvent[] = [];
    await consumeAgentEventStream(9, {
      signal: new AbortController().signal,
      fetchImpl: fetchMock,
      onEvent: (item) => received.push(item),
    });
    expect(received[0]).toMatchObject({
      type: 'message.delta',
      payload: { message_id: 'a1', delta: '你好' },
    });
    expect(received[1].type).toBe('run.completed');
  });
});

describe('Agent Studio completeness', () => {
  it('默认配置下仅核心字段决定完整度', () => {
    const config = emptyStudioConfig();
    expect(evaluateStudioCompleteness(config)).toMatchObject({ percent: 67, complete: false });
    config.objective = {
      name: '分析师',
      problem: '分析经营数据',
      success_criteria: [],
      exclusions: [],
    };
    expect(evaluateStudioCompleteness(config)).toMatchObject({ percent: 100, complete: true });
    expect(evaluateDraftSave(config)).toMatchObject({ ok: true });
    const normalized = normalizeStudioConfig(config);
    expect(normalized.model.model_id).toBeTruthy();
    expect(normalized.guardrails.forbidden_actions.length).toBeGreaterThan(0);
    expect(normalized.loop.sop.length).toBeGreaterThan(0);
    expect(normalized.release.change_summary).toBeTruthy();
  });
});

describe('discovery decisions', () => {
  const changed: DiscoveryItem = {
    id: 'item-1',
    resource_type: 'agent',
    external_key: 'analyst',
    status: 'changed',
    decision: 'pending',
  };

  it('changed 资源仅允许安全的版本化决策', () => {
    expect(availableDiscoveryDecisions(changed)).toEqual([
      'link',
      'keep_platform',
      'ignore',
      'external',
    ]);
    expect(resolveDiscoveryDecision(changed, 'keep_platform').decision).toBe('keep_platform');
    expect(() => resolveDiscoveryDecision(changed, 'import')).toThrow('不允许决策');
  });
});
