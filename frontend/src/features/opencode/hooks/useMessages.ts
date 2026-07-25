import { useCallback, useEffect } from 'react';
import * as oc from '../client';
import type { OcMessagesEnvelope } from '../types';
import { useOpencodeStore } from '../stores/opencodeStore';

const EMPTY: OcMessagesEnvelope[] = [];

export function useMessages(sessionId: string | null) {
  const setMessages = useOpencodeStore((s) => s.setMessages);
  // ⚠️ 不能返回 `?? []`—— 每次是新数组，会触发 getSnapshot cache 失效、无限重渲染。
  const messages = useOpencodeStore((s) =>
    sessionId ? s.messagesBySession[sessionId] ?? EMPTY : EMPTY,
  );

  const load = useCallback(async () => {
    if (!sessionId) return;
    const list = await oc.listMessages(sessionId);
    setMessages(sessionId, list);
  }, [sessionId, setMessages]);

  useEffect(() => {
    void load();
  }, [load]);

  return { messages, reload: load };
}
