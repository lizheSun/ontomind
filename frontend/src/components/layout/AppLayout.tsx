/**
 * 平台主布局 — 对齐 Yao Assistants 三栏：图标轨 64 + 上下文 256 + 内容。
 */
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Avatar, Dropdown, Tooltip } from 'antd';
import type { MenuProps } from 'antd';
import {
  ApiOutlined,
  AppstoreOutlined,
  DesktopOutlined,
  CodeOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  LogoutOutlined,
  MessageOutlined,
  MoonOutlined,
  RightOutlined,
  RobotOutlined,
  SafetyOutlined,
  SearchOutlined,
  SunOutlined,
  UserOutlined,
} from '@ant-design/icons';
import useUserStore from '../../stores/userStore';
import AideHost from './AideHost';
import { BrandMark } from '../common/BrandMark';
import { CmdKOmnibar } from '../common/CmdKOmnibar';
import { ChatSessionRail } from '../../pages/chat/ChatSessionRail';
import {
  DOMAINS,
  RAIL_W,
  SIDEBAR_W,
  domainHome,
  findDomain,
  type DomainDef,
} from '../../nav';
import {
  readColorMode,
  setColorMode,
  onColorModeChange,
  applyColorMode,
  type ColorMode,
} from '../../theme';

const DOMAIN_ICONS: Record<string, ReactNode> = {
  overview: <DashboardOutlined />,
  chat: <MessageOutlined />,
  board: <AppstoreOutlined />,
  codeops: <CodeOutlined />,
  dataops: <DatabaseOutlined />,
  modelops: <RobotOutlined />,
  agentops: <ApiOutlined />,
  govops: <SafetyOutlined />,
  infra: <DesktopOutlined />,
};

const QUICK_PROMPTS = [
  { label: '打开任务看板', to: '/board' },
  { label: '打开统一会话（OpenCode / DSH）', to: '/chat' },
  { label: '打开 AIDE 编码环境', to: '/infra/aide' },
  { label: '配置当前生效的 LLM', to: '/govops/llm' },
  { label: '设计一个 Agent 并发布', to: '/agentops/agents' },
];

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { currentUser, fetchCurrentUser } = useUserStore();
  const [expandedSubs, setExpandedSubs] = useState<Set<string>>(new Set());
  const [cmdOpen, setCmdOpen] = useState(false);
  const [mode, setMode] = useState<ColorMode>(() => readColorMode());

  useEffect(() => {
    applyColorMode(mode);
    return onColorModeChange(setMode);
  }, [mode]);

  useEffect(() => {
    if (!currentUser) fetchCurrentUser();
  }, [currentUser, fetchCurrentUser]);

  const currentDomain = useMemo(() => findDomain(location.pathname), [location.pathname]);

  useEffect(() => {
    const path = location.pathname;
    for (const sub of currentDomain.sub) {
      if (sub.children?.some((c) => path.startsWith(c.key))) {
        setExpandedSubs((prev) => {
          if (prev.has(sub.key)) return prev;
          const next = new Set(prev);
          next.add(sub.key);
          return next;
        });
      }
    }
  }, [location.pathname, currentDomain]);

  const toggleExpand = useCallback((key: string) => {
    setExpandedSubs((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const goDomain = useCallback(
    (d: DomainDef) => navigate(domainHome(d)),
    [navigate],
  );

  const userMenu: MenuProps['items'] = [
    { key: 'users', icon: <UserOutlined />, label: '用户管理' },
    { type: 'divider' },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录' },
  ];

  const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
    if (key === 'logout') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
      return;
    }
    if (key === 'users') navigate('/users');
  };

  const showContext = currentDomain.key !== 'board';
  const leftOffset = RAIL_W + (showContext ? SIDEBAR_W : 0);

  return (
    <div className="om-shell">
      <nav className="om-rail" aria-label="主导航">
        <div className="om-rail-top">
          <button type="button" className="om-rail-brand" title="OntoMind" onClick={() => navigate('/overview')}>
            <BrandMark size={32} />
          </button>
        </div>
        <div className="om-rail-mid">
          {DOMAINS.map((d) => {
            const active = currentDomain.key === d.key;
            return (
              <Tooltip key={d.key} title={d.label} placement="right">
                <button
                  type="button"
                  className={active ? 'om-rail-item active' : 'om-rail-item'}
                  aria-label={d.label}
                  aria-current={active ? 'page' : undefined}
                  onClick={() => goDomain(d)}
                >
                  {DOMAIN_ICONS[d.key]}
                </button>
              </Tooltip>
            );
          })}
        </div>
        <div className="om-rail-bot">
          <Tooltip title="搜索 ⌘K" placement="right">
            <button type="button" className="om-rail-item" aria-label="搜索" onClick={() => setCmdOpen(true)}>
              <SearchOutlined />
            </button>
          </Tooltip>
          <Tooltip title={mode === 'dark' ? '浅色' : '深色'} placement="right">
            <button
              type="button"
              className="om-rail-item"
              aria-label="切换主题"
              onClick={() => setColorMode(mode === 'dark' ? 'light' : 'dark')}
            >
              {mode === 'dark' ? <SunOutlined /> : <MoonOutlined />}
            </button>
          </Tooltip>
          <Dropdown menu={{ items: userMenu, onClick: handleMenuClick }} placement="topRight">
            <button type="button" className="om-rail-item" aria-label="账户" style={{ padding: 0 }}>
              <Avatar size={28} style={{ background: 'var(--accent)', fontSize: 12 }}>
                {(currentUser?.displayName || currentUser?.username || 'A').slice(0, 1).toUpperCase()}
              </Avatar>
            </button>
          </Dropdown>
        </div>
      </nav>

      {showContext && (
        <aside className="om-context">
          <div className="om-context-head">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <span style={{ fontSize: 18, color: currentDomain.color }}>{DOMAIN_ICONS[currentDomain.key]}</span>
              <div className="om-context-title">{currentDomain.key === 'overview' ? 'OntoMind' : currentDomain.label}</div>
            </div>
            <div className="om-context-hint">
              {currentDomain.key === 'overview'
                ? 'AI 领域工程平台。工作区、Agent、数据与算力都在这里。'
                : currentDomain.hint}
            </div>
          </div>
          <div className="om-context-body">
            {currentDomain.key === 'chat' ? (
              <ChatSessionRail />
            ) : currentDomain.key === 'overview' ? (
              <>
                <div className="om-kicker" style={{ padding: '8px 10px 0' }}>可以这样走</div>
                <div className="om-prompt-list">
                  {QUICK_PROMPTS.map((p) => (
                    <button key={p.to} type="button" className="om-prompt-item" onClick={() => navigate(p.to)}>
                      {p.label}
                    </button>
                  ))}
                </div>
              </>
            ) : (
              currentDomain.sub.map((s) => {
                const hasChildren = Boolean(s.children?.length);
                const isExpanded = expandedSubs.has(s.key);
                const anyChildActive = s.children?.some((c) => location.pathname.startsWith(c.key));

                if (hasChildren) {
                  return (
                    <div key={s.key}>
                      <button
                        type="button"
                        className={anyChildActive ? 'om-nav-item active' : 'om-nav-item'}
                        onClick={() => {
                          toggleExpand(s.key);
                          if (!isExpanded && s.children?.[0]) navigate(s.children[0].key);
                        }}
                      >
                        <span style={{ flex: 1 }}>{s.label}</span>
                        <RightOutlined
                          style={{
                            fontSize: 10,
                            color: 'var(--text-tertiary)',
                            transform: isExpanded ? 'rotate(90deg)' : 'none',
                            transition: 'transform .16s ease',
                          }}
                        />
                      </button>
                      {isExpanded &&
                        s.children!.map((c) => {
                          const childActive = location.pathname.startsWith(c.key);
                          return (
                            <button
                              key={c.key}
                              type="button"
                              className={childActive ? 'om-nav-item om-nav-child active' : 'om-nav-item om-nav-child'}
                              onClick={() => navigate(c.key)}
                            >
                              {c.label}
                            </button>
                          );
                        })}
                    </div>
                  );
                }

                const subActive = location.pathname.startsWith(s.key);
                return (
                  <button
                    key={s.key}
                    type="button"
                    className={subActive ? 'om-nav-item active' : 'om-nav-item'}
                    onClick={() => navigate(s.key)}
                  >
                    {s.label}
                  </button>
                );
              })
            )}
          </div>
        </aside>
      )}

      <main className="om-main">
        <Outlet />
      </main>

      <AideHost sidebarW={leftOffset} />
      <CmdKOmnibar open={cmdOpen} onOpenChange={setCmdOpen} />
    </div>
  );
}
