import { useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, Avatar, Dropdown, Typography, theme } from 'antd';
import type { MenuProps } from 'antd';
import {
  DashboardOutlined,
  ApiOutlined,
  NodeIndexOutlined,
  ThunderboltOutlined,
  SendOutlined,
  AppstoreOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  LogoutOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { useAppStore } from '../../stores/appStore';
import useUserStore from '../../stores/userStore';

const { Header, Sider, Content } = Layout;

type MenuItem = Required<MenuProps>['items'][number];

const sideMenuItems: MenuItem[] = [
  {
    key: '/',
    icon: <DashboardOutlined />,
    label: '仪表盘',
  },
  {
    key: 'layer-group',
    label: '五层架构',
    type: 'group',
    children: [
      { key: '/perception', icon: <ApiOutlined />, label: '感知层' },
      { key: '/cognition', icon: <NodeIndexOutlined />, label: '认知层' },
      { key: '/decision', icon: <ThunderboltOutlined />, label: '决策层' },
      { key: '/execution', icon: <SendOutlined />, label: '执行层' },
      { key: '/application', icon: <AppstoreOutlined />, label: '应用层' },
    ],
  },
  { type: 'divider' },
  {
    key: '/users',
    icon: <TeamOutlined />,
    label: '用户管理',
  },
];

export default function AppLayout() {
  const collapsed = useAppStore((s) => s.collapsed);
  const setCollapsed = useAppStore((s) => s.setCollapsed);
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
      {/* ---------- 侧边导航 ---------- */}
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        width={240}
        style={{
          background: 'rgba(10,15,31,0.85)',
          backdropFilter: 'blur(20px)',
          borderRight: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        {/* Logo 区域 */}
        <div
          style={{
            height: 56,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            padding: collapsed ? 0 : '0 20px',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
          }}
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
          {!collapsed && (
            <span
              style={{
                marginLeft: 12,
                fontSize: 17,
                fontWeight: 700,
                color: '#e8eef5',
                letterSpacing: -0.3,
              }}
            >
              OntoMind
            </span>
          )}
        </div>

        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          defaultOpenKeys={['layer-group']}
          items={sideMenuItems}
          onClick={({ key }) => {
            if (key.startsWith('/')) navigate(key);
          }}
          style={{
            background: 'transparent',
            borderInlineEnd: 'none',
            marginTop: 8,
            fontSize: 13,
          }}
        />
      </Sider>

      {/* ---------- 主区域 ---------- */}
      <Layout>
        {/* 顶栏 */}
        <Header
          style={{
            height: 56,
            padding: '0 20px',
            background: 'rgba(10,15,31,0.7)',
            backdropFilter: 'blur(16px)',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            position: 'sticky',
            top: 0,
            zIndex: 100,
          }}
        >
          <Button
            type="text"
            icon={
              collapsed ? (
                <MenuUnfoldOutlined style={{ fontSize: 18, color: token.colorTextSecondary }} />
              ) : (
                <MenuFoldOutlined style={{ fontSize: 18, color: token.colorTextSecondary }} />
              )
            }
            onClick={() => setCollapsed(!collapsed)}
            style={{ width: 40, height: 40 }}
          />

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
                  backgroundImage:
                    'linear-gradient(135deg, #3b82f6, #8b5cf6)',
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
        </Header>

        {/* 内容区 */}
        <Content
          style={{
            margin: 24,
            minHeight: 280,
          }}
        >
          <div className="page-enter">
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  );
}
