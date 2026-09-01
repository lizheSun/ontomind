import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  App as AntApp,
  Alert,
  Button,
  Drawer,
  Input,
  Progress,
  Select,
  Space,
  Steps,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import OntologyGraph from '../../../components/dataops/OntologyGraph';
import { listDataSources, listDatabases } from '../../../services/dataops.service';
import { listMetaTables } from '../../../services/metadata.service';
import {
  createBuildJob,
  createOntology,
  exportOntology,
  generateCQs,
  getBuildJob,
  getOntologyGraph,
  inferRelations,
  listCQs,
  listLinkTypes,
  listMappings,
  listObjectTypes,
  listOntologies,
  listVersions,
  ontologyErrMsg,
  publishOntology,
  reviewOntologyElements,
  verifyAllCQs,
} from '../../../services/ontology.service';
import type { DataSource } from '../../../types/dataops';
import type {
  GraphData,
  LinkType,
  ObjectType,
  Ontology,
  OntologyBuildJob,
  OntologyCQ,
  OntologyMapping,
  OntologyVersion,
  ReviewItem,
} from '../../../types/ontology';

const { Title, Text, Paragraph } = Typography;
const CTX = 'ontomind_ontology_ctx';

type Ctx = { oid?: number; sourceId?: number; database?: string };

function loadCtx(): Ctx {
  try {
    return JSON.parse(localStorage.getItem(CTX) || '{}') as Ctx;
  } catch {
    return {};
  }
}

function saveCtx(c: Ctx) {
  localStorage.setItem(CTX, JSON.stringify(c));
}

function statusTag(v: string) {
  const color = v === 'accepted' ? 'green' : v === 'draft' ? 'gold' : v === 'rejected' ? 'red' : 'default';
  return <Tag color={color}>{v}</Tag>;
}

export default function OntologyPage() {
  const { message, modal } = AntApp.useApp();
  const [list, setList] = useState<Ontology[]>([]);
  const [oid, setOid] = useState<number>();
  const [sources, setSources] = useState<DataSource[]>([]);
  const [sourceId, setSourceId] = useState<number>();
  const [databases, setDatabases] = useState<string[]>([]);
  const [database, setDatabase] = useState<string>();
  const [mode, setMode] = useState<'rules' | 'hybrid'>('rules');
  const [useFragment, setUseFragment] = useState(true);

  const [graph, setGraph] = useState<GraphData>({ nodes: [], edges: [] });
  const [types, setTypes] = useState<ObjectType[]>([]);
  const [links, setLinks] = useState<LinkType[]>([]);
  const [mappings, setMappings] = useState<OntologyMapping[]>([]);
  const [cqs, setCQs] = useState<OntologyCQ[]>([]);
  const [versions, setVersions] = useState<OntologyVersion[]>([]);
  const [job, setJob] = useState<OntologyBuildJob | null>(null);
  const [passRate, setPassRate] = useState<number | null>(null);
  const [metaTableCount, setMetaTableCount] = useState<number | null>(null);
  const [newName, setNewName] = useState('消金本体');
  const [buildOpen, setBuildOpen] = useState(false);
  const [tab, setTab] = useState('guide');
  const [selectedDraftKeys, setSelectedDraftKeys] = useState<React.Key[]>([]);
  const [busy, setBusy] = useState(false);

  const current = list.find((o) => o.id === oid);
  const drafts = useMemo(() => {
    const rows: Array<ReviewItem & { key: string; label: string; confidence: number; kind: string }> = [];
    for (const t of types.filter((x) => x.status === 'draft')) {
      rows.push({
        key: `object_type-${t.id}`,
        element_type: 'object_type',
        element_id: t.id,
        action: 'accept',
        label: t.display_name || t.key,
        confidence: t.confidence,
        kind: '类',
      });
    }
    for (const l of links.filter((x) => x.status === 'draft')) {
      rows.push({
        key: `link_type-${l.id}`,
        element_type: 'link_type',
        element_id: l.id,
        action: 'accept',
        label: `${l.from_key} → ${l.to_key}`,
        confidence: l.confidence,
        kind: '关系',
      });
    }
    for (const m of mappings.filter((x) => x.status === 'draft')) {
      rows.push({
        key: `mapping-${m.id}`,
        element_type: 'mapping',
        element_id: m.id,
        action: 'accept',
        label: `${m.element_key} ↔ ${m.table_name || '?'}.${m.column_name || '*'}`,
        confidence: m.confidence,
        kind: '映射',
      });
    }
    return rows;
  }, [types, links, mappings]);

  const step = useMemo(() => {
    if (!oid) return 0;
    if (!types.length) return 1;
    if (drafts.length) return 2;
    if (!mappings.some((m) => m.status === 'accepted') && mappings.length === 0) return 3;
    if (passRate == null && !cqs.length) return 4;
    if ((current?.current_version || 0) < 1) return 5;
    return 6;
  }, [oid, types.length, drafts.length, mappings, passRate, cqs.length, current]);

  const refresh = useCallback(async (id: number) => {
    const [g, t, l, m, cq, v] = await Promise.all([
      getOntologyGraph(id),
      listObjectTypes(id),
      listLinkTypes(id),
      listMappings(id),
      listCQs(id),
      listVersions(id),
    ]);
    setGraph(g);
    setTypes(t);
    setLinks(l);
    setMappings(m);
    setCQs(cq);
    setVersions(v);
  }, []);

  useEffect(() => {
    const ctx = loadCtx();
    void (async () => {
      const [ontos, srcs] = await Promise.all([listOntologies(), listDataSources()]);
      setList(ontos);
      setSources(srcs);
      const sid = ctx.sourceId && srcs.some((s) => s.id === ctx.sourceId) ? ctx.sourceId : srcs[0]?.id;
      setSourceId(sid);
      const id = ctx.oid && ontos.some((o) => o.id === ctx.oid) ? ctx.oid : ontos[0]?.id;
      if (id) {
        setOid(id);
        await refresh(id);
      }
    })().catch((e) => message.error(ontologyErrMsg(e, '加载失败')));
  }, [refresh, message]);

  useEffect(() => {
    if (!sourceId) return;
    void listDatabases(sourceId)
      .then((dbs) => {
        setDatabases(dbs);
        const ctx = loadCtx();
        setDatabase((prev) => {
          if (prev && dbs.includes(prev)) return prev;
          if (ctx.database && dbs.includes(ctx.database)) return ctx.database;
          return dbs[0];
        });
      })
      .catch(() => setDatabases([]));
  }, [sourceId]);

  useEffect(() => {
    if (oid || sourceId || database) saveCtx({ oid, sourceId, database });
  }, [oid, sourceId, database]);

  useEffect(() => {
    if (!sourceId || !database) {
      setMetaTableCount(null);
      return;
    }
    void listMetaTables({ source_id: sourceId, database })
      .then((rows) => setMetaTableCount(rows.length))
      .catch(() => setMetaTableCount(0));
  }, [sourceId, database]);

  useEffect(() => {
    if (!job || job.status === 'succeeded' || job.status === 'failed') return;
    const t = window.setInterval(() => {
      void getBuildJob(job.id)
        .then(async (j) => {
          setJob(j);
          if (j.status === 'succeeded' && oid) {
            await refresh(oid);
            setTab('review');
            message.success('构建完成，请审阅 draft 元素');
          }
          if (j.status === 'failed') message.error(j.error_detail || '构建失败');
        })
        .catch(() => undefined);
    }, 2000);
    return () => window.clearInterval(t);
  }, [job, oid, refresh, message]);

  const onCreate = async () => {
    try {
      setBusy(true);
      const slug = `${newName.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-${Date.now().toString().slice(-4)}`;
      const o = await createOntology({
        name: newName.trim() || '未命名本体',
        slug,
        domain: 'consumer_finance',
      });
      const rows = await listOntologies();
      setList(rows);
      setOid(o.id);
      await refresh(o.id);
      setTab('guide');
      message.success('本体已创建');
    } catch (e) {
      message.error(ontologyErrMsg(e, '创建失败'));
    } finally {
      setBusy(false);
    }
  };

  const onBuild = async () => {
    if (!oid) return;
    if (!sourceId || !database) {
      message.warning('请选择数据源与库（或仅用领域片段时也建议先选库）');
    }
    if (metaTableCount === 0 && !useFragment) {
      message.warning('该库尚无元数据快照，请先去「元数据与标注」扫描');
      return;
    }
    try {
      setBusy(true);
      const j = await createBuildJob(oid, {
        mode,
        batch_size: 8,
        reuse_domain_fragment: useFragment ? 'consumer_finance' : null,
        scope: sourceId && database ? { source_id: sourceId, database } : undefined,
      });
      setJob(j);
      setBuildOpen(false);
      setTab('guide');
      message.success('构建任务已启动');
    } catch (e) {
      message.error(ontologyErrMsg(e, '启动构建失败'));
    } finally {
      setBusy(false);
    }
  };

  const reviewItems = async (items: ReviewItem[]) => {
    if (!oid || !items.length) return;
    try {
      setBusy(true);
      const r = await reviewOntologyElements(oid, { items });
      message.success(`已更新 ${r.updated ?? items.length} 条`);
      setSelectedDraftKeys([]);
      await refresh(oid);
    } catch (e) {
      message.error(ontologyErrMsg(e, '审阅失败'));
    } finally {
      setBusy(false);
    }
  };

  const acceptAllDrafts = async () => {
    if (!oid) return;
    try {
      setBusy(true);
      const r = await reviewOntologyElements(oid, { accept_all_drafts: true });
      message.success(`已采纳 ${r.updated ?? 0} 条 draft`);
      await refresh(oid);
    } catch (e) {
      message.error(ontologyErrMsg(e, '批量采纳失败'));
    } finally {
      setBusy(false);
    }
  };

  const onPublish = async () => {
    if (!oid) return;
    const accepted = types.filter((t) => t.status === 'accepted').length;
    if (!accepted) {
      message.warning('没有已采纳的类，请先审阅 draft 或构建');
      setTab('review');
      return;
    }
    if (drafts.length) {
      modal.confirm({
        title: `还有 ${drafts.length} 条 draft 未处理`,
        content: '可先一键采纳全部 draft，再发布；或仅发布已 accepted 的元素。',
        okText: '采纳全部并发布',
        cancelText: '仅发布已采纳',
        onOk: async () => {
          await acceptAllDrafts();
          await doPublish();
        },
        onCancel: () => void doPublish(),
      });
      return;
    }
    await doPublish();
  };

  const doPublish = async () => {
    if (!oid) return;
    try {
      setBusy(true);
      const v = await publishOntology(oid, `发布 ${new Date().toLocaleString()}`);
      setList(await listOntologies());
      await refresh(oid);
      message.success(`已发布 v${v.version}`);
      setTab('versions');
    } catch (e) {
      message.error(ontologyErrMsg(e, '发布失败'));
    } finally {
      setBusy(false);
    }
  };

  const onCQ = async () => {
    if (!oid) return;
    try {
      setBusy(true);
      await generateCQs(oid, 'rules');
      const r = await verifyAllCQs(oid);
      setPassRate(typeof r.pass_rate === 'number' ? r.pass_rate : null);
      setCQs(await listCQs(oid));
      setTab('cq');
      message.success('CQ 已生成并校验');
    } catch (e) {
      message.error(ontologyErrMsg(e, 'CQ 失败'));
    } finally {
      setBusy(false);
    }
  };

  const onInfer = async () => {
    if (!oid || !sourceId || !database) {
      message.warning('推断关系需要选择数据源与库');
      return;
    }
    try {
      setBusy(true);
      await inferRelations(oid, { source_id: sourceId, database });
      await refresh(oid);
      message.success('关系推断完成');
      setTab('links');
    } catch (e) {
      message.error(ontologyErrMsg(e, '推断失败'));
    } finally {
      setBusy(false);
    }
  };

  const guidePane = (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Steps
        size="small"
        current={Math.min(step, 5)}
        items={[
          { title: '创建本体' },
          { title: '选库构建' },
          { title: '审阅 draft' },
          { title: '映射/关系' },
          { title: 'CQ 验收' },
          { title: '发布导出' },
        ]}
      />

      <Alert
        type="info"
        showIcon
        message="推荐闭环"
        description={
          <div>
            <Paragraph style={{ marginBottom: 8 }}>
              1) 在「元数据与标注」扫描目标库 → 2) 本页新建本体 → 3) 选择同一数据源/库并构建（可带消金领域片段）→ 4)
              审阅 draft → 5) 可选推断关系 → 6) CQ 验收 → 7) 发布版本并导出。
            </Paragraph>
            <Space wrap>
              <Link to="/dataops/catalog/biz-systems">打开元数据与标注</Link>
              <Text type="secondary">|</Text>
              <Text type="secondary">
                当前库元数据表数：{metaTableCount == null ? '—' : metaTableCount}
                {metaTableCount === 0 ? '（需先扫描）' : ''}
              </Text>
            </Space>
          </div>
        }
      />

      <div style={{ background: 'var(--bg-elevated, #fff)', borderRadius: 12, padding: 16 }}>
        <Space wrap align="start">
          <div>
            <Text type="secondary">数据源</Text>
            <br />
            <Select
              style={{ width: 200 }}
              value={sourceId}
              onChange={setSourceId}
              options={sources.map((s) => ({ value: s.id, label: s.name }))}
              placeholder="选择数据源"
            />
          </div>
          <div>
            <Text type="secondary">库</Text>
            <br />
            <Select
              style={{ width: 160 }}
              value={database}
              onChange={setDatabase}
              options={databases.map((d) => ({ value: d, label: d }))}
              placeholder="选择库"
              showSearch
            />
          </div>
          <div>
            <Text type="secondary">构建模式</Text>
            <br />
            <Select
              style={{ width: 120 }}
              value={mode}
              onChange={setMode}
              options={[
                { value: 'rules', label: 'rules' },
                { value: 'hybrid', label: 'hybrid' },
              ]}
            />
          </div>
          <div>
            <Text type="secondary">消金片段</Text>
            <br />
            <Select
              style={{ width: 120 }}
              value={useFragment ? 'yes' : 'no'}
              onChange={(v) => setUseFragment(v === 'yes')}
              options={[
                { value: 'yes', label: '启用' },
                { value: 'no', label: '关闭' },
              ]}
            />
          </div>
          <Button type="primary" disabled={!oid} loading={busy} onClick={() => setBuildOpen(true)} style={{ marginTop: 18 }}>
            开始构建
          </Button>
        </Space>
      </div>

      {job ? (
        <div style={{ background: '#fff', borderRadius: 12, padding: 12 }}>
          <Space>
            <Text>
              作业 #{job.id} · {job.phase || '—'} · {job.status}
            </Text>
            {job.error_detail ? <Text type="danger">{job.error_detail}</Text> : null}
          </Space>
          <Progress
            percent={Math.round((job.progress || 0) * 100)}
            status={job.status === 'failed' ? 'exception' : job.status === 'succeeded' ? 'success' : 'active'}
            size="small"
          />
        </div>
      ) : null}

      <Space wrap>
        <Tag>类 {types.length}（draft {types.filter((t) => t.status === 'draft').length}）</Tag>
        <Tag>关系 {links.length}</Tag>
        <Tag>映射 {mappings.length}</Tag>
        <Tag>CQ {cqs.length}</Tag>
        {passRate != null ? <Tag color="green">CQ 通过率 {Math.round(passRate * 100)}%</Tag> : null}
        {current ? <Tag color="blue">已发布 v{current.current_version}</Tag> : null}
      </Space>
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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <Space wrap>
          <Title level={4} style={{ margin: 0 }}>
            本体建模
          </Title>
          <Select
            style={{ minWidth: 200 }}
            value={oid}
            placeholder="选择本体"
            onChange={(v) => {
              setOid(v);
              void refresh(v);
            }}
            options={list.map((o) => ({ value: o.id, label: `${o.name} · v${o.current_version}` }))}
          />
          {current ? <Tag>v{current.current_version}</Tag> : null}
        </Space>
        <Space wrap>
          <Input
            style={{ width: 140 }}
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="新本体名称"
          />
          <Button loading={busy} onClick={() => void onCreate()}>
            新建
          </Button>
          <Button type="primary" disabled={!oid} onClick={() => setBuildOpen(true)}>
            构建
          </Button>
          <Button disabled={!oid} loading={busy} onClick={() => void acceptAllDrafts()}>
            采纳全部 draft
          </Button>
          <Button disabled={!oid} loading={busy} onClick={() => void onPublish()}>
            发布
          </Button>
          <Button
            disabled={!oid}
            onClick={async () => {
              if (!oid) return;
              try {
                const text = await exportOntology(oid, 'turtle');
                await navigator.clipboard.writeText(text);
                message.success('Turtle 已复制到剪贴板');
              } catch (e) {
                message.error(ontologyErrMsg(e, '导出失败'));
              }
            }}
          >
            导出
          </Button>
          <Button disabled={!oid} loading={busy} onClick={() => void onCQ()}>
            CQ 验收
          </Button>
        </Space>
      </div>

      <div style={{ flex: 1, minHeight: 0, background: '#fff', borderRadius: 12, padding: 12, overflow: 'auto' }}>
        <Tabs
          activeKey={tab}
          onChange={setTab}
          items={[
            { key: 'guide', label: '流程引导', children: guidePane },
            {
              key: 'graph',
              label: `图视图 (${graph.nodes.length})`,
              children: (
                <div style={{ height: 'calc(100vh - 220px)', minHeight: 420 }}>
                  <OntologyGraph data={graph} refreshKey={`${oid}-${graph.nodes.length}-${graph.edges.length}`} />
                </div>
              ),
            },
            {
              key: 'review',
              label: `待审 (${drafts.length})`,
              children: (
                <div>
                  <Space style={{ marginBottom: 12 }}>
                    <Button
                      type="primary"
                      disabled={!selectedDraftKeys.length}
                      onClick={() => {
                        const items = drafts
                          .filter((d) => selectedDraftKeys.includes(d.key))
                          .map((d) => ({
                            element_type: d.element_type,
                            element_id: d.element_id,
                            action: 'accept' as const,
                          }));
                        void reviewItems(items);
                      }}
                    >
                      采纳所选
                    </Button>
                    <Button
                      danger
                      disabled={!selectedDraftKeys.length}
                      onClick={() => {
                        const items = drafts
                          .filter((d) => selectedDraftKeys.includes(d.key))
                          .map((d) => ({
                            element_type: d.element_type,
                            element_id: d.element_id,
                            action: 'reject' as const,
                          }));
                        void reviewItems(items);
                      }}
                    >
                      驳回所选
                    </Button>
                    <Button onClick={() => void acceptAllDrafts()}>全部采纳</Button>
                  </Space>
                  <Table
                    size="small"
                    rowKey="key"
                    dataSource={drafts}
                    rowSelection={{
                      selectedRowKeys: selectedDraftKeys,
                      onChange: setSelectedDraftKeys,
                    }}
                    locale={{ emptyText: '没有 draft。构建后置信度中等的元素会出现在这里。' }}
                    columns={[
                      { title: '类型', dataIndex: 'kind', width: 70 },
                      { title: '内容', dataIndex: 'label' },
                      {
                        title: '置信度',
                        dataIndex: 'confidence',
                        width: 90,
                        render: (v: number) => (
                          <Tag color={v >= 0.85 ? 'green' : 'gold'}>{v.toFixed(2)}</Tag>
                        ),
                      },
                    ]}
                  />
                </div>
              ),
            },
            {
              key: 'types',
              label: `类 (${types.length})`,
              children: (
                <Table
                  size="small"
                  rowKey="id"
                  dataSource={types}
                  columns={[
                    { title: 'key', dataIndex: 'key', width: 160 },
                    { title: '名称', dataIndex: 'display_name' },
                    { title: '父类', dataIndex: 'parent_key', width: 120 },
                    {
                      title: '置信度',
                      dataIndex: 'confidence',
                      width: 90,
                      render: (v: number) => (
                        <Tag color={v >= 0.85 ? 'green' : 'gold'}>{Number(v).toFixed(2)}</Tag>
                      ),
                    },
                    { title: '状态', dataIndex: 'status', width: 100, render: statusTag },
                    { title: '来源', dataIndex: 'source', width: 80 },
                  ]}
                />
              ),
            },
            {
              key: 'links',
              label: `关系 (${links.length})`,
              children: (
                <div>
                  <Button style={{ marginBottom: 12 }} loading={busy} onClick={() => void onInfer()}>
                    推断关系（需已选库）
                  </Button>
                  <Table
                    size="small"
                    rowKey="id"
                    dataSource={links}
                    columns={[
                      { title: 'key', dataIndex: 'key', width: 140 },
                      { title: 'from', dataIndex: 'from_key', width: 120 },
                      { title: 'to', dataIndex: 'to_key', width: 120 },
                      { title: '基数', dataIndex: 'cardinality', width: 80 },
                      {
                        title: '置信度',
                        dataIndex: 'confidence',
                        width: 90,
                        render: (v: number) => Number(v).toFixed(2),
                      },
                      { title: '状态', dataIndex: 'status', width: 100, render: statusTag },
                    ]}
                  />
                </div>
              ),
            },
            {
              key: 'mappings',
              label: `映射 (${mappings.length})`,
              children: (
                <Table
                  size="small"
                  rowKey="id"
                  dataSource={mappings}
                  locale={{ emptyText: '暂无映射。带 scope 构建后，物理表列会映射到本体元素。' }}
                  columns={[
                    { title: '元素', dataIndex: 'element_key', width: 140 },
                    { title: '类型', dataIndex: 'element_type', width: 100 },
                    { title: '库', dataIndex: 'database', width: 100 },
                    { title: '表', dataIndex: 'table_name', width: 140 },
                    { title: '列', dataIndex: 'column_name', width: 120 },
                    { title: '状态', dataIndex: 'status', width: 100, render: statusTag },
                  ]}
                />
              ),
            },
            {
              key: 'cq',
              label: `CQ (${cqs.length})`,
              children: (
                <div>
                  <Space style={{ marginBottom: 12 }}>
                    <Button type="primary" loading={busy} onClick={() => void onCQ()}>
                      生成并校验
                    </Button>
                    {passRate != null ? (
                      <Tag color={passRate >= 0.6 ? 'green' : 'orange'}>
                        通过率 {Math.round(passRate * 100)}%
                      </Tag>
                    ) : null}
                  </Space>
                  <Table
                    size="small"
                    rowKey="id"
                    dataSource={cqs}
                    columns={[
                      { title: '问题', dataIndex: 'question' },
                      {
                        title: '结果',
                        dataIndex: 'verify_status',
                        width: 90,
                        render: (v: string) => (
                          <Tag color={v === 'pass' ? 'green' : v === 'fail' ? 'red' : 'default'}>{v}</Tag>
                        ),
                      },
                      { title: '说明', dataIndex: 'verify_note', ellipsis: true },
                    ]}
                  />
                </div>
              ),
            },
            {
              key: 'versions',
              label: `版本 (${versions.length})`,
              children: (
                <Table
                  size="small"
                  rowKey="id"
                  dataSource={versions}
                  columns={[
                    { title: '版本', dataIndex: 'version', width: 80 },
                    { title: '说明', dataIndex: 'change_note' },
                    { title: '时间', dataIndex: 'created_at', width: 180 },
                  ]}
                />
              ),
            },
          ]}
        />
      </div>

      <Drawer
        title="构建本体"
        open={buildOpen}
        onClose={() => setBuildOpen(false)}
        size={420}
        destroyOnHidden
        extra={
          <Button type="primary" loading={busy} onClick={() => void onBuild()}>
            启动
          </Button>
        }
      >
        <Paragraph type="secondary">
          按批 delta 构建：extract → align → judge → merge。建议选择已扫描的库；无库时仅注入消金领域片段。
        </Paragraph>
        <Space orientation="vertical" style={{ width: '100%' }} size={12}>
          <div>
            <Text>数据源</Text>
            <Select
              style={{ width: '100%', marginTop: 4 }}
              value={sourceId}
              onChange={setSourceId}
              options={sources.map((s) => ({ value: s.id, label: s.name }))}
            />
          </div>
          <div>
            <Text>数据库</Text>
            <Select
              style={{ width: '100%', marginTop: 4 }}
              value={database}
              onChange={setDatabase}
              options={databases.map((d) => ({ value: d, label: d }))}
              showSearch
            />
          </div>
          <div>
            <Text>模式</Text>
            <Select
              style={{ width: '100%', marginTop: 4 }}
              value={mode}
              onChange={setMode}
              options={[
                { value: 'rules', label: 'rules（无需 LLM）' },
                { value: 'hybrid', label: 'hybrid（需 LLM 配置）' },
              ]}
            />
          </div>
          <div>
            <Text>消金领域片段</Text>
            <Select
              style={{ width: '100%', marginTop: 4 }}
              value={useFragment ? 'yes' : 'no'}
              onChange={(v) => setUseFragment(v === 'yes')}
              options={[
                { value: 'yes', label: '启用（推荐）' },
                { value: 'no', label: '关闭' },
              ]}
            />
          </div>
          {metaTableCount === 0 ? (
            <Alert
              type="warning"
              showIcon
              message="该库尚无 meta 快照"
              action={
                <Link to="/dataops/catalog/biz-systems">
                  <Button size="small">去扫描</Button>
                </Link>
              }
            />
          ) : (
            <Alert type="success" showIcon message={`已发现 ${metaTableCount} 张元数据表可参与构建`} />
          )}
        </Space>
      </Drawer>
    </div>
  );
}
