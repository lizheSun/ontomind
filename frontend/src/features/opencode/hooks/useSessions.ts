/**
 * 会话 CRUD hook.
 * 同时把 opencode session.id 通过后端 /opencode/session-link 记录到业务侧.
 */
import { useCallback, useEffect } from 'react';
import * as oc from '../client';
import api from '../../../services/api';
import { useOpencodeStore } from '../stores/opencodeStore';

export function useSessions() {
  const setSessions = useOpencodeStore((s) => s.setSessions);
  const upsertSession = useOpencodeStore((s) => s.upsertSession);
  const removeSession = useOpencodeStore((s) => s.removeSession);
  const setActive = useOpencodeStore((s) => s.setActiveSession);
  const sessions = useOpencodeStore((s) => s.sessions);
  const activeSessionId = useOpencodeStore((s) => s.activeSessionId);

  const load = useCallback(async () => {
    const list = await oc.listSessions();
    setSessions(list);
  }, [setSessions]);

  const create = useCallback(
    async (title?: string, projectId?: number) => {
      const s = await oc.createSession({ title });
      upsertSession(s);
      setActive(s.id);

      // 业务侧映射（异步，不阻塞 UI）
      api
        .post('/opencode/session-link', {
          opencode_session_id: s.id,
          project_id: projectId,
          title: s.title,
        })
        .catch(() => {
          /* 业务映射失败不影响对话使用 */
        });

      return s;
    },
    [upsertSession, setActive],
  );

  const remove = useCallback(
    async (id: string) => {
      await oc.deleteSession(id);
      removeSession(id);
    },
    [removeSession],
  );

  const rename = useCallback(
    async (id: string, title: string) => {
      const s = await oc.updateSession(id, { title });
      upsertSession(s);
      // 同步业务侧 title
      api
        .post('/opencode/session-link', {
          opencode_session_id: id,
          title,
        })
        .catch(() => undefined);
      return s;
    },
    [upsertSession],
  );

  const select = useCallback((id: string | null) => setActive(id), [setActive]);

  useEffect(() => {
    void load();
  }, [load]);

  // 首次加载/列表变化后：若当前选中不在列表，重置到第一条（或 null）
  useEffect(() => {
    if (sessions.length === 0) {
      if (activeSessionId) setActive(null);
      return;
    }
    if (!activeSessionId || !sessions.find((s) => s.id === activeSessionId)) {
      setActive(sessions[0].id);
    }
  }, [activeSessionId, sessions, setActive]);

  return { sessions, activeSessionId, load, create, remove, rename, select };
}
