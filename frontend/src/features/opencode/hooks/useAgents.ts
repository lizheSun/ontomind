import { useCallback, useEffect, useState } from 'react';
import * as oc from '../client';
import type { OcAgent } from '../types';

export function useAgents() {
  const [agents, setAgents] = useState<OcAgent[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await oc.listAgents();
      setAgents(list);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { agents, loading, reload: load };
}
