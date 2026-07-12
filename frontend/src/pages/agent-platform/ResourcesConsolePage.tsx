import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Badge,
  Button,
  Card,
  Descriptions,
  Divider,
  Drawer,
  Empty,
  Flex,
  Form,
  Input,
  InputNumber,
  Modal,
  Radio,
  Select,
  Space,
  Spin,
  Statistic,
  Steps,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  ApiOutlined,
  AppstoreOutlined,
  CloudServerOutlined,
  CodeOutlined,
  DeploymentUnitOutlined,
  EditOutlined,
  FolderOpenOutlined,
  PlusOutlined,
  ReloadOutlined,
  RobotOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import { agentPlatformService } from '../../services/agentPlatform.service';
import type { NodeCreatePayload } from '../../services/agentPlatform.service';
import type {
  AgentSummary,
  ComputeNode,
  DiscoveryDecision,
  DiscoveryItem,
  InventoryResource,
  NodeInventory,
  OpenCodeContainer,
} from './types';
import { availableDiscoveryDecisions, resolveDiscoveryDecision } from './domain';
import { PlatformPageHeader } from './components';

const { Text, Paragraph, Title } = Typography;

const decisionLabels: Record<DiscoveryDecision, string> = {
  pending: '待处理',
  import: '导入新资源',
  link: '关联已有资源',
  keep_platform: '保留平台版本',
  ignore: '忽略',
  external: '保持外部管理',
};

const containerStatus: Record<OpenCodeContainer['status'], { color: string; label: string }> = {
  running: { color: 'success', label: '运行中' },
  stopped: { color: 'default', label: '已停止' },
  not_installed: { color: 'warning', label: '未安装' },
};

interface NodeWizardValues {
  name: string;
  hostname?: string;
  platform?: string;
  labels_text?: string;
  connector_type: 'local' | 'ssh';
  address?: string;
  port?: number;
  username?: string;
  credential_type: 'private_key' | 'password';
  credential_value?: string;
  host_key_algorithm?: string;
  host_key_fingerprint?: string;
  managed_roots_text: string;
}

function resourceColumns(onSelect: (row: InventoryResource) => void): ColumnsType<InventoryResource> {
  return [
    {
      title: '名称',
      dataIndex: 'external_key',
      render: (value, row) => (
        <Button type="link" style={{ padding: 0 }} onClick={() => onSelect(row)}>
          {value}
        </Button>
      ),
    },
    {
      title: '来源',
      dataIndex: 'origin',
      render: (value) => (
        <Tag color={value === 'both' ? 'purple' : value === 'platform' ? 'blue' : 'green'}>
          {value === 'both' ? '平台+OpenCode' : value === 'platform' ? '平台' : 'OpenCode'}
        </Tag>
      ),
    },
    {
      title: '位置',
      dataIndex: 'location',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      render: (value) => <Tag>{value}</Tag>,
    },
  ];
}

export default function ResourcesConsolePage() {
  const navigate = useNavigate();
  const [nodes, setNodes] = useState<ComputeNode[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [inventory, setInventory] = useState<NodeInventory | null>(null);
  const [selectedResource, setSelectedResource] = useState<InventoryResource | null>(null);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [loadingInventory, setLoadingInventory] = useState(false);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardStep, setWizardStep] = useState(0);
  const [form] = Form.useForm<NodeWizardValues>();
  const connectorType = Form.useWatch('connector_type', form);
  const [saving, setSaving] = useState(false);
  const [discoveryOpen, setDiscoveryOpen] = useState(false);
  const [discoveryId, setDiscoveryId] = useState<number | null>(null);
  const [items, setItems] = useState<DiscoveryItem[]>([]);
  const [discoveryLoading, setDiscoveryLoading] = useState(false);
  const [platformAgents, setPlatformAgents] = useState<AgentSummary[]>([]);
  const [publishingId, setPublishingId] = useState<number | null>(null);

  const loadInventory = useCallback(async (nodeId: number, refresh = false) => {
    setLoadingInventory(true);
    try {
      const data = await agentPlatformService.getNodeInventory(nodeId, refresh);
      setInventory(data);
      setSelectedResource(null);
    } catch (reason) {
      message.error(reason instanceof Error ? reason.message : '加载资源清单失败');
    } finally {
      setLoadingInventory(false);
    }
  }, []);

  const bootstrap = useCallback(async () => {
    setBootstrapping(true);
    try {
      await agentPlatformService.registerLocalNode();
      const [nodeList, agents] = await Promise.all([
        agentPlatformService.listNodes(),
        agentPlatformService.listAgents(),
      ]);
      setNodes(nodeList);
      setPlatformAgents(agents);
      const preferred =
        nodeList.find((node) => node.connection.connector_type === 'local') ?? nodeList[0];
      if (preferred) {
        setSelectedNodeId(preferred.id);
        await loadInventory(preferred.id, true);
      }
    } catch (reason) {
      message.error(reason instanceof Error ? reason.message : '初始化本机节点失败');
    } finally {
      setBootstrapping(false);
    }
  }, [loadInventory]);

  const publishPlatformAgent = async (agentId: number) => {
    setPublishingId(agentId);
    try {
      const versions = await agentPlatformService.listAgentVersions(agentId);
      if (!versions.length) throw new Error('尚无版本，请先编辑并保存草稿');
      await agentPlatformService.publishAgentVersion(agentId, versions[0].id);
      const agents = await agentPlatformService.listAgents();
      setPlatformAgents(agents);
      message.success('Agent 已发布，可在对话工作台使用');
    } catch (reason) {
      message.error(reason instanceof Error ? reason.message : '发布失败');
    } finally {
      setPublishingId(null);
    }
  };

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  const startDiscovery = async (nodeId: number) => {
    setDiscoveryLoading(true);
    setDiscoveryOpen(true);
    try {
      const run = await agentPlatformService.startDiscovery(nodeId);
      setDiscoveryId(run.id);
      const discovered = await agentPlatformService.listDiscoveryItems(run.id);
      setItems(discovered);
    } catch (reason) {
      message.error(reason instanceof Error ? reason.message : '启动发现失败');
    } finally {
      setDiscoveryLoading(false);
    }
  };

  const registerNode = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const labels = Object.fromEntries(
        (values.labels_text ?? '')
          .split(/\r?\n/)
          .map((line) => line.split('=', 2).map((part) => part.trim()))
          .filter(([key]) => key),
      );
      const payload: NodeCreatePayload = {
        name: values.name,
        hostname: values.hostname || null,
        platform: values.platform || null,
        labels,
        connection: {
          connector_type: values.connector_type,
          address: values.address || null,
          port: values.port || null,
          username: values.username || null,
          password:
            values.credential_type === 'password' ? values.credential_value || null : null,
          private_key:
            values.credential_type === 'private_key' ? values.credential_value || null : null,
          host_key_algorithm: values.host_key_algorithm || null,
          host_key_fingerprint: values.host_key_fingerprint || null,
          managed_roots: values.managed_roots_text
            .split(/\r?\n/)
            .map((root) => root.trim())
            .filter(Boolean),
        },
      };
      const node = await agentPlatformService.createNode(payload);
      setWizardOpen(false);
      const nodeList = await agentPlatformService.listNodes();
      setNodes(nodeList);
      setSelectedNodeId(node.id);
      await loadInventory(node.id, true);
      await startDiscovery(node.id);
    } catch (reason) {
      if (reason instanceof Error) message.error(reason.message);
    } finally {
      setSaving(false);
    }
  };

  const decide = async (item: DiscoveryItem, decision: DiscoveryDecision) => {
    if (!discoveryId) return;
    try {
      if (decision === 'pending') return;
      const optimistic = resolveDiscoveryDecision(item, decision);
      setItems((current) => current.map((row) => row.id === item.id ? optimistic : row));
      const saved = await agentPlatformService.decideDiscoveryItem(
        discoveryId,
        item.id,
        decision,
      );
      setItems((current) => current.map((row) => row.id === item.id ? saved : row));
    } catch (reason) {
      message.error(reason instanceof Error ? reason.message : '保存发现决策失败');
    }
  };

  const applyDiscovery = async () => {
    if (!discoveryId || !selectedNodeId) return;
    if (items.some((item) => item.decision === 'pending')) {
      message.warning('仍有资源未作出明确决策');
      return;
    }
    try {
      const importIds = items
        .filter((item) => item.decision === 'import')
        .map((item) => item.id);
      await agentPlatformService.applyDiscovery(discoveryId, importIds);
      message.success('发现决策已提交应用');
      setDiscoveryOpen(false);
      await loadInventory(selectedNodeId, false);
    } catch (reason) {
      message.error(reason instanceof Error ? reason.message : '应用发现结果失败');
    }
  };

  const stats = useMemo(() => ({
    nodes: nodes.length,
    online: nodes.filter((node) => node.status === 'online').length,
    opencode: inventory?.containers.filter((item) => item.status === 'running').length ?? 0,
    agents: inventory?.resources.agents.length ?? 0,
    skills: inventory?.resources.skills.length ?? 0,
    mcps: inventory?.resources.mcps.length ?? 0,
  }), [nodes, inventory]);

  const opencode = inventory?.containers[0] ?? null;

  const wizardContents = [
    <Form form={form} layout="vertical" key="basic" initialValues={{ connector_type: 'ssh', platform: 'linux', port: 22, credential_type: 'private_key', managed_roots_text: '~/.config/opencode' }}>
      <Form.Item name="connector_type" label="节点类型" rules={[{ required: true }]}>
        <Radio.Group options={[{ label: '注册本机', value: 'local' }, { label: '远程 Linux（SSH）', value: 'ssh' }]} optionType="button" />
      </Form.Item>
      <Form.Item name="name" label="节点名称" rules={[{ required: true, message: '请输入节点名称' }]}><Input /></Form.Item>
      <Flex gap={12}>
        <Form.Item name="hostname" label="主机名" style={{ flex: 1 }}><Input /></Form.Item>
        <Form.Item name="platform" label="平台" style={{ flex: 1 }}><Select options={['linux', 'darwin', 'windows'].map((value) => ({ value, label: value }))} /></Form.Item>
      </Flex>
      <Flex gap={12}>
        <Form.Item name="address" label="主机地址" rules={[{ required: connectorType === 'ssh', message: '请输入主机地址' }]} style={{ flex: 1 }}><Input placeholder="localhost 或 10.0.0.8" /></Form.Item>
        <Form.Item name="port" label="端口"><InputNumber min={1} max={65535} /></Form.Item>
      </Flex>
      <Form.Item name="labels_text" label="标签（每行 key=value）"><Input.TextArea rows={3} placeholder="environment=test" /></Form.Item>
    </Form>,
    <Form form={form} layout="vertical" key="credential">
      <Alert type="warning" showIcon message="凭据仅在提交时发送，保存后不会回显明文" style={{ marginBottom: 16 }} />
      <Form.Item name="username" label="用户名" rules={[{ required: connectorType === 'ssh', message: 'SSH 节点必须填写用户名' }]}><Input /></Form.Item>
      <Form.Item name="credential_type" label="认证方式"><Select options={[{ value: 'private_key', label: 'SSH 私钥' }, { value: 'password', label: '密码' }]} /></Form.Item>
      <Form.Item name="credential_value" label="凭据"><Input.TextArea rows={6} /></Form.Item>
    </Form>,
    <Form form={form} layout="vertical" key="trust">
      <Alert type="info" showIcon message="首次连接后必须核对服务端主机指纹；指纹变化将阻断后续操作。" />
      <Form.Item name="host_key_algorithm" label="Host key 算法" rules={[{ required: connectorType === 'ssh', message: 'SSH 节点必须填写算法' }]} style={{ marginTop: 16 }}><Input placeholder="ssh-ed25519" /></Form.Item>
      <Form.Item name="host_key_fingerprint" label="Host key 指纹" rules={[{ required: connectorType === 'ssh', message: 'SSH 节点必须填写指纹' }]}><Input placeholder="SHA256:..." /></Form.Item>
    </Form>,
    <Space direction="vertical" style={{ width: '100%' }} key="checks">
      {['网络与 SSH 可达', '系统信息只读权限', 'OpenCode 配置目录读取', '受管发布目录写入'].map((name) => (
        <Card size="small" key={name}><Flex justify="space-between"><Text>{name}</Text><Tag>注册后检查</Tag></Flex></Card>
      ))}
    </Space>,
    <Space direction="vertical" style={{ width: '100%' }} key="preview">
      <Alert type="success" showIcon message="注册后将自动启动只读发现" />
      <Form form={form} layout="vertical">
        <Form.Item name="managed_roots_text" label="受管配置根目录（每行一个）" rules={[{ required: true, message: '至少配置一个受管目录' }]}>
          <Input.TextArea rows={4} />
        </Form.Item>
      </Form>
    </Space>,
  ];

  if (bootstrapping) {
    return (
      <Flex align="center" justify="center" style={{ minHeight: 360 }}>
        <Space direction="vertical" align="center">
          <Spin size="large" />
          <Text type="secondary">正在自动注册本机并扫描 OpenCode 环境…</Text>
        </Space>
      </Flex>
    );
  }

  return (
    <div style={{ minWidth: 1080 }}>
      <PlatformPageHeader
        title="资源控制台"
        subtitle="计算节点 → OpenCode 容器 → Agent / Skill / MCP。在此编辑、发布平台 Agent。"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => void bootstrap()}>重新扫描本机</Button>
            <Button onClick={() => navigate('/resources/legacy')}>旧版资源页</Button>
            <Button onClick={() => navigate('/workspace')}>对话工作台</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/agent-platform/agents/new/studio')}>
              定制 Agent
            </Button>
            <Button icon={<PlusOutlined />} onClick={() => { form.resetFields(); setWizardStep(0); setWizardOpen(true); }}>注册远程节点</Button>
          </Space>
        }
      />

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="层级说明"
        description="第一层是物理计算节点；第二层是 OpenCode 运行时；第三层是 Agent / Skill / MCP。平台 Agent 的编辑与发布在下方「平台 Agent」中操作。"
      />

      <Card
        title="平台 Agent（编辑 / 发布）"
        size="small"
        style={{ marginBottom: 16 }}
        extra={<Button type="link" onClick={() => navigate('/agent-platform/agents/new/studio')}>新建</Button>}
      >
        <Table<AgentSummary>
          rowKey="id"
          size="small"
          pagination={false}
          locale={{ emptyText: '暂无平台 Agent，请先定制并保存' }}
          dataSource={platformAgents}
          columns={[
            { title: '名称', dataIndex: 'name' },
            {
              title: '状态',
              dataIndex: 'is_published',
              render: (published: boolean, row) => (
                <Tag color={published ? 'success' : 'default'}>
                  {published ? `已发布 v${row.version}` : '未发布'}
                </Tag>
              ),
            },
            {
              title: '描述',
              dataIndex: 'description',
              ellipsis: true,
              render: (value) => value || '-',
            },
            {
              title: '操作',
              key: 'actions',
              width: 260,
              render: (_, row) => (
                <Space>
                  <Button
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() => navigate(`/agent-platform/agents/${row.id}/studio`)}
                  >
                    编辑
                  </Button>
                  <Button
                    size="small"
                    type="primary"
                    icon={<RocketOutlined />}
                    loading={publishingId === row.id}
                    onClick={() => void publishPlatformAgent(row.id)}
                  >
                    {row.is_published ? '重新发布' : '发布'}
                  </Button>
                  <Button size="small" onClick={() => navigate('/workspace')}>
                    去对话
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 12, marginBottom: 16 }}>
        {[
          ['计算节点', stats.nodes, <CloudServerOutlined key="n" />],
          ['在线节点', stats.online, <CodeOutlined key="o" />],
          ['OpenCode', stats.opencode, <RobotOutlined key="r" />],
          ['Agent', stats.agents, <DeploymentUnitOutlined key="a" />],
          ['Skill', stats.skills, <AppstoreOutlined key="s" />],
          ['MCP', stats.mcps, <ApiOutlined key="m" />],
        ].map(([label, value, icon]) => (
          <Card key={String(label)} size="small">
            <Statistic title={String(label)} value={value as string | number} prefix={icon} />
          </Card>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '280px minmax(0, 1fr) 320px', gap: 14 }}>
        <Card title="计算节点" size="small">
          <Space direction="vertical" style={{ width: '100%' }}>
            {nodes.map((node) => (
              <Card
                key={node.id}
                size="small"
                hoverable
                style={{
                  borderColor: selectedNodeId === node.id ? '#3b82f6' : undefined,
                  cursor: 'pointer',
                }}
                onClick={() => {
                  setSelectedNodeId(node.id);
                  void loadInventory(node.id, false);
                }}
              >
                <Space direction="vertical" size={2}>
                  <Space>
                    <CloudServerOutlined />
                    <Text strong>{node.name}</Text>
                  </Space>
                  <Text type="secondary">{node.hostname || node.connection.address || '-'}</Text>
                  <Space>
                    <Tag>{node.connection.connector_type}</Tag>
                    <Badge status={node.status === 'online' ? 'success' : 'default'} text={node.status} />
                  </Space>
                </Space>
              </Card>
            ))}
            {!nodes.length ? <Empty description="暂无节点" /> : null}
          </Space>
        </Card>

        <Spin spinning={loadingInventory}>
          <Space direction="vertical" style={{ width: '100%' }} size={14}>
            {opencode ? (
              <Card
                title={
                  <Space>
                    <RobotOutlined />
                    <span>OpenCode 容器</span>
                    <Tag color={containerStatus[opencode.status].color}>
                      {containerStatus[opencode.status].label}
                    </Tag>
                  </Space>
                }
                extra={
                  selectedNodeId ? (
                    <Button size="small" icon={<ReloadOutlined />} onClick={() => void loadInventory(selectedNodeId, true)}>
                      重新发现
                    </Button>
                  ) : null
                }
              >
                <Descriptions size="small" column={2} items={[
                  { key: 'node', label: '所属节点', children: opencode.node_name },
                  { key: 'host', label: '主机', children: opencode.hostname || '-' },
                  { key: 'cli', label: 'CLI', children: opencode.cli_path || '未检测到' },
                  { key: 'version', label: '版本', children: opencode.version || '-' },
                  { key: 'config', label: '配置文件', children: opencode.config_path || '-' },
                  { key: 'roots', label: '受管目录', children: opencode.managed_roots.join(', ') || '-' },
                ]} />
              </Card>
            ) : (
              <Card><Empty description="请选择计算节点，或重新扫描本机" /></Card>
            )}

            <Card title="OpenCode 下的资源">
              <Tabs
                items={[
                  {
                    key: 'agents',
                    label: `Agent (${inventory?.resources.agents.length ?? 0})`,
                    children: (
                      <Table
                        rowKey={(row) => row.external_key}
                        size="small"
                        pagination={false}
                        columns={resourceColumns(setSelectedResource)}
                        dataSource={inventory?.resources.agents ?? []}
                      />
                    ),
                  },
                  {
                    key: 'skills',
                    label: `Skill (${inventory?.resources.skills.length ?? 0})`,
                    children: (
                      <Table
                        rowKey={(row) => row.external_key}
                        size="small"
                        pagination={false}
                        columns={resourceColumns(setSelectedResource)}
                        dataSource={inventory?.resources.skills ?? []}
                      />
                    ),
                  },
                  {
                    key: 'mcps',
                    label: `MCP (${inventory?.resources.mcps.length ?? 0})`,
                    children: (
                      <Table
                        rowKey={(row) => row.external_key}
                        size="small"
                        pagination={false}
                        columns={resourceColumns(setSelectedResource)}
                        dataSource={inventory?.resources.mcps ?? []}
                      />
                    ),
                  },
                  {
                    key: 'config',
                    label: 'OpenCode 配置',
                    children: opencode?.config_preview ? (
                      <pre style={{ margin: 0, maxHeight: 320, overflow: 'auto', fontSize: 12 }}>
                        {JSON.stringify(opencode.config_preview, null, 2)}
                      </pre>
                    ) : (
                      <Empty description="未读取到 opencode.json" />
                    ),
                  },
                ]}
              />
            </Card>
          </Space>
        </Spin>

        <Card title="资源详情 / 运行位置" size="small">
          {selectedResource ? (
            <Space direction="vertical" style={{ width: '100%' }}>
              <Title level={5} style={{ margin: 0 }}>{selectedResource.external_key}</Title>
              <Tag>{selectedResource.resource_type}</Tag>
              <Descriptions size="small" column={1} items={[
                { key: 'origin', label: '来源', children: selectedResource.origin },
                { key: 'location', label: '配置位置', children: selectedResource.location },
                { key: 'node', label: '运行节点', children: inventory?.node.name ?? '-' },
                { key: 'container', label: '运行时', children: opencode?.name ?? 'OpenCode' },
                { key: 'config', label: 'OpenCode 配置', children: opencode?.config_path ?? '-' },
              ]} />
              <Divider style={{ margin: '8px 0' }} />
              <Text type="secondary">远程快照</Text>
              <pre style={{ margin: 0, maxHeight: 220, overflow: 'auto', fontSize: 12 }}>
                {JSON.stringify(selectedResource.remote_snapshot, null, 2)}
              </pre>
              {selectedResource.resource_type === 'agent' ? (
                <Space direction="vertical" style={{ width: '100%' }}>
                  {selectedResource.platform_resource_id ? (
                    <>
                      <Button
                        block
                        type="primary"
                        icon={<EditOutlined />}
                        onClick={() => navigate(`/agent-platform/agents/${selectedResource.platform_resource_id}/studio`)}
                      >
                        编辑此 Agent
                      </Button>
                      <Button
                        block
                        icon={<RocketOutlined />}
                        loading={publishingId === selectedResource.platform_resource_id}
                        onClick={() => void publishPlatformAgent(selectedResource.platform_resource_id!)}
                      >
                        发布上线
                      </Button>
                    </>
                  ) : null}
                  <Button block onClick={() => navigate('/agent-platform/agents/new/studio')}>
                    基于此定制新 Agent
                  </Button>
                </Space>
              ) : null}
            </Space>
          ) : (
            <Empty
              image={<FolderOpenOutlined style={{ fontSize: 42, color: '#506380' }} />}
              description="选择 Agent / Skill / MCP 查看它在哪个节点、哪个 OpenCode 实例上运行"
            />
          )}
        </Card>
      </div>

      <Modal
        width={760}
        open={wizardOpen}
        title="注册远程计算节点"
        onCancel={() => setWizardOpen(false)}
        footer={[
          <Button key="back" disabled={wizardStep === 0} onClick={() => setWizardStep((value) => value - 1)}>上一步</Button>,
          wizardStep < 4
            ? <Button key="next" type="primary" onClick={() => setWizardStep((value) => value + 1)}>下一步</Button>
            : <Button key="submit" type="primary" loading={saving} onClick={() => void registerNode()}>注册并发现</Button>,
        ]}
      >
        <Steps current={wizardStep} size="small" items={['基本信息', '凭据', '主机信任', '权限检查', '发现预览'].map((title) => ({ title }))} style={{ margin: '12px 0 28px' }} />
        {wizardContents[wizardStep]}
      </Modal>

      <Drawer
        width={760}
        open={discoveryOpen}
        title="发现预览与冲突决策"
        onClose={() => setDiscoveryOpen(false)}
        extra={<Button type="primary" disabled={!items.length} onClick={() => void applyDiscovery()}>应用已确认决策</Button>}
      >
        <Alert type="info" showIcon message="发现只记录快照；只有应用明确决策后才会写入正式资源。" style={{ marginBottom: 16 }} />
        <Table<DiscoveryItem>
          rowKey="id"
          loading={discoveryLoading}
          pagination={false}
          dataSource={items}
          columns={[
            { title: '类型', dataIndex: 'resource_type', render: (value) => <Tag>{value}</Tag> },
            { title: '资源', dataIndex: 'external_key', render: (value) => <Text code>{value}</Text> },
            { title: '状态', dataIndex: 'status', render: (value) => <Tag>{value}</Tag> },
            {
              title: '处理决策',
              render: (_, item) => (
                <Select
                  value={item.decision}
                  style={{ width: 170 }}
                  onChange={(value: DiscoveryDecision) => void decide(item, value)}
                  options={availableDiscoveryDecisions(item).map((value) => ({ value, label: decisionLabels[value] }))}
                />
              ),
            },
          ]}
        />
        <Divider />
        <Paragraph type="secondary">changed 资源只能导入为新版本、保留平台版本或忽略，不会直接覆盖正式版本。</Paragraph>
      </Drawer>
    </div>
  );
}
