import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import type { CSSProperties, KeyboardEvent, ReactNode } from 'react';
import { Avatar, Button, Card, Empty, Input, Space, Spin, Tag, Tooltip, Typography, message as antdMessage } from 'antd';
import {
  RobotOutlined,
  UserOutlined,
  SendOutlined,
  ToolOutlined,
  CheckCircleTwoTone,
  CloseCircleTwoTone,
  LoadingOutlined,
  ClearOutlined,
} from '@ant-design/icons';

const { Text, Paragraph } = Typography;

/* ────────────────────────────────────────────────────────────────
 * Types
 * ──────────────────────────────────────────────────────────────── */

export type AgentChatRole = 'user' | 'assistant' | 'system';

export type AgentToolPartStatus =
  | 'pending' // tool call streamed, not yet approved / executing
  | 'awaiting-approval'
  | 'approved'
  | 'rejected'
  | 'running'
  | 'success'
  | 'error';

/** A single "part" of an assistant turn: either a text chunk or a tool call. */
export type AgentChatPart =
  | {
      kind: 'text';
      id: string;
      /** Streamed text. May grow over time. */
      text: string;
      /** When true, still receiving delta chunks. */
      streaming?: boolean;
    }
  | {
      kind: 'tool';
      id: string;
      /** Tool identifier, e.g. `sql.query`, `fs.read_file`. */
      toolName: string;
      /** Arguments passed to the tool (JSON-serializable). */
      args?: unknown;
      /** Tool output once it has run. */
      result?: unknown;
      /** Optional error message when status = 'error'. */
      error?: string;
      /** Lifecycle status; controls approval buttons and spinner. */
      status: AgentToolPartStatus;
      /** When true, this tool call requires explicit user approval before running. */
      requiresApproval?: boolean;
    };

export interface AgentChatMessage {
  id: string;
  role: AgentChatRole;
  /** Ordered parts. For user / system turns, usually a single text part. */
  parts: AgentChatPart[];
  /** Optional creation timestamp (ms) — used for tooltip only. */
  createdAt?: number;
  /** When true, the whole message is still being generated. */
  streaming?: boolean;
}

export interface AgentChatPanelProps {
  /** Ordered messages to render. */
  messages: AgentChatMessage[];
  /** Whether the assistant is currently streaming a response. */
  streaming?: boolean;
  /** Called when the user submits a new prompt. */
  onSend?: (text: string) => void | Promise<void>;
  /** Called when the user approves a pending tool call. */
  onApproveTool?: (messageId: string, toolPartId: string) => void | Promise<void>;
  /** Called when the user rejects a pending tool call. */
  onRejectTool?: (messageId: string, toolPartId: string) => void | Promise<void>;
  /** Called when the user clicks the clear/reset button. */
  onClear?: () => void;
  /** Optional title for the card header. */
  title?: string;
  /** Optional subtitle / status text. */
  statusText?: ReactNode;
  /** Placeholder for the composer input. */
  placeholder?: string;
  /** Height for the message list area. */
  height?: number | string;
  /** Disable the composer. */
  disabled?: boolean;
  /** Render as a bare panel without Card wrapper. */
  bordered?: boolean;
  /** Optional extra header content. */
  extra?: ReactNode;
  /** Custom empty state. */
  emptyText?: ReactNode;
}

/* ────────────────────────────────────────────────────────────────
 * Helpers
 * ──────────────────────────────────────────────────────────────── */

const roleStyle = (role: AgentChatRole): CSSProperties => {
  switch (role) {
    case 'user':
      return {
        background: 'rgba(96, 165, 250, 0.12)',
        border: '1px solid rgba(96, 165, 250, 0.28)',
      };
    case 'assistant':
      return {
        background: 'rgba(255, 255, 255, 0.04)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
      };
    case 'system':
    default:
      return {
        background: 'rgba(148, 163, 184, 0.08)',
        border: '1px dashed rgba(148, 163, 184, 0.24)',
      };
  }
};

const statusMeta = (
  status: AgentToolPartStatus,
): { color: string; label: string; icon: ReactNode } => {
  switch (status) {
    case 'pending':
      return { color: 'default', label: '待处理', icon: <ToolOutlined /> };
    case 'awaiting-approval':
      return { color: 'gold', label: '待审批', icon: <ToolOutlined /> };
    case 'approved':
      return {
        color: 'blue',
        label: '已批准',
        icon: <CheckCircleTwoTone twoToneColor="#3b82f6" />,
      };
    case 'rejected':
      return {
        color: 'red',
        label: '已拒绝',
        icon: <CloseCircleTwoTone twoToneColor="#ef4444" />,
      };
    case 'running':
      return { color: 'processing', label: '执行中', icon: <LoadingOutlined spin /> };
    case 'success':
      return {
        color: 'green',
        label: '完成',
        icon: <CheckCircleTwoTone twoToneColor="#22c55e" />,
      };
    case 'error':
      return {
        color: 'red',
        label: '失败',
        icon: <CloseCircleTwoTone twoToneColor="#ef4444" />,
      };
  }
};

const formatJson = (value: unknown): string => {
  if (value === undefined) return '';
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
};

const formatTime = (ts?: number): string | undefined => {
  if (!ts) return undefined;
  try {
    return new Date(ts).toLocaleTimeString();
  } catch {
    return undefined;
  }
};

/* ────────────────────────────────────────────────────────────────
 * Sub-renderers
 * ──────────────────────────────────────────────────────────────── */

interface ToolPartViewProps {
  messageId: string;
  part: Extract<AgentChatPart, { kind: 'tool' }>;
  onApprove?: (messageId: string, partId: string) => void | Promise<void>;
  onReject?: (messageId: string, partId: string) => void | Promise<void>;
}

function ToolPartView({ messageId, part, onApprove, onReject }: ToolPartViewProps) {
  const meta = statusMeta(part.status);
  const argsText = useMemo(() => formatJson(part.args), [part.args]);
  const resultText = useMemo(() => formatJson(part.result), [part.result]);
  const isAwaiting = part.status === 'awaiting-approval';

  return (
    <div
      data-testid="agent-chat-tool-part"
      data-tool-part-id={part.id}
      data-tool-status={part.status}
      style={{
        marginTop: 8,
        padding: '10px 12px',
        borderRadius: 10,
        background: 'rgba(15, 23, 42, 0.55)',
        border: '1px solid rgba(148, 163, 184, 0.18)',
      }}
    >
      <Space size={8} wrap style={{ marginBottom: 6 }}>
        <Tag icon={meta.icon} color={meta.color} bordered={false}>
          {meta.label}
        </Tag>
        <Text strong style={{ fontSize: 13 }}>
          {part.toolName}
        </Text>
        {part.requiresApproval && !isAwaiting ? (
          <Tag color="geekblue" bordered={false}>
            需审批
          </Tag>
        ) : null}
      </Space>

      {argsText ? (
        <pre
          style={{
            margin: 0,
            padding: 8,
            borderRadius: 6,
            background: 'rgba(2, 6, 23, 0.55)',
            color: '#cbd5f5',
            fontSize: 12,
            lineHeight: 1.5,
            maxHeight: 180,
            overflow: 'auto',
          }}
        >
          {argsText}
        </pre>
      ) : null}

      {part.error ? (
        <Paragraph
          style={{
            marginTop: 8,
            marginBottom: 0,
            color: '#fb7185',
            fontSize: 12,
            whiteSpace: 'pre-wrap',
          }}
        >
          {part.error}
        </Paragraph>
      ) : null}

      {resultText && !part.error ? (
        <>
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 8 }}>
            结果
          </Text>
          <pre
            style={{
              margin: '4px 0 0',
              padding: 8,
              borderRadius: 6,
              background: 'rgba(2, 6, 23, 0.55)',
              color: '#e2e8f0',
              fontSize: 12,
              lineHeight: 1.5,
              maxHeight: 220,
              overflow: 'auto',
            }}
          >
            {resultText}
          </pre>
        </>
      ) : null}

      {isAwaiting ? (
        <Space style={{ marginTop: 10 }}>
          <Button
            size="small"
            type="primary"
            icon={<CheckCircleTwoTone twoToneColor="#22c55e" />}
            onClick={() => void onApprove?.(messageId, part.id)}
            data-testid="agent-chat-tool-approve"
          >
            批准
          </Button>
          <Button
            size="small"
            danger
            icon={<CloseCircleTwoTone twoToneColor="#ef4444" />}
            onClick={() => void onReject?.(messageId, part.id)}
            data-testid="agent-chat-tool-reject"
          >
            拒绝
          </Button>
        </Space>
      ) : null}
    </div>
  );
}

interface MessageViewProps {
  message: AgentChatMessage;
  onApprove?: (messageId: string, partId: string) => void | Promise<void>;
  onReject?: (messageId: string, partId: string) => void | Promise<void>;
}

function MessageView({ message, onApprove, onReject }: MessageViewProps) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const time = formatTime(message.createdAt);

  const avatar = isUser ? (
    <Avatar size={28} icon={<UserOutlined />} style={{ background: '#3b82f6' }} />
  ) : isSystem ? (
    <Avatar size={28} icon={<RobotOutlined />} style={{ background: '#64748b' }} />
  ) : (
    <Avatar size={28} icon={<RobotOutlined />} style={{ background: '#22c55e' }} />
  );

  const roleLabel = isUser ? '用户' : isSystem ? '系统' : 'Agent';

  return (
    <div
      data-testid="agent-chat-message"
      data-message-id={message.id}
      data-role={message.role}
      style={{
        display: 'flex',
        gap: 10,
        marginBottom: 12,
        flexDirection: isUser ? 'row-reverse' : 'row',
      }}
    >
      {avatar}
      <div style={{ maxWidth: '86%', minWidth: 120 }}>
        <Space size={8} style={{ marginBottom: 4 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {roleLabel}
          </Text>
          {time ? (
            <Tooltip title={time}>
              <Text type="secondary" style={{ fontSize: 11 }}>
                {time}
              </Text>
            </Tooltip>
          ) : null}
          {message.streaming ? (
            <Tag color="processing" bordered={false} icon={<LoadingOutlined spin />}>
              流式输出中
            </Tag>
          ) : null}
        </Space>
        <div
          style={{
            padding: '10px 12px',
            borderRadius: 12,
            ...roleStyle(message.role),
          }}
        >
          {message.parts.length === 0 && message.streaming ? (
            <Spin size="small" />
          ) : (
            message.parts.map((part) => {
              if (part.kind === 'text') {
                return (
                  <Paragraph
                    key={part.id}
                    data-testid="agent-chat-text-part"
                    data-part-id={part.id}
                    style={{
                      margin: 0,
                      whiteSpace: 'pre-wrap',
                      fontSize: 13,
                      lineHeight: 1.6,
                      color: '#e5e7eb',
                    }}
                  >
                    {part.text}
                    {part.streaming ? (
                      <span
                        aria-hidden
                        style={{
                          display: 'inline-block',
                          width: 6,
                          height: 12,
                          marginLeft: 4,
                          background: '#60a5fa',
                          verticalAlign: 'middle',
                          animation: 'agent-chat-blink 1s steps(2, start) infinite',
                        }}
                      />
                    ) : null}
                  </Paragraph>
                );
              }
              return (
                <ToolPartView
                  key={part.id}
                  messageId={message.id}
                  part={part}
                  onApprove={onApprove}
                  onReject={onReject}
                />
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────
 * Main component
 * ──────────────────────────────────────────────────────────────── */

export function AgentChatPanel({
  messages,
  streaming = false,
  onSend,
  onApproveTool,
  onRejectTool,
  onClear,
  title = 'Agent 会话',
  statusText,
  placeholder = '向 Agent 发消息，Shift+Enter 换行，Enter 发送',
  height = 480,
  disabled = false,
  bordered = true,
  extra,
  emptyText,
}: AgentChatPanelProps) {
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const listRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll to bottom when messages update.
  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages, streaming]);

  const canSend = draft.trim().length > 0 && !disabled && !sending && !!onSend;

  const submit = useCallback(async () => {
    if (!onSend) return;
    const text = draft.trim();
    if (!text) return;
    setSending(true);
    try {
      await onSend(text);
      setDraft('');
    } catch (err) {
      const msg = err instanceof Error ? err.message : '发送失败';
      antdMessage.error(msg);
    } finally {
      setSending(false);
    }
  }, [draft, onSend]);

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      if (canSend) void submit();
    }
  };

  const list = (
    <div
      ref={listRef}
      data-testid="agent-chat-message-list"
      style={{
        height,
        overflowY: 'auto',
        padding: 12,
        background: 'rgba(2, 6, 23, 0.35)',
        borderRadius: 10,
        border: '1px solid rgba(255,255,255,0.05)',
      }}
    >
      <style>{'@keyframes agent-chat-blink { to { visibility: hidden; } }'}</style>
      {messages.length === 0 ? (
        <div
          style={{
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={emptyText ?? '暂无消息，输入内容开始对话'}
          />
        </div>
      ) : (
        messages.map((m) => (
          <MessageView
            key={m.id}
            message={m}
            onApprove={onApproveTool}
            onReject={onRejectTool}
          />
        ))
      )}
    </div>
  );

  const composer = (
    <div style={{ marginTop: 10, display: 'flex', gap: 8, alignItems: 'flex-end' }}>
      <Input.TextArea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        autoSize={{ minRows: 1, maxRows: 4 }}
        disabled={disabled || sending}
        data-testid="agent-chat-input"
        style={{ flex: 1, background: 'rgba(15, 23, 42, 0.55)' }}
      />
      <Button
        type="primary"
        icon={<SendOutlined />}
        onClick={() => void submit()}
        disabled={!canSend}
        loading={sending}
        data-testid="agent-chat-send"
      >
        发送
      </Button>
    </div>
  );

  const body = (
    <div>
      {list}
      {onSend ? composer : null}
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
          {streaming ? (
            <Tag color="processing" bordered={false} icon={<LoadingOutlined spin />}>
              生成中
            </Tag>
          ) : null}
          {statusText ? (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {statusText}
            </Text>
          ) : null}
        </Space>
      }
      extra={
        <Space>
          {extra}
          {onClear ? (
            <Tooltip title="清空会话">
              <Button
                size="small"
                type="text"
                icon={<ClearOutlined />}
                onClick={onClear}
                aria-label="clear-agent-chat"
                data-testid="agent-chat-clear"
              />
            </Tooltip>
          ) : null}
        </Space>
      }
      style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)' }}
      styles={{ body: { padding: 12 } }}
    >
      {body}
    </Card>
  );
}

export default AgentChatPanel;
