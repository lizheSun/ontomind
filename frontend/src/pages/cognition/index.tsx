import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Card, Button, Table, Tag, Space, Select, Tabs, Drawer, message, Spin,
  Empty, Modal, Switch, Descriptions, Typography, Popconfirm, Collapse,
} from 'antd';
import {
  ThunderboltOutlined, NodeIndexOutlined, DownloadOutlined,
  ReloadOutlined, RobotOutlined, ApartmentOutlined,
  ExportOutlined, EyeOutlined, DeleteOutlined, BookOutlined,
} from '@ant-design/icons';
import { cognitionAPI, perceptionAPI, resourcesAPI, llmAPI } from '../../services';
import OntologyGraph from './OntologyGraph';

const { Text } = Typography;

const METHOD_OPTIONS = [
  { value: 'rules', label: '📐 确定性规则（仅 schema）' },
  { value: 'llm', label: '🤖 平台 LLM 增强' },
  { value: 'agent', label: '🦾 Agent 增强（带私有知识）' },
];

const SEVERITY_COLOR: Record<string, string> = {
  info: '#60a5fa', warn: '#fbbf24', error: '#fb7185',
};
const SOURCE_COLOR: Record<string, string> = {
  schema: '#60a5fa', profile: '#34d399', llm: '#a78bfa', agent: '#ec4899',
};

export default function Cognition() {
  const [dataSources, setDataSources] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [llmConfigs, setLlmConfigs] = useState<any[]>([]);

  const [selectedDs, setSelectedDs] = useState<number | undefined>(undefined);
  const [versions, setVersions] = useState<any[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<number | undefined>(undefined);

  const [graphData, setGraphData] = useState<{ nodes: any[]; edges: any[] } | null>(null);
  const [entities, setEntities] = useState<any[]>([]);
  const [relationships, setRelationships] = useState<any[]>([]);
  const [constraints, setConstraints] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  // 构建
  const [buildOpen, setBuildOpen] = useState(false);
  const [buildForm, setBuildForm] = useState({ method: 'rules', llmConfigId: undefined as number | undefined, agentId: undefined as number | undefined, useJudge: false, stream: false });
  const [building, setBuilding] = useState(false);
  const [buildDrawerOpen, setBuildDrawerOpen] = useState(false);
  const [buildEvents, setBuildEvents] = useState<any[]>([]);
  const buildWsRef = useRef<WebSocket | null>(null);

  // 实体详情抽屉
  const [entityDrawer, setEntityDrawer] = useState(false);
  const [selEntity, setSelEntity] = useState<any>(null);

  const classMap = (): Record<number, any> => {
    const m: Record<number, any> = {};
    entities.forEach((e) => (m[e.id] = e));
    return m;
  };
  const propMap = (): Record<number, any> => {
    const m: Record<number, any> = {};
    entities.forEach((e) => (e.properties || []).forEach((p: any) => (m[p.id] = p)));
    return m;
  };
  const relMap = (): Record<number, any> => {
    const m: Record<number, any> = {};
    relationships.forEach((r) => (m[r.id] = r));
    return m;
  };

  useEffect(() => {
    perceptionAPI.listDataSources().then((res) => {
      const ds = res.data?.data || res.data || [];
      setDataSources(ds);
      if (ds.length && selectedDs === undefined) setSelectedDs(ds[0].id);
    }).catch(() => message.error('加载数据源失败'));
    resourcesAPI.listAgents({ skip: 0, limit: 200 }).then((res) => setAgents(res.data?.data || [])).catch(() => {});
    llmAPI.listConfigs().then((res) => setLlmConfigs(res.data?.data || res.data || [])).catch(() => {});
  }, []);

  const loadVersions = useCallback(async (dsId: number) => {
    try {
      const res = await cognitionAPI.listVersions(dsId);
      const vs = res.data?.data || [];
      setVersions(vs);
      if (vs.length && selectedVersionId === undefined) {
        setSelectedVersionId(vs[0].id);
        loadVersionContent(vs[0].id);
      }
    } catch { /* ignore */ }
  }, [selectedVersionId]);

  useEffect(() => {
    if (selectedDs !== undefined) loadVersions(selectedDs);
  }, [selectedDs, loadVersions]);

  const loadVersionContent = useCallback(async (vid: number) => {
    setLoading(true);
    try {
      const [g, e, r, c] = await Promise.all([
        cognitionAPI.getGraph(vid),
        cognitionAPI.getEntities(vid),
        cognitionAPI.getRelationships(vid),
        cognitionAPI.getConstraints(vid),
      ]);
      setGraphData(g.data?.data || null);
      setEntities(e.data?.data || []);
      setRelationships(r.data?.data || []);
      setConstraints(c.data?.data || []);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '加载本体内容失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedVersionId !== undefined) loadVersionContent(selectedVersionId);
  }, [selectedVersionId, loadVersionContent]);

  const handleDeleteVersion = async (id: number) => {
    try {
      await cognitionAPI.deleteVersion(id);
      message.success('已删除');
      if (selectedVersionId === id) setSelectedVersionId(undefined);
      if (selectedDs !== undefined) loadVersions(selectedDs);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '删除失败');
    }
  };

  const doBuild = async () => {
    if (selectedDs === undefined) { message.warning('请先选择数据源'); return; }
    setBuildOpen(false);
    const payload = {
      datasource_id: selectedDs,
      method: buildForm.method,
      llm_config_id: buildForm.method === 'llm' ? buildForm.llmConfigId : undefined,
      agent_id: buildForm.method === 'agent' ? buildForm.agentId : undefined,
      use_judge: buildForm.useJudge,
    };
    if (!buildForm.stream) {
      setBuilding(true);
      try {
        const res = await cognitionAPI.build(payload);
        const v = res.data?.data;
        message.success('构建完成');
        setSelectedVersionId(v.id);
        await loadVersions(selectedDs);
        await loadVersionContent(v.id);
      } catch (err: any) {
        message.error(err?.response?.data?.detail || '构建失败');
      } finally {
        setBuilding(false);
      }
      return;
    }
    // 流式
    setBuildDrawerOpen(true);
    setBuildEvents([]);
    setBuilding(true);
    const ws = new WebSocket(cognitionAPI.buildStreamUrl());
    buildWsRef.current = ws;
    ws.onopen = () => ws.send(JSON.stringify(payload));
    ws.onmessage = (ev) => {
      try {
        const evt = JSON.parse(ev.data);
        setBuildEvents((prev) => [...prev, evt]);
        if (evt.type === 'result' && evt.content?.id) {
          message.success('构建完成');
          const newId = evt.content.id;
          setBuildDrawerOpen(false);
          setSelectedVersionId(newId);
          loadVersions(selectedDs).then(() => loadVersionContent(newId));
        }
        if (evt.type === 'error') message.error(evt.content);
        if (evt.type === 'done') setBuilding(false);
      } catch { /* ignore */ }
    };
    ws.onerror = () => { setBuildEvents((p) => [...p, { type: 'error', content: 'WebSocket 连接失败' }]); setBuilding(false); };
    ws.onclose = () => setBuilding(false);
  };

  const handleExport = async (fmt: string) => {
    if (selectedVersionId === undefined) { message.warning('请先选择版本'); return; }
    try {
      const res = await cognitionAPI.exportOntology(selectedVersionId, fmt);
      const { content, filename } = res.data?.data || {};
      const mime = fmt === 'json' ? 'application/json' : 'text/turtle';
      const blob = new Blob([content], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = filename || `ontology.${fmt}`;
      a.click();
      URL.revokeObjectURL(url);
      message.success(`已导出 ${fmt.toUpperCase()}`);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '导出失败');
    }
  };

  const openEntity = (e: any) => { setSelEntity(e); setEntityDrawer(true); };

  const curVersion = versions.find((v) => v.id === selectedVersionId);
  const stats = curVersion?.stats ? (typeof curVersion.stats === 'string' ? JSON.parse(curVersion.stats) : curVersion.stats) : null;

  const entityCols = [
    { title: '类名', dataIndex: 'local_name', key: 'ln', render: (t: string, r: any) => <Space><ApartmentOutlined style={{ color: r.entity_type === 'enumeration' ? '#fbbf24' : '#3b82f6' }} /><b>{t}</b>{r.label ? <Text type="secondary" style={{ fontSize: 12 }}>{r.label}</Text> : null}</Space> },
    { title: '中文标签', dataIndex: 'label', key: 'label', render: (t: string) => t || '-' },
    { title: '业务域', dataIndex: 'domain', key: 'domain', width: 90, render: (d: string) => d ? <Tag style={{ borderRadius: 6, background: 'rgba(96,165,250,0.12)', color: '#60a5fa', border: 'none' }}>{d}</Tag> : '-' },
    { title: '类型', dataIndex: 'entity_type', key: 'et', width: 100, render: (t: string) => <Tag style={{ borderRadius: 6, background: 'rgba(167,139,250,0.12)', color: '#a78bfa', border: 'none' }}>{t || 'class'}</Tag> },
    { title: '属性数', key: 'pc', width: 70, render: (_: any, r: any) => <Text style={{ color: '#8895b4' }}>{(r.properties || []).length}</Text> },
    { title: '置信度', dataIndex: 'confidence', key: 'conf', width: 80, render: (c: number) => c != null ? `${Math.round(c * 100)}%` : '-' },
    { title: '操作', key: 'act', width: 70, render: (_: any, r: any) => <Button size="small" type="link" icon={<EyeOutlined />} onClick={() => openEntity(r)}>详情</Button> },
  ];
  const relCols = [
    { title: '关系名', dataIndex: 'name', key: 'name', render: (t: string) => <Tag style={{ borderRadius: 6, background: 'rgba(59,130,246,0.12)', color: '#60a5fa', border: 'none' }}>{t}</Tag> },
    { title: '主体', dataIndex: 'from_class_id', key: 'from', render: (id: number) => classMap()[id]?.label || classMap()[id]?.local_name || id },
    { title: '客体', dataIndex: 'to_class_id', key: 'to', render: (id: number) => classMap()[id]?.label || classMap()[id]?.local_name || id },
    { title: '基数', dataIndex: 'cardinality', key: 'card', width: 80, render: (c: string) => <Text style={{ color: '#8895b4', fontFamily: 'monospace' }}>{c}</Text> },
    { title: '置信度', dataIndex: 'confidence', key: 'conf', width: 80, render: (c: number) => c != null ? `${Math.round(c * 100)}%` : '-' },
  ];
  const consCols = [
    { title: '约束类型', dataIndex: 'constraint_type', key: 'ct', render: (t: string) => <Tag style={{ borderRadius: 6, background: 'rgba(255,255,255,0.06)', color: '#e8eef5', border: 'none' }}>{t}</Tag> },
    {
      title: '作用对象', key: 'target', render: (_: any, r: any) => {
        if (r.target_type === 'class') { const c = classMap()[r.target_id]; return c ? `类: ${c.label || c.local_name}` : `类#${r.target_id}`; }
        if (r.target_type === 'property') { const p = propMap()[r.target_id]; return p ? `属性: ${p.name}` : `属性#${r.target_id}`; }
        const rel = relMap()[r.target_id]; return rel ? `关系: ${rel.name}` : `关系#${r.target_id}`;
      },
    },
    { title: '表达式', dataIndex: 'expression', key: 'exp', ellipsis: true, render: (e: any) => <Text style={{ fontSize: 12, color: '#8895b4', fontFamily: 'monospace' }}>{typeof e === 'string' ? e : JSON.stringify(e)}</Text> },
    { title: '来源', dataIndex: 'source', key: 'src', width: 90, render: (s: string) => <Tag style={{ borderRadius: 6, background: `${SOURCE_COLOR[s] || '#60a5fa'}22`, color: SOURCE_COLOR[s] || '#60a5fa', border: 'none' }}>{s}</Tag> },
    { title: '级别', dataIndex: 'severity', key: 'sev', width: 80, render: (s: string) => <Tag style={{ borderRadius: 6, background: `${SEVERITY_COLOR[s] || '#60a5fa'}22`, color: SEVERITY_COLOR[s] || '#60a5fa', border: 'none' }}>{s}</Tag> },
  ];

  return (
    <div>
      {/* 头部 + 构建控制栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h2 style={{ color: '#e8eef5', fontSize: 20, fontWeight: 700, margin: 0, letterSpacing: -0.3 }}>
            认知层 · 本体自动构建
          </h2>
          <p style={{ color: '#506380', margin: '4px 0 0', fontSize: 12 }}>
            从库表结构抽取实体/关系/约束，组装可版本化本体与图谱
          </p>
        </div>
        <Space wrap>
          <Select
            style={{ width: 200 }}
            placeholder="选择数据源"
            value={selectedDs}
            onChange={(v) => { setSelectedDs(v); setSelectedVersionId(undefined); setGraphData(null); setEntities([]); setRelationships([]); setConstraints([]); }}
            options={dataSources.map((d) => ({ value: d.id, label: d.name }))}
          />
          <Select
            style={{ width: 220 }}
            placeholder="选择本体版本"
            value={selectedVersionId}
            onChange={(v) => setSelectedVersionId(v)}
            options={versions.map((v) => ({ value: v.id, label: `${v.name}（${v.status}）` }))}
          />
          <Button icon={<ReloadOutlined />} type="text" style={{ color: '#8895b4' }} onClick={() => selectedDs !== undefined && loadVersions(selectedDs)} loading={loading} />
          <Popconfirm title="确定删除该版本？" onConfirm={() => selectedVersionId && handleDeleteVersion(selectedVersionId)} okText="删除" cancelText="取消">
            <Button icon={<DeleteOutlined />} danger type="text" disabled={!selectedVersionId} style={{ color: '#fb7185' }} />
          </Popconfirm>
          <Button type="primary" icon={<ThunderboltOutlined />} onClick={() => setBuildOpen(true)} style={{ borderRadius: 10, background: 'linear-gradient(135deg,#3b82f6,#8b5cf6)', border: 'none' }} loading={building}>
            构建本体
          </Button>
          <Button icon={<DownloadOutlined />} onClick={() => handleExport('turtle')} disabled={!selectedVersionId} style={{ borderRadius: 10 }}>
            导出 OWL
          </Button>
          <Button icon={<ExportOutlined />} onClick={() => handleExport('json')} disabled={!selectedVersionId} style={{ borderRadius: 10 }}>
            导出 JSON
          </Button>
        </Space>
      </div>

      <Collapse
        ghost
        defaultActiveKey={[]}
        style={{
          marginBottom: 16,
          background: 'rgba(255,255,255,0.03)',
          borderRadius: 12,
          border: '1px solid rgba(255,255,255,0.06)',
        }}
        items={[{
          key: 'plan',
          label: (
            <Space>
              <BookOutlined style={{ color: '#a78bfa' }} />
              <span style={{ color: '#e8eef5', fontWeight: 600 }}>本体自动构建方案</span>
              <span style={{ color: '#506380', fontSize: 12 }}>三段式流水线 · 点击展开</span>
            </Space>
          ),
          children: (
            <div style={{ color: '#8895b4', fontSize: 13, lineHeight: 1.85 }}>
              <p style={{ color: '#e8eef5', margin: '0 0 8px', fontWeight: 600 }}>三段式流水线（借鉴 2025 RIGOR 论文：上下文检索 → 生成 → Judge 校验）</p>
              <p style={{ margin: '0 0 6px' }}><b style={{ color: '#60a5fa' }}>Step 1 · 确定性抽取（rules）</b>：零 LLM 成本，纯结构驱动。</p>
              <p style={{ margin: '0 0 6px', paddingLeft: 12 }}>表 → 本体类；字段 → 数据属性（映射到 xsd 类型）；外键 → 对象属性 + 关系（基数由可空性推断 0..1 / 1）。</p>
              <p style={{ margin: '0 0 6px', paddingLeft: 12 }}>约束来自 schema 与<b>数据画像</b>：非空 → 必填基数 cardinality；唯一 → 函数性 functional；枚举 → 枚举约束 enum；email/phone/url → pattern；数值/日期 → 值域 range。</p>
              <p style={{ margin: '0 0 6px' }}><b style={{ color: '#a78bfa' }}>Step 2 · 语义增强（llm / agent，可选）</b>：将整库 schema 摘要喂给平台 LLM 或 Agent。</p>
              <p style={{ margin: '0 0 6px', paddingLeft: 12 }}>在不改类名前提下精化中文标签 / 定义 / 业务域；补充 schema 外键未体现的语义关系（如 belongsTo / contains）。Agent 可携带私有知识上下文。</p>
              <p style={{ margin: '0 0 6px' }}><b style={{ color: '#fbbf24' }}>Step 3 · Judge 校验（可选）</b>：用 LLM 审查本体一致性。</p>
              <p style={{ margin: '0 0 10px', paddingLeft: 12 }}>检查错误实体定义 / 关系方向、冗余关系、基数合理性，产出问题清单（计入"校验建议"统计）。</p>
              <p style={{ color: '#e8eef5', margin: '0 0 6px', fontWeight: 600 }}>三种构建方式</p>
              <p style={{ margin: '0 0 10px', paddingLeft: 12 }}>
                <Tag style={{ background: 'rgba(96,165,250,0.12)', color: '#60a5fa', border: 'none' }}>规则</Tag> 仅 Step 1，最快零成本；
                <Tag style={{ background: 'rgba(167,139,250,0.12)', color: '#a78bfa', border: 'none' }}>平台 LLM</Tag> Step 1+2；
                <Tag style={{ background: 'rgba(236,72,153,0.12)', color: '#ec4899', border: 'none' }}>Agent</Tag> Step 1+2（带私有知识）。
                勾选"Judge-LLM 一致性校验"启用 Step 3。
              </p>
              <p style={{ margin: 0, color: '#506380' }}>操作：选择数据源 → 点击「构建本体」→ 选择方式 →（可选）Judge → 开始构建。产物以版本组织，可导出 OWL/Turtle 或 JSON。</p>
            </div>
          ),
        }]}
      />

      {stats && (
        <Space style={{ marginBottom: 16 }} wrap>
          <StatChip label="实体" value={stats.entity} color="#3b82f6" />
          <StatChip label="关系" value={stats.relationship} color="#8b5cf6" />
          <StatChip label="属性" value={stats.property} color="#34d399" />
          <StatChip label="约束" value={stats.constraint} color="#fbbf24" />
          {stats.judge_issues != null && <StatChip label="校验建议" value={stats.judge_issues} color="#fb7185" />}
        </Space>
      )}

      {!selectedVersionId ? (
        <Card style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)' }}>
          <Empty description="请选择数据源并构建本体，或选择一个已有版本" style={{ padding: '60px 0' }} />
        </Card>
      ) : (
        <Tabs
          items={[
            {
              key: 'graph',
              label: <span><NodeIndexOutlined /> 本体图谱</span>,
              children: (
                <Card
                  style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)', height: 560 }}
                  styles={{ body: { height: '100%', padding: 0, background: 'radial-gradient(ellipse at center, rgba(139,92,246,0.04) 0%, transparent 70%)' } }}
                >
                  {loading ? <div style={{ textAlign: 'center', paddingTop: 240 }}><Spin size="large" /></div>
                    : graphData && graphData.nodes.length ? (
                      <OntologyGraph data={graphData} onNodeClick={(n) => { const e = entities.find((x) => `c${x.id}` === n.id); if (e) openEntity(e); }} />
                    ) : <Empty description="暂无图谱数据" style={{ paddingTop: 200 }} />}
                </Card>
              ),
            },
            {
              key: 'entities',
              label: <span><ApartmentOutlined /> 实体（{entities.length}）</span>,
              children: <Card style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)' }}><Table columns={entityCols} dataSource={entities} rowKey="id" loading={loading} pagination={{ pageSize: 12, size: 'small' }} onRow={(r) => ({ onClick: () => openEntity(r), style: { cursor: 'pointer' } })} /></Card>,
            },
            {
              key: 'rels',
              label: <span>关系（{relationships.length}）</span>,
              children: <Card style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)' }}><Table columns={relCols} dataSource={relationships} rowKey="id" loading={loading} pagination={{ pageSize: 12, size: 'small' }} /></Card>,
            },
            {
              key: 'cons',
              label: <span>约束（{constraints.length}）</span>,
              children: <Card style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)' }}><Table columns={consCols} dataSource={constraints} rowKey="id" loading={loading} pagination={{ pageSize: 12, size: 'small' }} /></Card>,
            },
          ]}
        />
      )}

      {/* 构建配置弹窗 */}
      <Modal
        title={<Space><ThunderboltOutlined style={{ color: '#a78bfa' }} /><span>构建本体</span></Space>}
        open={buildOpen}
        onCancel={() => setBuildOpen(false)}
        onOk={doBuild}
        okText="开始构建"
        cancelText="取消"
        okButtonProps={{ style: { borderRadius: 10, background: 'linear-gradient(135deg,#3b82f6,#8b5cf6)', border: 'none' } }}
        cancelButtonProps={{ style: { borderRadius: 10 } }}
      >
        <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <Text style={{ color: '#8895b4', fontSize: 12 }}>构建方式</Text>
            <Select style={{ width: '100%', marginTop: 6 }} value={buildForm.method} onChange={(v) => setBuildForm((f) => ({ ...f, method: v }))} options={METHOD_OPTIONS} />
          </div>
          {buildForm.method === 'llm' && (
            <div>
              <Text style={{ color: '#8895b4', fontSize: 12 }}>平台 LLM 配置</Text>
              <Select style={{ width: '100%', marginTop: 6 }} placeholder="默认激活配置" value={buildForm.llmConfigId} onChange={(v) => setBuildForm((f) => ({ ...f, llmConfigId: v }))}
                options={llmConfigs.map((c: any) => ({ value: c.id, label: `${c.name}（${c.provider}）${c.is_active ? ' · 激活' : ''}` }))} />
            </div>
          )}
          {buildForm.method === 'agent' && (
            <div>
              <Text style={{ color: '#8895b4', fontSize: 12 }}>Agent（可带私有知识上下文）</Text>
              <Select style={{ width: '100%', marginTop: 6 }} placeholder="选择 Agent" value={buildForm.agentId} onChange={(v) => setBuildForm((f) => ({ ...f, agentId: v }))}
                options={agents.map((a: any) => ({ value: a.id, label: `${a.agent_type === 'openclaw' ? '🦞' : a.agent_type === 'opencode' ? '💻' : '🤖'} ${a.name}` }))} />
            </div>
          )}
          <Space size="large">
            <Space>
              <Switch checked={buildForm.useJudge} onChange={(v) => setBuildForm((f) => ({ ...f, useJudge: v }))} />
              <Text style={{ fontSize: 13 }}>Judge-LLM 一致性校验</Text>
            </Space>
            <Space>
              <Switch checked={buildForm.stream} onChange={(v) => setBuildForm((f) => ({ ...f, stream: v }))} />
              <Text style={{ fontSize: 13 }}>流式过程</Text>
            </Space>
          </Space>
        </div>
      </Modal>

      {/* 流式构建抽屉 */}
      <Drawer title={<Space><RobotOutlined style={{ color: '#a78bfa' }} /><span>构建过程</span></Space>} open={buildDrawerOpen} onClose={() => setBuildDrawerOpen(false)} styles={{ body: { padding: 12 }, wrapper: { width: 460 } }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {buildEvents.length === 0 && <Text type="secondary">等待构建开始...</Text>}
          {buildEvents.map((evt, i) => {
            let color = '#8895b4'; let bg = 'transparent'; let icon = '·';
            if (evt.type === 'status') { color = '#60a5fa'; bg = 'rgba(96,165,250,0.06)'; icon = '⏳'; }
            else if (evt.type === 'text') { color = '#34d399'; bg = 'rgba(52,211,153,0.04)'; icon = '💬'; }
            else if (evt.type === 'error') { color = '#f59e0b'; bg = 'rgba(245,158,11,0.06)'; icon = '⚠️'; }
            else if (evt.type === 'done') { color = '#34d399'; bg = 'rgba(52,211,153,0.08)'; icon = '✅'; }
            else if (evt.type === 'result') { color = '#34d399'; bg = 'rgba(52,211,153,0.06)'; icon = '📦'; }
            return (
              <div key={i} style={{ fontSize: 12, color, background: bg, padding: '6px 10px', borderRadius: 8, lineHeight: 1.5, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                <span style={{ marginRight: 6 }}>{icon}</span>{evt.content}
              </div>
            );
          })}
          {building && <Spin style={{ marginTop: 8 }} />}
        </div>
      </Drawer>

      {/* 实体详情抽屉 */}
      <Drawer title={<Space><ApartmentOutlined style={{ color: '#3b82f6' }} /><span>{selEntity?.label || selEntity?.local_name || '实体'}</span></Space>} open={entityDrawer} onClose={() => setEntityDrawer(false)} styles={{ body: { padding: 16 }, wrapper: { width: 640 } }}>
        {selEntity && (
          <div>
            <Descriptions column={1} size="small" style={{ marginBottom: 16, background: 'rgba(255,255,255,0.03)', borderRadius: 10, padding: 12 }} styles={{ label: { color: '#8895b4' }, content: { color: '#e8eef5' } }}>
              <Descriptions.Item label="类名">{selEntity.local_name}</Descriptions.Item>
              <Descriptions.Item label="中文标签">{selEntity.label || '-'}</Descriptions.Item>
              <Descriptions.Item label="业务域">{selEntity.domain || '-'}</Descriptions.Item>
              <Descriptions.Item label="类型">{selEntity.entity_type || 'class'}</Descriptions.Item>
              <Descriptions.Item label="定义">{selEntity.definition || '-'}</Descriptions.Item>
              <Descriptions.Item label="置信度">{selEntity.confidence != null ? `${Math.round(selEntity.confidence * 100)}%` : '-'}</Descriptions.Item>
            </Descriptions>

            <Text strong style={{ color: '#e8eef5', fontSize: 14 }}>属性（{(selEntity.properties || []).length}）</Text>
            <Table
              style={{ marginTop: 8, marginBottom: 16 }}
              columns={[
                { title: '属性名', dataIndex: 'name', key: 'n', render: (t: string) => <b style={{ fontFamily: 'monospace' }}>{t}</b> },
                { title: '类型', dataIndex: 'property_type', key: 'pt', width: 90, render: (t: string) => <Tag style={{ borderRadius: 4, fontSize: 10, background: t === 'object' ? 'rgba(167,139,250,0.12)' : 'rgba(52,211,153,0.12)', color: t === 'object' ? '#a78bfa' : '#34d399', border: 'none' }}>{t}</Tag> },
                { title: '值域', dataIndex: 'range_type', key: 'rt', render: (t: string) => <Text style={{ fontSize: 12, color: '#8895b4', fontFamily: 'monospace' }}>{t}</Text> },
                { title: '语义', dataIndex: 'semantic_type', key: 'st', width: 90, render: (t: string) => t ? <Tag style={{ borderRadius: 3, fontSize: 10, background: 'rgba(255,255,255,0.06)', color: '#8895b4', border: 'none' }}>{t}</Tag> : null },
              ]}
              dataSource={selEntity.properties || []}
              rowKey="id"
              pagination={false}
              size="small"
            />

            <Text strong style={{ color: '#e8eef5', fontSize: 14 }}>相关约束</Text>
            <Table
              style={{ marginTop: 8 }}
              columns={[
                { title: '类型', dataIndex: 'constraint_type', key: 'ct', render: (t: string) => <Tag style={{ borderRadius: 4, fontSize: 10, background: 'rgba(255,255,255,0.06)', color: '#e8eef5', border: 'none' }}>{t}</Tag> },
                { title: '表达式', dataIndex: 'expression', key: 'exp', render: (e: any) => <Text style={{ fontSize: 12, color: '#8895b4', fontFamily: 'monospace' }}>{typeof e === 'string' ? e : JSON.stringify(e)}</Text> },
                { title: '来源', dataIndex: 'source', key: 'src', width: 90, render: (s: string) => <Tag style={{ borderRadius: 4, fontSize: 10, background: `${SOURCE_COLOR[s] || '#60a5fa'}22`, color: SOURCE_COLOR[s] || '#60a5fa', border: 'none' }}>{s}</Tag> },
              ]}
              dataSource={constraints.filter((c) => c.target_type === 'property' && (selEntity.properties || []).some((p: any) => p.id === c.target_id))}
              rowKey="id"
              pagination={false}
              size="small"
              locale={{ emptyText: '无' }}
            />
          </div>
        )}
      </Drawer>
    </div>
  );
}

function StatChip({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 14px', borderRadius: 10, background: 'rgba(255,255,255,0.03)', border: `1px solid ${color}22` }}>
      <span style={{ width: 8, height: 8, borderRadius: 8, background: color }} />
      <span style={{ color: '#8895b4', fontSize: 12 }}>{label}</span>
      <b style={{ color: '#e8eef5' }}>{value ?? 0}</b>
    </div>
  );
}
