import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button,
  Card,
  Descriptions,
  Drawer,
  Input,
  Radio,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  BarChartOutlined,
  DatabaseOutlined,
  DeleteOutlined,
  EyeOutlined,
  FileSearchOutlined,
  RobotOutlined,
  SyncOutlined,
  TableOutlined,
} from '@ant-design/icons';
import { PageHeader, AgentPicker } from '../../components/common';
import { perceptionAPI } from '../../services';
import useDataPlatformStore from '../../stores/dataPlatformStore';

// ---------------------------------------------------------------------------
// Sub-nav (inline duplicate of the same block in SourcesListPage.tsx — ~10 LOC).
// Kept inline per T30 strict files_touched (no new component file).
// ---------------------------------------------------------------------------
function DataPlatformSubNav({ active }: { active: 'sources' | 'metadata' }) {
  const navigate = useNavigate();
  return (
    <Radio.Group
      value={active}
      onChange={(e) => {
        const v = e.target.value as 'sources' | 'metadata';
        if (v === 'sources') navigate('/data-platform/sources');
        else navigate('/data-platform/metadata');
      }}
      style={{ marginBottom: 16 }}
    >
      <Radio.Button value="sources">
        <DatabaseOutlined /> 数据源
      </Radio.Button>
      <Radio.Button value="metadata">
        <FileSearchOutlined /> 元数据
      </Radio.Button>
    </Radio.Group>
  );
}

// ---------------------------------------------------------------------------
// MetadataPage — verbatim port of legacy `pages/perception/index.tsx`
// L68-91 (state), L94-253 (handlers), L480-565 (browse Card), L789-1029
// (Table Detail Drawer + WebSocket stream chat panel).
// ---------------------------------------------------------------------------
export default function MetadataPage() {
  // ----- Data source picker sources come from the data-platform store ------
  const sources = useDataPlatformStore((s) => s.sources);
  const fetchSources = useDataPlatformStore((s) => s.fetchSources);

  useEffect(() => {
    if (sources.length === 0) {
      void fetchSources();
    }
    // Mount-only. Store hydration is user-driven afterwards.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ===== 元数据浏览 state (verbatim from perception/index.tsx L68-91) =====
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
  const [profileData, setProfileData] = useState<any>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  // Agent 选择（标注用）
  const [annotateAgentId, setAnnotateAgentId] = useState<number | undefined>(undefined);
  // 标注对话流
  const [annotateEvents, setAnnotateEvents] = useState<
    { type: string; content?: string; tool?: string; input?: any }[]
  >([]);
  const [annotateInput, setAnnotateInput] = useState('');
  const [annotateSending, setAnnotateSending] = useState(false);
  const annotateWsRef = useRef<WebSocket | null>(null);

  // ===== Handlers (verbatim from perception/index.tsx L94-253) =====
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

  const handleOpenMeta = async (dsId: number) => {
    setMetaDsId(dsId);
    setMetaTables([]);
    setSelectedDb('');
    try {
      const res = await perceptionAPI.listDatabases(dsId);
      const dbs = res.data?.data || [];
      setDatabases(dbs);
      // Auto-pick first DB (source-configured "database" isn't tracked in
      // dataPlatformStore, so we just pick the first one).
      const defaultDb: string = dbs[0] || '';
      if (defaultDb) {
        setSelectedDb(defaultDb);
        void fetchMetaTables(dsId, defaultDb);
      }
    } catch {
      message.error('获取数据库列表失败');
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
      const res = await perceptionAPI.syncMetadata(
        metaDsId,
        syncAll ? undefined : selectedDb,
        syncAll,
      );
      message.success(res.data?.message || '同步完成');
      if (syncAll) {
        const tablesRes = await perceptionAPI.listMetaTables(metaDsId);
        setMetaTables(tablesRes.data?.data || []);
      } else {
        void fetchMetaTables(metaDsId, selectedDb);
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
    setProfileData(null);
    setAnnotateEvents([]);
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

  const handleProfile = async (tableId: number, force = false) => {
    setProfileLoading(true);
    try {
      await perceptionAPI.profileTable(tableId, force);
      const res = await perceptionAPI.getTableProfile(tableId);
      setProfileData(res.data?.data || null);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '数据画像失败');
    } finally {
      setProfileLoading(false);
    }
  };

  const handleAnnotate = (tableId: number) => {
    setAnnotateSending(true);
    setAnnotateEvents([]);

    const wsUrl = perceptionAPI.annotateStreamUrl(tableId);
    const ws = new WebSocket(wsUrl);
    annotateWsRef.current = ws;

    ws.onopen = () => {
      ws.send(
        JSON.stringify({
          prompt: annotateInput.trim() || '',
          agent_id: annotateAgentId,
          force: false,
        }),
      );
    };

    ws.onmessage = (event) => {
      try {
        const evt = JSON.parse(event.data);
        setAnnotateEvents((prev) => [...prev, evt]);

        if (evt.type === 'done') {
          perceptionAPI.getMetaTable(tableId).then((res) => {
            setTableDetail(res.data?.data);
          });
        }
      } catch {
        /* ignore parse errors */
      }
    };

    ws.onerror = () => {
      setAnnotateEvents((prev) => [
        ...prev,
        { type: 'error', content: 'WebSocket 连接失败' },
      ]);
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

  const handleDbChange = (db: string) => {
    setSelectedDb(db);
    if (metaDsId) void fetchMetaTables(metaDsId, db);
  };

  // ===== JSX =====
  return (
    <div>
      <DataPlatformSubNav active="metadata" />
      <PageHeader
        title="数据平台 · 元数据"
        subtitle="连接数据源 · 提取表结构 · 流式 AI 标注"
      />

      {/* 数据源选择器 */}
      <Card
        size="small"
        style={{
          marginBottom: 16,
          borderRadius: 14,
          border: '1px solid rgba(255,255,255,0.06)',
          background: 'rgba(255,255,255,0.02)',
        }}
      >
        <Space size={12} align="center">
          <span style={{ color: '#8895b4' }}>
            <DatabaseOutlined /> 数据源：
          </span>
          <Select
            style={{ minWidth: 260 }}
            placeholder="选择要浏览的数据源"
            value={metaDsId ?? undefined}
            onChange={(v) => void handleOpenMeta(v)}
            options={sources.map((s) => ({
              value: s.id,
              label: `${s.name} (${s.dialect})`,
            }))}
          />
        </Space>
      </Card>

      {/* 元数据浏览区（verbatim from perception L480-565）*/}
      {metaDsId && (
        <Card
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <FileSearchOutlined style={{ color: '#34d399' }} />
              <span style={{ fontWeight: 600 }}>元数据浏览</span>
              <Tag
                style={{
                  borderRadius: 6,
                  background: 'rgba(52,211,153,0.12)',
                  color: '#34d399',
                  border: 'none',
                  fontSize: 11,
                }}
              >
                {sources.find((d) => d.id === metaDsId)?.name}
              </Tag>
            </div>
          }
          extra={
            <Space>
              <label style={{ fontSize: 12, color: '#8895b4', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={syncAll}
                  onChange={(e) => setSyncAll(e.target.checked)}
                  style={{ marginRight: 4 }}
                />
                同步所有库
              </label>
              {!syncAll && (
                <Select
                  style={{ width: 180 }}
                  placeholder="选择数据库"
                  value={selectedDb || undefined}
                  onChange={handleDbChange}
                  options={databases.map((db) => ({ value: db, label: db }))}
                />
              )}
              <Button
                icon={<SyncOutlined />}
                loading={syncing}
                onClick={handleSyncMeta}
                style={{ borderRadius: 8 }}
              >
                提取元数据
              </Button>
              <Button
                type="text"
                icon={<DeleteOutlined />}
                onClick={() => {
                  setMetaDsId(null);
                  setMetaTables([]);
                }}
                style={{ color: '#8895b4' }}
              />
            </Space>
          }
          style={{
            borderRadius: 14,
            border: '1px solid rgba(255,255,255,0.06)',
            marginBottom: 20,
          }}
        >
          <Table
            columns={[
              {
                title: '表名',
                dataIndex: 'table_name',
                key: 'table_name',
                ellipsis: true,
                render: (name: string, r: any) => (
                  <Space>
                    <TableOutlined
                      style={{ color: r.table_type === 'view' ? '#a78bfa' : '#60a5fa' }}
                    />
                    <span style={{ fontWeight: 500 }}>{name}</span>
                  </Space>
                ),
              },
              {
                title: '类型',
                dataIndex: 'table_type',
                key: 'table_type',
                width: 80,
                render: (t: string) => (
                  <Tag
                    style={{
                      borderRadius: 4,
                      background:
                        t === 'view' ? 'rgba(167,139,250,0.12)' : 'rgba(96,165,250,0.12)',
                      color: t === 'view' ? '#a78bfa' : '#60a5fa',
                      border: 'none',
                      fontSize: 11,
                    }}
                  >
                    {t === 'view' ? '视图' : '表'}
                  </Tag>
                ),
              },
              {
                title: '注释',
                dataIndex: 'table_comment',
                key: 'table_comment',
                ellipsis: true,
                render: (c: string, r: any) => (
                  <span style={{ color: c ? '#8895b4' : '#3d4e6b', fontSize: 12 }}>
                    {c ||
                      (r.table_comment_llm ? (
                        <span style={{ color: '#a78bfa' }}>🤖 {r.table_comment_llm}</span>
                      ) : (
                        '—'
                      ))}
                  </span>
                ),
              },
              {
                title: '用途',
                dataIndex: 'purpose',
                key: 'purpose',
                width: 90,
                render: (p: string) =>
                  p ? (
                    <Tag
                      style={{
                        borderRadius: 4,
                        fontSize: 10,
                        background: 'rgba(255,255,255,0.06)',
                        color: '#8895b4',
                        border: 'none',
                      }}
                    >
                      {p}
                    </Tag>
                  ) : null,
              },
              {
                title: '字段',
                dataIndex: 'column_count',
                key: 'column_count',
                width: 60,
                render: (c: number) => <span style={{ color: '#8895b4' }}>{c || 0}</span>,
              },
              {
                title: '行数',
                dataIndex: 'row_count',
                key: 'row_count',
                width: 100,
                render: (r: number) =>
                  r != null ? (
                    <span style={{ color: '#8895b4' }}>{r.toLocaleString()}</span>
                  ) : (
                    '-'
                  ),
              },
              {
                title: '操作',
                key: 'action',
                width: 100,
                render: (_: any, r: any) => (
                  <Button
                    size="small"
                    type="link"
                    icon={<EyeOutlined />}
                    onClick={() => handleOpenTableDetail(r.id)}
                  >
                    详情
                  </Button>
                ),
              },
            ]}
            dataSource={metaTables}
            rowKey="id"
            loading={metaLoading}
            pagination={{ pageSize: 15, size: 'small' }}
            locale={{
              emptyText: selectedDb
                ? '暂无元数据，点击「提取元数据」从数据源同步'
                : '请先选择数据库',
            }}
            size="small"
          />
        </Card>
      )}

      {/* 表元数据详情 Drawer（verbatim from perception L789-1029）*/}
      <Drawer
        title={
          <Space>
            <TableOutlined style={{ color: '#60a5fa' }} />
            <span>{tableDetail?.table_name || '表详情'}</span>
            {tableDetail?.table_comment && (
              <Tag style={{ fontSize: 11 }}>{tableDetail.table_comment}</Tag>
            )}
          </Space>
        }
        open={tableDetailOpen}
        onClose={() => {
          setTableDetailOpen(false);
          handleStopAnnotate();
        }}
        width={1200}
        styles={{ body: { padding: 0, display: 'flex', height: '100%' } }}
        extra={
          <Space>
            <Button
              icon={<BarChartOutlined />}
              loading={profileLoading}
              onClick={() => tableDetail && handleProfile(tableDetail.id)}
              style={{ borderRadius: 8 }}
            >
              数据画像
            </Button>
            <Button
              icon={<EyeOutlined />}
              loading={previewLoading}
              onClick={() => tableDetail && handlePreview(tableDetail.id)}
              style={{ borderRadius: 8 }}
            >
              数据预览
            </Button>
          </Space>
        }
      >
        {tableDetailLoading ? (
          <div style={{ textAlign: 'center', padding: 60, width: '100%' }}>
            <Spin size="large" />
          </div>
        ) : tableDetail ? (
          <div style={{ display: 'flex', width: '100%', height: '100%' }}>
            {/* 左侧：表元数据 */}
            <div
              style={{
                flex: 1,
                overflow: 'auto',
                padding: 16,
                borderRight: '1px solid rgba(255,255,255,0.06)',
              }}
            >
              <Descriptions
                column={3}
                size="small"
                style={{
                  marginBottom: 16,
                  background: 'rgba(255,255,255,0.03)',
                  borderRadius: 10,
                  padding: 12,
                }}
                labelStyle={{ color: '#8895b4', fontSize: 12 }}
                contentStyle={{ color: '#e8eef5', fontSize: 12 }}
              >
                <Descriptions.Item label="数据库">
                  {tableDetail.database_name}
                </Descriptions.Item>
                <Descriptions.Item label="表类型">
                  {tableDetail.table_type === 'view' ? '视图' : '表'}
                </Descriptions.Item>
                <Descriptions.Item label="存储引擎">
                  {tableDetail.engine || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="字段数">
                  {tableDetail.column_count}
                </Descriptions.Item>
                <Descriptions.Item label="行数">
                  {tableDetail.row_count?.toLocaleString() || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="存储大小">
                  {tableDetail.storage_size_mb ? `${tableDetail.storage_size_mb} MB` : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="用途" span={3}>
                  {tableDetail.purpose ? (
                    <Tag style={{ borderRadius: 4, fontSize: 11 }}>{tableDetail.purpose}</Tag>
                  ) : (
                    '—'
                  )}
                  {tableDetail.domain && (
                    <Tag style={{ borderRadius: 4, fontSize: 11, marginLeft: 4 }}>
                      {tableDetail.domain}
                    </Tag>
                  )}
                </Descriptions.Item>
                <Descriptions.Item label="表注释" span={3}>
                  {tableDetail.table_comment || (
                    <span style={{ color: '#3d4e6b' }}>无</span>
                  )}
                </Descriptions.Item>
                {tableDetail.table_comment_llm && (
                  <Descriptions.Item label="LLM 描述" span={3}>
                    <span style={{ color: '#a78bfa' }}>
                      🤖 {tableDetail.table_comment_llm}
                    </span>
                  </Descriptions.Item>
                )}
              </Descriptions>

              <Typography.Title
                level={5}
                style={{ color: '#e8eef5', marginBottom: 12 }}
              >
                字段信息（{tableDetail.columns?.length || 0}）
              </Typography.Title>
              <Table
                columns={[
                  {
                    title: '#',
                    dataIndex: 'ordinal_position',
                    key: 'pos',
                    width: 40,
                    render: (p: number) => <span style={{ color: '#506380' }}>{p}</span>,
                  },
                  {
                    title: '字段名',
                    dataIndex: 'column_name',
                    key: 'name',
                    width: 160,
                    render: (name: string, r: any) => (
                      <Space>
                        <span
                          style={{
                            fontFamily: 'monospace',
                            fontWeight: 500,
                            color: '#e8eef5',
                          }}
                        >
                          {name}
                        </span>
                        {r.is_primary_key && (
                          <Tag
                            style={{
                              borderRadius: 3,
                              fontSize: 9,
                              background: 'rgba(245,158,11,0.15)',
                              color: '#f59e0b',
                              border: 'none',
                              margin: 0,
                            }}
                          >
                            PK
                          </Tag>
                        )}
                      </Space>
                    ),
                  },
                  {
                    title: '类型',
                    dataIndex: 'data_type_full',
                    key: 'type',
                    width: 130,
                    render: (t: string) => (
                      <span
                        style={{
                          fontFamily: 'monospace',
                          fontSize: 11,
                          color: '#60a5fa',
                        }}
                      >
                        {t}
                      </span>
                    ),
                  },
                  {
                    title: '允许空',
                    dataIndex: 'is_nullable',
                    key: 'nullable',
                    width: 60,
                    render: (n: boolean) =>
                      n ? (
                        <span style={{ color: '#506380' }}>YES</span>
                      ) : (
                        <span style={{ color: '#f87171' }}>NO</span>
                      ),
                  },
                  {
                    title: '注释',
                    dataIndex: 'column_comment',
                    key: 'comment',
                    ellipsis: true,
                    render: (c: string, r: any) => (
                      <span
                        style={{
                          fontSize: 12,
                          color: c
                            ? '#8895b4'
                            : r.column_comment_llm
                              ? '#a78bfa'
                              : '#3d4e6b',
                        }}
                      >
                        {c ||
                          (r.column_comment_llm ? `🤖 ${r.column_comment_llm}` : '—')}
                      </span>
                    ),
                  },
                  {
                    title: '语义',
                    dataIndex: 'semantic_type',
                    key: 'semantic',
                    width: 80,
                    render: (s: string) =>
                      s ? (
                        <Tag
                          style={{
                            borderRadius: 3,
                            fontSize: 10,
                            background: 'rgba(255,255,255,0.06)',
                            color: '#8895b4',
                            border: 'none',
                          }}
                        >
                          {s}
                        </Tag>
                      ) : null,
                  },
                ]}
                dataSource={tableDetail.columns || []}
                rowKey="id"
                pagination={false}
                size="small"
                scroll={{ y: 300 }}
              />

              {profileData?.profiles?.length > 0 && (
                <div style={{ marginTop: 20 }}>
                  <Typography.Title
                    level={5}
                    style={{ color: '#e8eef5', marginBottom: 12 }}
                  >
                    数据画像（{profileData.profiles.length} 字段）
                  </Typography.Title>
                  <Table
                    columns={[
                      {
                        title: '字段',
                        dataIndex: 'meta_column_id',
                        key: 'col',
                        width: 150,
                        render: (cid: number) => {
                          const col = (tableDetail.columns || []).find(
                            (c: any) => c.id === cid,
                          );
                          return (
                            <span
                              style={{
                                fontFamily: 'monospace',
                                fontWeight: 500,
                                color: '#e8eef5',
                              }}
                            >
                              {col?.column_name || `#${cid}`}
                            </span>
                          );
                        },
                      },
                      {
                        title: '格式',
                        dataIndex: 'detected_format',
                        key: 'fmt',
                        width: 80,
                        render: (f: string) =>
                          f ? (
                            <Tag
                              style={{
                                borderRadius: 4,
                                fontSize: 10,
                                background: 'rgba(96,165,250,0.12)',
                                color: '#60a5fa',
                                border: 'none',
                              }}
                            >
                              {f}
                            </Tag>
                          ) : (
                            '-'
                          ),
                      },
                      {
                        title: '枚举',
                        dataIndex: 'is_enum',
                        key: 'enum',
                        width: 56,
                        render: (b: boolean) =>
                          b ? (
                            <Tag
                              style={{
                                borderRadius: 4,
                                fontSize: 10,
                                background: 'rgba(251,191,36,0.15)',
                                color: '#fbbf24',
                                border: 'none',
                              }}
                            >
                              枚举
                            </Tag>
                          ) : (
                            <span style={{ color: '#3d4e6b' }}>-</span>
                          ),
                      },
                      {
                        title: '空值率',
                        dataIndex: 'null_ratio',
                        key: 'nr',
                        width: 70,
                        render: (v: number) =>
                          v != null ? (
                            <span style={{ color: v > 0.3 ? '#fbbf24' : '#8895b4' }}>
                              {Math.round(v * 100)}%
                            </span>
                          ) : (
                            '-'
                          ),
                      },
                      {
                        title: '去重数',
                        dataIndex: 'distinct_count',
                        key: 'dc',
                        width: 70,
                        render: (v: number) => (
                          <span style={{ color: '#8895b4' }}>{v ?? '-'}</span>
                        ),
                      },
                      {
                        title: '最值',
                        key: 'range',
                        width: 160,
                        ellipsis: true,
                        render: (_: any, p: any) =>
                          p.min_value != null ? (
                            <span
                              style={{
                                fontSize: 11,
                                color: '#8895b4',
                                fontFamily: 'monospace',
                              }}
                            >
                              {p.min_value} ~ {p.max_value}
                            </span>
                          ) : (
                            '-'
                          ),
                      },
                      {
                        title: '枚举候选',
                        key: 'ev',
                        ellipsis: true,
                        render: (_: any, p: any) =>
                          p.enum_values ? (
                            <Space size={4} wrap>
                              {p.enum_values.slice(0, 5).map((e: any, i: number) => (
                                <Tag
                                  key={i}
                                  style={{
                                    borderRadius: 4,
                                    fontSize: 10,
                                    background: 'rgba(255,255,255,0.06)',
                                    color: '#8895b4',
                                    border: 'none',
                                  }}
                                >
                                  {String(e.value)} ({e.count})
                                </Tag>
                              ))}
                            </Space>
                          ) : (
                            <span style={{ color: '#3d4e6b' }}>—</span>
                          ),
                      },
                    ]}
                    dataSource={profileData.profiles}
                    rowKey="id"
                    pagination={false}
                    size="small"
                    scroll={{ y: 240 }}
                  />
                </div>
              )}

              {previewData && (
                <div style={{ marginTop: 20 }}>
                  <Typography.Title
                    level={5}
                    style={{ color: '#e8eef5', marginBottom: 12 }}
                  >
                    数据预览（{previewData.rows?.length || 0} /{' '}
                    {previewData.total?.toLocaleString()} 行）
                  </Typography.Title>
                  <Table
                    columns={(previewData.columns || []).map((col: string) => ({
                      title: col,
                      dataIndex: col,
                      key: col,
                      ellipsis: true,
                      width: 150,
                      render: (v: any) => (
                        <span
                          style={{
                            fontSize: 11,
                            fontFamily: 'monospace',
                            color: '#8895b4',
                          }}
                        >
                          {v === null ? (
                            <span style={{ color: '#3d4e6b' }}>NULL</span>
                          ) : (
                            String(v)
                          )}
                        </span>
                      ),
                    }))}
                    dataSource={(previewData.rows || []).map((row: any, i: number) => ({
                      ...row,
                      _key: i,
                    }))}
                    rowKey="_key"
                    pagination={false}
                    size="small"
                    scroll={{ x: 'max-content', y: 200 }}
                  />
                </div>
              )}
            </div>

            {/* 右侧：标注对话面板 */}
            <div
              style={{
                width: 460,
                display: 'flex',
                flexDirection: 'column',
                height: '100%',
                background: 'rgba(255,255,255,0.01)',
              }}
            >
              {/* 标题栏 */}
              <div
                style={{
                  padding: '12px 16px',
                  borderBottom: '1px solid rgba(255,255,255,0.06)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <Space>
                  <RobotOutlined style={{ color: '#a78bfa' }} />
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#e8eef5' }}>
                    智能标注
                  </span>
                </Space>
                <AgentPicker
                  value={annotateAgentId}
                  onChange={(v) => setAnnotateAgentId(v ?? undefined)}
                  includePlatformLlm
                  includeLegacyAgents
                  size="small"
                  style={{ width: 160 }}
                />
              </div>

              {/* 事件流区域 */}
              <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
                {annotateEvents.length === 0 ? (
                  <div
                    style={{
                      textAlign: 'center',
                      color: '#506380',
                      fontSize: 12,
                      padding: '30px 16px',
                    }}
                  >
                    <RobotOutlined
                      style={{
                        fontSize: 28,
                        marginBottom: 10,
                        display: 'block',
                        color: '#3d4e6b',
                      }}
                    />
                    输入自定义 prompt 或直接发送使用默认标注 prompt
                    <br />
                    <span style={{ fontSize: 11, color: '#3d4e6b' }}>
                      将自动分析表结构并生成注释
                    </span>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {annotateEvents.map((evt, i) => {
                      let color = '#8895b4';
                      let bg = 'transparent';
                      let icon = '·';
                      if (evt.type === 'status') {
                        color = '#60a5fa';
                        bg = 'rgba(96,165,250,0.06)';
                        icon = '⏳';
                      } else if (evt.type === 'context') {
                        color = '#657a9a';
                        bg = 'rgba(255,255,255,0.03)';
                        icon = '📋';
                      } else if (evt.type === 'prompt') {
                        color = '#a78bfa';
                        bg = 'rgba(167,139,250,0.06)';
                        icon = '📝';
                      } else if (evt.type === 'thinking') {
                        color = '#a78bfa';
                        bg = 'rgba(167,139,250,0.04)';
                        icon = '💭';
                      } else if (evt.type === 'text') {
                        color = '#34d399';
                        bg = 'rgba(52,211,153,0.04)';
                        icon = '💬';
                      } else if (evt.type === 'tool_use') {
                        color = '#60a5fa';
                        bg = 'rgba(96,165,250,0.06)';
                        icon = '🔧';
                      } else if (evt.type === 'tool_result') {
                        color = '#94a3b8';
                        bg = 'rgba(148,163,184,0.04)';
                        icon = '📋';
                      } else if (evt.type === 'error') {
                        color = '#f59e0b';
                        bg = 'rgba(245,158,11,0.06)';
                        icon = '⚠️';
                      } else if (evt.type === 'applied') {
                        color = '#34d399';
                        bg = 'rgba(52,211,153,0.08)';
                        icon = '✅';
                      } else if (evt.type === 'done') {
                        color = '#34d399';
                        bg = 'rgba(52,211,153,0.06)';
                        icon = '✓';
                      } else if (evt.type === 'log') {
                        color = '#3d4e6b';
                        bg = 'transparent';
                        icon = '┃';
                      }
                      return (
                        <div
                          key={i}
                          style={{
                            fontSize: 12,
                            color,
                            background: bg,
                            padding: evt.type === 'log' ? '1px 0' : '6px 10px',
                            borderRadius: 8,
                            lineHeight: 1.5,
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word',
                            fontFamily:
                              evt.type === 'log' ||
                              evt.type === 'thinking' ||
                              evt.type === 'context'
                                ? 'JetBrains Mono, monospace'
                                : 'inherit',
                            opacity: evt.type === 'thinking' ? 0.8 : 1,
                          }}
                        >
                          <span style={{ marginRight: 6 }}>{icon}</span>
                          {evt.type === 'tool_use' && (
                            <span style={{ fontWeight: 600 }}>{evt.tool}: </span>
                          )}
                          {evt.type === 'tool_result' && (
                            <span style={{ fontWeight: 600 }}>{evt.tool}: </span>
                          )}
                          {evt.content}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* 输入区 */}
              <div
                style={{
                  padding: 12,
                  borderTop: '1px solid rgba(255,255,255,0.06)',
                }}
              >
                <Input.TextArea
                  rows={2}
                  placeholder="自定义 prompt（留空使用默认标注 prompt）"
                  value={annotateInput}
                  onChange={(e) => setAnnotateInput(e.target.value)}
                  disabled={annotateSending}
                  style={{
                    marginBottom: 8,
                    background: 'rgba(255,255,255,0.04)',
                    borderColor: 'rgba(255,255,255,0.08)',
                    fontSize: 12,
                  }}
                />
                <div style={{ display: 'flex', gap: 8 }}>
                  {annotateSending ? (
                    <Button
                      danger
                      icon={<DeleteOutlined />}
                      onClick={handleStopAnnotate}
                      style={{ flex: 1, borderRadius: 8 }}
                    >
                      停止
                    </Button>
                  ) : (
                    <Button
                      type="primary"
                      icon={<RobotOutlined />}
                      onClick={() => tableDetail && handleAnnotate(tableDetail.id)}
                      style={{ flex: 1, borderRadius: 8 }}
                    >
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
