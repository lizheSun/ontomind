/**
 * Skill 设计器 — 三段式：元数据 → 参数契约 → 执行逻辑.
 *
 * 设计原则：
 * - 三段在一个页面里，用分段导航切换，避免用户反复跳转丢失上下文
 * - 右侧常驻 SKILL.md 预览（后端渲染，与落盘完全一致）
 * - 每段保存独立，不要求一次性填完所有字段
 * - 实时校验（非功能要求 2）
 */
import { useCallback, useEffect, useState } from 'react';
import {
  App,
  Alert,
  Button,
  Divider,
  Empty,
  Input,
  Modal,
  Popconfirm,
  Segmented,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  DeleteOutlined,
  DownloadOutlined,
  PlusOutlined,
  ReloadOutlined,
  SaveOutlined,
  CodeOutlined,
  HistoryOutlined,
  RollbackOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { extractErrMsg } from '../../stores/computeStore';
import * as svc from '../../services/skillPlatform.service';
import type {
  SkillFullResponse,
  SkillListItem,
  SkillMetaPayload,
  
  SkillParamPayload,
  
  SkillVersionResponse,
  ExportedFile,
} from '../../types/skillPlatform';
import {
  SKILL_KIND_OPTIONS,
  LIFECYCLE_LABEL,
  LIFECYCLE_COLOR,
  RISK_COLOR,
} from '../../types/skillPlatform';

const { Text } = Typography;

type Section = 'meta' | 'params' | 'exec';

const EMPTY_META: SkillMetaPayload = {
  skill_kind: 'prompt',
  biz_tags: [],
  risk_level: 'low',
  lifecycle: 'draft',
};

export default function SkillDesignerPage() {
  const { notification } = App.useApp();

  const [list, setList] = useState<SkillListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [full, setFull] = useState<SkillFullResponse | null>(null);
  const [saving, setSaving] = useState(false);
  const [keyword, setKeyword] = useState('');

  const [section, setSection] = useState<Section>('meta');

  // 各段编辑状态
  const [meta, setMeta] = useState<SkillMetaPayload>({ ...EMPTY_META });
  const [paramsIn, setParamsIn] = useState<SkillParamPayload[]>([]);
  const [paramsOut, setParamsOut] = useState<SkillParamPayload[]>([]);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [body, setBody] = useState('');
  const [execPrompt, setExecPrompt] = useState<string>('');
  const [apiUrl, setApiUrl] = useState('');
  const [apiAuth, setApiAuth] = useState('none');
  const [apiSecret, setApiSecret] = useState('');

  // 导出 / 版本
  const [exportOpen, setExportOpen] = useState(false);
  const [exported, setExported] = useState<ExportedFile[]>([]);
  const [versionOpen, setVersionOpen] = useState(false);
  const [versions, setVersions] = useState<SkillVersionResponse[]>([]);

  const load = useCallback(async (kw?: string) => {
    setLoading(true);
    try {
      setList(await svc.listSkills(kw ? { keyword: kw } : undefined));
    } catch (err) {
      notification.error({ title: '获取列表失败', description: extractErrMsg(err) });
    } finally {
      setLoading(false);
    }
  }, [notification]);

  useEffect(() => { void load(); }, [load]);

  const loadFull = useCallback(async (id: number) => {
    try {
      const f = await svc.getSkill(id);
      setFull(f);
      setMeta(f.meta);
      setParamsIn(f.params_in);
      setParamsOut(f.params_out);
      setName(f.name);
      setDescription(f.description);
      setBody(f.body ?? '');
      setExecPrompt(f.exec_prompt?.system_prompt ?? '');
      setApiUrl(f.exec_api?.url_prod ?? '');
      setApiAuth(f.exec_api?.auth_type ?? 'none');
      setApiSecret(f.exec_api?.secret_ref ?? '');
    } catch (err) {
      notification.error({ title: '获取详情失败', description: extractErrMsg(err) });
    }
  }, [notification]);

  useEffect(() => {
    if (selectedId) { void loadFull(selectedId); setCreating(false); }
  }, [selectedId, loadFull]);

  const startCreate = () => {
    setSelectedId(null);
    setCreating(true);
    setFull(null);
    setMeta({ ...EMPTY_META });
    setParamsIn([]);
    setParamsOut([]);
    setName('');
    setDescription('');
    setBody('');
    setExecPrompt('');
    setApiUrl('');
    setApiAuth('none');
    setApiSecret('');
  };

  const save = async () => {
    if (!name.trim()) {
      notification.warning({ title: '请填写 Skill 标识', description: 'kebab-case，如 pay-order-query' });
      return;
    }
    setSaving(true);
    try {
      if (creating) {
        const c = await svc.createSkill({
          name: name.trim(),
          description: description.trim() || name.trim(),
          meta,
          body,
        });
        if (paramsIn.length) await svc.updateParams(c.id, 'in', paramsIn as never);
        if (paramsOut.length) await svc.updateParams(c.id, 'out', paramsOut as never);
        notification.success({ title: `Skill「${c.name}」已创建` });
        await load(keyword);
        setSelectedId(c.id);
        setCreating(false);
      } else if (selectedId) {
        await svc.updateSkill(selectedId, {
          description, body,
          meta: { ...meta },
          exec_prompt: { system_prompt: execPrompt, few_shots: [], output_format: 'text' },
          exec_api: { http_method: 'POST', url_prod: apiUrl, auth_type: apiAuth, secret_ref: apiSecret, headers: {}, param_mappings: [], timeout_ms: 5000, retry_times: 0, retry_backoff_ms: 200 },
        });
        notification.success({ title: '已保存' });
        await load(keyword);
        if (selectedId) await loadFull(selectedId);
      }
    } catch (err) {
      notification.error({ title: '保存失败', description: extractErrMsg(err), duration: 10 });
    } finally {
      setSaving(false);
    }
  };

  const doExport = async () => {
    if (!selectedId) return;
    try {
      const e = await svc.exportSkill(selectedId);
      setExported(e.files);
      setExportOpen(true);
    } catch (err) {
      notification.error({ title: '导出失败', description: extractErrMsg(err) });
    }
  };

  const openVersions = async () => {
    if (!selectedId) return;
    try {
      setVersions(await svc.listVersions(selectedId));
      setVersionOpen(true);
    } catch (err) {
      notification.error({ title: '获取版本失败', description: extractErrMsg(err) });
    }
  };

  const snapshot = async () => {
    if (!selectedId) return;
    const note = window.prompt('变更说明（可留空）');
    if (note === null) return;
    try {
      const v = await svc.createVersion(selectedId, note || undefined);
      notification.success({ title: `已存为 v${v.version}` });
    } catch (err) {
      notification.error({ title: '存版本失败', description: extractErrMsg(err) });
    }
  };

  const rollback = async (version: number) => {
    if (!selectedId) return;
    try {
      await svc.rollbackSkill(selectedId, version);
      notification.success({ title: `已回滚到 v${version}` });
      setVersionOpen(false);
      if (selectedId) await loadFull(selectedId);
    } catch (err) {
      notification.error({ title: '回滚失败', description: extractErrMsg(err) });
    }
  };

  const doClone = async () => {
    if (!selectedId) return;
    const n = window.prompt('新 Skill 标识（kebab-case）', `${full?.name ?? 'skill'}-copy`);
    if (!n) return;
    try {
      const c = await svc.cloneSkill(selectedId, n);
      notification.success({ title: `已克隆为 ${c.name}` });
      await load(keyword);
      setSelectedId(c.id);
    } catch (err) {
      notification.error({ title: '克隆失败', description: extractErrMsg(err) });
    }
  };

  const deleteRow = async (r: SkillListItem) => {
    try {
      await svc.deleteSkill(r.id);
      notification.success({ title: `已删除 ${r.name}` });
      if (selectedId === r.id) setSelectedId(null);
      await load(keyword);
    } catch (err) {
      notification.error({ title: '删除失败', description: extractErrMsg(err), duration: 10 });
    }
  };

  const addParam = (dir: 'in' | 'out') => {
    const p: SkillParamPayload = {
      name: '', data_type: 'string', required: false, enum_values: [], mask_rule: 'none',
      source: 'dialog', filtered: false, write_to_context: false, sort_order: 0,
    };
    if (dir === 'in') setParamsIn([...paramsIn, p]);
    else setParamsOut([...paramsOut, p]);
  };

  const patchParam = (dir: 'in' | 'out', idx: number, p: Partial<SkillParamPayload>) => {
    if (dir === 'in') setParamsIn(paramsIn.map((x, i) => i === idx ? { ...x, ...p } : x));
    else setParamsOut(paramsOut.map((x, i) => i === idx ? { ...x, ...p } : x));
  };

  const removeParam = (dir: 'in' | 'out', idx: number) => {
    if (dir === 'in') setParamsIn(paramsIn.filter((_, i) => i !== idx));
    else setParamsOut(paramsOut.filter((_, i) => i !== idx));
  };

  const columns: ColumnsType<SkillListItem> = [
    {
      title: 'Skill', key: 'name',
      render: (_, r) => (
        <Space orientation="vertical" size={0}>
          <Space size={5}>
            <Text strong style={{ fontSize: 12.5 }}>{r.name}</Text>
            <Tag color={RISK_COLOR[r.risk_level]} style={{ fontSize: 10, margin: 0 }}>{r.risk_level}</Tag>
            <Tag color={LIFECYCLE_COLOR[r.lifecycle]} style={{ fontSize: 10, margin: 0 }}>{LIFECYCLE_LABEL[r.lifecycle]}</Tag>
          </Space>
          <Text type="secondary" style={{ fontSize: 10.5 }}>
            {SKILL_KIND_OPTIONS.find(k => k.value === r.skill_kind)?.label ?? r.skill_kind} · {r.biz_line || '未分类'} · v{r.current_version}
          </Text>
        </Space>
      ),
    },
    {
      title: '', key: 'act', width: 40,
      render: (_, r) => r.is_builtin_preset ? null : (
        <Popconfirm title={`删除 ${r.name}？`} onConfirm={() => deleteRow(r)}>
          <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={e => e.stopPropagation()} />
        </Popconfirm>
      ),
    },
  ];

  const paramCols: ColumnsType<SkillParamPayload> = [
    {
      title: '参数名', dataIndex: 'name', width: 120,
      render: (v: string, _, i) => <Input size="small" value={v} placeholder="order_no" onChange={e => patchParam(section === 'params' ? 'in' : 'out', i, { name: e.target.value })} style={{ fontFamily: 'monospace', width: 120 }} />,
    },
    {
      title: '类型', dataIndex: 'data_type', width: 100,
      render: (v: string, _, i) => <Select size="small" value={v} onChange={v => patchParam(section === 'params' ? 'in' : 'out', i, { data_type: v })} options={['string', 'number', 'integer', 'boolean'].map(t => ({ value: t, label: t }))} style={{ width: 100 }} />,
    },
    {
      title: '必填', dataIndex: 'required', width: 60,
      render: (v: boolean, _, i) => (
        <Select size="small" value={v ? 'yes' : 'no'} onChange={v => patchParam(section === 'params' ? 'in' : 'out', i, { required: v === 'yes' })} options={[{ value: 'yes', label: '是' }, { value: 'no', label: '否' }]} style={{ width: 60 }} />
      ),
    },
    {
      title: '来源', dataIndex: 'source', width: 100,
      render: (v: string, _, i) => section === 'params' ? (
        <Select size="small" value={v || 'dialog'} onChange={v => patchParam('in', i, { source: v as 'dialog' | 'context' | 'system' | 'const' })} options={[
          { value: 'dialog', label: '对话抽取' }, { value: 'context', label: '会话变量' }, { value: 'system', label: '内置' }, { value: 'const', label: '固定值' },
        ]} style={{ width: 100 }} />
      ) : (
        <Text type="secondary" style={{ fontSize: 11 }}>—</Text>
      ),
    },
    {
      title: '脱敏', dataIndex: 'mask_rule', width: 80,
      render: (v: string, _, i) => section !== 'params' ? (
        <Select size="small" value={v || 'none'} onChange={v => patchParam('out', i, { mask_rule: v as 'none' | 'phone' | 'idcard' | 'bankcard' | 'email' | 'all' | 'custom' })} options={[
          { value: 'none', label: '无' }, { value: 'phone', label: '手机' }, { value: 'idcard', label: '身份证' }, { value: 'bankcard', label: '银行卡' }, { value: 'email', label: '邮箱' }, { value: 'all', label: '全部' },
        ]} style={{ width: 80 }} />
      ) : <Text type="secondary" style={{ fontSize: 11 }}>—</Text>,
    },
    {
      title: '', key: 'act', width: 40,
      render: (_, __, i) => <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => removeParam(section === 'params' ? 'in' : 'out', i)} />,
    },
  ];

  const editing = creating || !!selectedId;

  return (
    <div style={{ display: 'flex', gap: 14, alignItems: 'flex-start', maxWidth: 1680, margin: '0 auto', padding: '14px 16px' }}>
      {/* 【UI 重构】左：列表，白底卡片容器 */}
      <div style={{ width: 250, flexShrink: 0, background: '#FFFFFF', borderRadius: 12, border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 1px 4px rgba(0,0,0,0.04)', padding: '12px 14px' }}>
        <Input.Search size="small" placeholder="搜索 name / 描述" allowClear style={{ marginBottom: 8 }}
          onSearch={v => { setKeyword(v); void load(v); }} />
        <Space style={{ marginBottom: 8 }} size={4}>
          <Button size="small" type="primary" icon={<PlusOutlined />} onClick={startCreate}>新建</Button>
          <Button size="small" icon={<ReloadOutlined />} loading={loading} onClick={() => void load(keyword)} />
        </Space>
        <Table<SkillListItem> size="small" rowKey="id" columns={columns} dataSource={list} loading={loading} pagination={false} showHeader={false}
          scroll={{ y: 'calc(100vh - 300px)' }}
          onRow={r => ({ onClick: () => setSelectedId(r.id), style: { cursor: 'pointer', background: selectedId === r.id ? 'rgba(0,113,227,0.06)' : undefined } })} />{/* 【UI 重构】Apple Blue 替代原品牌色 */}
      </div>

      {/* 【UI 重构】中：设计器，白底卡片容器 */}
      <div style={{ flex: 1, minWidth: 0, background: '#FFFFFF', borderRadius: 12, border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 1px 4px rgba(0,0,0,0.04)', padding: '14px 16px' }}>
        {!editing ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<span>左侧选择一个 Skill 查看/编辑<br /><Text type="secondary" style={{ fontSize: 12 }}>或点「新建」从零创建</Text></span>} />
        ) : (
          <>
            {/* 基本信息 */}
            <div style={{ marginBottom: 12 }}>
              <Space size={8} wrap>
                <div>
                  <Text strong style={{ fontSize: 13 }}>Skill 标识 <Text type="danger">*</Text></Text>
                  <Input size="small" style={{ marginTop: 2, width: 200, fontFamily: 'monospace' }} placeholder="pay-order-query" value={name} disabled={!creating} onChange={e => setName(e.target.value)} />
                </div>
                <div>
                  <Text strong style={{ fontSize: 13 }}>形态</Text>
                  <Select size="small" style={{ marginTop: 2, width: 140 }} value={meta.skill_kind} onChange={v => setMeta({ ...meta, skill_kind: v as 'prompt' | 'api' | 'flow' })}
                    options={SKILL_KIND_OPTIONS.map(k => ({ value: k.value, label: k.label }))} />
                </div>
                <div>
                  <Text strong style={{ fontSize: 13 }}>风险等级</Text>
                  <Select size="small" style={{ marginTop: 2, width: 120 }} value={meta.risk_level} onChange={v => setMeta({ ...meta, risk_level: v as 'low' | 'medium' | 'high' })}
                    options={[{ value: 'low', label: '低危' }, { value: 'medium', label: '中危' }, { value: 'high', label: '高危' }]} />
                </div>
                <div>
                  <Text strong style={{ fontSize: 13 }}>生命周期</Text>
                  <div style={{ marginTop: 2 }}><Tag color={LIFECYCLE_COLOR[meta.lifecycle]}>{LIFECYCLE_LABEL[meta.lifecycle]}</Tag></div>
                </div>
              </Space>
            </div>

            {/* 分段导航 */}
            <Space style={{ marginBottom: 10 }} size={0} wrap>
              <Segmented size="small" value={section} onChange={v => setSection(v as Section)}
                options={[
                  { label: `① 元数据 (${full?.params_in?.length ?? paramsIn.length}入/${full?.params_out?.length ?? paramsOut.length}出)`, value: 'params' },
                  { label: '② 执行逻辑', value: 'exec' },
                ]} />
              {full?.validation && !full.validation.ok && (
                <Tag color="error" style={{ marginLeft: 8, fontSize: 10 }}>{full.validation.issues.filter(i => i.level === 'error').length} 处错误</Tag>
              )}
            </Space>

            {/* 段 2 + 3：参数 + 执行 */}
            <div style={{ maxHeight: 'calc(100vh - 340px)', overflowY: 'auto', paddingRight: 4 }}>
              {section === 'params' && (
                <>
                  <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 6 }}>入参（对话抽取 → 自动校验）</Text>
                  <Table size="small" rowKey={(_, i) => `in-${i}`} columns={paramCols} dataSource={paramsIn} pagination={false} locale={{ emptyText: '暂无入参' }} />
                  <Button size="small" type="dashed" icon={<PlusOutlined />} onClick={() => addParam('in')} style={{ margin: '6px 0 14px' }}>添加入参</Button>

                  <Divider style={{ margin: '8px 0' }} />
                  <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 6 }}>出参（data 字段，外壳固定 code / msg / data / session_vars）</Text>
                  <Table size="small" rowKey={(_, i) => `out-${i}`} columns={paramCols} dataSource={paramsOut} pagination={false} locale={{ emptyText: '暂无出参' }} />
                  <Button size="small" type="dashed" icon={<PlusOutlined />} onClick={() => addParam('out')} style={{ margin: '6px 0 14px' }}>添加出参</Button>
                </>
              )}

              {section === 'exec' && (
                <>
                  {meta.skill_kind === 'prompt' && (
                    <div>
                      <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>System Prompt</Text>
                      <Input.TextArea rows={8} style={{ fontFamily: 'monospace', fontSize: 12 }} placeholder="你是支付订单查询助手。只读查询，不做任何资金操作。" value={execPrompt} onChange={e => setExecPrompt(e.target.value)} />
                    </div>
                  )}
                  {meta.skill_kind === 'api' && (
                    <div>
                      <Space size={10} wrap style={{ marginBottom: 10 }}>
                        <div>
                          <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>生产环境地址</Text>
                          <Input size="small" style={{ width: 320, fontFamily: 'monospace' }} placeholder="https://pay.internal/api/order/query" value={apiUrl} onChange={e => setApiUrl(e.target.value)} />
                        </div>
                        <div>
                          <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>鉴权方式</Text>
                          <Select size="small" style={{ width: 120 }} value={apiAuth} onChange={setApiAuth} options={[
                            { value: 'none', label: '无' }, { value: 'bearer', label: 'Bearer' }, { value: 'ak_sk', label: 'AK/SK' }, { value: 'api_key', label: 'API Key' },
                          ]} />
                        </div>
                        <div>
                          <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
                            <Tooltip title="仅存配置中心引用键，禁止明文密钥。如 cc://skill/pay/aksk">密钥引用键</Tooltip>
                          </Text>
                          <Input size="small" style={{ width: 220, fontFamily: 'monospace' }} placeholder="cc://skill/pay-order-query/aksk" value={apiSecret} onChange={e => setApiSecret(e.target.value)} />
                        </div>
                      </Space>
                    </div>
                  )}
                  {meta.skill_kind === 'flow' && (
                    <Alert type="info" showIcon title="编排型" description="流程图编排功能将在后续版本中开放，当前请先选择 Prompt 或 API 形态。" />
                  )}
                </>
              )}

              {/* 保存 + 动作 */}
              <Divider style={{ margin: '12px 0' }} />
              <Space size={8}>
                <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={() => void save()}>{creating ? '创建' : '保存'}</Button>
                {!creating && selectedId && (
                  <>
                    <Button icon={<DownloadOutlined />} onClick={() => void doExport()}>导出</Button>
                    <Button icon={<HistoryOutlined />} onClick={() => void openVersions()}>版本</Button>
                    <Button icon={<SaveOutlined />} onClick={() => void snapshot()}>存为版本</Button>
                    <Button icon={<CopyOutlined />} onClick={() => void doClone()}>克隆</Button>
                  </>
                )}
                {creating && <Button onClick={() => setCreating(false)}>取消</Button>}
              </Space>
            </div>
          </>
        )}
      </div>

      {/* 【UI 重构】右：预览，白底卡片容器 */}
      <div style={{ width: 360, flexShrink: 0, background: '#FFFFFF', borderRadius: 12, border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 1px 4px rgba(0,0,0,0.04)', padding: '14px 16px' }}>
        <Space size={6} style={{ marginBottom: 6 }}>
          <CodeOutlined style={{ color: '#0071e3' }} />{/* 【UI 重构】Apple Blue */}
          <Text strong style={{ fontSize: 13 }}>导出预览</Text>
        </Space>
        {full ? (
          <pre style={{ background: '#1a1918', color: '#e0e0e0', padding: 12, borderRadius: 8, maxHeight: 'calc(100vh - 280px)', overflow: 'auto', fontSize: 11.5, fontFamily: "'JetBrains Mono', monospace", lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-all', margin: 0 }}>
            {`---\nname: ${full.name}\ndescription: "${full.description}"\nlicense: ${full.license || 'MIT'}\ncompatibility: opencode\nmetadata:\n  omd_skill_kind: ${meta.skill_kind}\n  omd_risk_level: ${meta.risk_level}\n  omd_lifecycle: ${meta.lifecycle}\n---\n\n${full.body || ''}`}
          </pre>
        ) : (
          <Alert type="info" showIcon title={creating ? '创建后可预览' : '选择一个 Skill'} description={<span style={{ fontSize: 12 }}>预览由后端渲染，与实际写入容器的文件<b>完全一致</b>。</span>} />
        )}
      </div>

      {/* 导出 Modal */}
      <Modal title="导出目录" open={exportOpen} onCancel={() => setExportOpen(false)} footer={null} width={760} destroyOnHidden>
        {exported.length > 0 && (
          <div style={{ maxHeight: 500, overflow: 'auto' }}>
            {exported.filter(f => f.plane === 'data').map(f => (
              <div key={f.path} style={{ marginBottom: 8 }}>
                <Space size={6}><Text code style={{ fontSize: 11 }}>{f.path}</Text><Text type="secondary" style={{ fontSize: 10 }}>{f.bytes}B</Text></Space>
                <pre style={{ background: '#1a1918', color: '#e0e0e0', padding: 8, borderRadius: 6, fontSize: 11, fontFamily: "'JetBrains Mono', monospace", maxHeight: 200, overflow: 'auto', margin: 0 }}>
                  {f.content.slice(0, 800)}
                </pre>
              </div>
            ))}
          </div>
        )}
      </Modal>

      {/* 版本 Modal */}
      <Modal title="版本历史" open={versionOpen} onCancel={() => setVersionOpen(false)} footer={null} width={600} destroyOnHidden>
        {versions.length === 0 ? <Empty description="还没有版本快照" /> : (
          <Table size="small" rowKey="id" pagination={false} dataSource={versions}
            columns={[
              { title: '版本', dataIndex: 'version', width: 70, render: v => `v${v}` },
              { title: '说明', dataIndex: 'change_note', render: v => v || '—' },
              { title: '时间', dataIndex: 'created_at', width: 150, render: v => v ? new Date(v).toLocaleString() : '—' },
              { title: '', key: 'act', width: 90, render: (_, r: SkillVersionResponse) => (
                <Popconfirm title={`回滚到 v${r.version}？`} onConfirm={() => void rollback(r.version)}>
                  <Button size="small" icon={<RollbackOutlined />}>回滚</Button>
                </Popconfirm>
              )},
            ]} />
        )}
      </Modal>
    </div>
  );
}