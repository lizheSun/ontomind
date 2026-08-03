import { ConfigProvider, theme, App as AntApp } from 'antd';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import Login from './pages/Login';
import { CmdKOmnibar } from './components/common';

import AidePage from './pages/aide/AidePage';
import UsersPage from './pages/users/index';

/** 路由守卫 */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('access_token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          fontFamily:
            "'Geist', -apple-system, BlinkMacSystemFont, 'Noto Sans SC', 'PingFang SC', sans-serif",
          colorPrimary: '#3b52af',
          colorSuccess: '#476a4b',
          colorWarning: '#a86e12',
          colorError: '#a5361e',
          colorInfo: '#3b52af',
          colorTextBase: '#1a1918',
          colorBgBase: '#fafaf7',
          colorBgContainer: '#ffffff',
          colorBgElevated: '#ffffff',
          colorBgLayout: '#fafaf7',
          colorBorder: 'rgba(26,25,24,0.10)',
          colorBorderSecondary: 'rgba(26,25,24,0.08)',
          borderRadius: 10,
          borderRadiusLG: 14,
          borderRadiusSM: 6,
          wireframe: false,
          controlItemBgActive: 'rgba(59, 82, 175, 0.08)',
          controlItemBgActiveHover: 'rgba(59, 82, 175, 0.14)',
        },
        components: {
          Layout: {
            bodyBg: '#fafaf7',
            headerBg: 'rgba(250,250,247,0.85)',
          },
          Menu: {
            itemBg: 'transparent',
            itemSelectedBg: 'transparent',
            itemHoverBg: 'transparent',
            itemColor: '#605c56',
            itemSelectedColor: '#1a1918',
            itemHoverColor: '#1a1918',
            horizontalItemSelectedColor: '#1a1918',
            itemBorderRadius: 0,
          },
          Card: {
            colorBgContainer: '#ffffff',
          },
          Table: {
            headerBg: 'transparent',
            rowHoverBg: 'rgba(26,25,24,0.04)',
            borderColor: 'rgba(26,25,24,0.08)',
          },
          Button: {
            primaryShadow: 'none',
          },
          Input: {
            activeBorderColor: '#3b52af',
            activeShadow: '0 0 0 3px rgba(59,82,175,0.10)',
          },
        },
      }}
    >
      <AntApp>
        <BrowserRouter>
          <CmdKOmnibar />
          <Routes>
            <Route path="/login" element={<Login />} />

            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/aide" replace />} />

              {/* --- 当前活跃模块（只剩 2 个）--- */}
              <Route path="aide" element={<AidePage />} />
              <Route path="users" element={<UsersPage />} />

              {/* --- 已下线模块 → 重定向到 AIDE，老书签不 404 ---
                  2026-08-03 两批清理：
                  第一批：对话工作台 / 感知层 / 认知层 / 决策层 / 执行层
                          / 资源管理 / Agent Looper / Agent Platform
                  第二批：专家团 / 算力调度 / 数据平台 / 知识库 / LLM 配置 */}
              <Route path="workspace" element={<Navigate to="/aide" replace />} />
              <Route path="perception" element={<Navigate to="/aide" replace />} />
              <Route path="cognition" element={<Navigate to="/aide" replace />} />
              <Route path="decision" element={<Navigate to="/aide" replace />} />
              <Route path="execution" element={<Navigate to="/aide" replace />} />
              <Route path="resources/*" element={<Navigate to="/aide" replace />} />
              <Route path="agent-platform/*" element={<Navigate to="/aide" replace />} />
              <Route path="experts/*" element={<Navigate to="/aide" replace />} />
              <Route path="compute/*" element={<Navigate to="/aide" replace />} />
              <Route path="data-platform/*" element={<Navigate to="/aide" replace />} />
              <Route path="knowledge-base/*" element={<Navigate to="/aide" replace />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  );
}
