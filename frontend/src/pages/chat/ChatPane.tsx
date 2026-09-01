/**
 * 会话主区：记录 + 输入。/chat 与看板任务层共用。
 */
import { useEffect, useRef } from 'react';
import { CodeOutlined, RobotOutlined } from '@ant-design/icons';
import { EmptyState } from '../../components/common/EmptyState';
import { useChatStore } from '../../stores/chatStore';
import { AGENT_META } from './agentMeta';
import { ChatComposer } from './ChatComposer';
import { ChatTranscript } from './ChatTranscript';

export function ChatPane({
  allowEmptyCreate = true,
}: {
  allowEmptyCreate?: boolean;
}) {
  const activeId = useChatStore((s) => s.activeId);
  const messages = useChatStore((s) => s.messages);
  const pluginId = useChatStore((s) => s.pluginId);
  const streaming = useChatStore((s) => s.streaming);
  const statusText = useChatStore((s) => s.statusText);
  const error = useChatStore((s) => s.error);
  const loading = useChatStore((s) => s.loading);
  const loadPlugins = useChatStore((s) => s.loadPlugins);
  const send = useChatStore((s) => s.send);

  const scroller = useRef<HTMLDivElement>(null);
  const pinBottom = useRef(true);
  const meta = AGENT_META[pluginId];

  useEffect(() => {
    void loadPlugins();
  }, [loadPlugins]);

  useEffect(() => {
    const el = scroller.current;
    if (!el || !pinBottom.current) return;
    el.scrollTop = el.scrollHeight;
  }, [messages, statusText]);

  const onScroll = () => {
    const el = scroller.current;
    if (!el) return;
    pinBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  };

  const emptyHome = allowEmptyCreate && !activeId && !loading;
  const emptyTask = Boolean(activeId) && messages.length === 0 && !loading && !streaming;
  const showWelcome = emptyHome || emptyTask;

  return (
    <div className="om-chat">
      <div className="om-chat-scroll" ref={scroller} onScroll={onScroll}>
        {showWelcome ? (
          <div className="om-chat-empty">
            <EmptyState
              icon={
                pluginId === 'opencode' ? (
                  <CodeOutlined style={{ fontSize: 28, color: 'var(--accent)' }} />
                ) : (
                  <RobotOutlined style={{ fontSize: 28, color: 'var(--accent)' }} />
                )
              }
              title={meta.name}
              description={meta.blurb}
            />
            <div className="om-kicker">可以这样问</div>
            <div className="om-chat-hints">
              {meta.hints.map((h) => (
                <button key={h} type="button" className="om-chat-hint-chip" onClick={() => void send(h)}>
                  {h}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <ChatTranscript messages={messages} streaming={streaming} statusText={statusText} />
        )}
        {error ? <div className="om-chat-error om-chat-error-bar">{error}</div> : null}
      </div>
      <ChatComposer />
    </div>
  );
}
