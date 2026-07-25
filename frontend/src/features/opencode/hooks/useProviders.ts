import { useCallback, useEffect, useState } from 'react';
import * as oc from '../client';

export interface ProviderModelInfo {
  id: string;
  name: string;
  family?: string;
}
export interface ProviderInfo {
  id: string;
  name: string;
  models: ProviderModelInfo[];
}

export function useProviders() {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [defaults, setDefaults] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await oc.listProviders();
      setProviders(
        (resp.providers || []).map((p) => ({
          id: p.id,
          name: p.name || p.id,
          models: Object.entries(p.models || {}).map(([id, m]) => ({
            id,
            name: m?.name || id,
            family: m?.family,
          })),
        })),
      );
      setDefaults(resp.default || {});
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { providers, defaults, loading, reload: load };
}
