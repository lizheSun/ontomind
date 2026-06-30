import { ConfigProvider, theme, App as AntApp } from 'antd';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import Login from './pages/Login';

import Dashboard from './pages/dashboard/index';
import PerceptionIndex from './pages/perception/index';
import CognitionIndex from './pages/cognition/index';
import DecisionIndex from './pages/decision/index';
import ExecutionIndex from './pages/execution/index';
import ApplicationIndex from './pages/application/index';
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
        algorithm: theme.darkAlgorithm,
        token: {
          fontFamily:
            "'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Noto Sans SC', 'PingFang SC', sans-serif",
          colorPrimary: '#3b82f6',
          colorSuccess: '#34d399',
          colorWarning: '#fbbf24',
          colorError: '#fb7185',
          colorInfo: '#60a5fa',
          colorTextBase: '#e8eef5',
          colorBgBase: '#060b14',
          colorBgContainer: '#0a0f1f',
          colorBgElevated: '#111827',
          colorBorder: 'rgba(255,255,255,0.08)',
          colorBorderSecondary: 'rgba(255,255,255,0.05)',
          borderRadius: 10,
          borderRadiusLG: 16,
          borderRadiusSM: 6,
          wireframe: false,
        },
        components: {
          Layout: {
            bodyBg: '#060b14',
            headerBg: 'rgba(10,15,31,0.7)',
            siderBg: 'rgba(10,15,31,0.85)',
            triggerBg: 'rgba(10,15,31,0.9)',
          },
          Menu: {
            darkItemBg: 'transparent',
            darkItemSelectedBg: 'rgba(59,130,246,0.12)',
            darkItemHoverBg: 'rgba(255,255,255,0.05)',
            itemBorderRadius: 10,
          },
          Card: {
            colorBgContainer: 'rgba(255,255,255,0.02)',
          },
          Table: {
            headerBg: 'rgba(255,255,255,0.02)',
            rowHoverBg: 'rgba(255,255,255,0.04)',
            borderColor: 'rgba(255,255,255,0.05)',
          },
          Button: {
            primaryShadow: '0 2px 12px rgba(59,130,246,0.3)',
          },
          Input: {
            activeBorderColor: 'rgba(59,130,246,0.5)',
            activeShadow: '0 0 0 2px rgba(59,130,246,0.15)',
          },
        },
      }}
    >
      <AntApp>
        <BrowserRouter>
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
              <Route index element={<Dashboard />} />
              <Route path="perception" element={<PerceptionIndex />} />
              <Route path="cognition" element={<CognitionIndex />} />
              <Route path="decision" element={<DecisionIndex />} />
              <Route path="execution" element={<ExecutionIndex />} />
              <Route path="application" element={<ApplicationIndex />} />
              <Route path="users" element={<UsersPage />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  );
}
