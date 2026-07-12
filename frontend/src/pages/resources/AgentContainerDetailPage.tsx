/**
 * AgentContainerDetailPage — 智能体容器详情页 (T50 Wave 10)
 *
 * 呈现单个 Agent Container（当前后端仍存于 `agents` 表）的完整信息：
 * 名称、类型、runtime、版本、Docker 镜像、entrypoint、端口、资源限制、
 * 环境变量模板等。
 *
 * 数据源：
 *   - `resourcesAPI.getAgent(id)` → Agent 元数据
 *
 * 注意：Agent Container 与 ComputeNode 的关联当前是通过节点上的 scan-agents
 * 结果建立的（DiscoveredAgent），不存在直接外键；因此本详情页专注呈现容器
 * 定义本身，而不列出「反向节点」列表。
 */
import { useCallback, useEffect, useState } from 'react';
import {
  App,
  Breadcrumb,
  Button,
  Descriptions,
  Space,
  Spin,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import {
  ArrowLeftOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  GlassPanel,
  PageHeader,
  TagPill,
} from '../../components/common';
import { resourcesAPI } from '../../services';
import type { Agent } from '../../types';

const { Paragraph } = Typography;

const TYPE_LABELS: Record<Agent['agent_type'], string> = {
  openclaw: 'OpenClaw',
  opencode: 'OpenCode',
  harness: 'Harness',
  custom: '自定义',
};

const TYPE_COLORS: Record<
  Agent['agent_type'],
  'amber' | 'emerald' | 'blue' | 'purple'
> = {
  openclaw: 'amber',
  opencode: 'emerald',
  harness: 'blue',
  custom: 'purple',
};

const RUNTIME_LABELS: Record<Agent['runtime'], string> = {
  docker: 'Docker',
  python: 'Python',
  node: 'Node.js',
  binary: '二进制',
};

type TabKey = 'overview' | 'runtime' | 'template';

function jsonBlock(data: unknown): string {
  if (data == null) return '(未设置)';
  try {
    return JSON.stringify(data, null, 2);
  } catch {
    return String(data);
  }
}

export default function AgentContainerDetailPage() {
  const { id: idParam } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const id = Number(idParam);

  const [agent, setAgent] = useState<Agent | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabKey>('overview');

  const loadAgent = useCallback(async () => {
    if (!Number.isFinite(id)) return;
    setLoading(true);
    try {
      const res = await resourcesAPI.getAgent(id);
      const data: Agent = res.data?.data ?? res.data;
      setAgent(data);
    } catch (err) {
      message.error(err instanceof Error ? err.message : '加载容器失败');
    } finally {
      setLoading(false);
    }
  }, [id, message]);

  useEffect(() => {
    if (!Number.isFinite(id)) {
      message.error('无效的容器 ID');
      navigate('/resources', { replace: true });
      return;
    }
    void loadAgent();
  }, [id, loadAgent, navigate, message]);

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <Spin />
      </div>
    );
  }

  if (!agent) {
    return (
      <div>
        <PageHeader
          title="智能体容器详情"
          subtitle="容器不存在或已被删除"
        />
        <GlassPanel>
          <Paragraph style={{ color: '#8895b4' }}>
            未找到 ID 为 {idParam} 的智能体容器。
          </Paragraph>
          <Button
            type="primary"
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/resources')}
          >
            返回资源列表
          </Button>
        </GlassPanel>
      </div>
    );
  }

  const overviewTab = (
    <GlassPanel>
      <Descriptions
        bordered
        size="small"
        column={2}
        styles={{ label: { width: 140 } }}
      >
        <Descriptions.Item label="容器名称">{agent.name}</Descriptions.Item>
        <Descriptions.Item label="类型">
          <TagPill color={TYPE_COLORS[agent.agent_type] ?? 'blue'}>
            {TYPE_LABELS[agent.agent_type] ?? agent.agent_type}
          </TagPill>
        </Descriptions.Item>
        <Descriptions.Item label="Runtime">
          <Tag>{RUNTIME_LABELS[agent.runtime] ?? agent.runtime}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="版本">
          {agent.version ? (
            <span
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 12,
                color: '#8895b4',
              }}
            >
              {agent.version}
            </span>
          ) : (
            '-'
          )}
        </Descriptions.Item>
        <Descriptions.Item label="状态">
          {agent.is_active ? (
            <Tag color="success">已启用</Tag>
          ) : (
            <Tag>未启用</Tag>
          )}
        </Descriptions.Item>
        <Descriptions.Item label="关联技能数">
          {agent.skill_ids?.length ?? 0}
        </Descriptions.Item>
        <Descriptions.Item label="描述" span={2}>
          {agent.description || '-'}
        </Descriptions.Item>
        <Descriptions.Item label="创建时间">
          {agent.created_at
            ? new Date(agent.created_at).toLocaleString()
            : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="更新时间">
          {agent.updated_at
            ? new Date(agent.updated_at).toLocaleString()
            : '-'}
        </Descriptions.Item>
      </Descriptions>
    </GlassPanel>
  );

  const runtimeTab = (
    <GlassPanel>
      <Descriptions
        bordered
        size="small"
        column={1}
        styles={{ label: { width: 160 } }}
      >
        <Descriptions.Item label="Docker 镜像">
          {agent.docker_image ? (
            <span
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 12,
                color: '#c5cee0',
              }}
            >
              {agent.docker_image}
            </span>
          ) : (
            '-'
          )}
        </Descriptions.Item>
        <Descriptions.Item label="Entrypoint">
          {agent.entrypoint ? (
            <span
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 12,
                color: '#c5cee0',
              }}
            >
              {agent.entrypoint}
            </span>
          ) : (
            '-'
          )}
        </Descriptions.Item>
        <Descriptions.Item label="端口">
          {agent.ports && agent.ports.length > 0 ? (
            <Space size={4} wrap>
              {agent.ports.map((p) => (
                <TagPill key={p} color="cyan">
                  {p}
                </TagPill>
              ))}
            </Space>
          ) : (
            '-'
          )}
        </Descriptions.Item>
        <Descriptions.Item label="资源限制">
          <pre
            style={{
              margin: 0,
              padding: 8,
              background: 'rgba(0,0,0,0.25)',
              borderRadius: 8,
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 12,
              color: '#c5cee0',
              maxHeight: 200,
              overflow: 'auto',
            }}
          >
            {jsonBlock(agent.resource_limit)}
          </pre>
        </Descriptions.Item>
        <Descriptions.Item label="Volume Mounts">
          <pre
            style={{
              margin: 0,
              padding: 8,
              background: 'rgba(0,0,0,0.25)',
              borderRadius: 8,
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 12,
              color: '#c5cee0',
              maxHeight: 200,
              overflow: 'auto',
            }}
          >
            {jsonBlock(agent.volume_mounts)}
          </pre>
        </Descriptions.Item>
      </Descriptions>
    </GlassPanel>
  );

  const templateTab = (
    <GlassPanel>
      <Descriptions
        bordered
        size="small"
        column={1}
        styles={{ label: { width: 160 } }}
      >
        <Descriptions.Item label="环境变量模板">
          <pre
            style={{
              margin: 0,
              padding: 8,
              background: 'rgba(0,0,0,0.25)',
              borderRadius: 8,
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 12,
              color: '#c5cee0',
              maxHeight: 240,
              overflow: 'auto',
            }}
          >
            {jsonBlock(agent.env_template)}
          </pre>
        </Descriptions.Item>
        <Descriptions.Item label="配置模板">
          <pre
            style={{
              margin: 0,
              padding: 8,
              background: 'rgba(0,0,0,0.25)',
              borderRadius: 8,
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 12,
              color: '#c5cee0',
              maxHeight: 320,
              overflow: 'auto',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {agent.config_template || '(未设置)'}
          </pre>
        </Descriptions.Item>
      </Descriptions>
    </GlassPanel>
  );

  return (
    <div>
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { title: <Link to="/resources">资源管理</Link> },
          { title: '智能体容器' },
          { title: agent.name },
        ]}
      />
      <PageHeader
        title={agent.name}
        subtitle={`${TYPE_LABELS[agent.agent_type] ?? agent.agent_type} · ${RUNTIME_LABELS[agent.runtime] ?? agent.runtime}${agent.version ? ` · v${agent.version}` : ''}`}
        extra={
          <Space>
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/resources')}
            >
              返回列表
            </Button>
            <Button icon={<ReloadOutlined />} onClick={loadAgent}>
              刷新
            </Button>
          </Space>
        }
      />
      <Tabs
        activeKey={activeTab}
        onChange={(k) => setActiveTab(k as TabKey)}
        items={[
          { key: 'overview', label: '基本信息', children: overviewTab },
          { key: 'runtime', label: 'Runtime 配置', children: runtimeTab },
          { key: 'template', label: '环境与配置模板', children: templateTab },
        ]}
      />
    </div>
  );
}
