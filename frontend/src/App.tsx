import { ConfigProvider, theme, App as AntApp } from 'antd';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import Login from './pages/Login';

import Dashboard from './pages/dashboard/index';
import PerceptionLegacyIndex from './pages/perception/index';
import PerceptionShell from './pages/perception/PerceptionShell';
import CognitionIndex from './pages/cognition/index';
import DecisionIndex from './pages/decision/index';
import ExecutionIndex from './pages/execution/index';
import ApplicationIndex from './pages/application/index';
import ResourcesPage from './pages/resources/index';
import AgentLooperWizard from './pages/resources/AgentLooperWizard';
import ComputeNodeDetailPage from './pages/resources/ComputeNodeDetailPage';
import AgentContainerDetailPage from './pages/resources/AgentContainerDetailPage';
import UsersPage from './pages/users/index';
import ProjectsPage from './pages/projects/index';
import DataPlatformIndex from './pages/data-platform';
import SourcesListPage from './pages/data-platform/SourcesListPage';
import SourceDetailPage from './pages/data-platform/SourceDetailPage';
import MetadataPage from './pages/data-platform/MetadataPage';
import KnowledgeBaseIndex from './pages/knowledge-base';
import DataAssetsPage from './pages/knowledge-base/DataAssetsPage';
import CodeReposPage from './pages/knowledge-base/CodeReposPage';
import DocumentsPage from './pages/knowledge-base/DocumentsPage';
import ExperiencesPage from './pages/knowledge-base/ExperiencesPage';
import KbSearchPage from './pages/knowledge-base/KbSearchPage';

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
          // Perception-layer additions (T02)
          controlItemBgActive: 'rgba(59, 130, 246, 0.14)',
          controlItemBgActiveHover: 'rgba(59, 130, 246, 0.20)',
        },
        components: {
          Layout: {
            bodyBg: '#060b14',
            headerBg: 'rgba(10,15,31,0.7)',
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
              <Route path="perception" element={<PerceptionShell />} />
              <Route path="perception-legacy" element={<PerceptionLegacyIndex />} />
              <Route path="cognition" element={<CognitionIndex />} />
              <Route path="decision" element={<DecisionIndex />} />
              <Route path="execution" element={<ExecutionIndex />} />
              <Route path="application" element={<ApplicationIndex />} />
              <Route path="resources" element={<ResourcesPage />} />
              <Route path="resources/agent-looper/new" element={<AgentLooperWizard />} />
              <Route path="resources/compute-nodes/:id" element={<ComputeNodeDetailPage />} />
              <Route path="resources/agent-containers/:id" element={<AgentContainerDetailPage />} />
              <Route path="projects" element={<ProjectsPage />} />
              <Route path="users" element={<UsersPage />} />
              {/* Wave 5 T20: data platform + knowledge base */}
              <Route path="data-platform" element={<DataPlatformIndex />} />
              <Route path="data-platform/sources" element={<SourcesListPage />} />
              <Route path="data-platform/sources/:sid" element={<SourceDetailPage />} />
              <Route path="data-platform/metadata" element={<MetadataPage />} />
              <Route path="knowledge-base" element={<KnowledgeBaseIndex />} />
              <Route path="knowledge-base/data-assets" element={<DataAssetsPage />} />
              <Route path="knowledge-base/code-repos" element={<CodeReposPage />} />
              <Route path="knowledge-base/documents" element={<DocumentsPage />} />
              <Route path="knowledge-base/experiences" element={<ExperiencesPage />} />
              <Route path="knowledge-base/search" element={<KbSearchPage />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  );
}
