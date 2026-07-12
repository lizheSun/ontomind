import { useMemo, useState } from 'react';
import {
  Alert,
  Avatar,
  Badge,
  Button,
  Card,
  Checkbox,
  Descriptions,
  Divider,
  Drawer,
  Flex,
  Form,
  Input,
  List,
  Modal,
  Progress,
  Radio,
  Segmented,
  Select,
  Space,
  Statistic,
  Steps,
  Table,
  Tag,
  Timeline,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  ApiOutlined,
  AppstoreOutlined,
  AuditOutlined,
  CloudServerOutlined,
  CodeOutlined,
  DeploymentUnitOutlined,
  ExperimentOutlined,
  MessageOutlined,
  NodeIndexOutlined,
  PlusOutlined,
  ReloadOutlined,
  RocketOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import AgentChatPanel from '../../components/common/AgentChatPanel';
import type {
  AgentChatMessage,
  AgentChatPart,
} from '../../components/common/AgentChatPanel';

const { Text, Title, Paragraph } = Typography;

type PrototypeSection = 'chat' | 'resources' | 'studio' | 'release';

type NodeRow = {
  key: string;
  name: string;
  host: string;
  environment: string;
  status: 'online' | 'degraded' | 'maintenance';
  runtimes: number;
  agents: number;
  lastScan: string;
};

const agents = [
  { id: 'analyst', name: '数据分析师', status: '已发布', version: 'v12', color: '#3b82f6' },
  { id: 'reviewer', name: '元数据审核员', status: '已发布', version: 'v7', color: '#8b5cf6' },
  { id: 'ops', name: '运维协作 Agent', status: '调试中', version: '草稿', color: '#10b981' },
];

const nodes: NodeRow[] = [
  {
    key: 'local',
    name: '开发工作站',
    host: 'localhost',
    environment: '开发',
    status: 'online',
    runtimes: 2,
    agents: 6,
    lastScan: '2 分钟前',
  },
  {
    key: 'linux-01',
    name: 'Agent Linux 01',
    host: '10.24.8.31',
    environment: '测试',
    status: 'online',
    runtimes: 1,
    agents: 4,
    lastScan: '8 分钟前',
  },
  {
    key: 'linux-02',
    name: 'Agent Linux 02',
    host: '10.24.8.32',
    environment: '生产',
    status: 'degraded',
    runtimes: 1,
    agents: 3,
    lastScan: '1 小时前',
  },
];

const initialMessages: AgentChatMessage[] = [
  {
    id: 'welcome',
    role: 'assistant',
    createdAt: Date.now() - 120000,
    parts: [
      {
        kind: 'text',
        id: 'welcome-text',
        text: '你好，我是数据分析师。你可以直接描述业务问题，我会先确认口径，再查询数据并总结发现。',
      },
    ],
  },
  {
    id: 'sample',
    role: 'assistant',
    createdAt: Date.now() - 60000,
    parts: [
      {
        kind: 'text',
        id: 'sample-text',
        text: '我已经完成口径确认，准备查询近 30 天的渠道转化数据。',
      },
      {
        kind: 'tool',
        id: 'sample-tool',
        toolName: 'data_platform.execute_sql',
        args: { source: 'finance_dw', mode: 'read_only', range: 'last_30_days' },
        status: 'awaiting-approval',
        requiresApproval: true,
      },
    ],
  },
];

function PrototypeHeader({
  section,
  onSectionChange,
}: {
  section: PrototypeSection;
  onSectionChange: (section: PrototypeSection) => void;
}) {
  const nav = [
    { key: 'chat' as const, label: '对话工作台', icon: <MessageOutlined /> },
    { key: 'resources' as const, label: '资源控制台', icon: <CloudServerOutlined /> },
    { key: 'studio' as const, label: 'Agent Studio', icon: <ExperimentOutlined /> },
    { key: 'release' as const, label: '发布中心', icon: <RocketOutlined /> },
  ];

  return (
    <Card
      styles={{ body: { padding: '14px 18px' } }}
      style={{ marginBottom: 16, borderColor: 'rgba(96,165,250,0.2)' }}
    >
      <Flex align="center" justify="space-between" gap={16} wrap>
        <Space size={12}>
          <Avatar shape="square" icon={<DeploymentUnitOutlined />} />
          <div>
            <Space size={8}>
              <Text strong>Agent Control Plane</Text>
              <Tag color="blue">可点击原型</Tag>
              <Tag>模拟数据</Tag>
            </Space>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                用于确认产品信息架构与关键交互，不连接真实 SSH 或 Agent
              </Text>
            </div>
          </div>
        </Space>
        <Segmented
          value={section}
          onChange={(value) => onSectionChange(value as PrototypeSection)}
          options={nav.map((item) => ({
            value: item.key,
            label: (
              <Space size={6}>
                {item.icon}
                {item.label}
              </Space>
            ),
          }))}
        />
      </Flex>
    </Card>
  );
}

function ChatWorkspace({ onOpenStudio }: { onOpenStudio: () => void }) {
  const [selectedAgent, setSelectedAgent] = useState('analyst');
  const [messages, setMessages] = useState<AgentChatMessage[]>(initialMessages);

  const selected = agents.find((agent) => agent.id === selectedAgent) ?? agents[0];

  const handleSend = (text: string) => {
    const stamp = Date.now();
    setMessages((current) => [
      ...current,
      {
        id: `user-${stamp}`,
        role: 'user',
        createdAt: stamp,
        parts: [{ kind: 'text', id: `user-text-${stamp}`, text }],
      },
      {
        id: `assistant-${stamp}`,
        role: 'assistant',
        createdAt: stamp + 1,
        parts: [
          {
            kind: 'text',
            id: `assistant-text-${stamp}`,
            text: '原型已收到你的问题。正式版本会通过实时事件流展示规划、工具调用、子 Agent 协作和 Eval 结果。',
          },
          {
            kind: 'tool',
            id: `assistant-tool-${stamp}`,
            toolName: 'knowledge.search',
            args: { query: text, scope: 'team' },
            result: { matches: 8, topSource: '业务口径知识库' },
            status: 'success',
          },
        ],
      },
    ]);
  };

  const updateToolStatus = (
    messageId: string,
    toolPartId: string,
    status: 'approved' | 'rejected',
  ) => {
    setMessages((current) =>
      current.map((chatMessage) => {
        if (chatMessage.id !== messageId) return chatMessage;
        const parts: AgentChatPart[] = chatMessage.parts.map((part) =>
          part.kind === 'tool' && part.id === toolPartId
            ? {
                ...part,
                status,
                result: status === 'approved' ? { approved: true, previewRows: 128 } : undefined,
              }
            : part,
        );
        return { ...chatMessage, parts };
      }),
    );
    message.success(status === 'approved' ? '已允许本次工具调用' : '已拒绝，Agent 将调整方案');
  };

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '240px minmax(460px, 1fr) 320px',
        gap: 14,
        minHeight: 680,
      }}
    >
      <Card title="Agent 与会话" styles={{ body: { padding: 12 } }}>
        <Button type="primary" block icon={<PlusOutlined />} style={{ marginBottom: 12 }}>
          新建会话
        </Button>
        <Input.Search placeholder="搜索 Agent 或会话" allowClear />
        <Divider style={{ margin: '14px 0 8px' }} />
        <Text type="secondary" style={{ fontSize: 12 }}>
          可用 Agent
        </Text>
        <List
          dataSource={agents}
          renderItem={(agent) => (
            <List.Item
              onClick={() => setSelectedAgent(agent.id)}
              style={{
                cursor: 'pointer',
                padding: '10px 8px',
                marginTop: 4,
                borderRadius: 8,
                borderBlockEnd: 'none',
                background:
                  selectedAgent === agent.id ? 'rgba(59,130,246,0.12)' : 'transparent',
              }}
            >
              <List.Item.Meta
                avatar={<Badge color={agent.color} dot><Avatar size={30}>{agent.name[0]}</Avatar></Badge>}
                title={<Text style={{ fontSize: 13 }}>{agent.name}</Text>}
                description={
                  <Space size={4}>
                    <Text type="secondary" style={{ fontSize: 11 }}>{agent.version}</Text>
                    <Tag bordered={false} style={{ fontSize: 10 }}>{agent.status}</Tag>
                  </Space>
                }
              />
            </List.Item>
          )}
        />
        <Divider style={{ margin: '10px 0' }} />
        <Text type="secondary" style={{ fontSize: 12 }}>
          最近会话
        </Text>
        <List
          size="small"
          dataSource={['渠道转化分析', '字段命名审核', '生产告警排查']}
          renderItem={(item) => (
            <List.Item style={{ paddingInline: 4 }}>
              <Text ellipsis style={{ fontSize: 12 }}>{item}</Text>
            </List.Item>
          )}
        />
      </Card>

      <AgentChatPanel
        title={selected.name}
        statusText={
          <Space size={6}>
            <Badge status={selected.status === '已发布' ? 'success' : 'processing'} />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {selected.status} · {selected.version}
            </Text>
          </Space>
        }
        extra={
          <Button size="small" icon={<SettingOutlined />} onClick={onOpenStudio}>
            配置
          </Button>
        }
        height={560}
        messages={messages}
        onSend={handleSend}
        onApproveTool={(messageId, partId) =>
          updateToolStatus(messageId, partId, 'approved')
        }
        onRejectTool={(messageId, partId) =>
          updateToolStatus(messageId, partId, 'rejected')
        }
        onClear={() => setMessages([])}
        placeholder={`向 ${selected.name} 提问，Enter 发送…`}
      />

      <Card
        title="执行轨迹"
        extra={<Tag color="processing">Run #1842</Tag>}
        styles={{ body: { padding: '16px 16px 4px' } }}
      >
        <Alert
          type="info"
          showIcon
          message="只展示结构化摘要，不展示模型私有思维链"
          style={{ marginBottom: 18 }}
        />
        <Timeline
          items={[
            {
              color: 'green',
              children: (
                <div>
                  <Text strong>任务解析</Text>
                  <Paragraph type="secondary" style={{ fontSize: 12, margin: '4px 0' }}>
                    识别为数据分析任务，确认统计范围和业务口径。
                  </Paragraph>
                </div>
              ),
            },
            {
              color: 'blue',
              dot: <NodeIndexOutlined />,
              children: (
                <div>
                  <Text strong>规划 3 个步骤</Text>
                  <Paragraph type="secondary" style={{ fontSize: 12, margin: '4px 0' }}>
                    查询口径 → 执行只读 SQL → 汇总异常趋势
                  </Paragraph>
                </div>
              ),
            },
            {
              color: 'orange',
              dot: <ToolOutlined />,
              children: (
                <div>
                  <Space>
                    <Text strong>工具等待审批</Text>
                    <Tag color="gold">中风险</Tag>
                  </Space>
                  <Paragraph type="secondary" style={{ fontSize: 12, margin: '4px 0' }}>
                    data_platform.execute_sql
                  </Paragraph>
                </div>
              ),
            },
            {
              color: 'gray',
              dot: <ExperimentOutlined />,
              children: (
                <div>
                  <Text strong>结果 Eval</Text>
                  <Paragraph type="secondary" style={{ fontSize: 12, margin: '4px 0' }}>
                    等待工具结果后执行完整性和口径一致性检查。
                  </Paragraph>
                </div>
              ),
            },
          ]}
        />
        <Divider />
        <Descriptions
          size="small"
          column={1}
          items={[
            { key: 'agent', label: 'Agent', children: `${selected.name} ${selected.version}` },
            { key: 'node', label: '运行节点', children: 'Agent Linux 01' },
            { key: 'elapsed', label: '已用时间', children: '8.4 秒' },
            { key: 'tools', label: '工具调用', children: '1 / 10' },
          ]}
        />
      </Card>
    </div>
  );
}

function ResourcesConsole() {
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardStep, setWizardStep] = useState(0);
  const [nodeType, setNodeType] = useState<'local' | 'ssh'>('ssh');
  const [discoveryOpen, setDiscoveryOpen] = useState(false);

  const columns: ColumnsType<NodeRow> = [
    {
      title: '计算节点',
      dataIndex: 'name',
      render: (value, record) => (
        <Space>
          <Avatar shape="square" icon={<CloudServerOutlined />} />
          <div>
            <Text strong>{value}</Text>
            <div><Text type="secondary" style={{ fontSize: 12 }}>{record.host}</Text></div>
          </div>
        </Space>
      ),
    },
    { title: '环境', dataIndex: 'environment', render: (value) => <Tag>{value}</Tag> },
    {
      title: '状态',
      dataIndex: 'status',
      render: (value: NodeRow['status']) => (
        <Badge
          status={value === 'online' ? 'success' : value === 'degraded' ? 'warning' : 'default'}
          text={value === 'online' ? '在线' : value === 'degraded' ? '部分异常' : '维护中'}
        />
      ),
    },
    { title: 'Runtime', dataIndex: 'runtimes', align: 'center' },
    { title: 'Agent', dataIndex: 'agents', align: 'center' },
    { title: '最近扫描', dataIndex: 'lastScan' },
    {
      title: '操作',
      key: 'action',
      render: () => (
        <Space>
          <Button size="small" onClick={() => setDiscoveryOpen(true)}>查看</Button>
          <Button size="small" icon={<ReloadOutlined />} onClick={() => setDiscoveryOpen(true)}>
            扫描
          </Button>
        </Space>
      ),
    },
  ];

  const wizardContents = [
    <Space direction="vertical" size={16} style={{ width: '100%' }} key="basic">
      <Radio.Group
        value={nodeType}
        onChange={(event) => setNodeType(event.target.value)}
        optionType="button"
        buttonStyle="solid"
        options={[
          { label: '注册本机', value: 'local' },
          { label: '远程 Linux（SSH）', value: 'ssh' },
        ]}
      />
      <Form layout="vertical">
        <Form.Item label="节点名称" required>
          <Input defaultValue={nodeType === 'local' ? '开发工作站' : 'Agent Linux 03'} />
        </Form.Item>
        {nodeType === 'ssh' && (
          <Flex gap={12}>
            <Form.Item label="主机地址" required style={{ flex: 1 }}>
              <Input defaultValue="10.24.8.33" />
            </Form.Item>
            <Form.Item label="SSH 端口" required>
              <Input defaultValue="22" style={{ width: 100 }} />
            </Form.Item>
          </Flex>
        )}
        <Form.Item label="环境标签">
          <Select defaultValue="test" options={[
            { label: '开发', value: 'dev' },
            { label: '测试', value: 'test' },
            { label: '生产', value: 'prod' },
          ]} />
        </Form.Item>
      </Form>
    </Space>,
    <Space direction="vertical" size={16} style={{ width: '100%' }} key="credential">
      <Alert
        type="warning"
        showIcon
        message="凭据只允许写入或选择引用，保存后不会回显明文"
      />
      <Form layout="vertical">
        <Form.Item label="认证方式">
          <Select defaultValue="key" options={[
            { label: 'SSH 私钥', value: 'key' },
            { label: '密码', value: 'password' },
            { label: '已有凭据引用', value: 'reference' },
          ]} />
        </Form.Item>
        <Form.Item label="用户名"><Input defaultValue="agent-admin" /></Form.Item>
        <Form.Item label="私钥"><Input.TextArea rows={5} placeholder="粘贴私钥，仅在提交时发送" /></Form.Item>
      </Form>
    </Space>,
    <Space direction="vertical" size={16} style={{ width: '100%' }} key="trust">
      <Alert
        type="info"
        showIcon
        message="首次连接必须确认主机指纹"
        description="请与服务器管理员通过可信渠道核对后再继续。"
      />
      <Card size="small">
        <Text type="secondary">ED25519 指纹</Text>
        <Paragraph copyable code style={{ marginTop: 8 }}>
          SHA256:5DJ8uC3Lw9xN7mR2uFQ8b4PXp0gT6YvWnK3aE1hZsLs
        </Paragraph>
      </Card>
      <Checkbox>我已通过可信渠道核对并信任该主机指纹</Checkbox>
    </Space>,
    <Space direction="vertical" size={14} style={{ width: '100%' }} key="check">
      {[
        ['SSH 连接', '通过', 'success'],
        ['读取系统信息', '通过', 'success'],
        ['读取 OpenCode 配置目录', '通过', 'success'],
        ['写入发布目录', '需要授权', 'warning'],
      ].map(([name, result, status]) => (
        <Card size="small" key={name}>
          <Flex justify="space-between">
            <Text>{name}</Text>
            <Badge status={status as 'success' | 'warning'} text={result} />
          </Flex>
        </Card>
      ))}
    </Space>,
    <Space direction="vertical" size={14} style={{ width: '100%' }} key="preview">
      <Alert type="success" showIcon message="发现 1 个 Runtime、4 个 Agent、8 个 Skill、3 个 MCP" />
      <Descriptions
        bordered
        size="small"
        column={1}
        items={[
          { key: 'runtime', label: 'Runtime', children: 'OpenCode 1.2.4 · 运行中' },
          { key: 'agent', label: 'Agent', children: '3 个新发现，1 个存在差异' },
          { key: 'skill', label: 'Skill', children: '8 个新发现' },
          { key: 'mcp', label: 'MCP', children: '2 个新发现，1 个已关联' },
        ]}
      />
      <Checkbox defaultChecked>注册后打开发现结果并逐项确认导入</Checkbox>
    </Space>,
  ];

  return (
    <>
      <Flex justify="space-between" align="flex-start" style={{ marginBottom: 16 }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>资源控制台</Title>
          <Text type="secondary">统一管理计算节点、Agent Runtime、Agent、Skill 与 MCP</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => setDiscoveryOpen(true)}>全量发现</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => {
            setWizardStep(0);
            setWizardOpen(true);
          }}>
            注册计算节点
          </Button>
        </Space>
      </Flex>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 16 }}>
        {[
          ['计算节点', 3, <CloudServerOutlined key="nodes" />],
          ['Agent Runtime', 4, <CodeOutlined key="runtimes" />],
          ['Agent', 13, <DeploymentUnitOutlined key="agents" />],
          ['Skill', 24, <AppstoreOutlined key="skills" />],
          ['MCP', 8, <ApiOutlined key="mcps" />],
        ].map(([label, value, icon]) => (
          <Card key={String(label)} size="small">
            <Statistic title={String(label)} value={Number(value)} prefix={icon} />
          </Card>
        ))}
      </div>

      <Card
        title="计算节点"
        extra={<Segmented size="small" options={['节点', 'Runtime', 'Agent', 'Skill', 'MCP']} />}
      >
        <Table columns={columns} dataSource={nodes} pagination={false} />
      </Card>

      <Modal
        width={760}
        open={wizardOpen}
        title="注册计算节点"
        onCancel={() => setWizardOpen(false)}
        footer={[
          <Button key="back" disabled={wizardStep === 0} onClick={() => setWizardStep((step) => step - 1)}>
            上一步
          </Button>,
          wizardStep < 4 ? (
            <Button key="next" type="primary" onClick={() => setWizardStep((step) => step + 1)}>
              下一步
            </Button>
          ) : (
            <Button key="done" type="primary" onClick={() => {
              setWizardOpen(false);
              setDiscoveryOpen(true);
              message.success('原型：节点已注册，等待确认导入发现资源');
            }}>
              完成注册
            </Button>
          ),
        ]}
      >
        <Steps
          current={wizardStep}
          size="small"
          items={[
            { title: '基本信息' },
            { title: '凭据' },
            { title: '主机信任' },
            { title: '权限检查' },
            { title: '发现预览' },
          ]}
          style={{ margin: '12px 0 28px' }}
        />
        {wizardContents[wizardStep]}
      </Modal>

      <Drawer
        width={720}
        open={discoveryOpen}
        onClose={() => setDiscoveryOpen(false)}
        title="OpenCode 发现结果"
        extra={<Tag color="blue">Agent Linux 01</Tag>}
      >
        <Alert
          type="info"
          showIcon
          message="发现不会修改远程配置；只有确认导入或发布时才会产生变更"
          style={{ marginBottom: 16 }}
        />
        <Table
          pagination={false}
          dataSource={[
            { key: '1', type: 'Agent', name: 'data-analyst', state: '有差异', action: '查看差异' },
            { key: '2', type: 'Agent', name: 'metadata-reviewer', state: '新发现', action: '导入' },
            { key: '3', type: 'Skill', name: 'sql-guard', state: '已关联', action: '查看' },
            { key: '4', type: 'MCP', name: 'team-search', state: '新发现', action: '导入' },
            { key: '5', type: 'MCP', name: 'legacy-files', state: '缺失', action: '处理' },
          ]}
          columns={[
            { title: '类型', dataIndex: 'type', render: (value) => <Tag>{value}</Tag> },
            { title: '名称', dataIndex: 'name', render: (value) => <Text code>{value}</Text> },
            {
              title: '发现状态',
              dataIndex: 'state',
              render: (value) => (
                <Tag color={
                  value === '有差异' ? 'orange' :
                  value === '新发现' ? 'blue' :
                  value === '已关联' ? 'green' : 'red'
                }>
                  {value}
                </Tag>
              ),
            },
            {
              title: '操作',
              dataIndex: 'action',
              render: (value, record) => (
                <Button
                  size="small"
                  type={record.state === '新发现' ? 'primary' : 'default'}
                  onClick={() => message.info(`原型操作：${value} ${record.name}`)}
                >
                  {value}
                </Button>
              ),
            },
          ]}
        />
        <Divider />
        <Title level={5}>冲突处理原则</Title>
        <Radio.Group defaultValue="review">
          <Space direction="vertical">
            <Radio value="review">暂不处理，保持平台与服务器现状</Radio>
            <Radio value="import">将服务器差异导入为平台新版本</Radio>
            <Radio value="platform">保留平台版本，等待下次人工发布</Radio>
          </Space>
        </Radio.Group>
      </Drawer>
    </>
  );
}

const studioSteps = [
  { title: '目标', icon: <AuditOutlined />, description: '目标与成功标准' },
  { title: '角色', icon: <MessageOutlined />, description: '指令与输出格式' },
  { title: '模型', icon: <AppstoreOutlined />, description: '模型与上下文' },
  { title: '能力', icon: <ToolOutlined />, description: 'Skill、MCP 与数据' },
  { title: '协作', icon: <NodeIndexOutlined />, description: '子 Agent 拓扑' },
  { title: 'Loop', icon: <ReloadOutlined />, description: 'Loop 与 SOP' },
  { title: 'Hook', icon: <CodeOutlined />, description: '生命周期扩展点' },
  { title: 'Eval', icon: <ExperimentOutlined />, description: '评估与发布门禁' },
  { title: '护栏', icon: <SafetyCertificateOutlined />, description: '边界与审批' },
  { title: '发布', icon: <RocketOutlined />, description: '调试与发布准备' },
];

function AgentStudio({ onOpenRelease }: { onOpenRelease: () => void }) {
  const [current, setCurrent] = useState(0);
  const [mode, setMode] = useState<'快速模式' | '专家模式'>('快速模式');

  const content = useMemo(() => {
    switch (current) {
      case 0:
        return (
          <Form layout="vertical">
            <Form.Item label="Agent 名称" required><Input defaultValue="渠道经营分析师" /></Form.Item>
            <Form.Item label="要解决的问题" required>
              <Input.TextArea rows={3} defaultValue="帮助经营团队分析渠道转化、定位异常并给出可验证的改进建议。" />
            </Form.Item>
            <Form.Item label="成功标准" required>
              <Input.TextArea rows={4} defaultValue={'1. 引用统一业务口径\n2. 所有数据结论可以追溯到查询\n3. 输出至少包含结论、证据和建议'} />
            </Form.Item>
            <Form.Item label="明确不做">
              <Input defaultValue="不修改生产数据；不自动对外发送报告" />
            </Form.Item>
          </Form>
        );
      case 4:
        return (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Alert type="info" showIcon message="先选择协作模式，再配置参与者；无需从空白 DAG 开始。" />
            <Radio.Group defaultValue="evaluator" style={{ width: '100%' }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                {[
                  ['single', 'Single', '一个 Agent 独立完成，成本最低'],
                  ['sequential', 'Sequential', '多个 Agent 按顺序传递结果'],
                  ['router', 'Router', '主 Agent 根据问题选择专家'],
                  ['parallel', 'Parallel', '多个 Agent 并行分析后合并'],
                  ['evaluator', 'Evaluator-Optimizer', '执行者产出，评估者反馈并驱动修订'],
                ].map(([value, title, description]) => (
                  <Card size="small" key={value}>
                    <Radio value={value}>
                      <Text strong>{title}</Text>
                      <Text type="secondary"> · {description}</Text>
                    </Radio>
                  </Card>
                ))}
              </Space>
            </Radio.Group>
            <Divider style={{ margin: 0 }} />
            <Flex gap={12} align="center" wrap>
              <Card size="small"><Tag color="blue">执行者</Tag> 数据分析师</Card>
              <Text>→</Text>
              <Card size="small"><Tag color="purple">评估者</Tag> 业务口径审核员</Card>
              <Text>→</Text>
              <Card size="small"><Tag color="green">通过</Tag> 输出结果</Card>
            </Flex>
          </Space>
        );
      case 7:
        return (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Alert
              type="info"
              showIcon
              message="Eval 回答“结果是否达到目标”，可作为发布门禁或运行时修订依据。"
            />
            <Table
              pagination={false}
              dataSource={[
                { key: '1', name: '输出结构检查', type: '规则', gate: true, weight: '关键项' },
                { key: '2', name: '业务口径一致性', type: 'LLM Judge', gate: true, weight: '40%' },
                { key: '3', name: 'SQL 只读安全', type: '规则', gate: true, weight: '关键项' },
                { key: '4', name: '建议可执行性', type: '人工', gate: false, weight: '20%' },
              ]}
              columns={[
                { title: '评估项', dataIndex: 'name' },
                { title: '方式', dataIndex: 'type', render: (value) => <Tag>{value}</Tag> },
                { title: '发布必选', dataIndex: 'gate', render: (value) => <Checkbox checked={value} /> },
                { title: '权重', dataIndex: 'weight' },
              ]}
            />
            <Button icon={<PlusOutlined />}>添加 Eval</Button>
          </Space>
        );
      case 9:
        return (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Progress percent={86} status="active" />
            <Alert
              type="warning"
              showIcon
              message="发布准备度 86%"
              description="还需要完成 1 个发布必选 Eval，并确认生产节点的 MCP 凭据。"
            />
            {[
              ['配置完整', true],
              ['依赖完整', false],
              ['安全策略完整', true],
              ['发布 Eval 通过', false],
              ['目标 Runtime 可用', true],
            ].map(([label, ok]) => (
              <Card size="small" key={String(label)}>
                <Flex justify="space-between">
                  <Text>{String(label)}</Text>
                  {ok ? <Tag color="green">通过</Tag> : <Tag color="orange">待处理</Tag>}
                </Flex>
              </Card>
            ))}
          </Space>
        );
      default:
        return (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Alert
              type="info"
              showIcon
              message={`${studioSteps[current].title}配置`}
              description={`${studioSteps[current].description}。原型用于验证十步方法论和快速/专家模式的信息密度。`}
            />
            <Form layout="vertical">
              <Form.Item label="推荐配置">
                <Select
                  defaultValue="recommended"
                  options={[
                    { label: '使用推荐配置', value: 'recommended' },
                    { label: '从已有 Agent 复制', value: 'copy' },
                    { label: '自定义', value: 'custom' },
                  ]}
                />
              </Form.Item>
              <Form.Item label="配置说明">
                <Input.TextArea rows={6} defaultValue="这里将根据当前步骤展示对应的表单、示例、风险提示和配置预览。" />
              </Form.Item>
            </Form>
          </Space>
        );
    }
  }, [current]);

  return (
    <>
      <Flex justify="space-between" align="flex-start" style={{ marginBottom: 16 }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>Agent Studio</Title>
          <Text type="secondary">渠道经营分析师 · 草稿 v13</Text>
        </div>
        <Space>
          <Segmented
            value={mode}
            onChange={(value) => setMode(value as '快速模式' | '专家模式')}
            options={['快速模式', '专家模式']}
          />
          <Button>保存草稿</Button>
          <Button type="primary" onClick={onOpenRelease}>发布检查</Button>
        </Space>
      </Flex>

      <div style={{ display: 'grid', gridTemplateColumns: '270px minmax(500px, 1fr) 280px', gap: 16 }}>
        <Card title="设计方法">
          <Steps
            direction="vertical"
            current={current}
            onChange={setCurrent}
            items={studioSteps.map((step) => ({
              title: step.title,
              description: step.description,
              icon: step.icon,
            }))}
          />
        </Card>
        <Card
          title={`第 ${current + 1} 步 · ${studioSteps[current].title}`}
          extra={<Tag color="blue">{mode}</Tag>}
        >
          {content}
          <Divider />
          <Flex justify="space-between">
            <Button disabled={current === 0} onClick={() => setCurrent((step) => step - 1)}>上一步</Button>
            <Button
              type="primary"
              disabled={current === studioSteps.length - 1}
              onClick={() => setCurrent((step) => step + 1)}
            >
              下一步
            </Button>
          </Flex>
        </Card>
        <Card title="方法提示">
          <Space direction="vertical" size={14}>
            <Progress type="circle" size={100} percent={68} />
            <Title level={5} style={{ margin: 0 }}>{studioSteps[current].title}</Title>
            <Paragraph type="secondary">
              {current === 4
                ? '多 Agent 不一定更好。只有任务可以明确拆分、角色之间有清晰输入输出时才使用协作。'
                : current === 7
                  ? '先定义可验证的成功标准，再选择规则、LLM Judge 或人工评估。'
                  : '当前步骤提供推荐默认值。快速模式只展示必填项，专家模式开放完整配置。'}
            </Paragraph>
            <Divider style={{ margin: 0 }} />
            <Text strong>当前风险</Text>
            <Tag color="orange">生产 MCP 凭据未确认</Tag>
            <Tag color="blue">1 个 Eval 待运行</Tag>
          </Space>
        </Card>
      </div>
    </>
  );
}

function ReleaseCenter({ onBackToStudio }: { onBackToStudio: () => void }) {
  const [releaseState, setReleaseState] = useState<'ready' | 'running' | 'done'>('ready');

  const publish = () => {
    setReleaseState('running');
    window.setTimeout(() => {
      setReleaseState('done');
      message.success('原型：v13 已发布到测试环境');
    }, 700);
  };

  return (
    <>
      <Flex justify="space-between" align="flex-start" style={{ marginBottom: 16 }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>发布中心</Title>
          <Text type="secondary">版本差异、Eval 门禁、目标环境与回滚</Text>
        </div>
        <Button onClick={onBackToStudio}>返回 Studio</Button>
      </Flex>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <Card title="待发布版本" extra={<Tag color="blue">渠道经营分析师 v13</Tag>}>
          <Descriptions
            column={1}
            items={[
              { key: 'base', label: '当前线上', children: 'v12 · 2026-07-10 发布' },
              { key: 'owner', label: '负责人', children: 'Agent Builder' },
              { key: 'change', label: '变更', children: '3 项配置、1 个 Skill、2 个 Eval' },
            ]}
          />
          <Divider />
          <Text strong>版本差异</Text>
          <pre style={{
            background: 'rgba(0,0,0,0.25)',
            borderRadius: 8,
            padding: 14,
            marginTop: 10,
            color: '#cbd5e1',
            whiteSpace: 'pre-wrap',
          }}>
{`+ 协作模式：evaluator-optimizer
+ 评估者：业务口径审核员
+ Skill：channel-metrics-v2
~ 最大迭代：5 → 8
~ 超时：60s → 90s`}
          </pre>
        </Card>

        <Card title="发布门禁" extra={<Tag color="green">4 / 5 通过</Tag>}>
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            {[
              ['配置完整性', '通过', 'green'],
              ['SQL 只读安全', '通过', 'green'],
              ['业务口径一致性', '92 分', 'green'],
              ['结果可执行性', '通过', 'green'],
              ['生产 MCP 凭据', '待确认', 'orange'],
            ].map(([name, result, color]) => (
              <Card size="small" key={name}>
                <Flex justify="space-between">
                  <Text>{name}</Text>
                  <Tag color={color}>{result}</Tag>
                </Flex>
              </Card>
            ))}
          </Space>
        </Card>

        <Card title="目标环境">
          <Checkbox.Group defaultValue={['test']} style={{ width: '100%' }}>
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <Card size="small">
                <Checkbox value="test">
                  <Text strong>测试环境</Text>
                  <Text type="secondary"> · Agent Linux 01 · OpenCode 1.2.4</Text>
                </Checkbox>
              </Card>
              <Card size="small">
                <Checkbox value="prod">
                  <Text strong>生产环境</Text>
                  <Text type="secondary"> · Agent Linux 02 · 节点部分异常</Text>
                </Checkbox>
              </Card>
            </Space>
          </Checkbox.Group>
          <Alert
            type="warning"
            showIcon
            message="生产环境需要管理员审批"
            style={{ marginTop: 14 }}
          />
        </Card>

        <Card title="发布操作">
          {releaseState === 'done' ? (
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              <Alert
                type="success"
                showIcon
                message="v13 已发布到测试环境"
                description="Deployment #D-204 · 所有远程操作已写入审计"
              />
              <Button block>查看 Deployment</Button>
              <Button danger block onClick={() => message.info('原型：进入下线/回滚确认')}>
                下线或回滚
              </Button>
            </Space>
          ) : (
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              <Alert
                type="info"
                showIcon
                message="发布不会覆盖历史版本"
                description="每个目标 Runtime 都会产生独立 Deployment，可单独下线或回滚。"
              />
              {releaseState === 'running' && <Progress percent={68} status="active" />}
              <Button
                type="primary"
                size="large"
                block
                loading={releaseState === 'running'}
                disabled={releaseState === 'running'}
                icon={<RocketOutlined />}
                onClick={publish}
              >
                确认发布到测试环境
              </Button>
            </Space>
          )}
        </Card>
      </div>
    </>
  );
}

export default function AgentPlatformPrototype() {
  const [section, setSection] = useState<PrototypeSection>('chat');

  return (
    <div style={{ minWidth: 1040 }}>
      <PrototypeHeader section={section} onSectionChange={setSection} />
      {section === 'chat' && <ChatWorkspace onOpenStudio={() => setSection('studio')} />}
      {section === 'resources' && <ResourcesConsole />}
      {section === 'studio' && <AgentStudio onOpenRelease={() => setSection('release')} />}
      {section === 'release' && <ReleaseCenter onBackToStudio={() => setSection('studio')} />}
    </div>
  );
}
