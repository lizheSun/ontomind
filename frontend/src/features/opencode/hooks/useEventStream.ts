/**
 * 全局 SSE 事件订阅 — 建议在 <ChatWorkspaceShell> 挂载一次，全局共享.
 * 断线自动重连，指数退避 (≤30s).
 */
import { useEffect, useRef } from 'react';
import { subscribeEvents } from '../client';
import { useOpencodeStore } from '../stores/opencodeStore';

export function useEventStream(enabled: boolean = true) {
  const dispatch = useOpencodeStore((s) => s.dispatchEvent);
  const attemptRef = useRef(0);

  useEffect(() => {
    if (!enabled) return;
    let es: EventSource | null = null;
    let reconnectTimer: number | undefined;
    let cancelled = false;

    const connect = () => {
      if (cancelled) return;
      es = subscribeEvents(
        (evt) => {
          attemptRef.current = 0; // 收到事件即视为健康
          dispatch(evt);
        },
        () => {
          // onerror: 关掉当前 ES，指数退避重连
          es?.close();
          es = null;
          const wait = Math.min(30000, 1000 * 2 ** attemptRef.current);
          attemptRef.current += 1;
          reconnectTimer = window.setTimeout(connect, wait);
        },
      );
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      es?.close();
    };
  }, [enabled, dispatch]);
}
