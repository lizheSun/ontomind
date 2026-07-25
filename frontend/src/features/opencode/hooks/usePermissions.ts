import { useCallback } from 'react';
import * as oc from '../client';
import type { OcPermissionResponse } from '../types';
import { useOpencodeStore } from '../stores/opencodeStore';

export function usePermissions() {
  const pending = useOpencodeStore((s) => s.pendingPermissions);
  const remove = useOpencodeStore((s) => s.removePermission);

  const respond = useCallback(
    async (permissionId: string, response: OcPermissionResponse, remember = false) => {
      const perm = pending.find((p) => p.id === permissionId);
      if (!perm) return;
      await oc.respondPermission(perm.sessionID, permissionId, response, remember);
      remove(permissionId);
    },
    [pending, remove],
  );

  return { pending, respond };
}
