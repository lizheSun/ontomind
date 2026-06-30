import { useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Avatar, Dropdown, Typography, theme } from 'antd';
import type { MenuProps } from 'antd';
import {
  DashboardOutlined,
  ApiOutlined,
  NodeIndexOutlined,
  ThunderboltOutlined,
  SendOutlined,
  AppstoreOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import useUserStore from '../../stores/userStore';

const { Header, Content } = Layout;

type MenuItem = Required<MenuProps>['items'][number];

const topMenuItems: MenuItem[] = [
  { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
  { key: '/perception', icon: <ApiOutlined />, label: '感知层' },
  { key: '/cognition', icon: <NodeIndexOutlined />, label: '认知层' },
  { key: '/decision', icon: <ThunderboltOutlined />, label: '决策层' },
  { key: '/execution', icon: <SendOutlined />, label: '执行层' },
  { key: '/application', icon: <AppstoreOutlined />, label: '应用层' },
  { key: '/resources', icon: <SettingOutlined />, label: '资源管理' },
  { key: '/users', icon: <TeamOutlined />, label: '用户管理' },
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
  const selectedKey = segments.length ? `/${segments[0]}` : '/';

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
          padding: '0 20px',
          background: 'rgba(10,15,31,0.7)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
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
            alignItems: 'center',
            flexShrink: 0,
            marginRight: 32,
            cursor: 'pointer',
          }}
          onClick={() => navigate('/')}
        >
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 800,
              fontSize: 15,
              color: '#fff',
              flexShrink: 0,
              letterSpacing: -0.5,
            }}
          >
            O
          </div>
          <span
            style={{
              marginLeft: 10,
              fontSize: 16,
              fontWeight: 700,
              color: '#e8eef5',
              letterSpacing: -0.3,
            }}
          >
            OntoMind
          </span>
        </div>

        {/* 横向导航菜单 */}
        <Menu
          theme="dark"
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
        <div style={{ flexShrink: 0, marginLeft: 16 }}>
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
                padding: '4px 8px',
                borderRadius: 10,
                transition: 'background 0.15s',
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')
              }
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              <Avatar
                size={32}
                style={{
                  backgroundColor: 'transparent',
                  backgroundImage: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
                  flexShrink: 0,
                }}
                icon={<UserOutlined />}
              />
              <Typography.Text
                style={{ color: token.colorTextSecondary, fontSize: 13, fontWeight: 500 }}
              >
                {currentUser?.displayName || currentUser?.username || '用户'}
              </Typography.Text>
            </div>
          </Dropdown>
        </div>
      </Header>

      {/* 内容区 */}
      <Content style={{ margin: 24, minHeight: 280 }}>
        <div className="page-enter">
          <Outlet />
        </div>
      </Content>
    </Layout>
  );
}
