import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Input, Modal, Tag, Typography } from 'antd';
import {
  LogoutOutlined,
  RobotOutlined,
  SearchOutlined,
  TeamOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';

const { Text } = Typography;

type OmnibarMode = 'nav' | 'act' | 'kb';

interface OmnibarItem {
  id: string;
  label: string;
  hint?: string;
  keywords?: string[];
  icon: React.ReactNode;
  mode: OmnibarMode;
  /** Route that owns this item — used for context-aware boosting. */
  scope?: string;
  run: () => void;
}

/**
 * Full navigation catalogue mirroring the routes registered in App.tsx.
 * Kept in-file (no runtime dependency on the router config) so the omnibar
 * remains self-contained and easy to unit-test.
 */
function buildNavItems(navigate: (to: string) => void): OmnibarItem[] {
  return [
    {
      id: 'nav:/aide',
      label: 'AIDE',
      hint: '/aide',
      keywords: ['aide', 'ide', 'opencode', '编辑器', 'editor', '开发'],
      icon: <RobotOutlined />,
      mode: 'nav',
      scope: '/aide',
      run: () => navigate('/aide'),
    },
    {
      id: 'nav:/users',
      label: '用户管理',
      hint: '/users',
      keywords: ['users', '用户', 'yonghu'],
      icon: <TeamOutlined />,
      mode: 'nav',
      scope: '/users',
      run: () => navigate('/users'),
    },
  ];
}

function buildActionItems(
  navigate: (to: string) => void,
  onClose: () => void,
): OmnibarItem[] {
  return [
    {
      id: 'act:logout',
      label: '退出登录',
      hint: '清除 token 并跳转到登录页',
      keywords: ['logout', 'signout', '退出', 'tuichu'],
      icon: <LogoutOutlined />,
      mode: 'act',
      run: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        onClose();
        navigate('/login');
      },
    },
    {
      id: 'act:reload',
      label: '刷新当前页',
      hint: 'window.location.reload()',
      keywords: ['reload', 'refresh', '刷新', 'shuaxin'],
      icon: <UnorderedListOutlined />,
      mode: 'act',
      run: () => {
        onClose();
        window.location.reload();
      },
    },
    {
      id: 'act:copy-url',
      label: '复制当前页 URL',
      hint: 'navigator.clipboard.writeText',
      keywords: ['copy', 'url', 'link', '复制', '链接'],
      icon: <UnorderedListOutlined />,
      mode: 'act',
      run: () => {
        if (typeof navigator !== 'undefined' && navigator.clipboard) {
          navigator.clipboard.writeText(window.location.href).catch(() => {});
        }
        onClose();
      },
    },
    {
      id: 'act:kb-search',
      label: '跳转到语义搜索',
      hint: '/knowledge-base/search',
      keywords: ['search', 'semantic', '搜索', 'kb'],
      icon: <SearchOutlined />,
      mode: 'act',
      run: () => navigate('/knowledge-base/search'),
    },
  ];
}

function detectMode(raw: string): { mode: OmnibarMode; query: string } {
  if (raw.startsWith('>')) return { mode: 'act', query: raw.slice(1).trim() };
  if (raw.startsWith('?')) return { mode: 'kb', query: raw.slice(1).trim() };
  return { mode: 'nav', query: raw.trim() };
}

/**
 * Case-insensitive substring match against label + keywords + hint.
 * Returns a numeric score for ranking (higher is better), or -1 if no match.
 */
function scoreItem(item: OmnibarItem, query: string, currentPath: string): number {
  if (!query) {
    // Empty query → surface everything; boost items in the current scope.
    return item.scope && currentPath.startsWith(item.scope) ? 10 : 0;
  }
  const q = query.toLowerCase();
  const label = item.label.toLowerCase();
  const hint = (item.hint ?? '').toLowerCase();
  const keywords = (item.keywords ?? []).map((k) => k.toLowerCase());

  let score = -1;
  if (label === q) score = Math.max(score, 100);
  if (label.startsWith(q)) score = Math.max(score, 80);
  if (label.includes(q)) score = Math.max(score, 60);
  if (hint.includes(q)) score = Math.max(score, 40);
  if (keywords.some((k) => k.startsWith(q))) score = Math.max(score, 55);
  if (keywords.some((k) => k.includes(q))) score = Math.max(score, 30);

  if (score >= 0 && item.scope && currentPath.startsWith(item.scope)) {
    score += 5;
  }
  return score;
}

export interface CmdKOmnibarProps {
  /** Optional externally-controlled open state; when omitted the omnibar owns its state. */
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function CmdKOmnibar({ open: controlledOpen, onOpenChange }: CmdKOmnibarProps = {}) {
  const navigate = useNavigate();
  const location = useLocation();

  const [internalOpen, setInternalOpen] = useState(false);
  const isControlled = controlledOpen !== undefined;
  const open = isControlled ? controlledOpen : internalOpen;

  const setOpen = useCallback(
    (next: boolean) => {
      if (!isControlled) setInternalOpen(next);
      onOpenChange?.(next);
    },
    [isControlled, onOpenChange],
  );

  const close = useCallback(() => setOpen(false), [setOpen]);

  const [rawQuery, setRawQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const items = useMemo<OmnibarItem[]>(
    () => [...buildNavItems(navigate), ...buildActionItems(navigate, close)],
    [navigate, close],
  );

  // Global Cmd+K / Ctrl+K listener.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const isCmdK = (e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K');
      if (isCmdK) {
        e.preventDefault();
        setOpen(!open);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, setOpen]);

  // Reset query + focus when re-opened.
  useEffect(() => {
    if (open) {
      setRawQuery('');
      setActiveIndex(0);
      // Focus after Modal finishes animating in.
      const t = setTimeout(() => inputRef.current?.focus(), 50);
      return () => clearTimeout(t);
    }
    return undefined;
  }, [open]);

  const { mode, query } = useMemo(() => detectMode(rawQuery), [rawQuery]);

  const results = useMemo<OmnibarItem[]>(() => {
    if (mode === 'kb') {
      // KB search is a single synthetic action that jumps to /knowledge-base/search?q=...
      const kbItem: OmnibarItem = {
        id: 'kb:go',
        label: query ? `在知识库中搜索 "${query}"` : '打开知识库搜索',
        hint: query
          ? `/knowledge-base/search?q=${encodeURIComponent(query)}`
          : '/knowledge-base/search',
        icon: <SearchOutlined />,
        mode: 'kb',
        run: () => {
          const path = query
            ? `/knowledge-base/search?q=${encodeURIComponent(query)}`
            : '/knowledge-base/search';
          navigate(path);
          close();
        },
      };
      return [kbItem];
    }

    const filtered = items.filter((it) => it.mode === mode);
    const scored = filtered
      .map((it) => ({ it, s: scoreItem(it, query, location.pathname) }))
      .filter(({ s }) => s >= 0);
    scored.sort((a, b) => b.s - a.s || a.it.label.localeCompare(b.it.label));
    return scored.slice(0, 20).map(({ it }) => it);
  }, [items, mode, query, location.pathname, navigate, close]);

  // Clamp active index when results shrink.
  useEffect(() => {
    if (activeIndex >= results.length) {
      setActiveIndex(results.length > 0 ? results.length - 1 : 0);
    }
  }, [results, activeIndex]);

  const runActive = useCallback(() => {
    const target = results[activeIndex];
    if (!target) return;
    target.run();
    // KB and act items may close themselves; nav items should also close.
    close();
  }, [results, activeIndex, close]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIndex((i) => (results.length ? (i + 1) % results.length : 0));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIndex((i) =>
          results.length ? (i - 1 + results.length) % results.length : 0,
        );
      } else if (e.key === 'Enter') {
        e.preventDefault();
        runActive();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        close();
      }
    },
    [results.length, runActive, close],
  );

  const modeLabel: Record<OmnibarMode, { text: string; color: string }> = {
    nav: { text: '导航', color: 'blue' },
    act: { text: '操作 (>)', color: 'purple' },
    kb: { text: '知识库 (?)', color: 'green' },
  };

  return (
    <Modal
      open={open}
      onCancel={close}
      footer={null}
      closable={false}
      destroyOnHidden
      width={640}
      styles={{
        body: { padding: 0, background: '#0a0f1f' },
      }}
      style={{ top: 96 }}
      mask={{ closable: true }}
    >
      <div
        style={{
          padding: '12px 14px 8px 14px',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}
      >
        <Tag color={modeLabel[mode].color} style={{ margin: 0 }}>
          {modeLabel[mode].text}
        </Tag>
        <Input
          ref={(el) => {
            inputRef.current = el?.input ?? null;
          }}
          variant="borderless"
          size="large"
          prefix={<SearchOutlined style={{ color: 'rgba(255,255,255,0.4)' }} />}
          placeholder="跳转页面 · 输入 > 执行动作 · 输入 ? 搜知识库"
          value={rawQuery}
          onChange={(e) => {
            setRawQuery(e.target.value);
            setActiveIndex(0);
          }}
          onKeyDown={handleKeyDown}
          autoFocus
          aria-label="Cmd+K omnibar"
        />
      </div>

      <div
        role="listbox"
        aria-label="omnibar-results"
        style={{ maxHeight: 420, overflowY: 'auto', padding: '6px 0' }}
      >
        {results.length === 0 && (
          <div style={{ padding: '24px 16px', textAlign: 'center' }}>
            <Text type="secondary">无匹配结果</Text>
          </div>
        )}
        {results.map((item, i) => {
          const active = i === activeIndex;
          return (
            <div
              key={item.id}
              role="option"
              aria-selected={active}
              onMouseEnter={() => setActiveIndex(i)}
              onClick={() => {
                setActiveIndex(i);
                item.run();
                close();
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '10px 16px',
                cursor: 'pointer',
                background: active ? 'rgba(59,130,246,0.14)' : 'transparent',
                borderLeft: active
                  ? '2px solid #3b82f6'
                  : '2px solid transparent',
              }}
            >
              <span
                style={{
                  fontSize: 16,
                  color: active ? '#60a5fa' : 'rgba(255,255,255,0.6)',
                  width: 20,
                  display: 'inline-flex',
                  justifyContent: 'center',
                }}
              >
                {item.icon}
              </span>
              <span style={{ flex: 1, minWidth: 0 }}>
                <div style={{ color: '#e8eef5', fontSize: 13, fontWeight: 500 }}>
                  {item.label}
                </div>
                {item.hint && (
                  <div
                    style={{
                      color: 'rgba(255,255,255,0.45)',
                      fontSize: 11,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {item.hint}
                  </div>
                )}
              </span>
              {item.scope && location.pathname.startsWith(item.scope) && (
                <Tag color="geekblue" style={{ margin: 0, fontSize: 10 }}>
                  当前
                </Tag>
              )}
            </div>
          );
        })}
      </div>

      <div
        style={{
          borderTop: '1px solid rgba(255,255,255,0.06)',
          padding: '8px 14px',
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: 11,
          color: 'rgba(255,255,255,0.45)',
        }}
      >
        <span>↑↓ 选择 · ↵ 执行 · Esc 关闭</span>
        <span>⌘K / Ctrl+K 唤起</span>
      </div>
    </Modal>
  );
}

export default CmdKOmnibar;
