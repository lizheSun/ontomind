import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  App as AntApp,
  Alert,
  Button,
  Drawer,
  Form,
  Input,
  InputNumber,
  Modal,
  Progress,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Tree,
  Typography,
} from 'antd';
import type { DataNode } from 'antd/es/tree';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { listDataSources, listDatabases } from '../../../services/dataops.service';
import {
  batchBindStandard,
  bindColumnStandard,
  createDatabaseBrief,
  createMetaScan,
  createStandard,
  deleteStandard,
  getDatabaseBrief,
  getActiveLlmSetting,
  getMetaJob,
  listMetaJobs,
  listStandards,
  listWorkspaceColumns,
  unbindColumnStandard,
  updateStandard,
} from '../../../services/metadata.service';
import type { DataSource } from '../../../types/dataops';
import type {
  ColumnWorkspaceItem,
  DatabaseBrief,
  LlmSetting,
  MetaScanJob,
  MetaStandard,
} from '../../../types/metadata';

const { Text, Title, Paragraph } = Typography;
const CTX_KEY = 'ontomind_meta_ctx';

type Ctx = { sourceId?: number; database?: string };

function loadCtx(): Ctx {
  try {
    return JSON.parse(localStorage.getItem(CTX_KEY) || '{}') as Ctx;
  } catch {
    return {};
  }
}

function saveCtx(ctx: Ctx) {
  localStorage.setItem(CTX_KEY, JSON.stringify(ctx));
}

export default function MetadataPage() {
  const { message, modal } = AntApp.useApp();
  const navigate = useNavigate();
  const [sources, setSources] = useState<DataSource[]>([]);
  const [sourceId, setSourceId] = useState<number>();
  const [databases, setDatabases] = useState<string[]>([]);
  const [database, setDatabase] = useState<string>();
  const [mainTab, setMainTab] = useState('catalog');

  const [brief, setBrief] = useState<DatabaseBrief | null>(null);
  const [columns, setColumns] = useState<ColumnWorkspaceItem[]>([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [filter, setFilter] = useState({
    table_name: '',
    column_name: '',
    security_level: undefined as string | undefined,
    bound: undefined as boolean | undefined,
    standard_id: undefined as number | undefined,
  });

  const [standards, setStandards] = useState<MetaStandard[]>([]);
  const [jobs, setJobs] = useState<MetaScanJob[]>([]);
  const [activeJob, setActiveJob] = useState<MetaScanJob | null>(null);
  const [llm, setLlm] = useState<LlmSetting | null>(null);

  const [bindOpen, setBindOpen] = useState(false);
  const [bindTargetIds, setBindTargetIds] = useState<number[]>([]);
  const [bindStandardId, setBindStandardId] = useState<number>();
  const [stdModal, setStdModal] = useState(false);
  const [editingStd, setEditingStd] = useState<MetaStandard | null>(null);
  const [stdForm] = Form.useForm();

  useEffect(() => {
    void (async () => {
      const rows = await listDataSources();
      setSources(rows);
      const ctx = loadCtx();
      const sid = ctx.sourceId && rows.some((r) => r.id === ctx.sourceId) ? ctx.sourceId : rows[0]?.id;
      setSourceId(sid);
      if (sid) {
        try {
          const dbs = await listDatabases(sid);
          setDatabases(dbs);
          const db = ctx.database && dbs.includes(ctx.database) ? ctx.database : dbs[0];
          setDatabase(db);
        } catch {
          setDatabases([]);
        }
      }
      setStandards(await listStandards());
      setLlm(await getActiveLlmSetting().catch(() => null));
    })();
  }, []);

  useEffect(() => {
    if (!sourceId) return;
    void listDatabases(sourceId)
      .then((dbs) => {
        setDatabases(dbs);
        setDatabase((prev) => (prev && dbs.includes(prev) ? prev : dbs[0]));
      })
      .catch(() => setDatabases([]));
  }, [sourceId]);

  useEffect(() => {
    if (sourceId && database) saveCtx({ sourceId, database });
  }, [sourceId, database]);

  const refreshWorkspace = useCallback(async () => {
    if (!sourceId || !database) return;
    const [cols, b, j] = await Promise.all([
      listWorkspaceColumns({
        source_id: sourceId,
        database,
        table_name: filter.table_name || undefined,
        column_name: filter.column_name || undefined,
        security_level: filter.security_level,
        bound: filter.bound,
        standard_id: filter.standard_id,
        limit: 300,
      }),
      getDatabaseBrief(sourceId, database),
      listMetaJobs({ source_id: sourceId, database, limit: 50 }),
    ]);
    setColumns(cols);
    setBrief(b);
    setJobs(j);
    const running = j.find((x) => x.status === 'pending' || x.status === 'running');
    if (running) setActiveJob(running);
  }, [sourceId, database, filter]);

  useEffect(() => {
    void refreshWorkspace().catch(() => undefined);
  }, [refreshWorkspace]);

  useEffect(() => {
    if (!activeJob || activeJob.status === 'succeeded' || activeJob.status === 'failed') return;
    const t = window.setInterval(() => {
      void getMetaJob(activeJob.id).then(async (j) => {
        setActiveJob(j);
        if (j.status === 'succeeded' || j.status === 'failed') {
          await refreshWorkspace();
          setStandards(await listStandards());
          if (j.status === 'failed') message.error(j.error_detail || '作业失败');
          else message.success(`作业 #${j.id} 完成`);
        }
      });
    }, 2000);
    return () => window.clearInterval(t);
  }, [activeJob, refreshWorkspace, message]);

  const treeData: DataNode[] = useMemo(() => {
    return sources.map((s) => ({
      key: `src-${s.id}`,
      title: s.name,
      selectable: false,
      children:
        s.id === sourceId
          ? databases.map((d) => ({
              key: `db-${s.id}-${d}`,
              title: d,
              isLeaf: true,
            }))
          : [{ key: `src-${s.id}-load`, title: '…', isLeaf: true, disableCheckbox: true }],
    }));
  }, [sources, sourceId, databases]);

  const startScan = async () => {
    if (!sourceId || !database) return;
    const j = await createMetaScan({ source_id: sourceId, database, with_profile: false });
    setActiveJob(j);
    setMainTab('jobs');
    message.success('结构扫描已启动');
  };

  const startBrief = async (mode: 'rules' | 'llm') => {
    if (!sourceId || !database) return;
    if (mode === 'llm' && llm && !llm.configured) {
      message.warning('LLM 未配置');
      return;
    }
    const j = await createDatabaseBrief({ source_id: sourceId, database, mode });
    setActiveJob(j);
    message.success(mode === 'llm' ? '智能分析已启动' : '规则分析已启动');
  };

  const openBind = (ids: number[]) => {
    setBindTargetIds(ids);
    setBindStandardId(standards[0]?.id);
    setBindOpen(true);
  };

  const doBind = async () => {
    if (!bindStandardId || !bindTargetIds.length) return;
    if (bindTargetIds.length === 1) {
      await bindColumnStandard(bindTargetIds[0], { standard_id: bindStandardId });
    } else {
      await batchBindStandard({ column_ids: bindTargetIds, standard_id: bindStandardId });
    }
    setBindOpen(false);
    setSelectedRowKeys([]);
    message.success('标准项已绑定');
    await refreshWorkspace();
    setStandards(await listStandards());
  };

  const openStdEditor = (row?: MetaStandard) => {
    setEditingStd(row || null);
    stdForm.setFieldsValue(
      row
        ? {
            code: row.code,
            name: row.name,
            security_level: row.security_level,
            semantic_type: row.semantic_type,
            data_type_expect: row.data_type_expect,
            description: row.description,
            mask_rule: row.mask_rule,
            len_min: (row.length_rule_json as { min?: number } | null)?.min,
            len_max: (row.length_rule_json as { max?: number } | null)?.max,
            regex: (row.quality_rule_json as { regex?: string } | null)?.regex,
          }
        : { security_level: 'L0' },
    );
    setStdModal(true);
  };

  const saveStd = async () => {
    const v = await stdForm.validateFields();
    const length_rule =
      v.len_min != null || v.len_max != null ? { min: v.len_min, max: v.len_max } : undefined;
    const quality_rule = v.regex ? { regex: v.regex } : undefined;
    if (editingStd) {
      await updateStandard(editingStd.id, {
        name: v.name,
        security_level: v.security_level,
        semantic_type: v.semantic_type,
        data_type_expect: v.data_type_expect,
        description: v.description,
        mask_rule: v.mask_rule,
        length_rule,
        quality_rule,
        bump_version: true,
        change_note: 'UI 更新',
      });
    } else {
      await createStandard({
        code: v.code,
        name: v.name,
        security_level: v.security_level,
        semantic_type: v.semantic_type,
        data_type_expect: v.data_type_expect,
        description: v.description,
        mask_rule: v.mask_rule,
        length_rule_json: length_rule,
        quality_rule_json: quality_rule,
      });
    }
    setStdModal(false);
    setStandards(await listStandards());
    message.success('标准项已保存');
  };

  const catalogPane = (
    <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: 12, minHeight: 0, height: '100%' }}>
      <div style={{ background: 'var(--bg-elevated, #fff)', borderRadius: 12, padding: 8, overflow: 'auto' }}>
        <Text type="secondary" style={{ fontSize: 12, padding: '0 8px' }}>
          数据源 → 库
        </Text>
        <Tree
          treeData={treeData}
          selectedKeys={sourceId && database ? [`db-${sourceId}-${database}`] : []}
          defaultExpandAll
          onSelect={(keys) => {
            const k = String(keys[0] || '');
            const m = /^db-(\d+)-(.+)$/.exec(k);
            if (m) {
              setSourceId(Number(m[1]));
              setDatabase(m[2]);
            }
          }}
          onExpand={(_, info) => {
            const k = String(info.node.key);
            const m = /^src-(\d+)$/.exec(k);
            if (m) setSourceId(Number(m[1]));
          }}
        />
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, minHeight: 0, overflow: 'auto' }}>
        {!database ? (
          <Alert type="info" message="请选择左侧库" showIcon />
        ) : (
          <>
            <div
              style={{
                background: 'var(--bg-elevated, #fff)',
                borderRadius: 12,
                padding: 16,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <Title level={5} style={{ margin: 0 }}>
                  {database}
                </Title>
                <Space>
                  <Button size="small" onClick={() => void startScan()}>
                    扫描结构
                  </Button>
                  <Button size="small" onClick={() => void startBrief('rules')}>
                    规则分析
                  </Button>
                  <Button size="small" type="primary" onClick={() => void startBrief('llm')}>
                    智能分析
                  </Button>
                </Space>
              </div>
              {activeJob && (activeJob.status === 'pending' || activeJob.status === 'running') ? (
                <div style={{ marginBottom: 8 }}>
                  <Text type="secondary">
                    进行中 #{activeJob.id} · {activeJob.job_kind}
                  </Text>
                  <Progress percent={Math.round((activeJob.progress || 0) * 100)} size="small" />
                </div>
              ) : null}
              {brief?.content_md ? (
                <div style={{ maxHeight: 180, overflow: 'auto', fontSize: 13 }}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{brief.content_md}</ReactMarkdown>
                </div>
              ) : (
                <Paragraph type="secondary" style={{ margin: 0 }}>
                  尚无库概况。先「扫描结构」，再「规则分析」或「智能分析」。
                </Paragraph>
              )}
            </div>

            <div style={{ background: 'var(--bg-elevated, #fff)', borderRadius: 12, padding: 12, flex: 1 }}>
              <Form layout="inline" style={{ marginBottom: 12, rowGap: 8 }}>
                <Form.Item label="表名">
                  <Input
                    allowClear
                    style={{ width: 120 }}
                    value={filter.table_name}
                    onChange={(e) => setFilter((f) => ({ ...f, table_name: e.target.value }))}
                  />
                </Form.Item>
                <Form.Item label="列名">
                  <Input
                    allowClear
                    style={{ width: 120 }}
                    value={filter.column_name}
                    onChange={(e) => setFilter((f) => ({ ...f, column_name: e.target.value }))}
                  />
                </Form.Item>
                <Form.Item label="安全等级">
                  <Select
                    allowClear
                    style={{ width: 90 }}
                    value={filter.security_level}
                    onChange={(v) => setFilter((f) => ({ ...f, security_level: v }))}
                    options={['L0', 'L1', 'L2', 'L3'].map((x) => ({ value: x, label: x }))}
                  />
                </Form.Item>
                <Form.Item label="标准">
                  <Select
                    allowClear
                    style={{ width: 140 }}
                    value={filter.standard_id}
                    onChange={(v) => setFilter((f) => ({ ...f, standard_id: v }))}
                    options={standards.map((s) => ({ value: s.id, label: s.name }))}
                  />
                </Form.Item>
                <Form.Item label="绑定">
                  <Select
                    allowClear
                    style={{ width: 100 }}
                    value={filter.bound === undefined ? undefined : filter.bound ? '1' : '0'}
                    onChange={(v) =>
                      setFilter((f) => ({
                        ...f,
                        bound: v === undefined ? undefined : v === '1',
                      }))
                    }
                    options={[
                      { value: '1', label: '已绑' },
                      { value: '0', label: '未绑' },
                    ]}
                  />
                </Form.Item>
                <Button type="primary" onClick={() => void refreshWorkspace()}>
                  查询
                </Button>
                <Button
                  disabled={!selectedRowKeys.length}
                  onClick={() => openBind(selectedRowKeys.map(Number))}
                >
                  批量标准标注
                </Button>
              </Form>
              <Table
                size="small"
                rowKey="id"
                dataSource={columns}
                rowSelection={{
                  selectedRowKeys,
                  onChange: setSelectedRowKeys,
                }}
                pagination={{ pageSize: 50, size: 'small' }}
                scroll={{ x: 1100 }}
                columns={[
                  { title: '表', dataIndex: 'table_name', width: 140, fixed: 'left' },
                  { title: '列', dataIndex: 'column_name', width: 140, fixed: 'left' },
                  { title: '类型', dataIndex: 'column_type', width: 110, ellipsis: true },
                  { title: '物理注释', dataIndex: 'column_comment', ellipsis: true },
                  {
                    title: '标准项',
                    width: 140,
                    render: (_: unknown, r: ColumnWorkspaceItem) =>
                      r.standard_name ? (
                        <Tag color="blue">
                          {r.standard_name}
                          {r.standard_code ? ` (${r.standard_code})` : ''}
                        </Tag>
                      ) : (
                        <Text type="secondary">未标</Text>
                      ),
                  },
                  {
                    title: '安全',
                    width: 70,
                    render: (_: unknown, r: ColumnWorkspaceItem) =>
                      r.effective_security_level || r.pii_level || '—',
                  },
                  {
                    title: '长度规则',
                    width: 100,
                    render: (_: unknown, r: ColumnWorkspaceItem) => {
                      const lr = r.length_rule_json as { min?: number; max?: number } | null;
                      if (!lr) return '—';
                      return `${lr.min ?? '?'}~${lr.max ?? '?'}`;
                    },
                  },
                  {
                    title: '状态',
                    width: 80,
                    render: (_: unknown, r: ColumnWorkspaceItem) => r.bind_status || '未绑',
                  },
                  {
                    title: '操作',
                    width: 140,
                    fixed: 'right',
                    render: (_: unknown, r: ColumnWorkspaceItem) => (
                      <Space size={4}>
                        <Button type="link" size="small" onClick={() => openBind([r.id])}>
                          标注
                        </Button>
                        {r.bind_id ? (
                          <Button
                            type="link"
                            size="small"
                            danger
                            onClick={() =>
                              void unbindColumnStandard(r.id).then(async () => {
                                message.success('已解绑');
                                await refreshWorkspace();
                              })
                            }
                          >
                            解绑
                          </Button>
                        ) : null}
                      </Space>
                    ),
                  },
                ]}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );

  const standardsPane = (
    <div style={{ background: 'var(--bg-elevated, #fff)', borderRadius: 12, padding: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <Text type="secondary">一个标准项可绑定多个字段；每个字段最多一个标准项</Text>
        <Button type="primary" onClick={() => openStdEditor()}>
          新建标准项
        </Button>
      </div>
      <Table
        size="small"
        rowKey="id"
        dataSource={standards}
        columns={[
          { title: '编码', dataIndex: 'code', width: 140 },
          { title: '名称', dataIndex: 'name', width: 120 },
          { title: '安全', dataIndex: 'security_level', width: 70 },
          { title: '语义', dataIndex: 'semantic_type', width: 100 },
          {
            title: '长度',
            width: 90,
            render: (_: unknown, r: MetaStandard) => {
              const lr = r.length_rule_json as { min?: number; max?: number } | null;
              return lr ? `${lr.min ?? '?'}~${lr.max ?? '?'}` : '—';
            },
          },
          {
            title: '质量规则',
            ellipsis: true,
            render: (_: unknown, r: MetaStandard) =>
              r.quality_rule_json ? JSON.stringify(r.quality_rule_json) : '—',
          },
          { title: '已绑字段', dataIndex: 'bound_column_count', width: 90 },
          { title: '版本', dataIndex: 'current_version', width: 60 },
          {
            title: '操作',
            width: 140,
            render: (_: unknown, r: MetaStandard) => (
              <Space>
                <Button type="link" size="small" onClick={() => openStdEditor(r)}>
                  编辑
                </Button>
                <Button
                  type="link"
                  size="small"
                  danger
                  onClick={() => {
                    modal.confirm({
                      title: `删除 ${r.code}？`,
                      onOk: async () => {
                        await deleteStandard(r.id);
                        setStandards(await listStandards());
                        message.success('已删除');
                      },
                    });
                  }}
                >
                  删除
                </Button>
              </Space>
            ),
          },
        ]}
      />
    </div>
  );

  const jobsPane = (
    <div style={{ background: 'var(--bg-elevated, #fff)', borderRadius: 12, padding: 12 }}>
      <Space style={{ marginBottom: 12 }}>
        <Button
          onClick={() =>
            void listMetaJobs({ source_id: sourceId, database, limit: 50 }).then(setJobs)
          }
        >
          刷新
        </Button>
        <Text type="secondary">扫描 / 库分析 / 标注作业；刷新后可继续跟踪未完成任务</Text>
      </Space>
      <Table
        size="small"
        rowKey="id"
        dataSource={jobs}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 70 },
          { title: '类型', dataIndex: 'job_kind', width: 90 },
          { title: '库', dataIndex: 'database', width: 100 },
          {
            title: '状态',
            dataIndex: 'status',
            width: 100,
            render: (v: string) => (
              <Tag color={v === 'succeeded' ? 'green' : v === 'failed' ? 'red' : 'processing'}>{v}</Tag>
            ),
          },
          {
            title: '进度',
            width: 140,
            render: (_: unknown, r: MetaScanJob) => (
              <Progress percent={Math.round((r.progress || 0) * 100)} size="small" />
            ),
          },
          { title: '耗时ms', dataIndex: 'duration_ms', width: 90 },
          {
            title: '错误',
            dataIndex: 'error_detail',
            ellipsis: true,
            render: (v: string) => v || '—',
          },
          {
            title: '操作',
            width: 90,
            render: (_: unknown, r: MetaScanJob) => (
              <Button
                type="link"
                size="small"
                onClick={() => {
                  setActiveJob(r);
                  if (r.status === 'pending' || r.status === 'running') message.info('已恢复跟踪');
                }}
              >
                跟踪
              </Button>
            ),
          },
        ]}
      />
    </div>
  );

  return (
    <div
      className="page-enter"
      style={{
        padding: 16,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4} style={{ margin: 0 }}>
          元数据与标注
        </Title>
        <Space>
          {llm && !llm.configured ? (
            <Alert
              type="warning"
              showIcon
              style={{ padding: '4px 12px' }}
              message="LLM 未配置，智能分析不可用"
              action={
                <Button size="small" type="primary" onClick={() => navigate('/govops/llm')}>
                  去配置
                </Button>
              }
            />
          ) : (
            <Button onClick={() => navigate('/govops/llm')}>
              LLM 配置{llm?.configured ? ' ✓' : ''}
            </Button>
          )}
        </Space>
      </div>

      <Tabs
        activeKey={mainTab}
        onChange={setMainTab}
        style={{ flex: 1, minHeight: 0 }}
        items={[
          { key: 'catalog', label: '库目录', children: catalogPane },
          { key: 'standards', label: '标准项', children: standardsPane },
          { key: 'jobs', label: '作业中心', children: jobsPane },
        ]}
      />

      <Drawer
        title="标准标注"
        open={bindOpen}
        onClose={() => setBindOpen(false)}
        size={420}
        destroyOnHidden
        extra={
          <Button type="primary" onClick={() => void doBind()}>
            确认绑定
          </Button>
        }
      >
        <Paragraph type="secondary">将为 {bindTargetIds.length} 个字段绑定同一标准项（字段原绑定会被替换）</Paragraph>
        <Select
          style={{ width: '100%' }}
          value={bindStandardId}
          onChange={setBindStandardId}
          options={standards.map((s) => ({
            value: s.id,
            label: `${s.name} (${s.code}) · ${s.security_level}`,
          }))}
        />
        {bindStandardId ? (
          <div style={{ marginTop: 16 }}>
            {(() => {
              const s = standards.find((x) => x.id === bindStandardId);
              if (!s) return null;
              return (
                <Space orientation="vertical" size={4}>
                  <Text>安全等级：{s.security_level}</Text>
                  <Text>长度：{JSON.stringify(s.length_rule_json || {})}</Text>
                  <Text>质量：{JSON.stringify(s.quality_rule_json || {})}</Text>
                  <Text type="secondary">{s.description}</Text>
                </Space>
              );
            })()}
          </div>
        ) : null}
      </Drawer>

      <Modal
        title={editingStd ? '编辑标准项' : '新建标准项'}
        open={stdModal}
        onCancel={() => setStdModal(false)}
        onOk={() => void saveStd()}
        destroyOnHidden
        mask={{ closable: true }}
      >
        <Form form={stdForm} layout="vertical">
          <Form.Item name="code" label="编码" rules={[{ required: !editingStd }]}>
            <Input disabled={!!editingStd} placeholder="STD_MOBILE" />
          </Form.Item>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="手机号" />
          </Form.Item>
          <Form.Item name="security_level" label="安全等级" rules={[{ required: true }]}>
            <Select options={['L0', 'L1', 'L2', 'L3'].map((x) => ({ value: x, label: x }))} />
          </Form.Item>
          <Form.Item name="semantic_type" label="语义类型">
            <Input placeholder="phone / id_card / identifier" />
          </Form.Item>
          <Form.Item name="data_type_expect" label="期望数据类型">
            <Input placeholder="varchar" />
          </Form.Item>
          <Space>
            <Form.Item name="len_min" label="最小长度">
              <InputNumber />
            </Form.Item>
            <Form.Item name="len_max" label="最大长度">
              <InputNumber />
            </Form.Item>
          </Space>
          <Form.Item name="regex" label="质量正则">
            <Input placeholder="^1\\d{10}$" />
          </Form.Item>
          <Form.Item name="mask_rule" label="脱敏策略">
            <Input placeholder="mask_mid4" />
          </Form.Item>
          <Form.Item name="description" label="说明">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
