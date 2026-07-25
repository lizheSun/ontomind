import { ConfigProvider, theme, App as AntApp } from 'antd';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import Login from './pages/Login';
import { CmdKOmnibar } from './components/common';

import PerceptionLegacyIndex from './pages/perception/index';
import PerceptionShell from './pages/perception/PerceptionShell';
import CognitionIndex from './pages/cognition/index';
import DecisionIndex from './pages/decision/index';
import ExecutionIndex from './pages/execution/index';
import ResourcesPage from './pages/resources/index';
import AgentLooperWizard from './pages/resources/AgentLooperWizard';
import ComputeNodeDetailPage from './pages/resources/ComputeNodeDetailPage';
import AgentContainerDetailPage from './pages/resources/AgentContainerDetailPage';
import AgentDetailPage from './pages/resources/AgentDetailPage';
import SkillDetailPage from './pages/resources/SkillDetailPage';
import MCPDetailPage from './pages/resources/MCPDetailPage';
import AgentPlatformPrototype from './pages/resources/AgentPlatformPrototype';
import {
  ChatWorkspacePage,
  AgentStudioPage,
} from './pages/agent-platform';
import ExpertTeamPage from './pages/experts/ExpertTeamPage';
import UsersPage from './pages/users/index';
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
            <Route path="/prototype/agent-platform" element={<AgentPlatformPrototype />} />

            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/workspace" replace />} />
              <Route path="workspace" element={<ChatWorkspacePage />} />
              <Route path="agent-platform/resources" element={<Navigate to="/experts" replace />} />
              <Route path="agent-platform/agents/new/studio" element={<AgentStudioPage />} />
              <Route path="agent-platform/agents/:id/studio" element={<AgentStudioPage />} />
              <Route path="experts" element={<ExpertTeamPage />} />
              <Route path="perception" element={<PerceptionShell />} />
              <Route path="perception-legacy" element={<PerceptionLegacyIndex />} />
              <Route path="cognition" element={<CognitionIndex />} />
              <Route path="decision" element={<DecisionIndex />} />
              <Route path="execution" element={<ExecutionIndex />} />
              <Route path="resources" element={<ResourcesPage />} />
              <Route path="resources/legacy" element={<ResourcesPage />} />
              <Route path="resources/agent-looper/new" element={<AgentLooperWizard />} />
              <Route path="resources/compute-nodes/:id" element={<ComputeNodeDetailPage />} />
              <Route path="resources/agent-containers/:id" element={<AgentContainerDetailPage />} />
              <Route path="resources/agent-looper/:id" element={<AgentDetailPage />} />
              <Route path="resources/agent/new" element={<AgentDetailPage />} />
              <Route path="resources/agent/:id" element={<AgentDetailPage />} />
              <Route path="resources/skills/:id" element={<SkillDetailPage />} />
              <Route path="resources/mcps/:id" element={<MCPDetailPage />} />
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