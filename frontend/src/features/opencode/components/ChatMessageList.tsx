/**
 * ChatMessageList — opencode-style 消息流.
 * 视觉核心：user 右对齐圆角气泡；assistant 左对齐纯文本流；无 role 标签，靠位置区分.
 */
import { useEffect, useRef } from 'react';
import { useMessages } from '../hooks/useMessages';
import { useOpencodeStore } from '../stores/opencodeStore';
import MessagePart from './MessagePart';

export default function ChatMessageList() {
  const activeSessionId = useOpencodeStore((s) => s.activeSessionId);
  const streaming = useOpencodeStore((s) => s.streaming);
  const { messages } = useMessages(activeSessionId);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streaming]);

  if (!activeSessionId) {
    return (
      <div className="oc-empty" style={{ height: '100%' }}>
        选择一个会话开始，或直接在下方发消息新建会话
      </div>
    );
  }

  return (
    <div className="oc-turn">
      {messages.length === 0 ? (
        <div className="oc-empty" style={{ padding: '80px 0' }}>
          发送第一条消息开始对话
        </div>
      ) : (
        messages.map((m) => (
          <div key={m.info.id} className="oc-msg-wrap" data-role={m.info.role}>
            <div className="oc-msg" data-role={m.info.role}>
              {m.parts.map((part, idx) => (
                <MessagePart
                  key={(part as { id?: string }).id || `${m.info.id}-${idx}`}
                  part={part}
                />
              ))}
              {m.info.role === 'assistant' && m.info.modelID && (
                <div className="oc-msg-meta">
                  {m.info.providerID}/{m.info.modelID}
                  <span className="oc-god-only" style={{ marginLeft: 8, opacity: 0.6 }}>
                    · {m.info.id.slice(0, 12)}
                  </span>
                </div>
              )}
            </div>
          </div>
        ))
      )}
      {streaming && (
        <div className="oc-msg-wrap" data-role="assistant">
          <div className="oc-msg" data-role="assistant">
            <span className="oc-thinking">Thinking</span>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
