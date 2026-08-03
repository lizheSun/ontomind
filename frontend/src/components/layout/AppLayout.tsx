import { useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Avatar, Dropdown, Typography, theme } from 'antd';
import type { MenuProps } from 'antd';
import {
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import useUserStore from '../../stores/userStore';
import { ZenGodToggle } from '../common';
import AideHost from './AideHost';

const { Header, Content } = Layout;

type MenuItem = Required<MenuProps>['items'][number];

const topMenuItems: MenuItem[] = [
  { key: '/aide', icon: <CodeOutlined />, label: 'AIDE' },
  { key: '/users', icon: <SettingOutlined />, label: '用户管理' },
];

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { token } = theme.useToken();
  const { currentUser, fetchCurrentUser } = useUserStore();

  useEffect(() => {
    if (!currentUser) fetchCurrentUser();
  }, [currentUser, fetchCurrentUser]);

  const segments = location.pathname.split('/').filter(Boolean);
  const selectedKey = segments.length === 0 ? '/aide' : `/${segments[0]}`;

  /** 需要铺满可用区（无 Content margin / 无 page-enter transform）的路由 */
  const isFullBleed = segments[0] === 'aide';

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  return (
    <Layout style={{ minHeight: '100vh' }} className="bg-grid">
      {/* ---------- 顶栏导航 ---------- */}
      <Header
        style={{
          height: 56,
          padding: '0 24px',
          background: 'rgba(250,250,247,0.85)',
          backdropFilter: 'saturate(180%) blur(12px)',
          WebkitBackdropFilter: 'saturate(180%) blur(12px)',
          borderBottom: '1px solid rgba(26,25,24,0.08)',
          display: 'flex',
          alignItems: 'center',
          position: 'sticky',
          top: 0,
          zIndex: 100,
        }}
      >
        {/* Logo */}
        <div
          style={{
            display: 'flex',
            alignItems: 'baseline',
            flexShrink: 0,
            marginRight: 40,
            cursor: 'pointer',
            gap: 10,
          }}
          onClick={() => navigate('/')}
        >
          <span
            style={{
              fontFamily: "'Fraunces', serif",
              fontSize: 22,
              fontWeight: 500,
              color: '#1a1918',
              letterSpacing: '-0.02em',
              lineHeight: 1,
              fontStyle: 'italic',
            }}
          >
            OntoMind
          </span>
          <span
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10,
              color: '#8f8b84',
              letterSpacing: '0.14em',
              textTransform: 'uppercase',
              transform: 'translateY(-2px)',
            }}
          >
            v0.1
          </span>
        </div>

        {/* 横向导航菜单 */}
        <Menu
          mode="horizontal"
          selectedKeys={[selectedKey]}
          items={topMenuItems}
          onClick={({ key }) => {
            if (key.startsWith('/')) navigate(key);
          }}
          style={{
            flex: 1,
            minWidth: 0,
            background: 'transparent',
            borderBottom: 'none',
            fontSize: 13,
          }}
        />

        {/* 用户区域 */}
        <div
          style={{
            flexShrink: 0,
            marginLeft: 16,
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}
        >
          <ZenGodToggle />
          <Dropdown
            menu={{
              items: [
                {
                  key: 'info',
                  icon: <UserOutlined />,
                  label: (
                    <span>
                      {currentUser?.displayName || currentUser?.username || '用户'}
                      {currentUser?.email && (
                        <Typography.Text
                          style={{
                            fontSize: 11,
                            color: token.colorTextTertiary,
                            display: 'block',
                          }}
                        >
                          {currentUser.email}
                        </Typography.Text>
                      )}
                    </span>
                  ),
                  disabled: true,
                },
                { type: 'divider' },
                {
                  key: 'logout',
                  icon: <LogoutOutlined />,
                  label: '退出登录',
                  danger: true,
                },
              ] as MenuProps['items'],
              onClick: ({ key }) => {
                if (key === 'logout') handleLogout();
              },
            }}
            placement="bottomRight"
          >
            <div
              style={{
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '4px 10px 4px 4px',
                borderRadius: 999,
                transition: 'background 0.15s',
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.background = 'rgba(26,25,24,0.04)')
              }
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              <Avatar
                size={30}
                style={{
                  backgroundColor: '#1a1918',
                  color: '#fafaf7',
                  flexShrink: 0,
                  fontFamily: "'Fraunces', serif",
                  fontWeight: 500,
                }}
              >
                {(currentUser?.displayName || currentUser?.username || 'U')
                  .slice(0, 1)
                  .toUpperCase()}
              </Avatar>
              <Typography.Text
                style={{
                  color: '#35322e',
                  fontSize: 13,
                  fontWeight: 500,
                }}
              >
                {currentUser?.displayName || currentUser?.username || '用户'}
              </Typography.Text>
            </div>
          </Dropdown>
        </div>
      </Header>

      {/* 内容区 —— AIDE 走全幅无内边距（iframe 需要铺满 + 全屏不被 transform 困住） */}
      {isFullBleed ? (
        <Content style={{ margin: 0, minHeight: 0 }}>
          <Outlet />
        </Content>
      ) : (
        <Content style={{ margin: 24, minHeight: 280 }}>
          <div className="page-enter">
            <Outlet />
          </div>
        </Content>
      )}
      {/* AIDE iframe 常驻宿主 —— 挂在路由外层，切走路由不卸载，
          避免每次进 /aide 都重新加载 opencode UI（只用 display 切显隐）。 */}
      <AideHost />
    </Layout>
  );
}
