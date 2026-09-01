import { useMemo } from 'react';
import { CheckCircleOutlined, CloseCircleOutlined, LoadingOutlined, ToolOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import type { HarnessMessage, MessagePart } from '../../types/harness';

function UserBubble({ parts }: { parts: MessagePart[] }) {
  const text = parts.find((p) => p.kind === 'text')?.text || '';
  const files = parts.filter((p) => p.kind === 'file');
  return (
    <div className="om-chat-row user">
      <div className="om-chat-bubble user">
        {text}
        {files.length ? (
          <div className="om-chat-bubble-files">
            {files.map((f, i) => (
              <span key={`${f.text || f.name}-${i}`} className="om-chat-chip om-chat-chip-static">
                {f.name || f.text}
              </span>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function ThinkingBlock({ text, open }: { text: string; open?: boolean }) {
  return (
    <details className="om-chat-think" open={open !== false}>
      <summary className="om-chat-think-sum">{text ? '思考过程' : '正在思考…'}</summary>
      <pre className="om-chat-think-body">{text || '…'}</pre>
    </details>
  );
}

function ToolCard({ part }: { part: MessagePart }) {
  const status = part.tool_status || 'running';
  const icon =
    status === 'running' ? (
      <LoadingOutlined />
    ) : status === 'error' ? (
      <CloseCircleOutlined style={{ color: 'var(--danger)' }} />
    ) : (
      <CheckCircleOutlined style={{ color: 'var(--success)' }} />
    );
  const extra = status === 'running' ? '执行中' : status === 'error' ? '失败' : '完成';
  return (
    <div className={`om-chat-tool om-chat-tool-${status}`}>
      <div className="om-chat-tool-head">
        <ToolOutlined />
        <span className="om-chat-tool-name">{part.tool_name || '工具'}</span>
        {part.summary ? <span className="om-chat-tool-sum">{part.summary}</span> : null}
        <span className="om-chat-tool-st">
          {icon} {extra}
        </span>
      </div>
      {part.output ? <pre className="om-chat-tool-out">{part.output}</pre> : null}
    </div>
  );
}

function AssistantParts({ parts, streaming }: { parts: MessagePart[]; streaming?: boolean }) {
  return (
    <div className="om-chat-assistant">
      {parts.map((p, i) => {
        if (p.kind === 'thinking' && (p.text || streaming))
          return <ThinkingBlock key={p.part_id || i} text={p.text || ''} open />;
        if (p.kind === 'execute') return <ToolCard key={p.part_id || p.tool_id || i} part={p} />;
        if (p.kind === 'error')
          return (
            <div key={i} className="om-chat-error">
              {p.text}
            </div>
          );
        if (p.kind === 'text' && p.text)
          return (
            <div key={i} className="om-chat-md">
              <ReactMarkdown>{p.text}</ReactMarkdown>
            </div>
          );
        return null;
      })}
    </div>
  );
}

export function ChatTranscript({
  messages,
  streaming,
  statusText,
}: {
  messages: HarnessMessage[];
  streaming: boolean;
  statusText: string;
}) {
  const last = messages[messages.length - 1];
  const showCursor = streaming && last?.role === 'assistant';

  const rows = useMemo(() => messages, [messages]);

  return (
    <div className="om-chat-thread">
      {rows.map((m) => {
        if (m.role === 'user') {
          return <UserBubble key={m.id} parts={m.parts} />;
        }
        const hasErrorPart = m.parts.some((p) => p.kind === 'error');
        return (
          <div key={m.id} className="om-chat-row assistant">
            <AssistantParts parts={m.parts} streaming={streaming && m.id === last?.id} />
            {m.error_text && !hasErrorPart ? <div className="om-chat-error">{m.error_text}</div> : null}
          </div>
        );
      })}
      {showCursor && statusText ? <div className="om-chat-status">{statusText}</div> : null}
      {showCursor && last.parts.length === 0 && !statusText ? (
        <div className="om-chat-status">正在连接插件…</div>
      ) : null}
    </div>
  );
}
