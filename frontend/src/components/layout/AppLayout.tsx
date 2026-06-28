import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, theme, Avatar, Dropdown } from 'antd';
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
} from '@ant-design/icons';

const { Header, Sider, Content } = Layout;

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
  { key: '/perception', icon: <ApiOutlined />, label: '感知层' },
  { key: '/cognition', icon: <NodeIndexOutlined />, label: '认知层' },
  { key: '/decision', icon: <ThunderboltOutlined />, label: '决策层' },
  { key: '/execution', icon: <SendOutlined />, label: '执行层' },
  { key: '/application', icon: <AppstoreOutlined />, label: '应用层' },
];

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { token } = theme.useToken();

  const selectedKey = '/' + (location.pathname.split('/')[1] || '');

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed} theme="dark" width={220}>
        <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <h1 style={{ color: token.colorPrimary, fontSize: collapsed ? 18 : 20, margin: 0, whiteSpace: 'nowrap' }}>
            {collapsed ? 'OM' : 'OntoMind'}
          </h1>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>

      <Layout>
        <Header style={{ padding: '0 24px', background: token.colorBgContainer, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
          />
          <Dropdown menu={{
            items: [
              { key: 'profile', icon: <UserOutlined />, label: '个人信息' },
              { type: 'divider' },
              { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true },
            ]
          }}>
            <Avatar style={{ cursor: 'pointer', backgroundColor: token.colorPrimary }} icon={<UserOutlined />} />
          </Dropdown>
        </Header>

        <Content style={{ margin: 24, padding: 24, background: token.colorBgContainer, borderRadius: 8, minHeight: 280 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
