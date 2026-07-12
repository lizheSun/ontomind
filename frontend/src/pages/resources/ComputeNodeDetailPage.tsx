/**
 * ComputeNodeDetailPage — 计算节点详情页 (T50 Wave 10)
 *
 * 呈现单个计算节点的完整信息：主机名、OS、CPU/内存/磁盘、IP、状态、心跳，
 * 以及节点上关联的 Agent Container 列表（通过 scan-agents 发现）。
 *
 * 数据源：
 *   - `resourcesAPI.getComputeNode(id)` → Instance/ComputeNode 元数据
 *   - `resourcesAPI.scanAgentsOnNode(id)` → DiscoveredAgent[]（关联容器）
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
import type { ColumnsType } from 'antd/es/table';
import {
  ArrowLeftOutlined,
  ExperimentOutlined,
  HeartOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  DataTable,
  GlassPanel,
  PageHeader,
  TagPill,
} from '../../components/common';
import { resourcesAPI } from '../../services';
import type {
  AgentScanResult,
  DiscoveredAgent,
  Instance,
} from '../../types';

const { Paragraph, Text } = Typography;

const TYPE_LABELS: Record<Instance['instance_type'], string> = {
  physical: '物理机',
  docker: 'Docker',
  k8s_pod: 'K8s Pod',
};

const TYPE_COLORS: Record<
  Instance['instance_type'],
  'blue' | 'emerald' | 'purple'
> = {
  physical: 'blue',
  docker: 'emerald',
  k8s_pod: 'purple',
};

const STATUS_LABELS: Record<Instance['status'], string> = {
  online: '在线',
  offline: '离线',
  maintenance: '维护中',
};

const AGENT_TYPE_COLORS: Record<
  DiscoveredAgent['agent_type'],
  'amber' | 'emerald' | 'blue' | 'purple'
> = {
  openclaw: 'amber',
  opencode: 'emerald',
  harness: 'blue',
  custom: 'purple',
};

type TabKey = 'overview' | 'containers';

function formatMemory(memMb?: number): string {
  if (memMb == null) return '-';
  if (memMb >= 1024) return `${(memMb / 1024).toFixed(1)} GB`;
  return `${memMb} MB`;
}

function formatHeartbeat(ts?: string): string {
  if (!ts) return '-';
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleString();
}

export default function ComputeNodeDetailPage() {
  const { id: idParam } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const id = Number(idParam);

  const [node, setNode] = useState<Instance | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabKey>('overview');
  const [containers, setContainers] = useState<DiscoveredAgent[]>([]);
  const [scanning, setScanning] = useState(false);
  const [heartbeating, setHeartbeating] = useState(false);
  const [lastScanAt, setLastScanAt] = useState<string | null>(null);

  const loadNode = useCallback(async () => {
    if (!Number.isFinite(id)) return;
    setLoading(true);
    try {
      const res = await resourcesAPI.getInstance(id);
      const data: Instance = res.data?.data ?? res.data;
      setNode(data);
    } catch (err) {
      message.error(err instanceof Error ? err.message : '加载节点失败');
    } finally {
      setLoading(false);
    }
  }, [id, message]);

  const scanContainers = useCallback(async () => {
    if (!Number.isFinite(id)) return;
    setScanning(true);
    try {
      const res = await resourcesAPI.scanAgents(id);
      const data: AgentScanResult = res.data?.data ?? res.data;
      const list = data?.agents ?? [];
      setContainers(list);
      setLastScanAt(new Date().toLocaleString());
      const healthy = list.filter((a) => a.is_healthy).length;
      message.success(
        `扫描完成：发现 ${list.length} 个容器，${healthy} 个健康`,
      );
    } catch (err) {
      message.error(err instanceof Error ? err.message : '扫描失败');
    } finally {
      setScanning(false);
    }
  }, [id, message]);

  const handleHeartbeat = async () => {
    if (!Number.isFinite(id)) return;
    setHeartbeating(true);
    try {
      await resourcesAPI.heartbeatInstance(id);
      message.success('心跳已发送');
      await loadNode();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '心跳失败');
    } finally {
      setHeartbeating(false);
    }
  };

  useEffect(() => {
    if (!Number.isFinite(id)) {
      message.error('无效的节点 ID');
      navigate('/resources', { replace: true });
      return;
    }
    void loadNode();
  }, [id, loadNode, navigate, message]);

  const containerColumns: ColumnsType<DiscoveredAgent> = [
    {
      title: '容器',
      key: 'label',
      render: (_: unknown, row) => (
        <Space size={6}>
          <span style={{ fontSize: 16 }}>{row.icon}</span>
          <span style={{ color: '#e8eef5', fontWeight: 500 }}>{row.label}</span>
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'agent_type',
      key: 'agent_type',
      width: 130,
      render: (t: DiscoveredAgent['agent_type']) => (
        <TagPill color={AGENT_TYPE_COLORS[t] ?? 'blue'}>{t}</TagPill>
      ),
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      width: 110,
      render: (v?: string) =>
        v ? (
          <span
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 12,
              color: '#8895b4',
            }}
          >
            {v}
          </span>
        ) : (
          '-'
        ),
    },
    {
      title: '地址',
      key: 'address',
      width: 180,
      render: (_: unknown, row) => (
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 12,
            color: '#8895b4',
          }}
        >
          {row.host}:{row.port}
        </span>
      ),
    },
    {
      title: '进程',
      dataIndex: 'process_name',
      key: 'process_name',
      width: 150,
      render: (v?: string) =>
        v ? (
          <span
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 12,
              color: '#8895b4',
            }}
          >
            {v}
          </span>
        ) : (
          '-'
        ),
    },
    {
      title: '交互',
      dataIndex: 'interaction_mode',
      key: 'interaction_mode',
      width: 90,
      render: (m: DiscoveredAgent['interaction_mode']) => (
        <Tag>{m}</Tag>
      ),
    },
    {
      title: '健康',
      dataIndex: 'is_healthy',
      key: 'is_healthy',
      width: 90,
      render: (h: boolean, row) =>
        h ? (
          <Tag color="success">健康</Tag>
        ) : row.error ? (
          <Tag color="error">异常</Tag>
        ) : (
          <Tag>未知</Tag>
        ),
    },
  ];

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <Spin />
      </div>
    );
  }

  if (!node) {
    return (
      <div>
        <PageHeader title="计算节点详情" subtitle="节点不存在或已被删除" />
        <GlassPanel>
          <Paragraph style={{ color: '#8895b4' }}>
            未找到 ID 为 {idParam} 的计算节点。
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
        <Descriptions.Item label="节点名称">{node.name}</Descriptions.Item>
        <Descriptions.Item label="类型">
          <TagPill color={TYPE_COLORS[node.instance_type] ?? 'blue'}>
            {TYPE_LABELS[node.instance_type] ?? node.instance_type}
          </TagPill>
        </Descriptions.Item>
        <Descriptions.Item label="主机 / IP">
          <span
            style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}
          >
            {node.host}
          </span>
        </Descriptions.Item>
        <Descriptions.Item label="端口">
          <span
            style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}
          >
            {node.port}
          </span>
        </Descriptions.Item>
        <Descriptions.Item label="协议">
          <Tag>{node.protocol}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="操作系统">
          {node.os ?? '-'}
        </Descriptions.Item>
        <Descriptions.Item label="CPU">
          {node.cpu_cores != null ? `${node.cpu_cores} 核` : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="内存">
          {formatMemory(node.memory_mb)}
        </Descriptions.Item>
        <Descriptions.Item label="磁盘">
          {node.disk_gb != null ? `${node.disk_gb} GB` : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="状态">
          <Tag
            color={
              node.status === 'online'
                ? 'success'
                : node.status === 'maintenance'
                  ? 'warning'
                  : 'default'
            }
          >
            {STATUS_LABELS[node.status] ?? node.status}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="最近心跳" span={2}>
          <Space size={4}>
            <HeartOutlined style={{ color: '#fb7185' }} />
            <span
              style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}
            >
              {formatHeartbeat(node.last_heartbeat)}
            </span>
          </Space>
        </Descriptions.Item>
        <Descriptions.Item label="标签" span={2}>
          {node.labels && Object.keys(node.labels).length > 0 ? (
            <Space size={4} wrap>
              {Object.entries(node.labels).map(([k, v]) => (
                <TagPill key={k} color="cyan">
                  {k}: {String(v)}
                </TagPill>
              ))}
            </Space>
          ) : (
            '-'
          )}
        </Descriptions.Item>
        <Descriptions.Item label="描述" span={2}>
          {node.description || '-'}
        </Descriptions.Item>
        <Descriptions.Item label="创建时间">
          {node.created_at ? new Date(node.created_at).toLocaleString() : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="更新时间">
          {node.updated_at ? new Date(node.updated_at).toLocaleString() : '-'}
        </Descriptions.Item>
      </Descriptions>
    </GlassPanel>
  );

  const containersTab = (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 12,
        }}
      >
        <Text style={{ color: '#8895b4', fontSize: 12 }}>
          {lastScanAt ? `最近扫描：${lastScanAt}` : '点击「扫描容器」发现节点上的 Agent 容器'}
        </Text>
        <Button
          type="primary"
          icon={<ExperimentOutlined />}
          loading={scanning}
          onClick={scanContainers}
        >
          扫描容器
        </Button>
      </div>
      <DataTable<DiscoveredAgent>
        rowKey={(row) => `${row.agent_type}-${row.host}-${row.port}`}
        columns={containerColumns}
        dataSource={containers}
        loading={scanning}
        emptyTitle="暂无关联容器"
        emptyDescription="尚未扫描或该节点上未运行 Agent 容器"
      />
    </div>
  );

  return (
    <div>
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { title: <Link to="/resources">资源管理</Link> },
          { title: '计算节点' },
          { title: node.name },
        ]}
      />
      <PageHeader
        title={node.name}
        subtitle={`${node.host}:${node.port} · ${TYPE_LABELS[node.instance_type] ?? node.instance_type}`}
        extra={
          <Space>
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/resources')}
            >
              返回列表
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={loadNode}
            >
              刷新
            </Button>
            <Button
              icon={<HeartOutlined />}
              loading={heartbeating}
              onClick={handleHeartbeat}
            >
              心跳
            </Button>
          </Space>
        }
      />
      <Tabs
        activeKey={activeTab}
        onChange={(k) => setActiveTab(k as TabKey)}
        items={[
          { key: 'overview', label: '节点信息', children: overviewTab },
          {
            key: 'containers',
            label: `关联容器${containers.length > 0 ? ` (${containers.length})` : ''}`,
            children: containersTab,
          },
        ]}
      />
    </div>
  );
}
