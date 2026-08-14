import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, App as AntApp } from 'antd';
import Login from './pages/Login';
import AppLayout from './components/layout/AppLayout';
import OverviewPage from './pages/overview/OverviewPage';
import PlaceholderPage from './components/common/PlaceholderPage';
import WarehousePage from './pages/dataops/WarehousePage';
import SmartDevPage from './pages/dataops/smart-dev/SmartDevPage';

// Infra
import InfraComputePage from './pages/infra/InfraComputePage';
import InfraAidePage from './pages/infra/InfraAidePage';
import NodeManagement from './components/compute/NodeManagement';
import DockerManagement from './components/compute/DockerManagement';
import ServicesPanel from './components/compute/ServicesPanel';

// AgentOps
import AgentOpsAgentsPage from './pages/agentops/AgentOpsAgentsPage';
import AgentOpsSkillsPage from './pages/agentops/AgentOpsSkillsPage';
import AgentOpsBundlesPage from './pages/agentops/AgentOpsBundlesPage';
import AgentOpsDeployPage from './pages/agentops/AgentOpsDeployPage';

// Placeholder
import UsersPage from './pages/users';

export default function App() {
  return (
    <ConfigProvider theme={{
      token: {
        // 【UI 重构】Apple 字体栈 + 品牌蓝 + 柔和圆角
        fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Geist', 'Segoe UI', sans-serif",
        colorPrimary: '#0071e3',
        borderRadius: 12,
        colorText: '#1d1d1f',
        colorTextSecondary: '#6e6e73',
        colorBgContainer: '#FFFFFF',
        colorBgLayout: '#FFFFFF',
        colorBorder: 'rgba(0,0,0,0.12)',
      },
    }}>
      <AntApp>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<AppLayout />}>
              <Route index element={<Navigate to="/overview" replace />} />
              {/* 总览 */}
              <Route path="overview" element={<OverviewPage />} />
              {/* CodeOps */}
              <Route path="codeops/workspace" element={<PlaceholderPage title="AI 编码工作台" desc="AI Agent 辅助的代码开发环境，支持上下文感知、增量开发、安全审查。" />} />
              <Route path="codeops/pipelines" element={<PlaceholderPage title="CI/CD 流水线" desc="AI 驱动的智能 CI/CD 流水线，含部署风险预测、金丝雀发布。" />} />
              <Route path="codeops/*" element={<Navigate to="/codeops/workspace" replace />} />
              {/* DataOps */}
              <Route path="dataops/catalog" element={<Navigate to="/dataops/catalog/biz-systems" replace />} />
              <Route path="dataops/catalog/biz-systems" element={<PlaceholderPage title="业务系统" desc="业务应用系统与服务边界资产。" />} />
              <Route path="dataops/catalog/warehouse" element={<WarehousePage />} />
              <Route path="dataops/catalog/etl" element={<PlaceholderPage title="ETL代码库" desc="数据集成与调度作业代码资产。" />} />
              <Route path="dataops/catalog/code" element={<PlaceholderPage title="业务代码库" desc="业务服务与应用源码资产。" />} />
              <Route path="dataops/catalog/knowledge" element={<PlaceholderPage title="知识库" desc="文档、向量索引与 RAG 语料资产。" />} />
              <Route path="dataops/catalog/smart-dev" element={<SmartDevPage />} />
              <Route path="dataops/lineage" element={<PlaceholderPage title="数据血缘" desc="数据→特征→模型→Agent→应用 全链路血缘追踪。" />} />
              <Route path="dataops/quality" element={<PlaceholderPage title="数据质量" desc="五维数据质量监控。" />} />
              <Route path="dataops/*" element={<Navigate to="/dataops/catalog/biz-systems" replace />} />
              {/* ModelOps */}
              <Route path="modelops/experiments" element={<PlaceholderPage title="实验管理" desc="模型实验对比、超参数追踪、LLM-as-Judge 评估。" />} />
              <Route path="modelops/gateway" element={<PlaceholderPage title="推理网关" desc="7 层推理架构、4 种路由策略、语义缓存、金丝雀发布。" />} />
              <Route path="modelops/monitoring" element={<PlaceholderPage title="模型监控" desc="5 层可观测性：基础设施/成本/质量/漂移/用户信号。" />} />
              <Route path="modelops/*" element={<Navigate to="/modelops/experiments" replace />} />
              {/* AgentOps */}
              <Route path="agentops/agents" element={<AgentOpsAgentsPage />} />
              <Route path="agentops/skills" element={<AgentOpsSkillsPage />} />
              <Route path="agentops/bundles" element={<AgentOpsBundlesPage />} />
              <Route path="agentops/deploy" element={<AgentOpsDeployPage />} />
              <Route path="agentops/*" element={<Navigate to="/agentops/agents" replace />} />
              {/* GovOps */}
              <Route path="govops/catalog" element={<PlaceholderPage title="统一资产目录" desc="跨域搜索代码、数据、模型、Agent 资产。" />} />
              <Route path="govops/security" element={<PlaceholderPage title="安全合规" desc="AI 安全护栏、合规框架检查、Prompt 注入防御。" />} />
              <Route path="govops/cost" element={<PlaceholderPage title="成本归因" desc="Token 消耗归因、GPU 成本追踪、预算管理。" />} />
              <Route path="govops/*" element={<Navigate to="/govops/catalog" replace />} />
              {/* Infra */}
              <Route path="infra/compute" element={<InfraComputePage />}>
                <Route index element={<Navigate to="nodes" replace />} />
                <Route path="nodes" element={<NodeManagement />} />
                <Route path="docker" element={<DockerManagement />} />
                <Route path="services" element={<ServicesPanel />} />
              </Route>
              <Route path="infra/aide" element={<InfraAidePage />} />
              <Route path="infra/*" element={<Navigate to="/infra/compute" replace />} />
              {/* 用户 */}
              <Route path="users" element={<UsersPage />} />
              {/* 旧路由重定向 */}
              <Route path="compute" element={<Navigate to="/infra/compute" replace />} />
              <Route path="aide" element={<Navigate to="/infra/aide" replace />} />
              <Route path="agent-factory" element={<Navigate to="/agentops/agents" replace />} />
              <Route path="skill-platform" element={<Navigate to="/agentops/skills" replace />} />
              {/* 历史遗留 */}
              <Route path="workspace" element={<Navigate to="/infra/aide" replace />} />
              <Route path="perception" element={<Navigate to="/infra/aide" replace />} />
              <Route path="cognition" element={<Navigate to="/infra/aide" replace />} />
              <Route path="decision" element={<Navigate to="/infra/aide" replace />} />
              <Route path="execution" element={<Navigate to="/infra/aide" replace />} />
              <Route path="resources/*" element={<Navigate to="/infra/aide" replace />} />
              <Route path="agent-platform/*" element={<Navigate to="/infra/aide" replace />} />
              <Route path="experts/*" element={<Navigate to="/infra/aide" replace />} />
              <Route path="data-platform/*" element={<Navigate to="/infra/aide" replace />} />
              <Route path="knowledge-base/*" element={<Navigate to="/infra/aide" replace />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  );
}