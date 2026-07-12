import { useEffect, useRef, useState, useCallback } from 'react';
import { Card, Spin, Empty, Space, Tag, Button } from 'antd';
import { RobotOutlined, ReloadOutlined } from '@ant-design/icons';

/**
 * postMessage protocol for agent embed ↔ parent communication.
 *
 * Parent → iframe (agent):
 *   { type: 'agent.embed.init', agentId, context }
 *   { type: 'agent.embed.context', context }
 *   { type: 'agent.embed.request', requestId, payload }
 *
 * iframe (agent) → Parent:
 *   { type: 'agent.embed.ready' }
 *   { type: 'agent.embed.result', requestId?, data }
 *   { type: 'agent.embed.event', event, data? }
 *   { type: 'agent.embed.error', message }
 */

export type AgentEmbedContext = Record<string, unknown>;

export type AgentEmbedInboundMessage =
  | { type: 'agent.embed.ready' }
  | { type: 'agent.embed.result'; requestId?: string; data: unknown }
  | { type: 'agent.embed.event'; event: string; data?: unknown }
  | { type: 'agent.embed.error'; message: string };

export type AgentEmbedOutboundMessage =
  | { type: 'agent.embed.init'; agentId: string | number; context?: AgentEmbedContext }
  | { type: 'agent.embed.context'; context: AgentEmbedContext }
  | { type: 'agent.embed.request'; requestId: string; payload: unknown };

export const AGENT_EMBED_MSG_PREFIX = 'agent.embed.';

export interface AgentEmbedRunnerProps {
  /** Agent identifier (numeric id or string slug). */
  agentId: string | number;
  /** Runtime context forwarded to the agent iframe. */
  context?: AgentEmbedContext;
  /** Source URL of the agent frame. Defaults to `/agent-embed/{agentId}`. */
  src?: string;
  /** Fixed height for the iframe container. */
  height?: number | string;
  /** Title displayed in the card header. */
  title?: string;
  /** Whether to render the Card wrapper (default true). */
  bordered?: boolean;
  /** Called when the iframe reports it is ready. */
  onReady?: () => void;
  /** Called for every inbound message from the agent. */
  onMessage?: (msg: AgentEmbedInboundMessage) => void;
  /** Called with `agent.embed.result` payloads. */
  onResult?: (data: unknown, requestId?: string) => void;
  /** Called with `agent.embed.error` payloads. */
  onError?: (message: string) => void;
  /** Test hook to override window.location.origin. */
  parentOrigin?: string;
}

const isAgentEmbedMessage = (data: unknown): data is AgentEmbedInboundMessage => {
  if (typeof data !== 'object' || data === null) return false;
  const t = (data as { type?: unknown }).type;
  return typeof t === 'string' && t.startsWith(AGENT_EMBED_MSG_PREFIX);
};

export function AgentEmbedRunner({
  agentId,
  context,
  src,
  height = 480,
  title = 'Agent',
  bordered = true,
  onReady,
  onMessage,
  onResult,
  onError,
}: AgentEmbedRunnerProps) {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const [ready, setReady] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const resolvedSrc =
    src ?? (typeof agentId === 'string' || typeof agentId === 'number'
      ? `/agent-embed/${agentId}`
      : '');

  const post = useCallback(
    (msg: AgentEmbedOutboundMessage) => {
      const win = iframeRef.current?.contentWindow;
      if (!win) return;
      try {
        win.postMessage(msg, '*');
      } catch {
        /* ignore cross-origin serialization errors */
      }
    },
    [],
  );

  // Send init once ready
  useEffect(() => {
    if (ready) {
      post({ type: 'agent.embed.init', agentId, context });
    }
  }, [ready, agentId, context, post]);

  // Push context updates after init
  useEffect(() => {
    if (ready && context !== undefined) {
      post({ type: 'agent.embed.context', context });
    }
  }, [context, ready, post]);

  // Listen for inbound messages
  useEffect(() => {
    const handler = (event: MessageEvent) => {
      if (!isAgentEmbedMessage(event.data)) return;
      // Only accept messages originating from our iframe window
      if (
        iframeRef.current &&
        event.source !== iframeRef.current.contentWindow
      ) {
        return;
      }
      const msg = event.data;
      onMessage?.(msg);
      switch (msg.type) {
        case 'agent.embed.ready':
          setReady(true);
          setErrorMsg(null);
          onReady?.();
          break;
        case 'agent.embed.result':
          onResult?.(msg.data, msg.requestId);
          break;
        case 'agent.embed.error':
          setErrorMsg(msg.message);
          onError?.(msg.message);
          break;
        default:
          break;
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [onMessage, onReady, onResult, onError]);

  const reload = () => {
    setReady(false);
    setErrorMsg(null);
    setReloadKey((k) => k + 1);
  };

  const body = (
    <div style={{ position: 'relative', height, borderRadius: 12, overflow: 'hidden' }}>
      {resolvedSrc ? (
        <iframe
          key={reloadKey}
          ref={iframeRef}
          title={`agent-${agentId}`}
          src={resolvedSrc}
          style={{
            width: '100%',
            height: '100%',
            border: 0,
            background: 'rgba(255,255,255,0.02)',
          }}
          data-testid="agent-embed-iframe"
          data-agent-id={String(agentId)}
        />
      ) : (
        <Empty description="未提供 agentId" />
      )}
      {!ready && !errorMsg && resolvedSrc && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(6,11,20,0.7)',
            pointerEvents: 'none',
          }}
        >
          <Spin tip="Agent 加载中..." />
        </div>
      )}
      {errorMsg && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(6,11,20,0.85)',
            color: '#fb7185',
            fontSize: 13,
            padding: 16,
            textAlign: 'center',
          }}
          data-testid="agent-embed-error"
        >
          {errorMsg}
        </div>
      )}
    </div>
  );

  if (!bordered) {
    return body;
  }

  return (
    <Card
      title={
        <Space>
          <RobotOutlined style={{ color: '#60a5fa' }} />
          <span style={{ fontWeight: 600 }}>{title}</span>
          <Tag color={ready ? 'green' : 'default'} bordered={false}>
            {ready ? 'ready' : 'loading'}
          </Tag>
        </Space>
      }
      extra={
        <Button
          size="small"
          type="text"
          icon={<ReloadOutlined />}
          onClick={reload}
          aria-label="reload-agent-embed"
        >
          重载
        </Button>
      }
      style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)' }}
      styles={{ body: { padding: 12 } }}
    >
      {body}
    </Card>
  );
}

export default AgentEmbedRunner;
