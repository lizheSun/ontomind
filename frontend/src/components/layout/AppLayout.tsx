/**
 * 平台主布局 — 一级导航在顶栏，二级导航在左侧边栏。
 * 【UI 重构】Apple 官网风格：毛玻璃固定导航、浅色侧栏、移动端折叠。
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Avatar, Dropdown, Space, Typography, Grid } from 'antd';
import type { MenuProps } from 'antd';
import {
  ApiOutlined,
  CloudServerOutlined,
  CodeOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  RightOutlined,
  RobotOutlined,
  SafetyOutlined,
  UserOutlined,
} from '@ant-design/icons';
import useUserStore from '../../stores/userStore';
import AideHost from './AideHost';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;
const { useBreakpoint } = Grid;

interface SubChild {
  key: string;
  label: string;
}

interface SubItem {
  key: string;
  label: string;
  children?: SubChild[];
}

interface DomainDef {
  key: string;
  icon: React.ReactNode;
  label: string;
  color: string;
  sub: SubItem[];
}

const DOMAINS: DomainDef[] = [
  { key: 'overview', icon: <DashboardOutlined />, label: '总览', color: '#86868b', sub: [] },
  { key: 'codeops', icon: <CodeOutlined />, label: 'CodeOps', color: '#0071e3', sub: [
    { key: '/codeops/workspace', label: '编码工作台' },
    { key: '/codeops/pipelines', label: 'CI/CD 流水线' },
  ]},
  { key: 'dataops', icon: <DatabaseOutlined />, label: 'DataOps', color: '#0a84ff', sub: [
    { key: '/dataops/catalog', label: '资产地图(AI)', children: [
      { key: '/dataops/catalog/biz-systems', label: '元数据与标注' },
      { key: '/dataops/catalog/warehouse', label: '数据仓库' },
      { key: '/dataops/catalog/ontology', label: '本体建模' },
      { key: '/dataops/catalog/etl', label: 'ETL代码库' },
      { key: '/dataops/catalog/code', label: '业务代码库' },
      { key: '/dataops/catalog/knowledge', label: '知识库' },
      { key: '/dataops/catalog/smart-dev', label: '智能数开' },
    ]},
    { key: '/dataops/lineage', label: '数据血缘' },
    { key: '/dataops/quality', label: '数据质量' },
  ]},
  { key: 'modelops', icon: <RobotOutlined />, label: 'ModelOps', color: '#5b5bf6', sub: [
    { key: '/modelops/experiments', label: '实验管理' },
    { key: '/modelops/gateway', label: '推理网关' },
    { key: '/modelops/monitoring', label: '模型监控' },
  ]},
  { key: 'agentops', icon: <ApiOutlined />, label: 'AgentOps', color: '#ff9f0a', sub: [
    { key: '/agentops/agents', label: 'Agent 设计' },
    { key: '/agentops/skills', label: 'Skill 设计' },
    { key: '/agentops/bundles', label: '编排方案' },
    { key: '/agentops/deploy', label: '发布中心' },
  ]},
  { key: 'govops', icon: <SafetyOutlined />, label: 'GovOps', color: '#ff375f', sub: [
    { key: '/govops/llm', label: 'LLM 配置' },
    { key: '/govops/catalog', label: '资产目录' },
    { key: '/govops/security', label: '安全合规' },
    { key: '/govops/cost', label: '成本归因' },
  ]},
  { key: 'infra', icon: <CloudServerOutlined />, label: 'Infra', color: '#34c759', sub: [
    { key: '/infra/compute', label: '算力管理', children: [
      { key: '/infra/compute/nodes', label: '节点管理' },
      { key: '/infra/compute/docker', label: 'Docker 管理' },
      { key: '/infra/compute/services', label: '服务' },
    ]},
    { key: '/infra/aide', label: 'AIDE' },
  ]},
];

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { currentUser, fetchCurrentUser } = useUserStore();
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    try {
      return localStorage.getItem('ontomind_sidebar_open') !== '0';
    } catch {
      return true;
    }
  });
  const [expandedSubs, setExpandedSubs] = useState<Set<string>>(new Set());
  const screens = useBreakpoint();
  const isMobile = !screens.md;

  const toggleSidebar = useCallback(() => {
    setSidebarOpen((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('ontomind_sidebar_open', next ? '1' : '0');
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  const openSidebar = useCallback(() => {
    setSidebarOpen(true);
    try {
      localStorage.setItem('ontomind_sidebar_open', '1');
    } catch {
      /* ignore */
    }
  }, []);

  const domainHome = useCallback((d: DomainDef) => {
    if (!d.sub.length) return `/${d.key}`;
    const first = d.sub[0];
    if (first.children && first.children.length > 0) return first.children[0].key;
    return first.key;
  }, []);

  useEffect(() => {
    if (!currentUser) fetchCurrentUser();
  }, [currentUser, fetchCurrentUser]);

  const currentDomain = useMemo(() => {
    const p = location.pathname.split('/')[1] || 'overview';
    return DOMAINS.find((d) => d.key === p) || DOMAINS[0];
  }, [location.pathname]);

  // 自动展开当前路径所在的三级菜单所属的二级项
  useEffect(() => {
    const path = location.pathname;
    for (const sub of currentDomain.sub) {
      if (sub.children) {
        const hasActive = sub.children.some((c) => path.startsWith(c.key));
        if (hasActive) {
          setExpandedSubs((prev) => {
            if (prev.has(sub.key)) return prev;
            const next = new Set(prev);
            next.add(sub.key);
            return next;
          });
        }
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

  const userMenu: MenuProps['items'] = [
    { key: 'profile', icon: <UserOutlined />, label: currentUser?.displayName || currentUser?.username || '用户' },
    { type: 'divider' },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录' },
  ];

  const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
    if (key === 'logout') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
  };

  const showSidebar = sidebarOpen && currentDomain.sub.length > 0 && !isMobile;

  return (
    <Layout style={{ minHeight: '100vh', background: '#FFFFFF' }}>
      {/* ===== 顶栏（Apple 毛玻璃固定导航）===== */}
      <Header style={{
        height: 52, lineHeight: '52px',
        background: 'rgba(255,255,255,0.72)',
        backdropFilter: 'saturate(180%) blur(20px)',
        WebkitBackdropFilter: 'saturate(180%) blur(20px)',
        borderBottom: '1px solid rgba(0,0,0,0.06)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 22px', position: 'sticky', top: 0, zIndex: 100,
      }}>
        {/* 左侧：Logo + 域导航 */}
        <Space size={0}>
          {/* 【UI 重构】Apple 风格 logo：SF 粗体、靛蓝强调 */}
          <Text style={{
            fontFamily: "var(--font-sans)",
            fontSize: 17, fontWeight: 600,
            color: '#1d1d1f', marginRight: 24,
            letterSpacing: '-0.02em',
          }}>
            OntoMind
          </Text>
          <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {DOMAINS.map((d) => {
              const active = currentDomain.key === d.key;
              return (
                <div
                  key={d.key}
                  onClick={() => {
                    openSidebar();
                    navigate(domainHome(d));
                  }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 5,
                    padding: '0 11px', height: 52, cursor: 'pointer',
                    borderBottom: active ? `2px solid ${d.color}` : '2px solid transparent',
                    color: active ? d.color : '#6e6e73',
                    fontSize: 13, fontWeight: active ? 600 : 500,
                    transition: 'color .18s ease, border-color .18s ease',
                    background: 'transparent',
                  }}
                  onMouseEnter={(e) => { if (!active) e.currentTarget.style.color = '#1d1d1f'; }}
                  onMouseLeave={(e) => { if (!active) e.currentTarget.style.color = '#6e6e73'; }}
                >
                  <span style={{ fontSize: 15 }}>{d.icon}</span>
                  <span>{d.label}</span>
                </div>
              );
            })}
          </div>
        </Space>

        {/* 右侧：侧栏折叠 + 用户 */}
        <Space size={10}>
          {currentDomain.sub.length > 0 && !isMobile ? (
            <button
              type="button"
              onClick={toggleSidebar}
              title={sidebarOpen ? '收起侧栏' : '展开侧栏'}
              style={{
                width: 28,
                height: 28,
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '1px solid rgba(0,0,0,0.08)',
                borderRadius: 8,
                background: sidebarOpen ? 'rgba(0,0,0,0.03)' : '#fff',
                color: '#6e6e73',
                cursor: 'pointer',
                fontSize: 14,
              }}
            >
              {sidebarOpen ? <MenuFoldOutlined /> : <MenuUnfoldOutlined />}
            </button>
          ) : null}
          <Dropdown menu={{ items: userMenu, onClick: handleMenuClick }} placement="bottomRight">
            <Space size={6} style={{ cursor: 'pointer' }}>
              <Avatar size={26} icon={<UserOutlined />} style={{ background: '#0071e3' }} />
              <Text style={{ fontSize: 12, color: '#1d1d1f' }}>{currentUser?.displayName || currentUser?.username || 'admin'}</Text>
            </Space>
          </Dropdown>
        </Space>
      </Header>

      <Layout style={{ minHeight: 'calc(100vh - 52px)', background: '#FFFFFF' }}>
        {/* ===== 左侧栏：二级导航（Apple 浅色）===== */}
        {showSidebar && (
          <Sider width={180} style={{
            background: '#F5F5F7',
            borderRight: '1px solid rgba(0,0,0,0.06)',
            overflow: 'auto',
            position: 'relative',
          }} trigger={null}>
            <div style={{ padding: '14px 0' }}>
              {/* 当前域标题 */}
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '0 10px 10px 14px',
                color: currentDomain.color, fontSize: 12.5, fontWeight: 600,
                letterSpacing: '0.02em', textTransform: 'uppercase',
                justifyContent: 'space-between',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                  <span style={{ fontSize: 14 }}>{currentDomain.icon}</span>
                  <span>{currentDomain.label}</span>
                </div>
                <button
                  type="button"
                  onClick={toggleSidebar}
                  title="收起侧栏"
                  style={{
                    width: 22,
                    height: 22,
                    border: 'none',
                    borderRadius: 6,
                    background: 'transparent',
                    color: '#86868b',
                    cursor: 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <MenuFoldOutlined style={{ fontSize: 12 }} />
                </button>
              </div>
              <div style={{ height: 1, background: 'rgba(0,0,0,0.06)', margin: '0 10px 6px' }} />
              {/* 子菜单项 */}
              {currentDomain.sub.map((s) => {
                const hasChildren = s.children && s.children.length > 0;
                const isExpanded = expandedSubs.has(s.key);
                const anyChildActive = s.children?.some((c) => location.pathname.startsWith(c.key));

                if (hasChildren) {
                  // 有三级子菜单 → 展开/折叠
                  return (
                    <div key={s.key}>
                      <div
                        onClick={() => { toggleExpand(s.key); if (!isExpanded) navigate(s.children![0].key); }}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 8,
                          padding: '8px 14px', margin: '2px 6px',
                          borderRadius: 8, cursor: 'pointer',
                          fontSize: 13, fontWeight: anyChildActive ? 600 : 500,
                          color: anyChildActive ? currentDomain.color : '#424245',
                          background: anyChildActive ? `${currentDomain.color}12` : 'transparent',
                          transition: 'all .18s ease',
                          justifyContent: 'space-between',
                        }}
                        onMouseEnter={(e) => { if (!anyChildActive) e.currentTarget.style.background = 'rgba(0,0,0,0.04)'; }}
                        onMouseLeave={(e) => { if (!anyChildActive) e.currentTarget.style.background = 'transparent'; }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{
                            width: 4, height: 4, borderRadius: '50%',
                            background: anyChildActive ? currentDomain.color : '#86868b',
                            flexShrink: 0,
                          }} />
                          {s.label}
                        </div>
                        <RightOutlined style={{
                          fontSize: 10, color: '#86868b',
                          transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                          transition: 'transform .18s ease',
                        }} />
                      </div>
                      {/* 三级子菜单 */}
                      {isExpanded && (
                        <div style={{ paddingLeft: 20 }}>
                          {s.children!.map((c) => {
                            const childActive = location.pathname.startsWith(c.key);
                            return (
                              <div
                                key={c.key}
                                onClick={() => navigate(c.key)}
                                style={{
                                  display: 'flex', alignItems: 'center', gap: 8,
                                  padding: '7px 14px', margin: '1px 6px',
                                  borderRadius: 8, cursor: 'pointer',
                                  fontSize: 12.5, fontWeight: childActive ? 600 : 400,
                                  color: childActive ? currentDomain.color : '#6e6e73',
                                  background: childActive ? `${currentDomain.color}0f` : 'transparent',
                                  transition: 'all .18s ease',
                                }}
                                onMouseEnter={(e) => { if (!childActive) e.currentTarget.style.background = 'rgba(0,0,0,0.03)'; }}
                                onMouseLeave={(e) => { if (!childActive) e.currentTarget.style.background = 'transparent'; }}
                              >
                                {c.label}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                }

                // 无子菜单的普通二级项
                const subActive = location.pathname.startsWith(s.key);
                return (
                  <div
                    key={s.key}
                    onClick={() => navigate(s.key)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      padding: '8px 14px', margin: '2px 6px',
                      borderRadius: 8, cursor: 'pointer',
                      fontSize: 13, fontWeight: subActive ? 600 : 500,
                      color: subActive ? currentDomain.color : '#424245',
                      background: subActive ? `${currentDomain.color}12` : 'transparent',
                      transition: 'all .18s ease',
                    }}
                    onMouseEnter={(e) => { if (!subActive) e.currentTarget.style.background = 'rgba(0,0,0,0.04)'; }}
                    onMouseLeave={(e) => { if (!subActive) e.currentTarget.style.background = 'transparent'; }}
                  >
                    <span style={{
                      width: 4, height: 4, borderRadius: '50%',
                      background: subActive ? currentDomain.color : '#86868b',
                      flexShrink: 0,
                    }} />
                    {s.label}
                  </div>
                );
              })}
            </div>
          </Sider>
        )}

        {/* ===== 内容区 ===== */}
          <Content style={{
            padding: 0, overflow: 'auto',
            minHeight: 'calc(100vh - 52px)',
            background: '#F5F5F7', /* 【UI 重构】浅灰底让白卡片浮起 */
          }}>
          <Outlet />
        </Content>
      </Layout>

      <AideHost sidebarW={showSidebar ? 180 : 0} />
    </Layout>
  );
}
