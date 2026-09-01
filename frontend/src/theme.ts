import { theme, type ThemeConfig } from 'antd';

export type ColorMode = 'dark' | 'light';

const STORAGE_KEY = 'om-theme';
const EVENT_NAME = 'om:theme-change';

/** 与本地 Yao CUI（:5091）一致：Outfit + #3371fc */
export const FONT_SANS =
  "Outfit, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans SC', sans-serif";
export const FONT_MONO =
  "'IBM Plex Mono', 'SF Mono', 'JetBrains Mono', Menlo, Monaco, monospace";

export const ACCENT = '#3371fc';
export const ACCENT_HOVER = '#4580ff';
export const ACCENT_ACTIVE = '#2861e6';

export function readColorMode(): ColorMode {
  if (typeof window === 'undefined') return 'light';
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === 'light' || raw === 'dark') return raw;
  } catch {
    /* ignore */
  }
  return 'light';
}

export function applyColorMode(mode: ColorMode): void {
  if (typeof document === 'undefined') return;
  document.documentElement.setAttribute('data-theme', mode);
  document.documentElement.style.colorScheme = mode;
}

export function setColorMode(mode: ColorMode): void {
  try {
    localStorage.setItem(STORAGE_KEY, mode);
  } catch {
    /* ignore */
  }
  applyColorMode(mode);
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent<ColorMode>(EVENT_NAME, { detail: mode }));
  }
}

export function onColorModeChange(fn: (mode: ColorMode) => void): () => void {
  const handler = (e: Event) => {
    const detail = (e as CustomEvent<ColorMode>).detail;
    if (detail === 'light' || detail === 'dark') fn(detail);
  };
  window.addEventListener(EVENT_NAME, handler);
  return () => window.removeEventListener(EVENT_NAME, handler);
}

export function getAntdTheme(mode: ColorMode): ThemeConfig {
  const dark = mode === 'dark';
  return {
    algorithm: dark ? theme.darkAlgorithm : theme.defaultAlgorithm,
    token: {
      fontFamily: FONT_SANS,
      colorPrimary: dark ? '#4580ff' : ACCENT,
      borderRadius: 6,
      colorText: dark ? '#e0e0e0' : '#111111',
      colorTextSecondary: dark ? '#a0a0a0' : '#666666',
      colorBgContainer: dark ? '#2f2f34' : '#ffffff',
      colorBgLayout: dark ? '#3b3b41' : '#f0f0f0',
      colorBgElevated: dark ? '#2f2f34' : '#ffffff',
      colorBorder: dark ? '#404046' : '#e6e6e6',
      colorBorderSecondary: dark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
      controlHeight: 32,
      controlHeightLG: 40,
    },
    components: {
      Button: { borderRadius: 6, primaryShadow: 'none' },
      Card: { borderRadiusLG: 9 },
      Modal: { borderRadiusLG: 9 },
      Tag: { borderRadiusSM: 4 },
      Input: { borderRadius: 6 },
    },
  };
}
