import { useState, useEffect, useCallback, useRef } from 'react';
import { Card, Button, Table, Tag, Modal, Form, Input, Select, Space, message, Spin, Descriptions, Typography, Alert, Popconfirm, InputNumber, Drawer, Tooltip, Tree } from 'antd';
import {
  PlusOutlined, UploadOutlined, ApiOutlined, ThunderboltOutlined, ExperimentOutlined,
  EditOutlined, DeleteOutlined, ReloadOutlined, DatabaseOutlined, TableOutlined,
  EyeOutlined, RobotOutlined, SyncOutlined, FileSearchOutlined,
} from '@ant-design/icons';
import { perceptionAPI, resourcesAPI } from '../../services';
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

  // ===== 元数据浏览 =====
  const [metaDsId, setMetaDsId] = useState<number | null>(null);
  const [databases, setDatabases] = useState<string[]>([]);
  const [selectedDb, setSelectedDb] = useState<string>('');
  const [metaTables, setMetaTables] = useState<any[]>([]);
  const [metaLoading, setMetaLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncAll, setSyncAll] = useState(false);
  const [tableDetail, setTableDetail] = useState<any>(null);
  const [tableDetailOpen, setTableDetailOpen] = useState(false);
  const [tableDetailLoading, setTableDetailLoading] = useState(false);
  const [previewData, setPreviewData] = useState<any>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [annotating, setAnnotating] = useState(false);
  // Agent 选择（标注用）
  const [agents, setAgents] = useState<any[]>([]);
  const [annotateAgentId, setAnnotateAgentId] = useState<number | undefined>(undefined);
  // 标注对话流
  const [annotateEvents, setAnnotateEvents] = useState<{ type: string; content?: string; tool?: string; input?: any }[]>([]);
  const [annotateInput, setAnnotateInput] = useState('');
  const [annotateSending, setAnnotateSending] = useState(false);
  const annotateWsRef = useRef<WebSocket | null>(null);

  // ===== 元数据操作 =====
  const handleOpenMeta = async (dsId: number) => {
    setMetaDsId(dsId);
    setMetaTables([]);
    setSelectedDb('');
    try {
      const res = await perceptionAPI.listDatabases(dsId);
      const dbs = res.data?.data || [];
      setDatabases(dbs);
      // 自动选第一个库或数据源配置的库
      const ds = dataSources.find(d => d.id === dsId);
      const defaultDb = ds?.database && dbs.includes(ds.database) ? ds.database : dbs[0] || '';
      if (defaultDb) {
        setSelectedDb(defaultDb);
        fetchMetaTables(dsId, defaultDb);
      }
    } catch {
      message.error('获取数据库列表失败');
    }
  };

  const fetchMetaTables = async (dsId: number, db: string) => {
    setMetaLoading(true);
    try {
      const res = await perceptionAPI.listMetaTables(dsId, db);
      setMetaTables(res.data?.data || []);
    } catch {
      message.error('获取表列表失败');
    } finally {
      setMetaLoading(false);
    }
  };

  const handleSyncMeta = async () => {
    if (!metaDsId) return;
    if (!syncAll && !selectedDb) {
      message.warning('请先选择数据库或勾选「同步所有库」');
      return;
    }
    setSyncing(true);
    try {
      const res = await perceptionAPI.syncMetadata(metaDsId, syncAll ? undefined : selectedDb, syncAll);
      message.success(res.data?.message || '同步完成');
      // 同步后刷新表列表
      if (syncAll) {
        // 同步所有库后，选第一个有数据的库
        const tablesRes = await perceptionAPI.listMetaTables(metaDsId);
        setMetaTables(tablesRes.data?.data || []);
      } else {
        fetchMetaTables(metaDsId, selectedDb);
      }
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '同步失败');
    } finally {
      setSyncing(false);
    }
  };

  const handleOpenTableDetail = async (tableId: number) => {
    setTableDetailOpen(true);
    setTableDetailLoading(true);
    setPreviewData(null);
    try {
      const res = await perceptionAPI.getMetaTable(tableId);
      setTableDetail(res.data?.data);
    } catch {
      message.error('获取表详情失败');
    } finally {
      setTableDetailLoading(false);
    }
  };

  const handlePreview = async (tableId: number) => {
    setPreviewLoading(true);
    try {
      const res = await perceptionAPI.previewData(tableId, 50, 0);
      setPreviewData(res.data?.data);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '数据预览失败');
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleAnnotate = async (tableId: number) => {
    setAnnotateSending(true);
    setAnnotateEvents([]);

    const wsUrl = perceptionAPI.annotateStreamUrl(tableId);
    const ws = new WebSocket(wsUrl);
    annotateWsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({
        prompt: annotateInput.trim() || '',
        agent_id: annotateAgentId,
        force: false,
      }));
    };

    ws.onmessage = (event) => {
      try {
        const evt = JSON.parse(event.data);
        setAnnotateEvents(prev => [...prev, evt]);

        if (evt.type === 'done') {
          // 刷新表详情
          perceptionAPI.getMetaTable(tableId).then(res => {
            setTableDetail(res.data?.data);
          });
        }
      } catch (e) { /* ignore */ }
    };

    ws.onerror = () => {
      setAnnotateEvents(prev => [...prev, { type: 'error', content: 'WebSocket 连接失败' }]);
      setAnnotateSending(false);
    };

    ws.onclose = () => {
      setAnnotateSending(false);
      annotateWsRef.current = null;
    };
  };

  const handleStopAnnotate = () => {
    if (annotateWsRef.current) {
      annotateWsRef.current.close();
      annotateWsRef.current = null;
    }
    setAnnotateSending(false);
  };

  const fetchAgents = useCallback(async () => {
    try {
      const res = await resourcesAPI.listAgents({ skip: 0, limit: 200 });
      setAgents(res.data?.data || []);
    } catch {
      // 忽略
    }
  }, []);

  useEffect(() => { fetchAgents(); }, [fetchAgents]);

  const handleDbChange = (db: string) => {
    setSelectedDb(db);
    if (metaDsId) fetchMetaTables(metaDsId, db);
  };

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
      width: 320,
      render: (_: any, record: DataSource) => (
        <Space size="small">
          <Button size="small" type="text" icon={<DatabaseOutlined />} style={{ color: '#34d399' }}
            onClick={() => handleOpenMeta(record.id)}>
            元数据
          </Button>
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

      {/* 元数据浏览区 */}
      {metaDsId && (
        <Card
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <FileSearchOutlined style={{ color: '#34d399' }} />
              <span style={{ fontWeight: 600 }}>元数据浏览</span>
              <Tag style={{ borderRadius: 6, background: 'rgba(52,211,153,0.12)', color: '#34d399', border: 'none', fontSize: 11 }}>
                {dataSources.find(d => d.id === metaDsId)?.name}
              </Tag>
            </div>
          }
          extra={
            <Space>
              <label style={{ fontSize: 12, color: '#8895b4', cursor: 'pointer' }}>
                <input type="checkbox" checked={syncAll} onChange={e => setSyncAll(e.target.checked)} style={{ marginRight: 4 }} />
                同步所有库
              </label>
              {!syncAll && (
                <Select
                  style={{ width: 180 }}
                  placeholder="选择数据库"
                  value={selectedDb || undefined}
                  onChange={handleDbChange}
                  options={databases.map(db => ({ value: db, label: db }))}
                />
              )}
              <Button icon={<SyncOutlined />} loading={syncing} onClick={handleSyncMeta} style={{ borderRadius: 8 }}>
                提取元数据
              </Button>
              <Button type="text" icon={<DeleteOutlined />} onClick={() => { setMetaDsId(null); setMetaTables([]); }} style={{ color: '#8895b4' }} />
            </Space>
          }
          style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)', marginBottom: 20 }}
        >
          <Table
            columns={[
              {
                title: '表名', dataIndex: 'table_name', key: 'table_name', ellipsis: true,
                render: (name: string, r: any) => (
                  <Space>
                    <TableOutlined style={{ color: r.table_type === 'view' ? '#a78bfa' : '#60a5fa' }} />
                    <span style={{ fontWeight: 500 }}>{name}</span>
                  </Space>
                ),
              },
              {
                title: '类型', dataIndex: 'table_type', key: 'table_type', width: 80,
                render: (t: string) => (
                  <Tag style={{ borderRadius: 4, background: t === 'view' ? 'rgba(167,139,250,0.12)' : 'rgba(96,165,250,0.12)', color: t === 'view' ? '#a78bfa' : '#60a5fa', border: 'none', fontSize: 11 }}>
                    {t === 'view' ? '视图' : '表'}
                  </Tag>
                ),
              },
              {
                title: '注释', dataIndex: 'table_comment', key: 'table_comment', ellipsis: true,
                render: (c: string, r: any) => (
                  <span style={{ color: c ? '#8895b4' : '#3d4e6b', fontSize: 12 }}>
                    {c || (r.table_comment_llm ? <span style={{ color: '#a78bfa' }}>🤖 {r.table_comment_llm}</span> : '—')}
                  </span>
                ),
              },
              {
                title: '用途', dataIndex: 'purpose', key: 'purpose', width: 90,
                render: (p: string) => p ? <Tag style={{ borderRadius: 4, fontSize: 10, background: 'rgba(255,255,255,0.06)', color: '#8895b4', border: 'none' }}>{p}</Tag> : null,
              },
              { title: '字段', dataIndex: 'column_count', key: 'column_count', width: 60, render: (c: number) => <span style={{ color: '#8895b4' }}>{c || 0}</span> },
              { title: '行数', dataIndex: 'row_count', key: 'row_count', width: 100, render: (r: number) => r != null ? <span style={{ color: '#8895b4' }}>{r.toLocaleString()}</span> : '-' },
              {
                title: '操作', key: 'action', width: 100,
                render: (_: any, r: any) => (
                  <Button size="small" type="link" icon={<EyeOutlined />} onClick={() => handleOpenTableDetail(r.id)}>
                    详情
                  </Button>
                ),
              },
            ]}
            dataSource={metaTables}
            rowKey="id"
            loading={metaLoading}
            pagination={{ pageSize: 15, size: 'small' }}
            locale={{ emptyText: selectedDb ? '暂无元数据，点击「提取元数据」从数据源同步' : '请先选择数据库' }}
            size="small"
          />
        </Card>
      )}

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

      {/* 表元数据详情 Drawer */}
      <Drawer
        title={
          <Space>
            <TableOutlined style={{ color: '#60a5fa' }} />
            <span>{tableDetail?.table_name || '表详情'}</span>
            {tableDetail?.table_comment && <Tag style={{ fontSize: 11 }}>{tableDetail.table_comment}</Tag>}
          </Space>
        }
        open={tableDetailOpen}
        onClose={() => setTableDetailOpen(false)}
        width={1200}
        styles={{ body: { padding: 0, display: 'flex', height: '100%' } }}
        extra={
          <Space>
            <Button icon={<EyeOutlined />} loading={previewLoading} onClick={() => tableDetail && handlePreview(tableDetail.id)} style={{ borderRadius: 8 }}>
              数据预览
            </Button>
          </Space>
        }
      >
        {tableDetailLoading ? (
          <div style={{ textAlign: 'center', padding: 60, width: '100%' }}><Spin size="large" /></div>
        ) : tableDetail ? (
          <div style={{ display: 'flex', width: '100%', height: '100%' }}>
            {/* 左侧：表元数据 */}
            <div style={{ flex: 1, overflow: 'auto', padding: 16, borderRight: '1px solid rgba(255,255,255,0.06)' }}>
              <Descriptions column={3} size="small" style={{ marginBottom: 16, background: 'rgba(255,255,255,0.03)', borderRadius: 10, padding: 12 }}
                labelStyle={{ color: '#8895b4', fontSize: 12 }} contentStyle={{ color: '#e8eef5', fontSize: 12 }}>
                <Descriptions.Item label="数据库">{tableDetail.database_name}</Descriptions.Item>
                <Descriptions.Item label="表类型">{tableDetail.table_type === 'view' ? '视图' : '表'}</Descriptions.Item>
                <Descriptions.Item label="存储引擎">{tableDetail.engine || '-'}</Descriptions.Item>
                <Descriptions.Item label="字段数">{tableDetail.column_count}</Descriptions.Item>
                <Descriptions.Item label="行数">{tableDetail.row_count?.toLocaleString() || '-'}</Descriptions.Item>
                <Descriptions.Item label="存储大小">{tableDetail.storage_size_mb ? `${tableDetail.storage_size_mb} MB` : '-'}</Descriptions.Item>
                <Descriptions.Item label="用途" span={3}>
                  {tableDetail.purpose ? <Tag style={{ borderRadius: 4, fontSize: 11 }}>{tableDetail.purpose}</Tag> : '—'}
                  {tableDetail.domain && <Tag style={{ borderRadius: 4, fontSize: 11, marginLeft: 4 }}>{tableDetail.domain}</Tag>}
                </Descriptions.Item>
                <Descriptions.Item label="表注释" span={3}>
                  {tableDetail.table_comment || <span style={{ color: '#3d4e6b' }}>无</span>}
                </Descriptions.Item>
                {tableDetail.table_comment_llm && (
                  <Descriptions.Item label="LLM 描述" span={3}>
                    <span style={{ color: '#a78bfa' }}>🤖 {tableDetail.table_comment_llm}</span>
                  </Descriptions.Item>
                )}
              </Descriptions>

              <Typography.Title level={5} style={{ color: '#e8eef5', marginBottom: 12 }}>字段信息（{tableDetail.columns?.length || 0}）</Typography.Title>
              <Table
                columns={[
                  { title: '#', dataIndex: 'ordinal_position', key: 'pos', width: 40, render: (p: number) => <span style={{ color: '#506380' }}>{p}</span> },
                  {
                    title: '字段名', dataIndex: 'column_name', key: 'name', width: 160,
                    render: (name: string, r: any) => (
                      <Space>
                        <span style={{ fontFamily: 'monospace', fontWeight: 500, color: '#e8eef5' }}>{name}</span>
                        {r.is_primary_key && <Tag style={{ borderRadius: 3, fontSize: 9, background: 'rgba(245,158,11,0.15)', color: '#f59e0b', border: 'none', margin: 0 }}>PK</Tag>}
                      </Space>
                    ),
                  },
                  { title: '类型', dataIndex: 'data_type_full', key: 'type', width: 130, render: (t: string) => <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#60a5fa' }}>{t}</span> },
                  { title: '允许空', dataIndex: 'is_nullable', key: 'nullable', width: 60, render: (n: boolean) => n ? <span style={{ color: '#506380' }}>YES</span> : <span style={{ color: '#f87171' }}>NO</span> },
                  {
                    title: '注释', dataIndex: 'column_comment', key: 'comment', ellipsis: true,
                    render: (c: string, r: any) => (
                      <span style={{ fontSize: 12, color: c ? '#8895b4' : (r.column_comment_llm ? '#a78bfa' : '#3d4e6b') }}>
                        {c || (r.column_comment_llm ? `🤖 ${r.column_comment_llm}` : '—')}
                      </span>
                    ),
                  },
                  { title: '语义', dataIndex: 'semantic_type', key: 'semantic', width: 80, render: (s: string) => s ? <Tag style={{ borderRadius: 3, fontSize: 10, background: 'rgba(255,255,255,0.06)', color: '#8895b4', border: 'none' }}>{s}</Tag> : null },
                ]}
                dataSource={tableDetail.columns || []}
                rowKey="id"
                pagination={false}
                size="small"
                scroll={{ y: 300 }}
              />

              {previewData && (
                <div style={{ marginTop: 20 }}>
                  <Typography.Title level={5} style={{ color: '#e8eef5', marginBottom: 12 }}>
                    数据预览（{previewData.rows?.length || 0} / {previewData.total?.toLocaleString()} 行）
                  </Typography.Title>
                  <Table
                    columns={(previewData.columns || []).map((col: string) => ({
                      title: col, dataIndex: col, key: col, ellipsis: true, width: 150,
                      render: (v: any) => <span style={{ fontSize: 11, fontFamily: 'monospace', color: '#8895b4' }}>{v === null ? <span style={{ color: '#3d4e6b' }}>NULL</span> : String(v)}</span>,
                    }))}
                    dataSource={(previewData.rows || []).map((row: any, i: number) => ({ ...row, _key: i }))}
                    rowKey="_key"
                    pagination={false}
                    size="small"
                    scroll={{ x: 'max-content', y: 200 }}
                  />
                </div>
              )}
            </div>

            {/* 右侧：标注对话面板 */}
            <div style={{ width: 460, display: 'flex', flexDirection: 'column', height: '100%', background: 'rgba(255,255,255,0.01)' }}>
              {/* 标题栏 */}
              <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Space>
                  <RobotOutlined style={{ color: '#a78bfa' }} />
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#e8eef5' }}>智能标注</span>
                </Space>
                <Select
                  size="small"
                  style={{ width: 160 }}
                  value={annotateAgentId}
                  onChange={(v) => setAnnotateAgentId(v)}
                  options={[
                    { value: undefined as any, label: '🏷️ 平台 LLM' },
                    ...agents.map(a => ({ value: a.id, label: `${a.agent_type === 'openclaw' ? '🦞' : a.agent_type === 'opencode' ? '💻' : '🤖'} ${a.name}` })),
                  ]}
                />
              </div>

              {/* 事件流区域 */}
              <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
                {annotateEvents.length === 0 ? (
                  <div style={{ textAlign: 'center', color: '#506380', fontSize: 12, padding: '30px 16px' }}>
                    <RobotOutlined style={{ fontSize: 28, marginBottom: 10, display: 'block', color: '#3d4e6b' }} />
                    输入自定义 prompt 或直接发送使用默认标注 prompt<br />
                    <span style={{ fontSize: 11, color: '#3d4e6b' }}>将自动分析表结构并生成注释</span>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {annotateEvents.map((evt, i) => {
                      let color = '#8895b4'; let bg = 'transparent'; let icon = '·';
                      if (evt.type === 'status') { color = '#60a5fa'; bg = 'rgba(96,165,250,0.06)'; icon = '⏳'; }
                      else if (evt.type === 'context') { color = '#657a9a'; bg = 'rgba(255,255,255,0.03)'; icon = '📋'; }
                      else if (evt.type === 'prompt') { color = '#a78bfa'; bg = 'rgba(167,139,250,0.06)'; icon = '📝'; }
                      else if (evt.type === 'thinking') { color = '#a78bfa'; bg = 'rgba(167,139,250,0.04)'; icon = '💭'; }
                      else if (evt.type === 'text') { color = '#34d399'; bg = 'rgba(52,211,153,0.04)'; icon = '💬'; }
                      else if (evt.type === 'tool_use') { color = '#60a5fa'; bg = 'rgba(96,165,250,0.06)'; icon = '🔧'; }
                      else if (evt.type === 'tool_result') { color = '#94a3b8'; bg = 'rgba(148,163,184,0.04)'; icon = '📋'; }
                      else if (evt.type === 'error') { color = '#f59e0b'; bg = 'rgba(245,158,11,0.06)'; icon = '⚠️'; }
                      else if (evt.type === 'applied') { color = '#34d399'; bg = 'rgba(52,211,153,0.08)'; icon = '✅'; }
                      else if (evt.type === 'done') { color = '#34d399'; bg = 'rgba(52,211,153,0.06)'; icon = '✓'; }
                      else if (evt.type === 'log') { color = '#3d4e6b'; bg = 'transparent'; icon = '┃'; }
                      return (
                        <div key={i} style={{
                          fontSize: 12, color, background: bg, padding: evt.type === 'log' ? '1px 0' : '6px 10px',
                          borderRadius: 8, lineHeight: 1.5, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                          fontFamily: evt.type === 'log' || evt.type === 'thinking' || evt.type === 'context' ? 'JetBrains Mono, monospace' : 'inherit',
                          opacity: evt.type === 'thinking' ? 0.8 : 1,
                        }}>
                          <span style={{ marginRight: 6 }}>{icon}</span>
                          {evt.type === 'tool_use' && <span style={{ fontWeight: 600 }}>{evt.tool}: </span>}
                          {evt.type === 'tool_result' && <span style={{ fontWeight: 600 }}>{evt.tool}: </span>}
                          {evt.content}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* 输入区 */}
              <div style={{ padding: 12, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                <Input.TextArea
                  rows={2}
                  placeholder="自定义 prompt（留空使用默认标注 prompt）"
                  value={annotateInput}
                  onChange={e => setAnnotateInput(e.target.value)}
                  disabled={annotateSending}
                  style={{ marginBottom: 8, background: 'rgba(255,255,255,0.04)', borderColor: 'rgba(255,255,255,0.08)', fontSize: 12 }}
                />
                <div style={{ display: 'flex', gap: 8 }}>
                  {annotateSending ? (
                    <Button danger icon={<DeleteOutlined />} onClick={handleStopAnnotate} style={{ flex: 1, borderRadius: 8 }}>
                      停止
                    </Button>
                  ) : (
                    <Button type="primary" icon={<RobotOutlined />} onClick={() => tableDetail && handleAnnotate(tableDetail.id)} style={{ flex: 1, borderRadius: 8 }}>
                      发送标注
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </Drawer>
    </div>
  );
}
