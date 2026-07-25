import { useCallback } from 'react';
import * as oc from '../client';
import type { OcPart } from '../types';
import { useOpencodeStore } from '../stores/opencodeStore';

export function useSendPrompt() {
  const setStreaming = useOpencodeStore((s) => s.setStreaming);
  const setError = useOpencodeStore((s) => s.setError);

  return useCallback(
    async (
      sessionId: string,
      text: string,
      opts: {
        model?: { providerID: string; modelID: string };
        agent?: string;
        extraParts?: OcPart[];
      } = {},
    ) => {
      // 从 store 拉取用户在 UI 里选中的 agent / model；opts 可覆盖
      const state = useOpencodeStore.getState();
      const agent = opts.agent ?? state.currentAgent;
      const model = opts.model ?? state.currentModel ?? undefined;

      const parts: OcPart[] = [{ type: 'text', text }, ...(opts.extraParts ?? [])];
      try {
        setStreaming(true);
        await oc.sendPromptAsync(sessionId, {
          parts,
          model: model || undefined,
          agent: agent || undefined,
        });
      } catch (err) {
        setStreaming(false);
        setError(err instanceof Error ? err.message : String(err));
        throw err;
      }
    },
    [setStreaming, setError],
  );
}
