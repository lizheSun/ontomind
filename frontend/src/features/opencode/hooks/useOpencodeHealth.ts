/**
 * 探活本机 opencode server，通过后端 /opencode/health 走一次（避免 CORS 探测坑）.
 * 用于路由守卫（OpencodeGuard）。
 */
import { useCallback, useEffect, useState } from 'react';
import api from '../../../services/api';
import { useOpencodeStore } from '../stores/opencodeStore';

export interface OpencodeHealthState {
  loading: boolean;
  healthy: boolean;
  baseUrl?: string;
  version?: string;
  reason?: string;
  refresh: () => Promise<void>;
}

export function useOpencodeHealth(pollMs: number | null = null): OpencodeHealthState {
  const [loading, setLoading] = useState(true);
  const [healthy, setHealthy] = useState(false);
  const [baseUrl, setBaseUrl] = useState<string | undefined>();
  const [version, setVersion] = useState<string | undefined>();
  const [reason, setReason] = useState<string | undefined>();
  const setServerStatus = useOpencodeStore((s) => s.setServerStatus);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await api.get('/opencode/health');
      const data = resp.data?.data ?? {};
      setHealthy(!!data.healthy);
      setBaseUrl(data.base_url);
      setVersion(data.version);
      setReason(data.reason);
      setServerStatus(!!data.healthy, data.version, data.base_url);
    } catch (err) {
      setHealthy(false);
      setReason(err instanceof Error ? err.message : String(err));
      setServerStatus(false);
    } finally {
      setLoading(false);
    }
  }, [setServerStatus]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!pollMs) return;
    const t = window.setInterval(() => void refresh(), pollMs);
    return () => window.clearInterval(t);
  }, [pollMs, refresh]);

  return { loading, healthy, baseUrl, version, reason, refresh };
}
