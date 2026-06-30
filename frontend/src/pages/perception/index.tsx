import { useState, useEffect, useCallback } from 'react';
import { Card, Button, Table, Tag, Modal, Form, Input, Select, Space, message, Spin, Descriptions, Typography, Alert, Popconfirm, InputNumber } from 'antd';
import { PlusOutlined, UploadOutlined, ApiOutlined, ThunderboltOutlined, ExperimentOutlined, EditOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons';
import { perceptionAPI } from '../../services';
import type { DataSource, TestConnectionResult, AutoConfigureResult } from '../../types';

const { TextArea } = Input;
const { Text, Paragraph } = Typography;

// 数据源类型配置
const SOURCE_TYPE_OPTIONS = [
  { value: 'mysql', label: 'MySQL' },
  { value: 'postgresql', label: 'PostgreSQL' },
  { value: 'doris', label: 'Apache Doris' },
  { value: 'clickhouse', label: 'ClickHouse' },
  { value: 'kafka', label: 'Kafka' },
  { value: 'mongodb', label: 'MongoDB' },
  { value: 'redis', label: 'Redis' },
  { value: 'api', label: 'REST API' },
  { value: 'file', label: '文件上传' },
];

const TYPE_COLORS: Record<string, string> = {
  mysql: '#3b82f6',
  postgresql: '#6366f1',
  doris: '#8b5cf6',
  clickhouse: '#f59e0b',
  kafka: '#ef4444',
  mongodb: '#10b981',
  redis: '#ec4899',
  api: '#06b6d4',
  file: '#64748b',
};

const STATUS_CONFIG: Record<string, { color: string; bg: string; text: string }> = {
  active: { color: '#34d399', bg: 'rgba(52,211,153,0.1)', text: '已连接' },
  inactive: { color: '#64748b', bg: 'rgba(255,255,255,0.05)', text: '未激活' },
  error: { color: '#f87171', bg: 'rgba(248,113,113,0.1)', text: '连接失败' },
};

export default function Perception() {
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState(false);

  // 智能添加弹窗
  const [autoModalOpen, setAutoModalOpen] = useState(false);
  const [rawConfig, setRawConfig] = useState('');
  const [autoLoading, setAutoLoading] = useState(false);
  const [autoResult, setAutoResult] = useState<AutoConfigureResult | null>(null);
  const [autoStep, setAutoStep] = useState('');

  // 手动添加/编辑弹窗
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formLoading, setFormLoading] = useState(false);
  const [form] = Form.useForm();

  // 测试连接弹窗
  const [testingId, setTestingId] = useState<number | null>(null);
  const [testResult, setTestResult] = useState<TestConnectionResult | null>(null);
  const [testModalOpen, setTestModalOpen] = useState(false);

  // 加载列表
  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const res = await perceptionAPI.listDataSources();
      setDataSources(res.data?.data || res.data || []);
    } catch {
      message.error('加载数据源列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  // 智能添加
  const handleAutoConfigure = async () => {
    if (!rawConfig.trim()) {
      message.warning('请粘贴配置信息');
      return;
    }
    setAutoLoading(true);
    setAutoResult(null);
    setAutoStep('正在调用 LLM 解析配置...');

    try {
      const res = await perceptionAPI.autoConfigure(rawConfig.trim());
      const result = res.data?.data || res.data;
      setAutoResult(result);
      setAutoStep('');
      message.success('智能添加完成！');
      fetchList();
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || '智能添加失败';
      message.error(detail);
      setAutoStep('');
    } finally {
      setAutoLoading(false);
    }
  };

  // 手动创建/编辑
  const handleFormSubmit = async () => {
    try {
      const values = await form.validateFields();
      setFormLoading(true);
      if (formMode === 'create') {
        await perceptionAPI.createDataSource(values);
        message.success('数据源添加成功');
      } else {
        await perceptionAPI.updateDataSource(editingId!, values);
        message.success('数据源更新成功');
      }
      setFormModalOpen(false);
      form.resetFields();
      fetchList();
    } catch (err: any) {
      if (err?.errorFields) return;
      const detail = err?.response?.data?.detail || err?.message || '操作失败';
      message.error(detail);
    } finally {
      setFormLoading(false);
    }
  };

  const openEdit = (record: DataSource) => {
    setFormMode('edit');
    setEditingId(record.id);
    form.setFieldsValue(record);
    setFormModalOpen(true);
  };

  const openCreate = () => {
    setFormMode('create');
    setEditingId(null);
    form.resetFields();
    setFormModalOpen(true);
  };

  // 删除
  const handleDelete = async (id: number) => {
    try {
      await perceptionAPI.deleteDataSource(id);
      message.success('删除成功');
      fetchList();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '删除失败');
    }
  };

  // 测试连接
  const handleTest = async (id: number) => {
    setTestingId(id);
    setTestResult(null);
    setTestModalOpen(true);
    try {
      const res = await perceptionAPI.testConnection(id);
      setTestResult(res.data?.data || res.data);
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err?.response?.data?.detail || '测试请求失败',
      });
    } finally {
      setTestingId(null);
    }
  };

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name', ellipsis: true },
    {
      title: '类型',
      dataIndex: 'source_type',
      key: 'source_type',
      width: 110,
      render: (t: string) => (
        <Tag style={{ borderRadius: 6, background: `${TYPE_COLORS[t] || '#60a5fa'}20`, color: TYPE_COLORS[t] || '#60a5fa', border: 'none' }}>
          {t?.toUpperCase?.() || t}
        </Tag>
      ),
    },
    {
      title: '连接地址',
      key: 'address',
      width: 200,
      render: (_: any, r: DataSource) => (
        <Text style={{ color: '#8895b4', fontSize: 13 }}>
          {r.host ? `${r.host}${r.port ? `:${r.port}` : ''}` : '-'}
        </Text>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (s: string) => {
        const cfg = STATUS_CONFIG[s] || STATUS_CONFIG.inactive;
        return (
          <Tag style={{ borderRadius: 6, background: cfg.bg, color: cfg.color, border: 'none' }}>
            {cfg.text}
          </Tag>
        );
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 240,
      render: (_: any, record: DataSource) => (
        <Space size="small">
          <Button size="small" type="text" icon={<ExperimentOutlined />} style={{ color: '#60a5fa' }}
            onClick={() => handleTest(record.id)}>
            测试
          </Button>
          <Button size="small" type="text" icon={<EditOutlined />} style={{ color: '#a78bfa' }}
            onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确定删除此数据源？" onConfirm={() => handleDelete(record.id)} okText="确定" cancelText="取消">
            <Button size="small" type="text" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* 头部 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <h2 style={{ color: '#e8eef5', fontSize: 20, fontWeight: 700, margin: 0, letterSpacing: -0.3 }}>
            感知层
          </h2>
          <p style={{ color: '#506380', margin: '4px 0 0', fontSize: 12 }}>
            数据源接入与文档管理
          </p>
        </div>
        <Space>
          <Button icon={<UploadOutlined />} style={{ borderRadius: 10 }}>上传文档</Button>
          <Button icon={<PlusOutlined />} onClick={openCreate} style={{ borderRadius: 10 }}>手动添加</Button>
          <Button type="primary" icon={<ThunderboltOutlined />} onClick={() => { setAutoModalOpen(true); setRawConfig(''); setAutoResult(null); }}
            style={{ borderRadius: 10, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', border: 'none' }}>
            智能添加
          </Button>
        </Space>
      </div>

      {/* 数据源列表 */}
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <ApiOutlined style={{ color: '#60a5fa' }} />
            <span style={{ fontWeight: 600 }}>已连接的数据源</span>
          </div>
        }
        extra={<Button icon={<ReloadOutlined />} type="text" style={{ color: '#8895b4' }} onClick={fetchList} loading={loading}>刷新</Button>}
        style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)', marginBottom: 20 }}
      >
        <Table
          columns={columns}
          dataSource={dataSources}
          rowKey="id"
          loading={loading}
          pagination={false}
          locale={{ emptyText: '暂无数据源，点击"智能添加"或"手动添加"开始接入' }}
        />
      </Card>

      {/* 文档卡片 */}
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <UploadOutlined style={{ color: '#a78bfa' }} />
            <span style={{ fontWeight: 600 }}>已上传文档</span>
          </div>
        }
        style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)' }}
      >
        <Table
          columns={[
            { title: '文件名', dataIndex: 'filename', key: 'filename' },
            { title: '类型', dataIndex: 'file_type', key: 'file_type' },
            { title: '大小', dataIndex: 'file_size', key: 'file_size' },
            { title: '状态', dataIndex: 'status', key: 'status' },
          ]}
          dataSource={[]}
          pagination={false}
          locale={{ emptyText: '暂无已上传文档' }}
        />
      </Card>

      {/* 智能添加弹窗 */}
      <Modal
        title={
          <Space>
            <ThunderboltOutlined style={{ color: '#a78bfa' }} />
            <span>智能添加数据源</span>
          </Space>
        }
        open={autoModalOpen}
        onCancel={() => { setAutoModalOpen(false); setAutoResult(null); }}
        footer={autoResult ? [
          <Button key="close" onClick={() => { setAutoModalOpen(false); setAutoResult(null); }} style={{ borderRadius: 10 }}>
            关闭
          </Button>,
          <Button key="add-more" type="primary" ghost onClick={() => { setRawConfig(''); setAutoResult(null); }} style={{ borderRadius: 10 }}>
            继续添加
          </Button>,
        ] : [
          <Button key="cancel" onClick={() => setAutoModalOpen(false)} style={{ borderRadius: 10 }}>取消</Button>,
          <Button key="submit" type="primary" onClick={handleAutoConfigure} loading={autoLoading}
            style={{ borderRadius: 10, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', border: 'none' }}>
            解析并添加
          </Button>,
        ]}
        width={680}
      >
        {/* 输入区 */}
        {!autoResult && (
          <div style={{ marginTop: 8 }}>
            <TextArea
              placeholder={`粘贴任意格式的配置信息，LLM 将自动识别并结构化，例如：

# Doris 配置
DORIS_HOST=10.18.1.249
DORIS_PORT=9031
DORIS_USER=root
DORIS_PASSWORD=DORIS#zx20240620
DORIS_DATABASE=tmp
DORIS_CHARSET=utf8mb4

或连接串:
mysql://user:pass@host:3306/dbname

或 JDBC URL:
jdbc:mysql://host:3306/db?user=root&password=xxx`}
              value={rawConfig}
              onChange={e => setRawConfig(e.target.value)}
              rows={10}
              style={{ fontFamily: 'monospace', fontSize: 13, borderRadius: 10, background: 'rgba(255,255,255,0.03)' }}
            />
          </div>
        )}

        {/* 加载状态 */}
        {autoLoading && (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin size="large" />
            <p style={{ color: '#8895b4', marginTop: 16 }}>{autoStep || '处理中...'}</p>
          </div>
        )}

        {/* 结果展示 */}
        {autoResult && (
          <div style={{ marginTop: 8 }}>
            {/* 解析结果 */}
            <div style={{ marginBottom: 16 }}>
              <Text strong style={{ color: '#e8eef5', fontSize: 14 }}>📋 解析配置</Text>
              <Descriptions column={2} size="small" style={{ marginTop: 12, background: 'rgba(255,255,255,0.03)', borderRadius: 10, padding: 12 }}
                labelStyle={{ color: '#8895b4' }} contentStyle={{ color: '#e8eef5' }}>
                <Descriptions.Item label="名称">{autoResult.parsed_config?.name}</Descriptions.Item>
                <Descriptions.Item label="类型">
                  <Tag color={TYPE_COLORS[autoResult.parsed_config?.source_type] || 'default'}>
                    {autoResult.parsed_config?.source_type?.toUpperCase?.()}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="主机">{autoResult.parsed_config?.host || '-'}</Descriptions.Item>
                <Descriptions.Item label="端口">{autoResult.parsed_config?.port || '-'}</Descriptions.Item>
                <Descriptions.Item label="用户名">{autoResult.parsed_config?.username || '-'}</Descriptions.Item>
                <Descriptions.Item label="数据库">{autoResult.parsed_config?.database || '-'}</Descriptions.Item>
                <Descriptions.Item label="字符集">{autoResult.parsed_config?.charset || '-'}</Descriptions.Item>
                <Descriptions.Item label="描述">{autoResult.parsed_config?.description || '-'}</Descriptions.Item>
              </Descriptions>
            </div>

            {/* 测试结果 */}
            <div>
              <Text strong style={{ color: '#e8eef5', fontSize: 14 }}>🔌 连接测试</Text>
              <Alert
                type={autoResult.test_result?.success ? 'success' : 'error'}
                message={autoResult.test_result?.success ? '连接成功' : '连接失败'}
                description={
                  <div>
                    <Paragraph style={{ margin: '4px 0', color: 'inherit' }}>{autoResult.test_result?.message}</Paragraph>
                    {autoResult.test_result?.details && (
                      <Paragraph type="secondary" style={{ margin: '4px 0', fontSize: 12 }}>{autoResult.test_result?.details}</Paragraph>
                    )}
                    {autoResult.test_result?.diagnosis && (
                      <div style={{ marginTop: 8, padding: 8, background: 'rgba(255,255,255,0.05)', borderRadius: 6 }}>
                        <Text style={{ fontSize: 12, color: '#a78bfa' }}>🤖 LLM 诊断: </Text>
                        <Text style={{ fontSize: 12, color: '#8895b4' }}>{autoResult.test_result?.diagnosis}</Text>
                      </div>
                    )}
                  </div>
                }
                style={{ marginTop: 8, borderRadius: 10 }}
              />
            </div>
          </div>
        )}
      </Modal>

      {/* 手动添加/编辑弹窗 */}
      <Modal
        title={formMode === 'create' ? '手动添加数据源' : '编辑数据源'}
        open={formModalOpen}
        onCancel={() => { setFormModalOpen(false); form.resetFields(); }}
        onOk={handleFormSubmit}
        confirmLoading={formLoading}
        okButtonProps={{ style: { borderRadius: 10 } }}
        cancelButtonProps={{ style: { borderRadius: 10 } }}
        width={560}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }} initialValues={{ source_type: 'mysql', charset: 'utf8mb4', is_active: true }}>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="例如：风控数据仓库" />
          </Form.Item>
          <Form.Item name="source_type" label="类型" rules={[{ required: true }]}>
            <Select options={SOURCE_TYPE_OPTIONS} />
          </Form.Item>
          <Space style={{ width: '100%' }} size={16}>
            <Form.Item name="host" label="主机" style={{ width: 260 }}>
              <Input placeholder="例如：10.18.1.249" />
            </Form.Item>
            <Form.Item name="port" label="端口">
              <InputNumber placeholder="3306" min={1} max={65535} style={{ width: 120 }} />
            </Form.Item>
          </Space>
          <Space style={{ width: '100%' }} size={16}>
            <Form.Item name="username" label="用户名" style={{ width: 200 }}>
              <Input placeholder="root" />
            </Form.Item>
            <Form.Item name="password" label="密码" style={{ width: 200 }}>
              <Input.Password placeholder="请输入密码" />
            </Form.Item>
          </Space>
          <Space style={{ width: '100%' }} size={16}>
            <Form.Item name="database" label="数据库" style={{ width: 200 }}>
              <Input placeholder="数据库名" />
            </Form.Item>
            <Form.Item name="charset" label="字符集" style={{ width: 200 }}>
              <Input placeholder="utf8mb4" />
            </Form.Item>
          </Space>
          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="数据源用途描述" />
          </Form.Item>
          <Form.Item name="extra_params" label="额外参数 (JSON)">
            <TextArea rows={2} placeholder='{"key": "value"}' style={{ fontFamily: 'monospace' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 测试连接结果弹窗 */}
      <Modal
        title={<Space><ExperimentOutlined style={{ color: '#60a5fa' }} />连接测试结果</Space>}
        open={testModalOpen}
        onCancel={() => { setTestModalOpen(false); fetchList(); }}
        footer={<Button onClick={() => { setTestModalOpen(false); fetchList(); }} style={{ borderRadius: 10 }}>关闭</Button>}
      >
        {testingId ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
            <p style={{ color: '#8895b4', marginTop: 16 }}>正在测试连接...</p>
          </div>
        ) : testResult ? (
          <div>
            <Alert
              type={testResult.success ? 'success' : 'error'}
              message={testResult.success ? '连接成功 ✅' : '连接失败 ❌'}
              description={
                <div>
                  <Paragraph style={{ margin: '4px 0', color: 'inherit' }}>{testResult.message}</Paragraph>
                  {testResult.details && (
                    <Paragraph type="secondary" style={{ margin: '4px 0', fontSize: 12 }}>{testResult.details}</Paragraph>
                  )}
                  {testResult.diagnosis && (
                    <div style={{ marginTop: 8, padding: 8, background: 'rgba(255,255,255,0.05)', borderRadius: 6 }}>
                      <Text style={{ fontSize: 12, color: '#a78bfa' }}>🤖 LLM 诊断: </Text>
                      <Text style={{ fontSize: 12, color: '#8895b4' }}>{testResult.diagnosis}</Text>
                    </div>
                  )}
                </div>
              }
              style={{ borderRadius: 10 }}
            />
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
