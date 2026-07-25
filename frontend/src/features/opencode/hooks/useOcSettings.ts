/**
 * useOcSettings — 前端偏好开关 (localStorage) + opencode 服务端 shell 覆盖.
 *
 * 前端渲染开关（不发到 server，UI 层用）：
 *   - showReasoningSummaries: 消息里是否显示 reasoning part
 *   - expandShellTool: 默认展开 shell 工具的 output pre
 *   - expandEditTool:  默认展开 edit / write / patch 工具的 output pre
 *   - newLayoutDesigns: 保留字段，本项目已经是 new layout（一直 true）
 *
 * 服务端偏好（通过 PATCH /config 写到 opencode server）：
 *   - shell: 'auto' | 'bash' | 'zsh' | 'fish' | 'sh' | 'pwsh'
 *
 * 组件用法：
 *   const { settings, set, updateShell } = useOcSettings();
 */
import { useCallback, useEffect, useState } from 'react';
import * as oc from '../client';

const LS_KEY = 'oc:ui-settings';

export type ShellOption = 'auto' | 'bash' | 'zsh' | 'fish' | 'sh' | 'pwsh';

export interface OcSettings {
  shell: ShellOption;
  showReasoningSummaries: boolean;
  expandShellTool: boolean;
  expandEditTool: boolean;
  newLayoutDesigns: boolean;
}

export const DEFAULT_SETTINGS: OcSettings = {
  shell: 'auto',
  showReasoningSummaries: false,
  expandShellTool: false,
  expandEditTool: false,
  newLayoutDesigns: true,
};

function load(): OcSettings {
  if (typeof window === 'undefined') return DEFAULT_SETTINGS;
  try {
    const raw = window.localStorage.getItem(LS_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    const j = JSON.parse(raw) as Partial<OcSettings>;
    return { ...DEFAULT_SETTINGS, ...j };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

function save(s: OcSettings): void {
  try {
    window.localStorage.setItem(LS_KEY, JSON.stringify(s));
    // 通知同一页面其它 hook 实例
    window.dispatchEvent(new CustomEvent<OcSettings>('oc:settings-change', { detail: s }));
  } catch {
    /* ignore */
  }
}

export function useOcSettings() {
  const [settings, setSettings] = useState<OcSettings>(() => load());

  // 订阅跨组件变更
  useEffect(() => {
    const onChange = (e: Event) => {
      const d = (e as CustomEvent<OcSettings>).detail;
      if (d) setSettings(d);
    };
    const onStorage = (e: StorageEvent) => {
      if (e.key === LS_KEY) setSettings(load());
    };
    window.addEventListener('oc:settings-change', onChange as EventListener);
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener('oc:settings-change', onChange as EventListener);
      window.removeEventListener('storage', onStorage);
    };
  }, []);

  const set = useCallback(<K extends keyof OcSettings>(key: K, value: OcSettings[K]) => {
    setSettings((prev) => {
      const next = { ...prev, [key]: value };
      save(next);
      return next;
    });
  }, []);

  /**
   * shell 特殊：更新本地 + PATCH 到 opencode server.
   * 'auto' 时下发 null（让 server 用默认逻辑）；否则传具体 shell 名.
   */
  const updateShell = useCallback(async (shell: ShellOption) => {
    set('shell', shell);
    try {
      await oc.patchConfig({ shell: shell === 'auto' ? null : shell });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('[oc] patch shell to server failed:', err);
    }
  }, [set]);

  return { settings, set, updateShell };
}
