import { useCallback, useEffect, useState } from 'react';
import { Button, Tooltip } from 'antd';
import { EyeOutlined, EyeInvisibleOutlined } from '@ant-design/icons';

/**
 * T58 · Zen / God dual mode + progressive disclosure.
 *
 * Zen 模式（闭眼）：简洁卡片，隐藏 JSON / 日志 / 技术细节。
 * God 模式（睁眼）：显示所有原始数据 / 高级面板。
 *
 * 全局单一入口，通过：
 * 1. localStorage['ui:mode'] 持久化；
 * 2. <html data-ui-mode="zen|god"> 供 CSS 直接命中（`[data-ui-mode="zen"] .god-only { display:none }`）；
 * 3. window CustomEvent('ui:mode-change') 供 JS 订阅；
 * 4. `useUIMode` hook 供组件反应式读取；
 * 5. `useProgressiveDisclosure(key, threshold)` 用于渐进式披露：
 *    只有当用户使用某功能 >= threshold 次后，或已进入 God 模式，才返回 true。
 */

export type UIMode = 'zen' | 'god';

const STORAGE_KEY = 'ui:mode';
const EVENT_NAME = 'ui:mode-change';
const USAGE_PREFIX = 'ui:usage:';
const DEFAULT_MODE: UIMode = 'zen';

function readModeFromStorage(): UIMode {
  if (typeof window === 'undefined') return DEFAULT_MODE;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw === 'god' ? 'god' : 'zen';
  } catch {
    return DEFAULT_MODE;
  }
}

function writeModeToStorage(mode: UIMode): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, mode);
  } catch {
    /* localStorage 不可用则忽略 */
  }
}

function applyModeToDom(mode: UIMode): void {
  if (typeof document === 'undefined') return;
  document.documentElement.setAttribute('data-ui-mode', mode);
}

/** 全局切换模式（外部调用 API）。 */
export function setUIMode(mode: UIMode): void {
  writeModeToStorage(mode);
  applyModeToDom(mode);
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent<UIMode>(EVENT_NAME, { detail: mode }));
  }
}

/** 读取当前 UI 模式的 hook；订阅 storage / CustomEvent 变更。 */
export function useUIMode(): [UIMode, (mode: UIMode) => void] {
  const [mode, setModeState] = useState<UIMode>(() => readModeFromStorage());

  useEffect(() => {
    applyModeToDom(mode);
  }, [mode]);

  useEffect(() => {
    const onCustom = (e: Event): void => {
      const detail = (e as CustomEvent<UIMode>).detail;
      if (detail === 'zen' || detail === 'god') {
        setModeState(detail);
      }
    };
    const onStorage = (e: StorageEvent): void => {
      if (e.key === STORAGE_KEY) {
        setModeState(e.newValue === 'god' ? 'god' : 'zen');
      }
    };
    window.addEventListener(EVENT_NAME, onCustom as EventListener);
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener(EVENT_NAME, onCustom as EventListener);
      window.removeEventListener('storage', onStorage);
    };
  }, []);

  const update = useCallback((next: UIMode) => {
    setUIMode(next);
    setModeState(next);
  }, []);

  return [mode, update];
}

/**
 * 渐进式披露：只有当用户对某功能的使用计数达到 `threshold`
 * （或用户处于 God 模式）时，返回 `true`。
 *
 * @param key       功能唯一标识（用于 localStorage bucket）
 * @param threshold 触发阈值，默认 3
 * @returns [visible, bump]  visible=当前是否披露；bump=+1 计数并可能触发披露
 */
export function useProgressiveDisclosure(
  key: string,
  threshold = 3,
): [boolean, () => void] {
  const [mode] = useUIMode();
  const storageKey = `${USAGE_PREFIX}${key}`;

  const readCount = useCallback((): number => {
    if (typeof window === 'undefined') return 0;
    try {
      const raw = window.localStorage.getItem(storageKey);
      const n = raw === null ? 0 : Number.parseInt(raw, 10);
      return Number.isFinite(n) && n >= 0 ? n : 0;
    } catch {
      return 0;
    }
  }, [storageKey]);

  const [count, setCount] = useState<number>(() => readCount());

  const bump = useCallback((): void => {
    const next = readCount() + 1;
    try {
      window.localStorage.setItem(storageKey, String(next));
    } catch {
      /* ignore */
    }
    setCount(next);
  }, [readCount, storageKey]);

  const visible = mode === 'god' || count >= threshold;
  return [visible, bump];
}

export interface ZenGodToggleProps {
  /**
   * 是否以固定位置浮动挂载（默认 true）。false 时以内联按钮渲染，便于放进 HeaderBar。
   */
  floating?: boolean;
  /**
   * 自定义样式（floating=true 时叠加到 fixed 容器上）。
   */
  style?: React.CSSProperties;
  /**
   * 无障碍标签前缀。
   */
  ariaLabelPrefix?: string;
}

/**
 * 全局 Zen/God 切换按钮：眼睛图标。
 * Zen=闭眼 (EyeInvisibleOutlined)，God=睁眼 (EyeOutlined)。
 */
export function ZenGodToggle(props: ZenGodToggleProps = {}): React.ReactElement {
  const { floating = true, style, ariaLabelPrefix = '界面模式' } = props;
  const [mode, setMode] = useUIMode();

  const isGod = mode === 'god';
  const nextMode: UIMode = isGod ? 'zen' : 'god';
  const label = isGod ? '当前 God 模式，点击切换到 Zen' : '当前 Zen 模式，点击切换到 God';

  const button = (
    <Tooltip title={label} placement="bottomRight">
      <Button
        type="text"
        shape="circle"
        aria-label={`${ariaLabelPrefix}: ${isGod ? 'God' : 'Zen'}`}
        aria-pressed={isGod}
        data-ui-mode-toggle={mode}
        icon={isGod ? <EyeOutlined /> : <EyeInvisibleOutlined />}
        onClick={() => setMode(nextMode)}
      />
    </Tooltip>
  );

  if (!floating) return button;

  return (
    <div
      style={{
        position: 'fixed',
        top: 12,
        right: 16,
        zIndex: 1200,
        pointerEvents: 'auto',
        ...style,
      }}
    >
      {button}
    </div>
  );
}

export default ZenGodToggle;
