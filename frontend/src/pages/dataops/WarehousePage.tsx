/**
 * DataOps · 数据仓库
 * 交互：左侧数据源 · 右侧三段式（连接 / 元数据 / 样例）
 * 视觉：简约大气 — 大留白、细分割、克制动效
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  App as AntApp,
  Button,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Segmented,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from 'antd';
import {
  ApiOutlined,
  DatabaseOutlined,
  PlusOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import * as dataopsApi from '../../services/dataops.service';
import type {
  ColumnInfo,
  DataSource,
  DataSourceCreate,
  DataSourceType,
  SampleResult,
  TableInfo,
} from '../../types/dataops';

const { Text, Paragraph } = Typography;

function errMsg(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const data = (err as { response?: { data?: { message?: string } } }).response?.data;
    if (data?.message) return data.message;
  }
  if (err instanceof Error) return err.message;
  return '请求失败';
}

type WorkspaceTab = 'connect' | 'meta' | 'sample';

const TYPE_META: Record<DataSourceType, { label: string; color: string; defaultPort: number }> = {
  doris: { label: 'Doris', color: '#0a84ff', defaultPort: 9030 },
  mysql: { label: 'MySQL', color: '#34c759', defaultPort: 3306 },
  hive: { label: 'Hive', color: '#ff9f0a', defaultPort: 10000 },
};

const STATUS_META: Record<string, { label: string; color: string }> = {
  online: { label: '在线', color: '#34c759' },
  offline: { label: '离线', color: '#ff3b30' },
  unknown: { label: '未测', color: '#86868b' },
};

export default function WarehousePage() {
  const { message, modal } = AntApp.useApp();
  const [sources, setSources] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [tab, setTab] = useState<WorkspaceTab>('connect');

  const [addOpen, setAddOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [form] = Form.useForm<DataSourceCreate>();

  const [databases, setDatabases] = useState<string[]>([]);
  const [tables, setTables] = useState<TableInfo[]>([]);
  const [columns, setColumns] = useState<ColumnInfo[]>([]);
  const [dbLoading, setDbLoading] = useState(false);
  const [tableLoading, setTableLoading] = useState(false);
  const [colLoading, setColLoading] = useState(false);
  const [activeDb, setActiveDb] = useState<string | null>(null);
  const [activeTable, setActiveTable] = useState<string | null>(null);

  const [sampleLimit, setSampleLimit] = useState(10);
  const [sampleLoading, setSampleLoading] = useState(false);
  const [sample, setSample] = useState<SampleResult | null>(null);

  const selected = useMemo(
    () => sources.find((s) => s.id === selectedId) ?? null,
    [sources, selectedId],
  );

  const loadSources = useCallback(async () => {
    setLoading(true);
    try {
      const list = await dataopsApi.listDataSources();
      setSources(list);
      setSelectedId((prev) => {
        if (prev && list.some((s) => s.id === prev)) return prev;
        return list[0]?.id ?? null;
      });
    } catch (err) {
      message.error(errMsg(err));
    } finally {
      setLoading(false);
    }
  }, [message]);

  useEffect(() => {
    void loadSources();
  }, [loadSources]);

  useEffect(() => {
    setDatabases([]);
    setTables([]);
    setColumns([]);
    setActiveDb(selected?.database ?? null);
    setActiveTable(null);
    setSample(null);
  }, [selectedId, selected?.database]);

  const runTest = async (sourceId: number) => {
    setTesting(true);
    try {
      const result = await dataopsApi.testDataSource({ source_id: sourceId });
      message.success(
        `${result.message}${result.latency_ms != null ? ` · ${result.latency_ms}ms` : ''}${
          result.server_info ? ` · ${result.server_info}` : ''
        }`,
      );
      await loadSources();
    } catch (err) {
      message.error(errMsg(err));
      await loadSources();
    } finally {
      setTesting(false);
    }
  };

  const openAdd = () => {
    form.setFieldsValue({
      source_type: 'doris',
      port: 9030,
      charset: 'utf8mb4',
      username: 'root',
    });
    setAddOpen(true);
  };

  const submitAdd = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const created = await dataopsApi.createDataSource(values);
      message.success('数据源已添加');
      setAddOpen(false);
      form.resetFields();
      await loadSources();
      setSelectedId(created.id);
      setTab('connect');
    } catch (err) {
      if (err && typeof err === 'object' && 'errorFields' in err) return;
      message.error(errMsg(err));
    } finally {
      setSaving(false);
    }
  };

  const removeSource = (src: DataSource) => {
    modal.confirm({
      title: `删除「${src.name}」？`,
      content: '仅删除平台登记，不影响远端数据库。',
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await dataopsApi.deleteDataSource(src.id);
        message.success('已删除');
        await loadSources();
      },
    });
  };

  const loadDatabases = async () => {
    if (!selected) return;
    setDbLoading(true);
    try {
      const list = await dataopsApi.listDatabases(selected.id);
      setDatabases(list);
      if (!activeDb && selected.database && list.includes(selected.database)) {
        setActiveDb(selected.database);
      } else if (!activeDb && list.length) {
        setActiveDb(list[0]);
      }
    } catch (err) {
      message.error(errMsg(err));
    } finally {
      setDbLoading(false);
    }
  };

  const loadTables = async (database: string) => {
    if (!selected) return;
    setActiveDb(database);
    setActiveTable(null);
    setColumns([]);
    setTableLoading(true);
    try {
      const list = await dataopsApi.listTables(selected.id, database);
      setTables(list);
    } catch (err) {
      message.error(errMsg(err));
      setTables([]);
    } finally {
      setTableLoading(false);
    }
  };

  const loadColumns = async (table: string) => {
    if (!selected || !activeDb) return;
    setActiveTable(table);
    setColLoading(true);
    try {
      const list = await dataopsApi.listColumns(selected.id, activeDb, table);
      setColumns(list);
    } catch (err) {
      message.error(errMsg(err));
      setColumns([]);
    } finally {
      setColLoading(false);
    }
  };

  const runSample = async () => {
    if (!selected || !activeDb || !activeTable) {
      message.warning('请先在「元数据」中选择库表');
      return;
    }
    setSampleLoading(true);
    try {
      const result = await dataopsApi.sampleTable(selected.id, {
        database: activeDb,
        table: activeTable,
        limit: sampleLimit,
      });
      setSample(result);
    } catch (err) {
      message.error(errMsg(err));
    } finally {
      setSampleLoading(false);
    }
  };

  useEffect(() => {
    if (tab === 'meta' && selected && databases.length === 0) {
      void loadDatabases();
    }
  }, [tab, selectedId]); // loadDatabases 依赖 selected，刻意不列入避免循环

  const sampleColumns = useMemo(
    () =>
      (sample?.columns ?? []).map((name) => ({
        title: name,
        dataIndex: name,
        key: name,
        ellipsis: true,
        width: 140,
        render: (v: unknown) =>
          v == null ? <Text type="secondary">NULL</Text> : String(v),
      })),
    [sample],
  );

  const sampleRows = useMemo(
    () =>
      (sample?.rows ?? []).map((row, idx) => {
        const obj: Record<string, unknown> = { key: idx };
        (sample?.columns ?? []).forEach((col, i) => {
          obj[col] = row[i];
        });
        return obj;
      }),
    [sample],
  );

  return (
    <div
      className="page-enter"
      style={{
        height: '100%',
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
        padding: '28px 32px 20px',
        gap: 18,
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 16 }}>
        <Space direction="vertical" size={4}>
          <Text
            style={{
              fontSize: 28,
              fontWeight: 700,
              letterSpacing: '-0.03em',
              color: '#1d1d1f',
              fontFamily: 'var(--font-sans)',
              lineHeight: 1.15,
            }}
          >
            数据仓库
          </Text>
          <Text style={{ fontSize: 13.5, color: '#6e6e73' }}>
            添加数据源 · 探查元数据 · 快速取样
          </Text>
        </Space>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => void loadSources()}>
            刷新
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openAdd}>
            添加数据源
          </Button>
        </Space>
      </div>

      {/* Body */}
      <div
        style={{
          flex: 1,
          minHeight: 0,
          display: 'grid',
          gridTemplateColumns: '260px 1fr',
          gap: 14,
        }}
      >
        {/* Source list */}
        <div
          style={{
            background: '#fff',
            border: '1px solid rgba(0,0,0,0.06)',
            borderRadius: 16,
            boxShadow: '0 1px 4px rgba(0,0,0,0.03)',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            minHeight: 0,
          }}
        >
          <div style={{ padding: '14px 16px 8px', borderBottom: '1px solid rgba(0,0,0,0.04)' }}>
            <Text style={{ fontSize: 12, fontWeight: 600, color: '#86868b', letterSpacing: '0.04em' }}>
              数据源
            </Text>
          </div>
          <div style={{ flex: 1, overflow: 'auto', padding: 8 }}>
            {loading ? (
              <div style={{ padding: 40, textAlign: 'center' }}>
                <Spin />
              </div>
            ) : sources.length === 0 ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="暂无数据源"
                style={{ marginTop: 48 }}
              >
                <Button type="primary" onClick={openAdd}>
                  添加第一个
                </Button>
              </Empty>
            ) : (
              sources.map((src) => {
                const active = src.id === selectedId;
                const tm = TYPE_META[src.source_type];
                const sm = STATUS_META[src.status] ?? STATUS_META.unknown;
                return (
                  <button
                    key={src.id}
                    type="button"
                    onClick={() => setSelectedId(src.id)}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      border: active ? `1px solid ${tm.color}44` : '1px solid transparent',
                      background: active ? `${tm.color}0d` : 'transparent',
                      borderRadius: 12,
                      padding: '12px 12px',
                      marginBottom: 4,
                      cursor: 'pointer',
                      transition: 'all .18s ease',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                      <Text strong style={{ fontSize: 13.5, color: '#1d1d1f' }}>
                        {src.name}
                      </Text>
                      <span
                        style={{
                          width: 7,
                          height: 7,
                          borderRadius: '50%',
                          background: sm.color,
                          marginTop: 5,
                          flexShrink: 0,
                        }}
                      />
                    </div>
                    <div style={{ marginTop: 6, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      <Tag bordered={false} style={{ background: `${tm.color}14`, color: tm.color, margin: 0 }}>
                        {tm.label}
                      </Tag>
                      <Text type="secondary" style={{ fontSize: 11.5 }}>
                        {src.host}:{src.port}
                      </Text>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Workspace */}
        <div
          style={{
            background: '#fff',
            border: '1px solid rgba(0,0,0,0.06)',
            borderRadius: 16,
            boxShadow: '0 1px 4px rgba(0,0,0,0.03)',
            minHeight: 0,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          {!selected ? (
            <div style={{ flex: 1, display: 'grid', placeItems: 'center' }}>
              <Empty description="选择或添加一个数据源开始" />
            </div>
          ) : (
            <>
              <div
                style={{
                  padding: '14px 18px',
                  borderBottom: '1px solid rgba(0,0,0,0.05)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: 12,
                }}
              >
                <Segmented
                  value={tab}
                  onChange={(v) => setTab(v as WorkspaceTab)}
                  options={[
                    { label: '连接', value: 'connect', icon: <ApiOutlined /> },
                    { label: '元数据', value: 'meta', icon: <DatabaseOutlined /> },
                    { label: '样例', value: 'sample', icon: <ThunderboltOutlined /> },
                  ]}
                />
                <Text type="secondary" style={{ fontSize: 12.5 }}>
                  {selected.name}
                </Text>
              </div>

              <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '22px 24px' }}>
                {tab === 'connect' && (
                  <Space direction="vertical" size={20} style={{ width: '100%', maxWidth: 720 }}>
                    <div>
                      <Text style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em' }}>
                        {selected.name}
                      </Text>
                      <Paragraph type="secondary" style={{ marginTop: 6, marginBottom: 0 }}>
                        {selected.description || '无备注'}
                      </Paragraph>
                    </div>
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
                        gap: 10,
                      }}
                    >
                      {[
                        { k: '类型', v: TYPE_META[selected.source_type].label },
                        { k: '主机', v: selected.host },
                        { k: '端口', v: String(selected.port) },
                        { k: '用户', v: selected.username },
                        { k: '默认库', v: selected.database || '—' },
                        { k: '字符集', v: selected.charset },
                        {
                          k: '状态',
                          v: (STATUS_META[selected.status] ?? STATUS_META.unknown).label,
                        },
                      ].map((item) => (
                        <div
                          key={item.k}
                          style={{
                            padding: '14px 16px',
                            borderRadius: 12,
                            background: 'rgba(0,0,0,0.02)',
                            border: '1px solid rgba(0,0,0,0.04)',
                          }}
                        >
                          <div style={{ fontSize: 11, color: '#86868b', marginBottom: 4 }}>{item.k}</div>
                          <div style={{ fontSize: 14, fontWeight: 600, color: '#1d1d1f' }}>{item.v}</div>
                        </div>
                      ))}
                    </div>
                    <Space>
                      <Button
                        type="primary"
                        loading={testing}
                        icon={<ApiOutlined />}
                        onClick={() => void runTest(selected.id)}
                      >
                        测试连接
                      </Button>
                      <Button danger onClick={() => removeSource(selected)}>
                        删除
                      </Button>
                    </Space>
                    {selected.source_type === 'hive' ? (
                      <Text type="secondary" style={{ fontSize: 12.5 }}>
                        Hive 可登记配置；当前运行时探活/元数据走 MySQL 协议（Doris / MySQL）。HiveServer2 将后续接入。
                      </Text>
                    ) : null}
                  </Space>
                )}

                {tab === 'meta' && (
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '180px 220px 1fr',
                      gap: 12,
                      minHeight: 420,
                    }}
                  >
                    <MetaPane
                      title="库"
                      loading={dbLoading}
                      onRefresh={() => void loadDatabases()}
                      items={databases.map((d) => ({
                        key: d,
                        label: d,
                        active: d === activeDb,
                        onClick: () => void loadTables(d),
                      }))}
                      empty="点击刷新拉取库列表"
                    />
                    <MetaPane
                      title="表"
                      loading={tableLoading}
                      items={tables.map((t) => ({
                        key: t.name,
                        label: t.name,
                        active: t.name === activeTable,
                        onClick: () => void loadColumns(t.name),
                      }))}
                      empty={activeDb ? '该库暂无表' : '先选库'}
                    />
                    <div
                      style={{
                        border: '1px solid rgba(0,0,0,0.06)',
                        borderRadius: 12,
                        overflow: 'hidden',
                        minHeight: 0,
                      }}
                    >
                      <div
                        style={{
                          padding: '10px 14px',
                          borderBottom: '1px solid rgba(0,0,0,0.05)',
                          display: 'flex',
                          justifyContent: 'space-between',
                        }}
                      >
                        <Text strong style={{ fontSize: 13 }}>
                          字段 {activeTable ? `· ${activeTable}` : ''}
                        </Text>
                        {activeTable ? (
                          <Button
                            type="link"
                            size="small"
                            onClick={() => {
                              setTab('sample');
                              void runSample();
                            }}
                          >
                            取样 →
                          </Button>
                        ) : null}
                      </div>
                      <div style={{ padding: 8 }}>
                        {colLoading ? (
                          <div style={{ padding: 40, textAlign: 'center' }}>
                            <Spin />
                          </div>
                        ) : columns.length === 0 ? (
                          <Empty
                            image={Empty.PRESENTED_IMAGE_SIMPLE}
                            description={activeTable ? '无字段' : '先选表'}
                          />
                        ) : (
                          <Table
                            size="small"
                            pagination={false}
                            rowKey="name"
                            dataSource={columns}
                            scroll={{ y: 360 }}
                            columns={[
                              { title: '列名', dataIndex: 'name', width: 160 },
                              { title: '类型', dataIndex: 'type', width: 140 },
                              {
                                title: '可空',
                                dataIndex: 'nullable',
                                width: 70,
                                render: (v: boolean) => (v ? 'YES' : 'NO'),
                              },
                              { title: '键', dataIndex: 'key', width: 70 },
                            ]}
                          />
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {tab === 'sample' && (
                  <Space direction="vertical" size={14} style={{ width: '100%' }}>
                    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
                      <Text type="secondary">库</Text>
                      <Select
                        style={{ minWidth: 140 }}
                        value={activeDb ?? undefined}
                        placeholder="选择库"
                        options={databases.map((d) => ({ value: d, label: d }))}
                        onChange={(v) => {
                          void loadTables(v);
                          setSample(null);
                        }}
                        onDropdownVisibleChange={(open) => {
                          if (open && databases.length === 0) void loadDatabases();
                        }}
                      />
                      <Text type="secondary">表</Text>
                      <Select
                        style={{ minWidth: 200 }}
                        value={activeTable ?? undefined}
                        placeholder="选择表"
                        options={tables.map((t) => ({ value: t.name, label: t.name }))}
                        onChange={(v) => {
                          setActiveTable(v);
                          setSample(null);
                        }}
                      />
                      <Text type="secondary">行数</Text>
                      <InputNumber
                        min={1}
                        max={50}
                        value={sampleLimit}
                        onChange={(v) => setSampleLimit(Number(v) || 10)}
                      />
                      <Button type="primary" loading={sampleLoading} onClick={() => void runSample()}>
                        查询样例
                      </Button>
                    </div>
                    {sample ? (
                      <>
                        <Text type="secondary" style={{ fontSize: 12, fontFamily: 'var(--font-mono)' }}>
                          {sample.sql} · {sample.rows.length} 行
                        </Text>
                        <Table
                          size="small"
                          pagination={false}
                          scroll={{ x: Math.max(600, sampleColumns.length * 140), y: 420 }}
                          columns={sampleColumns}
                          dataSource={sampleRows}
                        />
                      </>
                    ) : (
                      <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description="选择库表后点击「查询样例」（默认 5–10 行）"
                        style={{ marginTop: 48 }}
                      />
                    )}
                  </Space>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      <Modal
        title="添加数据源"
        open={addOpen}
        onCancel={() => setAddOpen(false)}
        onOk={() => void submitAdd()}
        confirmLoading={saving}
        okText="保存"
        cancelText="取消"
        destroyOnHidden
        width={520}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '必填' }]}>
            <Input placeholder="例如：Doris 生产仓" />
          </Form.Item>
          <Form.Item name="source_type" label="类型" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'doris', label: 'Doris' },
                { value: 'mysql', label: 'MySQL' },
                { value: 'hive', label: 'Hive（配置可存，探活后续）' },
              ]}
              onChange={(v: DataSourceType) => {
                form.setFieldValue('port', TYPE_META[v].defaultPort);
              }}
            />
          </Form.Item>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 120px', gap: 12 }}>
            <Form.Item name="host" label="主机" rules={[{ required: true, message: '必填' }]}>
              <Input placeholder="10.x.x.x" />
            </Form.Item>
            <Form.Item name="port" label="端口" rules={[{ required: true }]}>
              <InputNumber style={{ width: '100%' }} min={1} max={65535} />
            </Form.Item>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Form.Item name="username" label="用户" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="password" label="密码">
              <Input.Password placeholder="可选" />
            </Form.Item>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Form.Item name="database" label="默认库">
              <Input placeholder="例如 tmp" />
            </Form.Item>
            <Form.Item name="charset" label="字符集">
              <Input placeholder="utf8mb4" />
            </Form.Item>
          </div>
          <Form.Item name="description" label="备注">
            <Input.TextArea rows={2} placeholder="可选" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

function MetaPane({
  title,
  items,
  empty,
  loading,
  onRefresh,
}: {
  title: string;
  items: { key: string; label: string; active: boolean; onClick: () => void }[];
  empty: string;
  loading?: boolean;
  onRefresh?: () => void;
}) {
  return (
    <div
      style={{
        border: '1px solid rgba(0,0,0,0.06)',
        borderRadius: 12,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
      }}
    >
      <div
        style={{
          padding: '10px 12px',
          borderBottom: '1px solid rgba(0,0,0,0.05)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Text strong style={{ fontSize: 13 }}>
          {title}
        </Text>
        {onRefresh ? (
          <Button type="text" size="small" icon={<ReloadOutlined />} onClick={onRefresh} />
        ) : null}
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: 6 }}>
        {loading ? (
          <div style={{ padding: 24, textAlign: 'center' }}>
            <Spin size="small" />
          </div>
        ) : items.length === 0 ? (
          <Text type="secondary" style={{ fontSize: 12, display: 'block', padding: 12 }}>
            {empty}
          </Text>
        ) : (
          items.map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={item.onClick}
              style={{
                width: '100%',
                textAlign: 'left',
                border: 'none',
                borderRadius: 8,
                padding: '8px 10px',
                marginBottom: 2,
                cursor: 'pointer',
                background: item.active ? 'rgba(10,132,255,0.1)' : 'transparent',
                color: item.active ? '#0a84ff' : '#1d1d1f',
                fontWeight: item.active ? 600 : 400,
                fontSize: 12.5,
              }}
            >
              {item.label}
            </button>
          ))
        )}
      </div>
    </div>
  );
}
