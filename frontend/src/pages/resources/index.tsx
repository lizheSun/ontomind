import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Card, Table, Button, Modal, Form, Input, Select, Switch, Tag, Typography,
  Space, Popconfirm, message, Empty, InputNumber, App, Tabs, Badge, Tooltip,
  Drawer,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ApiOutlined,
  CheckCircleOutlined, SettingOutlined, ThunderboltOutlined,
  RobotOutlined, SendOutlined, CloudServerOutlined,
  CodeOutlined, ExperimentOutlined, ToolOutlined,
  PlayCircleOutlined, StopOutlined, ReloadOutlined,
  MonitorOutlined, LinkOutlined, BugOutlined,
  CloudUploadOutlined, DockerOutlined, DesktopOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import llmService from '../../services/llm.service';
import type { LLMConfig, LLMConfigCreate, LLMConfigUpdate } from '../../services/llm.service';
import { resourcesAPI } from '../../services/index';
import type { Instance, Agent, Skill, MCPConfig as MCPConfigType, AgentRun, LogEntry } from '../../types/index';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

// ===================== LLM 配置 Tab =====================

function LLMConfigTab() {
  const { notification } = App.useApp();
  const [configs, setConfigs] = useState<LLMConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState<LLMConfig | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  const [testModalOpen, setTestModalOpen] = useState(false);
  const [testMessages, setTestMessages] = useState<{ role: string; content: string }[]>([]);
  const [testInput, setTestInput] = useState('');
  const [testLoading, setTestLoading] = useState(false);

  const fetchConfigs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await llmService.listConfigs();
      setConfigs(res.data || []);
    } catch {
      notification.error({ title: '加载配置失败', placement: 'top' });
    } finally {
      setLoading(false);
    }
  }, [notification]);

  useEffect(() => { fetchConfigs(); }, [fetchConfigs]);

  const handleCreate = () => {
    setEditingConfig(null);
    form.resetFields();
    form.setFieldsValue({ provider: 'openai', is_active: false, timeout: '60', max_retries: '2' });
    setModalOpen(true);
  };

  const handleEdit = (config: LLMConfig) => {
    setEditingConfig(config);
    form.setFieldsValue(config);
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      if (editingConfig) {
        const payload: LLMConfigUpdate = {};
        for (const key of Object.keys(values)) {
          const v = values[key];
          if (v !== undefined && v !== (editingConfig as any)[key]) {
            (payload as any)[key] = v;
          }
        }
        await llmService.updateConfig(editingConfig.id, payload);
        message.success('更新成功');
      } else {
        await llmService.createConfig(values as LLMConfigCreate);
        message.success('创建成功');
      }
      setModalOpen(false);
      fetchConfigs();
    } catch (err: any) {
      if (err?.errorFields) return;
      notification.error({ title: '操作失败', description: err?.response?.data?.detail || err?.message, placement: 'top' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await llmService.deleteConfig(id);
      message.success('删除成功');
      fetchConfigs();
    } catch (err: any) {
      notification.error({ title: '删除失败', description: err?.response?.data?.detail || err?.message, placement: 'top' });
    }
  };

  const handleSetActive = async (id: number) => {
    try {
      await llmService.updateConfig(id, { is_active: true });
      message.success('已设为默认');
      fetchConfigs();
    } catch (err: any) {
      notification.error({ title: '操作失败', description: err?.response?.data?.detail || err?.message, placement: 'top' });
    }
  };

  const handleTestChat = async () => {
    if (!testInput.trim()) return;
    const msgs = [...testMessages, { role: 'user', content: testInput }];
    setTestMessages(msgs);
    setTestInput('');
    setTestLoading(true);
    try {
      const res = await llmService.chat({ messages: msgs });
      setTestMessages([...msgs, { role: 'assistant', content: res.data?.content || '' }]);
    } catch (err: any) {
      notification.error({ title: '调用失败', description: err?.response?.data?.detail || err?.message, placement: 'top' });
    } finally {
      setTestLoading(false);
    }
  };

  const providerColor = (p: string) =>
    p === 'openai' ? 'blue' : p === 'qwen' ? 'green' : 'purple';

  const columns: ColumnsType<LLMConfig> = [
    { title: '名称', dataIndex: 'name', key: 'name', width: 140 },
    {
      title: '协议', dataIndex: 'provider', key: 'provider', width: 100,
      render: (v: string) => <Tag color={providerColor(v)}>{v}</Tag>,
    },
    { title: 'API 地址', dataIndex: 'base_url', key: 'base_url', ellipsis: true, width: 200 },
    { title: '模型', dataIndex: 'model_name', key: 'model_name', width: 140 },
    {
      title: '默认', dataIndex: 'is_active', key: 'is_active', width: 70,
      render: (v: boolean, record) =>
        v ? <CheckCircleOutlined style={{ color: '#34d399', fontSize: 16 }} /> :
          <Button type="link" size="small" onClick={() => handleSetActive(record.id)} style={{ fontSize: 12 }}>启用</Button>,
    },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true, width: 140 },
    {
      title: '操作', key: 'actions', width: 140,
      render: (_, record) => (
        <Space size="small">
          <Button type="text" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Button type="text" size="small" icon={<ThunderboltOutlined />} onClick={() => {
            setTestMessages([]); setTestInput(''); setTestModalOpen(true);
          }} />
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)} okText="删除" cancelText="取消" okButtonProps={{ danger: true }}>
            <Button type="text" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>新增配置</Button>
        <Button icon={<SendOutlined />} onClick={() => {
          setTestMessages([]); setTestInput(''); setTestModalOpen(true);
        }}>测试对话</Button>
      </div>

      <Card
        title={<Space><ApiOutlined style={{ color: '#60a5fa' }} />LLM 配置列表</Space>}
        style={{ borderRadius: 16, background: 'rgba(255,255,255,0.015)', border: '1px solid rgba(255,255,255,0.06)' }}
      >
        {configs.length === 0 && !loading ? (
          <Empty description={<span style={{ color: '#506380' }}>暂无 LLM 配置</span>} style={{ padding: 40 }} />
        ) : (
          <Table dataSource={configs} columns={columns} rowKey="id" loading={loading} pagination={false} size="middle" style={{ background: 'transparent' }} />
        )}
      </Card>

      <Modal
        title={<Space>{editingConfig ? <EditOutlined style={{ color: '#60a5fa' }} /> : <PlusOutlined style={{ color: '#60a5fa' }} />}{editingConfig ? '编辑' : '新增'} LLM 配置</Space>}
        open={modalOpen} onCancel={() => setModalOpen(false)} width={640}
        footer={[<Button key="cancel" onClick={() => setModalOpen(false)}>取消</Button>, <Button key="submit" type="primary" loading={submitting} onClick={handleSubmit}>保存</Button>]}
        styles={{ body: { maxHeight: '60vh', overflowY: 'auto' } }}
      >
        <Form form={form} layout="vertical" size="large" initialValues={{ provider: 'openai', is_active: false, timeout: '60', max_retries: '2' }}>
          <Form.Item name="name" label="配置名称" rules={[{ required: true, message: '请输入' }]}>
            <Input placeholder="例如：GPT-4 Azure" />
          </Form.Item>
          <Space style={{ width: '100%' }} size={16}>
            <Form.Item name="provider" label="服务协议" rules={[{ required: true }]} style={{ width: 200 }}>
              <Select>
                <Select.Option value="openai">OpenAI</Select.Option>
                <Select.Option value="anthropic">Anthropic</Select.Option>
                <Select.Option value="qwen">Qwen</Select.Option>
              </Select>
            </Form.Item>
            <Form.Item name="model_name" label="模型" rules={[{ required: true }]} style={{ flex: 1 }}>
              <Input placeholder="gpt-4 / claude-3-5-sonnet" />
            </Form.Item>
          </Space>
          <Form.Item name="base_url" label="API Base URL" rules={[{ required: true }]}>
            <Input placeholder="https://api.openai.com/v1" />
          </Form.Item>
          <Form.Item name="api_key" label="API Key" rules={[{ required: true }]} extra="密钥仅本地加密存储">
            <Input.Password placeholder="sk-..." />
          </Form.Item>
          <Form.Item name="description" label="描述"><Input placeholder="可选" /></Form.Item>
          <Space size={16}>
            <Form.Item name="timeout" label="超时" style={{ width: 140 }}><InputNumber min={1} max={300} style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="max_retries" label="重试" style={{ width: 140 }}><InputNumber min={0} max={5} style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="is_active" label="默认" valuePropName="checked" style={{ paddingTop: 5 }}><Switch /></Form.Item>
          </Space>
          <Form.Item name="extra_headers" label="额外请求头 (JSON)">
            <TextArea rows={2} placeholder='{"X-Custom": "val"}' style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }} />
          </Form.Item>
          <Form.Item name="extra_body" label="额外请求体 (JSON)">
            <TextArea rows={2} placeholder='{"top_p": 0.9}' style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={<Space><RobotOutlined style={{ color: '#8b5cf6' }} />测试 LLM 对话</Space>}
        open={testModalOpen} onCancel={() => setTestModalOpen(false)} width={720} footer={null}
        styles={{ body: { padding: 0 } }}
      >
        <div style={{ minHeight: 300, maxHeight: 400, overflowY: 'auto', padding: 16, background: 'rgba(0,0,0,0.2)', display: 'flex', flexDirection: 'column', gap: 12 }}>
          {testMessages.length === 0 && <Text style={{ color: '#506380', textAlign: 'center', padding: 60, display: 'block' }}>输入消息测试默认 LLM</Text>}
          {testMessages.map((m, i) => (
            <div key={i} style={{
              alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '80%', padding: '10px 14px',
              borderRadius: 12, color: '#e8eef5', fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap',
              background: m.role === 'user' ? 'linear-gradient(135deg, #3b82f6, #8b5cf6)' : 'rgba(255,255,255,0.06)',
              border: m.role === 'user' ? 'none' : '1px solid rgba(255,255,255,0.08)',
            }}>{m.content}</div>
          ))}
          {testLoading && <Text style={{ color: '#506380', fontSize: 12 }}>思考中...</Text>}
        </div>
        <div style={{ padding: '12px 16px', borderTop: '1px solid rgba(255,255,255,0.06)', display: 'flex', gap: 8 }}>
          <TextArea value={testInput} onChange={e => setTestInput(e.target.value)}
            onPressEnter={e => { if (!e.shiftKey) { e.preventDefault(); handleTestChat(); } }}
            placeholder="Enter 发送，Shift+Enter 换行" autoSize={{ minRows: 1, maxRows: 4 }} style={{ flex: 1 }} />
          <Button type="primary" icon={<SendOutlined />} onClick={handleTestChat} loading={testLoading}>发送</Button>
        </div>
      </Modal>
    </div>
  );
}

// ===================== 通用 CRUD Tab 工厂 =====================

type TabName = 'instances' | 'agents' | 'skills' | 'mcps' | 'runs';

interface CrudConfig {
  name: TabName;
  label: string;
  icon: React.ReactNode;
  api: {
    list: (params?: any) => Promise<any>;
    create: (data: any) => Promise<any>;
    update: (id: number, data: any) => Promise<any>;
    delete: (id: number) => Promise<any>;
  };
  columns: ColumnsType<any>;
  formItems: React.ReactNode;
  defaultValues: Record<string, any>;
  extraActions?: (record: any, refresh: () => void) => React.ReactNode;
}

function CrudTab({ config }: { config: CrudConfig }) {
  const { notification } = App.useApp();
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  const fetchItems = useCallback(async () => {
    setLoading(true);
    try {
      const res = await config.api.list({ skip: 0, limit: 200 });
      setItems(res.data?.data || []);
    } catch { notification.error({ title: '加载失败', placement: 'top' }); }
    finally { setLoading(false); }
  }, [config.api]);

  useEffect(() => { fetchItems(); }, [fetchItems]);

  const handleCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue(config.defaultValues);
    setModalOpen(true);
  };

  const handleEdit = (item: any) => {
    setEditing(item);
    form.setFieldsValue(item);
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      if (editing) {
        await config.api.update(editing.id, values);
        message.success('更新成功');
      } else {
        await config.api.create(values);
        message.success('创建成功');
      }
      setModalOpen(false);
      fetchItems();
    } catch (err: any) {
      if (err?.errorFields) return;
      notification.error({ title: '操作失败', description: err?.response?.data?.detail || err?.message, placement: 'top' });
    } finally { setSubmitting(false); }
  };

  const handleDelete = async (id: number) => {
    try { await config.api.delete(id); message.success('删除成功'); fetchItems(); }
    catch (err: any) { notification.error({ title: '删除失败', description: err?.response?.data?.detail || err?.message, placement: 'top' }); }
  };

  const fullCols: ColumnsType<any> = [
    ...config.columns,
    {
      title: '操作', key: 'actions', width: config.extraActions ? 180 : 120,
      render: (_, record) => (
        <Space size="small">
          <Button type="text" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          {config.extraActions?.(record, fetchItems)}
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)} okText="删除" cancelText="取消" okButtonProps={{ danger: true }}>
            <Button type="text" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>新增{config.label}</Button>
      </div>
      <Card
        title={<Space>{config.icon}{config.label}列表</Space>}
        style={{ borderRadius: 16, background: 'rgba(255,255,255,0.015)', border: '1px solid rgba(255,255,255,0.06)' }}
      >
        {items.length === 0 && !loading ? (
          <Empty description={<span style={{ color: '#506380' }}>暂无{config.label}</span>} style={{ padding: 40 }} />
        ) : (
          <Table dataSource={items} columns={fullCols} rowKey="id" loading={loading} pagination={false} size="middle" style={{ background: 'transparent' }} />
        )}
      </Card>

      <Modal
        title={<Space>{editing ? <EditOutlined style={{ color: '#60a5fa' }} /> : <PlusOutlined style={{ color: '#60a5fa' }} />}{editing ? '编辑' : '新增'}{config.label}</Space>}
        open={modalOpen} onCancel={() => setModalOpen(false)} width={640}
        footer={[<Button key="cancel" onClick={() => setModalOpen(false)}>取消</Button>, <Button key="submit" type="primary" loading={submitting} onClick={handleSubmit}>保存</Button>]}
        styles={{ body: { maxHeight: '60vh', overflowY: 'auto' } }}
      >
        <Form form={form} layout="vertical" size="large">
          {config.formItems}
        </Form>
      </Modal>
    </div>
  );
}

// ===================== 实例 Tab =====================

const instanceColumns: ColumnsType<Instance> = [
  { title: '名称', dataIndex: 'name', key: 'name', width: 120 },
  { title: '地址', dataIndex: 'host', key: 'host', width: 140, render: (v, r) => `${v}:${r.port}` },
  {
    title: '类型', dataIndex: 'instance_type', key: 'instance_type', width: 80,
    render: (v: string) => ({
      physical: <Tag icon={<DesktopOutlined />} color="blue">物理机</Tag>,
      docker: <Tag icon={<DockerOutlined />} color="cyan">Docker</Tag>,
      k8s_pod: <Tag icon={<CloudServerOutlined />} color="purple">K8s</Tag>,
    }[v] || <Tag>{v}</Tag>),
  },
  {
    title: '状态', dataIndex: 'status', key: 'status', width: 90,
    render: (v: string) => ({
      online: <Badge status="success" text="在线" />,
      offline: <Badge status="default" text="离线" />,
      maintenance: <Badge status="warning" text="维护" />,
    }[v] || <Badge status="default" text={v} />),
  },
  { title: '系统', dataIndex: 'os', key: 'os', width: 100 },
  { title: 'CPU', dataIndex: 'cpu_cores', key: 'cpu_cores', width: 60, render: (v: number) => v ? `${v}核` : '-' },
  { title: '内存', dataIndex: 'memory_mb', key: 'memory_mb', width: 80, render: (v: number) => v ? `${Math.round(v / 1024)}G` : '-' },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
];

const instanceFormItems = (
  <>
    <Form.Item name="name" label="节点名称" rules={[{ required: true }]}><Input placeholder="prod-server-01" /></Form.Item>
    <Space style={{ width: '100%' }} size={16}>
      <Form.Item name="host" label="主机地址" rules={[{ required: true }]} style={{ flex: 1 }}><Input placeholder="192.168.1.100" /></Form.Item>
      <Form.Item name="port" label="端口" rules={[{ required: true }]} style={{ width: 120 }}><InputNumber min={1} max={65535} style={{ width: '100%' }} /></Form.Item>
    </Space>
    <Space style={{ width: '100%' }} size={16}>
      <Form.Item name="instance_type" label="节点类型" rules={[{ required: true }]} style={{ width: 200 }}>
        <Select>
          <Select.Option value="physical">物理机</Select.Option>
          <Select.Option value="docker">Docker</Select.Option>
          <Select.Option value="k8s_pod">K8s Pod</Select.Option>
        </Select>
      </Form.Item>
      <Form.Item name="protocol" label="管理协议" rules={[{ required: true }]} style={{ width: 200 }}>
        <Select>
          <Select.Option value="ssh">SSH</Select.Option>
          <Select.Option value="docker_api">Docker API</Select.Option>
        </Select>
      </Form.Item>
    </Space>
    <Space style={{ width: '100%' }} size={16}>
      <Form.Item name="os" label="操作系统" style={{ width: 200 }}><Input placeholder="Ubuntu 22.04" /></Form.Item>
      <Form.Item name="cpu_cores" label="CPU 核数" style={{ width: 120 }}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
      <Form.Item name="memory_mb" label="内存 (MB)" style={{ width: 140 }}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
      <Form.Item name="disk_gb" label="磁盘 (GB)" style={{ width: 130 }}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
    </Space>
    <Form.Item name="description" label="描述"><TextArea rows={2} /></Form.Item>
  </>
);

// ===================== Agent Tab =====================

const agentColumns: ColumnsType<Agent> = [
  { title: '名称', dataIndex: 'name', key: 'name', width: 120 },
  {
    title: '类型', dataIndex: 'agent_type', key: 'agent_type', width: 100,
    render: (v: string) => ({
      openclaw: <Tag color="orange">OpenClaw</Tag>,
      opencode: <Tag color="green">OpenCode</Tag>,
      harness: <Tag color="blue">Harness</Tag>,
      custom: <Tag color="default">自定义</Tag>,
    }[v] || <Tag>{v}</Tag>),
  },
  { title: '版本', dataIndex: 'version', key: 'version', width: 80 },
  {
    title: '运行方式', dataIndex: 'runtime', key: 'runtime', width: 90,
    render: (v: string) => ({
      docker: <Tag icon={<DockerOutlined />} color="cyan">Docker</Tag>,
      python: <Tag color="volcano">Python</Tag>,
      node: <Tag color="green">Node</Tag>,
      binary: <Tag color="default">Binary</Tag>,
    }[v] || <Tag>{v}</Tag>),
  },
  { title: '镜像', dataIndex: 'docker_image', key: 'docker_image', ellipsis: true, width: 180 },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  {
    title: '启用', dataIndex: 'is_active', key: 'is_active', width: 60,
    render: (v: boolean) => v ? <CheckCircleOutlined style={{ color: '#34d399' }} /> : <Badge status="default" />,
  },
];

const agentFormItems = (
  <>
    <Form.Item name="name" label="Agent 名称" rules={[{ required: true }]}><Input placeholder="my-custom-agent" /></Form.Item>
    <Space style={{ width: '100%' }} size={16}>
      <Form.Item name="agent_type" label="Agent 类型" rules={[{ required: true }]} style={{ width: 200 }}>
        <Select>
          <Select.Option value="openclaw">OpenClaw</Select.Option>
          <Select.Option value="opencode">OpenCode</Select.Option>
          <Select.Option value="harness">Harness</Select.Option>
          <Select.Option value="custom">自定义</Select.Option>
        </Select>
      </Form.Item>
      <Form.Item name="runtime" label="运行方式" rules={[{ required: true }]} style={{ width: 200 }}>
        <Select>
          <Select.Option value="docker">Docker</Select.Option>
          <Select.Option value="python">Python</Select.Option>
          <Select.Option value="node">Node.js</Select.Option>
          <Select.Option value="binary">Binary</Select.Option>
        </Select>
      </Form.Item>
      <Form.Item name="version" label="版本" style={{ width: 120 }}><Input placeholder="latest" /></Form.Item>
    </Space>
    <Form.Item name="docker_image" label="Docker 镜像"><Input placeholder="nginx:latest 或 ghcr.io/my-agent:v1" /></Form.Item>
    <Form.Item name="entrypoint" label="启动命令"><TextArea rows={2} placeholder="docker run --rm ... 或 python main.py" /></Form.Item>
    <Form.Item name="description" label="描述"><TextArea rows={2} /></Form.Item>
    <Form.Item name="is_active" label="启用" valuePropName="checked"><Switch /></Form.Item>
  </>
);

// ===================== Skill Tab =====================

const skillColumns: ColumnsType<Skill> = [
  { title: '名称', dataIndex: 'name', key: 'name', width: 120 },
  {
    title: '类型', dataIndex: 'skill_type', key: 'skill_type', width: 80,
    render: (v: string) => ({
      docker: <Tag icon={<DockerOutlined />} color="cyan">Docker</Tag>,
      mcp: <Tag color="purple">MCP</Tag>,
      script: <Tag icon={<CodeOutlined />} color="gold">Script</Tag>,
      api: <Tag icon={<LinkOutlined />} color="blue">API</Tag>,
    }[v] || <Tag>{v}</Tag>),
  },
  {
    title: '安装状态', dataIndex: 'is_installed', key: 'is_installed', width: 90,
    render: (v: boolean) => v ? <Badge status="success" text="已安装" /> : <Badge status="default" text="未安装" />,
  },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  {
    title: '标签', dataIndex: 'tags', key: 'tags', width: 140,
    render: (tags: string[]) => tags?.map(t => <Tag key={t} style={{ fontSize: 11 }}>{t}</Tag>),
  },
];

const skillFormItems = (
  <>
    <Form.Item name="name" label="技能名称" rules={[{ required: true }]}><Input placeholder="pdf-reader" /></Form.Item>
    <Space style={{ width: '100%' }} size={16}>
      <Form.Item name="skill_type" label="技能类型" rules={[{ required: true }]} style={{ width: 200 }}>
        <Select>
          <Select.Option value="docker">Docker</Select.Option>
          <Select.Option value="mcp">MCP</Select.Option>
          <Select.Option value="script">Script</Select.Option>
          <Select.Option value="api">API</Select.Option>
        </Select>
      </Form.Item>
      <Form.Item name="icon" label="图标" style={{ width: 200 }}><Input placeholder="FilePdfOutlined" /></Form.Item>
    </Space>
    <Form.Item name="docker_image" label="Docker 镜像"><Input placeholder="skill/pdf-reader:latest" /></Form.Item>
    <Form.Item name="install_cmd" label="安装命令"><Input placeholder="pip install pdfplumber" /></Form.Item>
    <Form.Item name="entrypoint" label="启动命令"><TextArea rows={2} /></Form.Item>
    <Form.Item name="description" label="描述"><TextArea rows={2} /></Form.Item>
  </>
);

// ===================== MCP Tab =====================

const mcpColumns: ColumnsType<MCPConfigType> = [
  { title: '名称', dataIndex: 'name', key: 'name', width: 120 },
  {
    title: '类型', dataIndex: 'mcp_type', key: 'mcp_type', width: 80,
    render: (v: string) => ({
      sse: <Tag color="blue">SSE</Tag>,
      stdio: <Tag color="green">Stdio</Tag>,
      http: <Tag color="orange">HTTP</Tag>,
    }[v] || <Tag>{v}</Tag>),
  },
  { title: '地址', dataIndex: 'url', key: 'url', ellipsis: true, width: 180 },
  { title: '命令', dataIndex: 'command', key: 'command', ellipsis: true, width: 140 },
  {
    title: '自动发现', dataIndex: 'auto_discovery_enabled', key: 'auto_discovery_enabled', width: 80,
    render: (v: boolean) => v ? <Tag color="purple">启用</Tag> : <Tag>手动</Tag>,
  },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
];

const mcpFormItems = (
  <>
    <Form.Item name="name" label="MCP 名称" rules={[{ required: true }]}><Input placeholder="my-api-tool" /></Form.Item>
    <Space style={{ width: '100%' }} size={16}>
      <Form.Item name="mcp_type" label="MCP 类型" rules={[{ required: true }]} style={{ width: 200 }}>
        <Select>
          <Select.Option value="sse">SSE</Select.Option>
          <Select.Option value="stdio">Stdio</Select.Option>
          <Select.Option value="http">HTTP</Select.Option>
        </Select>
      </Form.Item>
      <Form.Item name="url" label="连接地址" style={{ flex: 1 }}><Input placeholder="http://..." /></Form.Item>
    </Space>
    <Form.Item name="command" label="启动命令"><Input placeholder="npx @modelcontextprotocol/server-xxx" /></Form.Item>
    <Form.Item name="auto_discovery_url" label="自动发现 URL"><Input placeholder="https://api.example.com/openapi.json" /></Form.Item>
    <Form.Item name="auto_discovery_enabled" label="启用自动发现" valuePropName="checked"><Switch /></Form.Item>
    <Form.Item name="description" label="描述"><TextArea rows={2} /></Form.Item>
  </>
);

// ===================== AgentRun Tab =====================

function AgentRunTab() {
  const { notification } = App.useApp();
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [logDrawer, setLogDrawer] = useState<{ open: boolean; runId: number | null }>({ open: false, runId: null });
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  const [createModal, setCreateModal] = useState(false);
  const [form] = Form.useForm();

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    try {
      const res = await resourcesAPI.listRuns({ skip: 0, limit: 200 });
      setRuns(res.data?.data || []);
    } catch { notification.error({ title: '加载失败', placement: 'top' }); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchRuns(); }, [fetchRuns]);

  const handleStart = async () => {
    try {
      const values = await form.validateFields();
      await resourcesAPI.createRun(values);
      message.success('Agent 已启动');
      setCreateModal(false);
      form.resetFields();
      fetchRuns();
    } catch (err: any) {
      if (err?.errorFields) return;
      notification.error({ title: '启动失败', description: err?.response?.data?.detail || err?.message, placement: 'top' });
    }
  };

  const handleStop = async (id: number) => {
    try {
      await resourcesAPI.stopRun(id);
      message.success('已停止');
      fetchRuns();
    } catch (err: any) {
      notification.error({ title: '停止失败', description: err?.response?.data?.detail || err?.message, placement: 'top' });
    }
  };

  const openLogs = (runId: number) => {
    setLogs([]);
    setLogDrawer({ open: true, runId });

    if (wsRef.current) wsRef.current.close();

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const ws = new WebSocket(`${protocol}//${host}/resources/runs/${runId}/logs`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const entry = JSON.parse(event.data);
        if (entry.error) {
          setLogs(prev => [...prev, { timestamp: new Date().toISOString(), level: 'error', message: entry.error }]);
        } else {
          setLogs(prev => [...prev, entry]);
        }
        setTimeout(() => logEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
      } catch {
        setLogs(prev => [...prev, { timestamp: new Date().toISOString(), level: 'info', message: event.data }]);
      }
    };

    ws.onerror = () => {
      setLogs(prev => [...prev, { timestamp: new Date().toISOString(), level: 'error', message: 'WebSocket 连接错误' }]);
    };
  };

  const closeLogs = () => {
    if (wsRef.current) { wsRef.current.close(); wsRef.current = null; }
    setLogDrawer({ open: false, runId: null });
  };

  const columns: ColumnsType<AgentRun> = [
    { title: '运行名称', dataIndex: 'run_name', key: 'run_name', width: 140 },
    { title: 'Agent ID', dataIndex: 'agent_id', key: 'agent_id', width: 80 },
    { title: '节点 ID', dataIndex: 'instance_id', key: 'instance_id', width: 80 },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (v: string) => ({
        initializing: <Badge status="processing" text="初始化" />,
        running: <Badge status="success" text="运行中" />,
        error: <Badge status="error" text="错误" />,
        stopped: <Badge status="default" text="已停止" />,
      }[v] || <Badge status="default" text={v} />),
    },
    { title: '容器/进程', key: 'cid', width: 140, render: (_, r) => r.container_id || (r.pid ? `PID: ${r.pid}` : '-') },
    { title: '启动时间', dataIndex: 'started_at', key: 'started_at', width: 160, render: (v: string) => v ? new Date(v).toLocaleString() : '-' },
    {
      title: '操作', key: 'actions', width: 160,
      render: (_, record) => (
        <Space size="small">
          {(record.status === 'running' || record.status === 'initializing') && (
            <Button type="text" size="small" icon={<MonitorOutlined />} style={{ color: '#60a5fa' }} onClick={() => openLogs(record.id)}>日志</Button>
          )}
          {(record.status === 'running' || record.status === 'initializing') && (
            <Popconfirm title="确定停止？" onConfirm={() => handleStop(record.id)} okText="停止" cancelText="取消" okButtonProps={{ danger: true }}>
              <Button type="text" size="small" danger icon={<StopOutlined />}>停止</Button>
            </Popconfirm>
          )}
          {record.status === 'error' && (
            <Tooltip title={record.error_message}>
              <Button type="text" size="small" icon={<BugOutlined />} style={{ color: '#f87171' }}>错误</Button>
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', gap: 8 }}>
        <Button type="primary" icon={<PlayCircleOutlined />} onClick={() => { form.resetFields(); setCreateModal(true); }}>启动 Agent</Button>
        <Button icon={<ReloadOutlined />} onClick={fetchRuns}>刷新</Button>
      </div>
      <Card
        title={<Space><MonitorOutlined style={{ color: '#60a5fa' }} />运行监控</Space>}
        style={{ borderRadius: 16, background: 'rgba(255,255,255,0.015)', border: '1px solid rgba(255,255,255,0.06)' }}
      >
        {runs.length === 0 && !loading ? (
          <Empty description={<span style={{ color: '#506380' }}>暂无运行中的 Agent</span>} style={{ padding: 40 }} />
        ) : (
          <Table dataSource={runs} columns={columns} rowKey="id" loading={loading} pagination={false} size="middle" style={{ background: 'transparent' }} />
        )}
      </Card>

      <Modal
        title={<Space><PlayCircleOutlined style={{ color: '#34d399' }} />启动 Agent</Space>}
        open={createModal} onCancel={() => setCreateModal(false)} width={500}
        footer={[<Button key="cancel" onClick={() => setCreateModal(false)}>取消</Button>, <Button key="submit" type="primary" onClick={handleStart}>启动</Button>]}
      >
        <Form form={form} layout="vertical" size="large">
          <Form.Item name="run_name" label="运行名称" rules={[{ required: true }]}><Input placeholder="production-run-01" /></Form.Item>
          <Space style={{ width: '100%' }} size={16}>
            <Form.Item name="agent_id" label="Agent ID" style={{ width: 140 }}><InputNumber min={1} style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="instance_id" label="Instance ID" style={{ width: 140 }}><InputNumber min={1} style={{ width: '100%' }} /></Form.Item>
          </Space>
        </Form>
      </Modal>

      <Drawer
        title={<Space><MonitorOutlined style={{ color: '#60a5fa' }} />实时日志 {logDrawer.runId ? `#${logDrawer.runId}` : ''}</Space>}
        open={logDrawer.open} onClose={closeLogs} width={640}
        styles={{ body: { padding: 0 } }}
      >
        <div style={{ height: '100%', overflowY: 'auto', padding: 16, background: '#0a0e17', fontFamily: 'JetBrains Mono, monospace', fontSize: 12, lineHeight: 1.8 }}>
          {logs.length === 0 && <Text style={{ color: '#506380' }}>等待日志...</Text>}
          {logs.map((log, i) => (
            <div key={i} style={{ color: log.level === 'error' ? '#f87171' : log.level === 'warn' ? '#fbbf24' : '#94a3b8' }}>
              <span style={{ color: '#506380' }}>[{new Date(log.timestamp).toLocaleTimeString()}]</span> {log.message}
            </div>
          ))}
          <div ref={logEndRef} />
        </div>
        <div style={{ padding: '8px 16px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          <Space>
            <Badge status="processing" text="接收中" />
            <Button size="small" icon={<DownloadOutlined />} onClick={closeLogs}>断开</Button>
          </Space>
        </div>
      </Drawer>
    </div>
  );
}

// ===================== MCP 自动发现弹窗 =====================

function MCPAutoDiscoveryButton({ onCreated }: { onCreated: () => void }) {
  const { notification } = App.useApp();
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleDiscover = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      const res = await resourcesAPI.autoDiscoverMCP(values);
      message.success('自动发现完成');
      setOpen(false);
      form.resetFields();
      onCreated();
    } catch (err: any) {
      if (err?.errorFields) return;
      notification.error({ title: '发现失败', description: err?.response?.data?.detail || err?.message, placement: 'top' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Button icon={<ExperimentOutlined />} onClick={() => setOpen(true)}>自动发现 MCP</Button>
      <Modal
        title={<Space><ExperimentOutlined style={{ color: '#8b5cf6' }} />MCP 自动发现</Space>}
        open={open} onCancel={() => setOpen(false)} width={560}
        footer={[<Button key="cancel" onClick={() => setOpen(false)}>取消</Button>, <Button key="submit" type="primary" loading={loading} onClick={handleDiscover}>开始发现</Button>]}
      >
        <Form form={form} layout="vertical" size="large">
          <Form.Item name="api_url" label="API 端点 URL" rules={[{ required: true }]}>
            <Input placeholder="https://api.example.com/v1/query" />
          </Form.Item>
          <Form.Item name="method" label="HTTP 方法" initialValue="GET">
            <Select>
              <Select.Option value="GET">GET</Select.Option>
              <Select.Option value="POST">POST</Select.Option>
              <Select.Option value="PUT">PUT</Select.Option>
              <Select.Option value="DELETE">DELETE</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="description_text" label="API 功能描述（自然语言）">
            <TextArea rows={3} placeholder="用自然语言描述这个 API 的功能，帮助 LLM 推断参数...例如：查询用户订单列表，需要传入 user_id 和 page_size" />
          </Form.Item>
          <Form.Item name="request_body_example" label="请求体示例 (JSON)">
            <TextArea rows={3} placeholder='{"user_id": 123, "page_size": 20}' style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }} />
          </Form.Item>
          <Form.Item name="response_body_example" label="响应体示例 (JSON)">
            <TextArea rows={3} placeholder='{"orders": [...], "total": 100}' style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}

// ===================== 主页面 =====================

export default function ResourcesPage() {
  const [activeTab, setActiveTab] = useState('llm');

  const skillRefreshRef = useRef<() => void>(() => {});
  const [mcpRefreshKey, setMcpRefreshKey] = useState(0);

  const tabItems = [
    {
      key: 'llm',
      label: <span><ApiOutlined /> LLM 配置</span>,
      children: <LLMConfigTab />,
    },
    {
      key: 'instances',
      label: <span><CloudServerOutlined /> 计算节点</span>,
      children: (
        <CrudTab config={{
          name: 'instances', label: '计算节点', icon: <CloudServerOutlined style={{ color: '#60a5fa' }} />,
          api: { list: resourcesAPI.listInstances, create: resourcesAPI.createInstance, update: resourcesAPI.updateInstance, delete: resourcesAPI.deleteInstance },
          columns: instanceColumns, formItems: instanceFormItems,
          defaultValues: { instance_type: 'physical', protocol: 'ssh' },
        }} />
      ),
    },
    {
      key: 'agents',
      label: <span><RobotOutlined /> 智能体</span>,
      children: (
        <CrudTab config={{
          name: 'agents', label: '智能体', icon: <RobotOutlined style={{ color: '#8b5cf6' }} />,
          api: { list: resourcesAPI.listAgents, create: resourcesAPI.createAgent, update: resourcesAPI.updateAgent, delete: resourcesAPI.deleteAgent },
          columns: agentColumns, formItems: agentFormItems,
          defaultValues: { agent_type: 'custom', runtime: 'docker', version: 'latest', is_active: true },
        }} />
      ),
    },
    {
      key: 'skills',
      label: <span><ToolOutlined /> 技能</span>,
      children: (
        <CrudTab config={{
          name: 'skills', label: '技能', icon: <ToolOutlined style={{ color: '#f59e0b' }} />,
          api: { list: resourcesAPI.listSkills, create: resourcesAPI.createSkill, update: resourcesAPI.updateSkill, delete: resourcesAPI.deleteSkill },
          columns: skillColumns, formItems: skillFormItems,
          defaultValues: { skill_type: 'docker', is_active: true },
          extraActions: (record, refresh) => (
            record.is_installed ? null : (
              <Button type="text" size="small" icon={<CloudUploadOutlined />} style={{ color: '#34d399' }}
                onClick={async () => {
                  try {
                    await resourcesAPI.installSkill(record.id);
                    message.success('安装成功');
                    refresh();
                  } catch (err: any) { }
                }}>安装</Button>
            )
          ),
        }} />
      ),
    },
    {
      key: 'mcps',
      label: <span><LinkOutlined /> MCP 工具</span>,
      children: (
        <div key={mcpRefreshKey}>
          <div style={{ marginBottom: 16 }}>
            <MCPAutoDiscoveryButton onCreated={() => setMcpRefreshKey(k => k + 1)} />
          </div>
          <CrudTab config={{
            name: 'mcps', label: 'MCP 工具', icon: <LinkOutlined style={{ color: '#a78bfa' }} />,
            api: { list: resourcesAPI.listMCPs, create: resourcesAPI.createMCP, update: resourcesAPI.updateMCP, delete: resourcesAPI.deleteMCP },
            columns: mcpColumns, formItems: mcpFormItems,
            defaultValues: { mcp_type: 'http', auto_discovery_enabled: false, is_active: true },
          }} />
        </div>
      ),
    },
    {
      key: 'runs',
      label: <span><MonitorOutlined /> 运行监控</span>,
      children: <AgentRunTab />,
    },
  ];

  return (
    <div style={{ maxWidth: 1300 }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ color: '#e8eef5', marginBottom: 4 }}>
          <SettingOutlined style={{ marginRight: 10 }} />
          资源管理
        </Title>
        <Paragraph style={{ color: '#506380', marginBottom: 0 }}>
          Agent 编排中心 — 配置计算节点、智能体、技能与 MCP 工具，监控 Agent 运行状态
        </Paragraph>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        tabBarStyle={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
      />
    </div>
  );
}
