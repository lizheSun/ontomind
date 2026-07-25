import { useCallback, useEffect, useState } from 'react';
import * as oc from '../client';
import type { OcCommand } from '../types';

export function useCommands() {
  const [commands, setCommands] = useState<OcCommand[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await oc.listCommands();
      setCommands(list);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { commands, loading, reload: load };
}
