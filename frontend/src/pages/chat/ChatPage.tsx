/**
 * 统一会话 — 原生聊天，OpenCode / DSH 作为插件。
 * 不嵌入 AIDE iframe。
 */
import { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useChatStore } from '../../stores/chatStore';
import { ChatPane } from './ChatPane';

export default function ChatPage() {
  const select = useChatStore((s) => s.select);
  const [params] = useSearchParams();

  useEffect(() => {
    const raw = params.get('session');
    if (!raw) return;
    const id = Number(raw);
    if (!Number.isFinite(id) || id <= 0) return;
    void (async () => {
      await useChatStore.getState().loadSessions();
      await select(id);
    })();
  }, [params, select]);

  return <ChatPane />;
}
