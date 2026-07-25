/**
 * `@` 文件模糊搜索（debounce 200ms）.
 */
import { useCallback, useEffect, useState } from 'react';
import * as oc from '../client';

export function useFilesMention(query: string, opts: { limit?: number } = {}) {
  const [results, setResults] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const run = useCallback(
    async (q: string) => {
      if (!q.trim()) {
        setResults([]);
        return;
      }
      setLoading(true);
      try {
        const list = await oc.findFiles(q, { type: 'file', limit: opts.limit ?? 20 });
        setResults(list);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    },
    [opts.limit],
  );

  useEffect(() => {
    const t = window.setTimeout(() => void run(query), 200);
    return () => window.clearTimeout(t);
  }, [query, run]);

  return { results, loading };
}
