import { useState, useEffect, useCallback } from 'react';
import {
  Card, Table, Button, Modal, Form, Input, Select, Switch, Tag, Typography,
  Space, Popconfirm, message, Empty, InputNumber, App,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ApiOutlined,
  CheckCircleOutlined, SettingOutlined, ThunderboltOutlined,
  RobotOutlined, SendOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import llmService from '../../services/llm.service';
import type { LLMConfig, LLMConfigCreate, LLMConfigUpdate } from '../../services/llm.service';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;

export default function ResourcesPage() {
  const { notification } = App.useApp();
  const [configs, setConfigs] = useState<LLMConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState<LLMConfig | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  // ===== 测试对话 =====
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

  useEffect(() => {
    fetchConfigs();
  }, [fetchConfigs]);

  const handleCreate = () => {
    setEditingConfig(null);
    form.resetFields();
    form.setFieldsValue({
      provider: 'openai',
      is_active: false,
      timeout: '60',
      max_retries: '2',
    });
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
          if (v !== undefined && v !== editingConfig[key as keyof LLMConfig]) {
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
      if (err?.errorFields) return; // form validation
      notification.error({
        title: '操作失败',
        description: err?.response?.data?.detail || err?.message,
        placement: 'top',
      });
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
      notification.error({
        title: '删除失败',
        description: err?.response?.data?.detail || err?.message,
        placement: 'top',
      });
    }
  };

  const handleSetActive = async (id: number) => {
    try {
      await llmService.updateConfig(id, { is_active: true });
      message.success('已设为默认配置');
      fetchConfigs();
    } catch (err: any) {
      notification.error({
        title: '操作失败',
        description: err?.response?.data?.detail || err?.message,
        placement: 'top',
      });
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
      const reply = res.data?.content || '';
      setTestMessages([...msgs, { role: 'assistant', content: reply }]);
    } catch (err: any) {
      notification.error({
        title: '调用失败',
        description: err?.response?.data?.detail || err?.message,
        placement: 'top',
      });
    } finally {
      setTestLoading(false);
    }
  };

  const providerLabel = (p: string) =>
    p === 'openai' ? 'OpenAI 协议' : p === 'qwen' ? 'Qwen 协议' : 'Anthropic 协议';

  const providerColor = (p: string) =>
    p === 'openai' ? 'blue' : p === 'qwen' ? 'green' : 'purple';

  const columns: ColumnsType<LLMConfig> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 140,
    },
    {
      title: '协议',
      dataIndex: 'provider',
      key: 'provider',
      width: 120,
      render: (v: string) => <Tag color={providerColor(v)}>{providerLabel(v)}</Tag>,
    },
    {
      title: 'API 地址',
      dataIndex: 'base_url',
      key: 'base_url',
      ellipsis: true,
      width: 200,
    },
    {
      title: '模型',
      dataIndex: 'model_name',
      key: 'model_name',
      width: 160,
    },
    {
      title: '默认',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 70,
      render: (v: boolean, record) =>
        v ? (
          <CheckCircleOutlined style={{ color: '#34d399', fontSize: 16 }} />
        ) : (
          <Button
            type="link"
            size="small"
            onClick={() => handleSetActive(record.id)}
            style={{ fontSize: 12 }}
          >
            启用
          </Button>
        ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      width: 150,
    },
    {
      title: '操作',
      key: 'actions',
      width: 140,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          />
          <Button
            type="text"
            size="small"
            icon={<ThunderboltOutlined />}
            onClick={() => {
              setTestMessages([]);
              setTestInput('');
              setTestModalOpen(true);
            }}
          />
          <Popconfirm
            title="确定删除此配置？"
            onConfirm={() => handleDelete(record.id)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button type="text" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ maxWidth: 1200 }}>
      {/* 页头 */}
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ color: '#e8eef5', marginBottom: 4 }}>
          <SettingOutlined style={{ marginRight: 10 }} />
          资源管理
        </Title>
        <Paragraph style={{ color: '#506380', marginBottom: 0 }}>
          管理 LLM 服务配置，支持 OpenAI 与 Anthropic 协议
        </Paragraph>
      </div>

      {/* 工具栏 */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            新增配置
          </Button>
          <Button
            icon={<SendOutlined />}
            onClick={() => {
              setTestMessages([]);
              setTestInput('');
              setTestModalOpen(true);
            }}
          >
            测试对话
          </Button>
        </Space>
      </div>

      {/* 配置列表 */}
      <Card
        title={
          <Space>
            <ApiOutlined style={{ color: '#60a5fa' }} />
            <span>LLM 配置列表</span>
          </Space>
        }
        style={{
          borderRadius: 16,
          background: 'rgba(255,255,255,0.015)',
          border: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        {configs.length === 0 && !loading ? (
          <Empty
            description={<span style={{ color: '#506380' }}>暂无 LLM 配置，点击「新增配置」开始</span>}
            style={{ padding: 40 }}
          />
        ) : (
          <Table
            dataSource={configs}
            columns={columns}
            rowKey="id"
            loading={loading}
            pagination={false}
            size="middle"
            style={{ background: 'transparent' }}
          />
        )}
      </Card>

      {/* ===== 创建/编辑弹窗 ===== */}
      <Modal
        title={
          editingConfig ? (
            <Space>
              <EditOutlined style={{ color: '#60a5fa' }} />
              编辑 LLM 配置
            </Space>
          ) : (
            <Space>
              <PlusOutlined style={{ color: '#60a5fa' }} />
              新增 LLM 配置
            </Space>
          )
        }
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        width={640}
        footer={[
          <Button key="cancel" onClick={() => setModalOpen(false)}>
            取消
          </Button>,
          <Button
            key="submit"
            type="primary"
            loading={submitting}
            onClick={handleSubmit}
          >
            {editingConfig ? '保存' : '创建'}
          </Button>,
        ]}
        styles={{
          body: { maxHeight: '60vh', overflowY: 'auto' },
        }}
      >
        <Form
          form={form}
          layout="vertical"
          size="large"
          initialValues={{
            provider: 'openai',
            is_active: false,
            timeout: '60',
            max_retries: '2',
          }}
        >
          <Form.Item
            name="name"
            label="配置名称"
            rules={[{ required: true, message: '请输入配置名称' }]}
          >
            <Input placeholder="例如：GPT-4 Azure、Claude 生产环境" />
          </Form.Item>

          <Space style={{ width: '100%' }} size={16}>
            <Form.Item
              name="provider"
              label="服务协议"
              rules={[{ required: true }]}
              style={{ width: 200 }}
            >
              <Select>
                <Option value="openai">OpenAI 协议</Option>
                <Option value="anthropic">Anthropic 协议</Option>
                <Option value="qwen">Qwen 协议</Option>
              </Select>
            </Form.Item>

            <Form.Item
              name="model_name"
              label="模型名称"
              rules={[{ required: true, message: '请输入模型名称' }]}
              style={{ flex: 1 }}
            >
              <Input placeholder="gpt-4 / claude-3-5-sonnet" />
            </Form.Item>
          </Space>

          <Form.Item
            name="base_url"
            label="API Base URL"
            rules={[{ required: true, message: '请输入 API 地址' }]}
          >
            <Input placeholder="https://api.openai.com/v1" />
          </Form.Item>

          <Form.Item
            name="api_key"
            label="API Key"
            rules={[{ required: true, message: '请输入 API Key' }]}
            extra="密钥仅本地加密存储，不会明文传输到前端"
          >
            <Input.Password placeholder="sk-..." />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <Input placeholder="可选：说明此配置的用途" />
          </Form.Item>

          <Space style={{ width: '100%' }} size={16}>
            <Form.Item name="timeout" label="超时（秒）" style={{ width: 150 }}>
              <InputNumber min={1} max={300} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="max_retries" label="最大重试" style={{ width: 150 }}>
              <InputNumber min={0} max={5} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item
              name="is_active"
              label="设为默认"
              valuePropName="checked"
              style={{ paddingTop: 5 }}
            >
              <Switch />
            </Form.Item>
          </Space>

          <Form.Item name="extra_headers" label="额外请求头 (JSON)">
            <TextArea
              rows={2}
              placeholder='{"X-Custom-Header": "value"}'
              style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}
            />
          </Form.Item>

          <Form.Item name="extra_body" label="额外请求体 (JSON)">
            <TextArea
              rows={2}
              placeholder='{"top_p": 0.9}'
              style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* ===== 测试对话弹窗 ===== */}
      <Modal
        title={
          <Space>
            <RobotOutlined style={{ color: '#8b5cf6' }} />
            测试 LLM 对话
          </Space>
        }
        open={testModalOpen}
        onCancel={() => setTestModalOpen(false)}
        width={720}
        footer={null}
        styles={{ body: { padding: 0 } }}
      >
        <div
          style={{
            minHeight: 320,
            maxHeight: 440,
            overflowY: 'auto',
            padding: 16,
            background: 'rgba(0,0,0,0.2)',
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
          }}
        >
          {testMessages.length === 0 && (
            <Text style={{ color: '#506380', textAlign: 'center', padding: 60, display: 'block' }}>
              输入消息测试当前默认激活的 LLM 配置
            </Text>
          )}
          {testMessages.map((m, i) => (
            <div
              key={i}
              style={{
                alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '80%',
                padding: '10px 14px',
                borderRadius: 12,
                background:
                  m.role === 'user'
                    ? 'linear-gradient(135deg, #3b82f6, #8b5cf6)'
                    : 'rgba(255,255,255,0.06)',
                border:
                  m.role === 'user'
                    ? 'none'
                    : '1px solid rgba(255,255,255,0.08)',
                color: '#e8eef5',
                fontSize: 13,
                lineHeight: 1.6,
                whiteSpace: 'pre-wrap',
              }}
            >
              {m.content}
            </div>
          ))}
          {testLoading && (
            <Text style={{ color: '#506380', fontSize: 12, padding: 4 }}>思考中...</Text>
          )}
        </div>
        <div
          style={{
            padding: '12px 16px',
            borderTop: '1px solid rgba(255,255,255,0.06)',
            display: 'flex',
            gap: 8,
          }}
        >
          <Input.TextArea
            value={testInput}
            onChange={(e) => setTestInput(e.target.value)}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault();
                handleTestChat();
              }
            }}
            placeholder="输入消息，Enter 发送，Shift+Enter 换行"
            autoSize={{ minRows: 1, maxRows: 4 }}
            style={{ flex: 1 }}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleTestChat}
            loading={testLoading}
          >
            发送
          </Button>
        </div>
      </Modal>
    </div>
  );
}
