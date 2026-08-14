/**
 * Agent 设计器 — 左列表 / 右表单 + 权限矩阵 + 实时 .md 预览.
 *
 * 核心设计：
 * - 右侧常驻 .md 预览 → 用户能看到「最终会写进容器的到底是什么」
 * - 权限用矩阵而非 JSON → 从 UI 层面杜绝写错权限键（OpenCode 会静默忽略）
 * - 每个字段带示例与说明
 * - 保存前后端会再校验一次，错误信息带字段与修正建议
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  App,
  Alert,
  Button,
  Divider,
  Empty,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Segmented,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  CodeOutlined,
  DeleteOutlined,
  HistoryOutlined,
  ImportOutlined,
  PlusOutlined,
  ReloadOutlined,
  RollbackOutlined,
  SaveOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { extractErrMsg } from '../../stores/computeStore';
import * as svc from '../../services/agentFactory.service';
import type {
  AgentMode,
  AgentTemplate,
  AgentVersion,
  PermissionConfig,
  PermissionKeyMeta,
  ValidationResult,
} from '../../types/agentFactory';
import { agentModeLabel } from '../../types/agentFactory';
import PermissionMatrix from './PermissionMatrix';
import { ValidationPanel } from './shared';

const { Text } = Typography;

interface FormState {
  name: string;
  display_name: string;
  description: string;
  mode: AgentMode;
  model: string;
  prompt: string;
  temperature?: number;
  top_p?: number;
  steps?: number;
  permission_json: PermissionConfig;
  color: string;
  hidden: boolean;
  disable: boolean;
  category: string;
}

/**
 * System Prompt 模板 —— 一键填入后照着改，比对着空框发呆快得多。
 *
 * 结构参考内置预设的共同骨架：角色定位 → 工作方法 → 输出要求 → 禁止事项。
 * 「禁止事项」很关键：模型对「不要做什么」的遵循度高于泛泛的「要做好」。
 */
const PROMPT_TEMPLATE = `你是<角色，例如：资深代码评审专家>。<一句话说明能力边界，例如：只做分析，不修改任何文件。>

## 工作方法
1. <第一步做什么>
2. <第二步做什么>
3. <如何收敛/交付>

## 输出要求
- <格式要求，例如：按「文件:行号」定位每个问题>
- <每条要包含什么，例如：为什么是问题 + 建议怎么改>
- <如何分级，例如：区分「必须修」与「建议改」>

## 禁止事项
- <明确不要做的事，例如：不要为了凑数硬找问题>
- <边界，例如：不确定时先问，不要猜>
`;

const EMPTY: FormState = {
  name: '',
  display_name: '',
  description: '',
  mode: 'subagent',
  model: '',
  prompt: '',
  permission_json: {},
  color: '',
  hidden: false,
  disable: false,
  category: '',
};

function fromTemplate(t: AgentTemplate): FormState {
  return {
    name: t.name,
    display_name: t.display_name ?? '',
    description: t.description,
    mode: t.mode,
    model: t.model ?? '',
    prompt: t.prompt ?? '',
    temperature: t.temperature ?? undefined,
    top_p: t.top_p ?? undefined,
    steps: t.steps ?? undefined,
    permission_json: (t.permission_json ?? {}) as PermissionConfig,
    color: t.color ?? '',
    hidden: t.hidden,
    disable: t.disable,
    category: t.category ?? '',
  };
}

/** 表单 → 后端 payload（空串转 undefined，避免把空值写进产物） */
function toPayload(f: FormState) {
  return {
    name: f.name.trim(),
    display_name: f.display_name.trim() || undefined,
    description: f.description.trim(),
    mode: f.mode,
    model: f.model.trim() || undefined,
    prompt: f.prompt || undefined,
    temperature: f.temperature,
    top_p: f.top_p,
    steps: f.steps,
    permission_json: Object.keys(f.permission_json).length ? f.permission_json : undefined,
    color: f.color.trim() || undefined,
    hidden: f.hidden,
    disable: f.disable,
    category: f.category.trim() || undefined,
  };
}

export default function AgentDesigner({ meta }: { meta: PermissionKeyMeta[] }) {
  const { notification } = App.useApp();

  const [list, setList] = useState<AgentTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [saving, setSaving] = useState(false);

  const [preview, setPreview] = useState<string>('');
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [keyword, setKeyword] = useState('');

  // 版本
  const [versionOpen, setVersionOpen] = useState(false);
  const [versions, setVersions] = useState<AgentVersion[]>([]);
  // 导入
  const [importOpen, setImportOpen] = useState(false);
  const [importText, setImportText] = useState('');
  const [importName, setImportName] = useState('');

  const selected = useMemo(
    () => list.find((x) => x.id === selectedId) ?? null,
    [list, selectedId],
  );

  const load = useCallback(
    async (kw?: string) => {
      setLoading(true);
      try {
        const rows = await svc.listAgents(kw ? { keyword: kw } : undefined);
        setList(rows);
      } catch (err) {
        notification.error({ title: '获取 Agent 列表失败', description: extractErrMsg(err) });
      } finally {
        setLoading(false);
      }
    },
    [notification],
  );

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 选中变化 → 回填表单
  useEffect(() => {
    if (selected) {
      setForm(fromTemplate(selected));
      setCreating(false);
    }
  }, [selected]);

  // 表单变化 → 实时校验 + 实时预览（防抖）
  useEffect(() => {
    if (!form.name && !creating) return;
    const t = window.setTimeout(() => {
      void (async () => {
        try {
          const r = await svc.validateAgent(toPayload(form) as Record<string, unknown>);
          setValidation(r);
        } catch {
          /* 校验失败不打扰用户 */
        }
      })();
    }, 400);
    return () => window.clearTimeout(t);
  }, [form, creating]);

  // 已保存的 agent 才能拿后端渲染的 .md（保证与实际落盘一致）
  const refreshPreview = useCallback(async () => {
    if (!selectedId) {
      setPreview('');
      return;
    }
    try {
      const p = await svc.previewAgent(selectedId);
      setPreview(p.artifacts[0]?.content ?? '');
    } catch {
      setPreview('');
    }
  }, [selectedId]);

  useEffect(() => {
    void refreshPreview();
  }, [refreshPreview]);

  const patch = (p: Partial<FormState>) => setForm((s) => ({ ...s, ...p }));

  const startCreate = () => {
    setSelectedId(null);
    setCreating(true);
    setForm(EMPTY);
    setPreview('');
    setValidation(null);
  };

  const save = async () => {
    if (!form.name.trim()) {
      notification.warning({ title: '请填写 agent 名', description: '例如 code-reviewer' });
      return;
    }
    if (!form.description.trim()) {
      notification.warning({
        title: '请填写描述',
        description: 'primary agent 完全依据描述判断何时委派这个 subagent',
      });
      return;
    }
    setSaving(true);
    try {
      if (creating) {
        const created = await svc.createAgent(toPayload(form) as never);
        notification.success({ title: `Agent「${created.name}」已创建` });
        await load(keyword);
        setSelectedId(created.id);
        setCreating(false);
      } else if (selectedId) {
        const { name, ...rest } = toPayload(form);
        void name; // name 是落盘文件名，不允许改
        await svc.updateAgent(selectedId, rest as never);
        notification.success({ title: '已保存' });
        await load(keyword);
        await refreshPreview();
      }
    } catch (err) {
      notification.error({
        title: '保存失败',
        description: extractErrMsg(err),
        duration: 12,
      });
    } finally {
      setSaving(false);
    }
  };

  const remove = async (t: AgentTemplate) => {
    try {
      await svc.deleteAgent(t.id);
      notification.success({ title: `已删除 ${t.name}` });
      if (selectedId === t.id) setSelectedId(null);
      await load(keyword);
    } catch (err) {
      notification.error({ title: '删除失败', description: extractErrMsg(err), duration: 10 });
    }
  };

  const openVersions = async () => {
    if (!selectedId) return;
    try {
      setVersions(await svc.listAgentVersions(selectedId));
      setVersionOpen(true);
    } catch (err) {
      notification.error({ title: '获取版本失败', description: extractErrMsg(err) });
    }
  };

  const snapshot = async () => {
    if (!selectedId) return;
    const note = window.prompt('本次变更说明（可留空）');
    if (note === null) return;
    try {
      const v = await svc.createAgentVersion(selectedId, note || undefined);
      notification.success({ title: `已存为 v${v.version}` });
      await load(keyword);
    } catch (err) {
      notification.error({ title: '存版本失败', description: extractErrMsg(err) });
    }
  };

  const rollback = async (version: number) => {
    if (!selectedId) return;
    try {
      await svc.rollbackAgent(selectedId, version);
      notification.success({ title: `已回滚到 v${version}` });
      setVersionOpen(false);
      await load(keyword);
      const fresh = await svc.getAgent(selectedId);
      setForm(fromTemplate(fresh));
      await refreshPreview();
    } catch (err) {
      notification.error({ title: '回滚失败', description: extractErrMsg(err) });
    }
  };

  const doImport = async () => {
    if (!importText.trim()) {
      notification.warning({ title: '请粘贴 agent .md 内容' });
      return;
    }
    try {
      const t = await svc.importAgent({
        content: importText,
        name: importName.trim() || undefined,
        overwrite: true,
      });
      notification.success({ title: `已导入 ${t.name}` });
      setImportOpen(false);
      setImportText('');
      setImportName('');
      await load(keyword);
      setSelectedId(t.id);
    } catch (err) {
      notification.error({ title: '导入失败', description: extractErrMsg(err), duration: 12 });
    }
  };

  const columns: ColumnsType<AgentTemplate> = [
    {
      title: 'Agent',
      key: 'name',
      render: (_, r) => (
        <Space orientation="vertical" size={0}>
          <Space size={5}>
            <Text strong style={{ fontSize: 12.5 }}>
              {r.name}
            </Text>
            {r.color && (
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: 2,
                  background: r.color,
                  display: 'inline-block',
                }}
              />
            )}
            {r.is_builtin_preset && (
              <Tag color="blue" style={{ fontSize: 10, margin: 0 }}>
                预设
              </Tag>
            )}
          </Space>
          <Text type="secondary" style={{ fontSize: 10.5 }}>
            {agentModeLabel[r.mode]} · {r.category || '未分类'} · v{r.current_version}
          </Text>
        </Space>
      ),
    },
    {
      title: '',
      key: 'act',
      width: 40,
      render: (_, r) =>
        r.is_builtin_preset ? null : (
          <Popconfirm title={`删除 ${r.name}？`} onConfirm={() => remove(r)}>
            <Button
              size="small"
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={(e) => e.stopPropagation()}
            />
          </Popconfirm>
        ),
    },
  ];

  const editing = creating || !!selected;

  return (
    <div style={{ display: 'flex', gap: 14, height: '100%', alignItems: 'flex-start', padding: '14px 16px' }}>{/* 【UI 重构】统一 gap 14 对齐 SkillDesignerPage */}
      {/* ---------- 左：列表 ---------- */}
      <div style={{
        width: 260, flexShrink: 0,
        background: '#FFFFFF', borderRadius: 12,
        border: '1px solid rgba(0,0,0,0.06)',
        boxShadow: '0 1px 4px rgba(0,0,0,0.04)', /* 【UI 重构】统一阴影对齐 SkillDesignerPage */
        padding: '12px 14px', display: 'flex', flexDirection: 'column',
        maxHeight: '100%',
      }}>
        <Space style={{ marginBottom: 8, width: '100%' }} size={4}>
          <Input.Search
            size="small"
            placeholder="搜索 name / 描述"
            allowClear
            onSearch={(v) => {
              setKeyword(v);
              void load(v);
            }}
          />
        </Space>
        <Space style={{ marginBottom: 8 }} size={4}>
          <Button size="small" type="primary" icon={<PlusOutlined />} onClick={startCreate}>
            新建
          </Button>
          <Button size="small" icon={<ImportOutlined />} onClick={() => setImportOpen(true)}>
            导入
          </Button>
          <Button
            size="small"
            icon={<ReloadOutlined />}
            loading={loading}
            onClick={() => void load(keyword)}
          />
        </Space>
        <Table<AgentTemplate>
          size="small"
          rowKey="id"
          columns={columns}
          dataSource={list}
          loading={loading}
          pagination={false}
          showHeader={false}
          scroll={{ y: 'calc(100vh - 300px)' }}
          onRow={(r) => ({
            onClick: () => setSelectedId(r.id),
            style: {
              cursor: 'pointer',
              background: selectedId === r.id ? 'rgba(0,113,227,0.06)' : undefined, /* 【UI 重构】Apple Blue */
            },
          })}
        />
      </div>

      {/* ---------- 中：表单 ---------- */}
      <div style={{
        flex: 1, minWidth: 0, maxHeight: '100%', overflowY: 'auto', padding: '14px 16px', /* 【UI 重构】padding 对齐 SkillDesignerPage */
        background: '#FFFFFF', borderRadius: 12,
        border: '1px solid rgba(0,0,0,0.06)',
        boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
      }}>
        {!editing ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <span>
                左侧选择一个 Agent 查看/编辑
                <br />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  或点「新建」从零创建，「导入」把手写的 .md 收进平台
                </Text>
              </span>
            }
          />
        ) : (
          <>
            {/* 基础信息 */}
            <div style={{ marginBottom: 12 }}>
              <Text strong style={{ fontSize: 13 }}>
                Agent 名 <Text type="danger">*</Text>
              </Text>
              <Text type="secondary" style={{ fontSize: 11.5, marginLeft: 8, fontFamily: 'monospace' }}>
                例：code-reviewer（= 落盘文件名 code-reviewer.md）
              </Text>
              <Input
                size="small"
                style={{ marginTop: 4, fontFamily: 'monospace' }}
                placeholder="code-reviewer"
                value={form.name}
                disabled={!creating}
                onChange={(e) => patch({ name: e.target.value })}
              />
              {!creating && (
                <Text type="secondary" style={{ fontSize: 11 }}>
                  name 不可修改 —— 它是 OpenCode 里的 agent 标识与落盘文件名
                </Text>
              )}
            </div>

            <div style={{ marginBottom: 12 }}>
              <Text strong style={{ fontSize: 13 }}>
                描述 <Text type="danger">*</Text>
              </Text>
              <Tooltip title="primary agent 完全依据这段描述判断「什么时候该委派这个 subagent」，写清「做什么 + 什么场景用」">
                <Text type="secondary" style={{ fontSize: 11.5, marginLeft: 8 }}>
                  决定自动委派，≤1024 字符
                </Text>
              </Tooltip>
              <Input.TextArea
                rows={2}
                style={{ marginTop: 4 }}
                placeholder="审查代码的正确性与安全性，只读不改。当需要 review 一段改动时使用。"
                value={form.description}
                onChange={(e) => patch({ description: e.target.value })}
              />
            </div>

            <Space size={12} style={{ marginBottom: 12, flexWrap: 'wrap' }}>
              <div>
                <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
                  模式
                </Text>
                <Segmented
                  size="small"
                  value={form.mode}
                  onChange={(v) => patch({ mode: v as AgentMode })}
                  options={[
                    { label: '子代理', value: 'subagent' },
                    { label: '主对话', value: 'primary' },
                    { label: '两者', value: 'all' },
                  ]}
                />
              </div>
              <div>
                <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
                  分类
                </Text>
                <Input
                  size="small"
                  placeholder="review"
                  value={form.category}
                  onChange={(e) => patch({ category: e.target.value })}
                  style={{ width: 120 }}
                />
              </div>
              <div>
                <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
                  颜色
                </Text>
                <Input
                  size="small"
                  placeholder="#0071e3"
                  value={form.color}
                  onChange={(e) => patch({ color: e.target.value })}
                  style={{ width: 110, fontFamily: 'monospace' }}
                />
              </div>
            </Space>

            <Space size={12} style={{ marginBottom: 12, flexWrap: 'wrap' }}>
              <div>
                <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
                  模型
                </Text>
                <Input
                  size="small"
                  placeholder="留空=继承（如 anthropic/claude-sonnet-4-5）"
                  value={form.model}
                  onChange={(e) => patch({ model: e.target.value })}
                  style={{ width: 260, fontFamily: 'monospace' }}
                />
              </div>
              <div>
                <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
                  <Tooltip title="0.0-0.2 确定性强（适合分析/评审）；0.3-0.5 平衡；0.6+ 更有创造性">
                    温度
                  </Tooltip>
                </Text>
                <InputNumber
                  size="small"
                  min={0}
                  max={2}
                  step={0.05}
                  placeholder="0.1"
                  value={form.temperature}
                  onChange={(v) => patch({ temperature: v ?? undefined })}
                  style={{ width: 90 }}
                />
              </div>
              <div>
                <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
                  <Tooltip title="迭代上限，触顶后模型被要求总结并列出剩余任务；控制成本用">
                    步数上限
                  </Tooltip>
                </Text>
                <InputNumber
                  size="small"
                  min={1}
                  max={200}
                  placeholder="不限"
                  value={form.steps}
                  onChange={(v) => patch({ steps: v ?? undefined })}
                  style={{ width: 90 }}
                />
              </div>
            </Space>

            <div style={{ marginBottom: 14 }}>
              <Space size={8} wrap style={{ marginBottom: 2 }}>
                <Text strong style={{ fontSize: 13 }}>
                  System Prompt
                </Text>
                <Tooltip title="这段文字会作为该 agent 的系统提示词写入 .md 正文，决定它「怎么干活」">
                  <Text type="secondary" style={{ fontSize: 11.5 }}>
                    Markdown；决定 agent 的行为方式
                  </Text>
                </Tooltip>
                <Button
                  type="link"
                  size="small"
                  icon={<ThunderboltOutlined />}
                  style={{ fontSize: 12, padding: 0, height: 'auto' }}
                  onClick={() => patch({ prompt: PROMPT_TEMPLATE })}
                >
                  填入模板
                </Button>
                <Button
                  type="link"
                  size="small"
                  style={{ fontSize: 12, padding: 0, height: 'auto' }}
                  onClick={() => {
                    const preset = list.find(
                      (x) => x.is_builtin_preset && x.prompt && x.id !== selectedId,
                    );
                    if (preset?.prompt) patch({ prompt: preset.prompt });
                  }}
                >
                  参考预设写法
                </Button>
              </Space>
              <Text
                type="secondary"
                style={{ fontSize: 11, display: 'block', marginBottom: 2 }}
              >
                建议四段：<b>角色定位</b> → <b>工作方法</b> → <b>输出要求</b> →{' '}
                <b>禁止事项</b>。写清「不要做什么」比泛泛要求「做好」更有效。
              </Text>
              <Input.TextArea
                rows={8}
                style={{ marginTop: 4, fontFamily: 'monospace', fontSize: 12 }}
                placeholder={'你是资深代码评审专家。只做分析，不修改任何文件。\n\n评审维度：\n1. 正确性 — ...'}
                value={form.prompt}
                onChange={(e) => patch({ prompt: e.target.value })}
              />
              <Text type="secondary" style={{ fontSize: 11 }}>
                {form.prompt.length} 字符 · 约 {Math.ceil(form.prompt.length / 2.5)} tokens
              </Text>
            </div>

            <Divider style={{ margin: '12px 0' }} />

            <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 8 }}>
              权限
            </Text>
            <PermissionMatrix
              value={form.permission_json}
              onChange={(v) => patch({ permission_json: v })}
              meta={meta}
            />

            <Divider style={{ margin: '12px 0' }} />

            <div style={{ marginBottom: 12 }}>
              <ValidationPanel result={validation} />
            </div>

            <Space size={8}>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                loading={saving}
                onClick={() => void save()}
                disabled={!!validation && !validation.ok}
              >
                {creating ? '创建' : '保存'}
              </Button>
              {!creating && selectedId && (
                <>
                  <Button icon={<HistoryOutlined />} onClick={() => void openVersions()}>
                    版本
                  </Button>
                  <Button icon={<SaveOutlined />} onClick={() => void snapshot()}>
                    存为版本
                  </Button>
                </>
              )}
              {creating && <Button onClick={() => setCreating(false)}>取消</Button>}
            </Space>
          </>
        )}
      </div>

      {/* ---------- 右：实时 .md 预览 ---------- */}
      <div style={{
        width: 380, flexShrink: 0,
        background: '#FFFFFF', borderRadius: 12,
        border: '1px solid rgba(0,0,0,0.06)',
        boxShadow: '0 1px 4px rgba(0,0,0,0.04)', /* 【UI 重构】统一阴影对齐 */
        padding: '14px 16px', maxHeight: '100%',
        display: 'flex', flexDirection: 'column',
      }}>
        <Space size={6} style={{ marginBottom: 6, flexShrink: 0 }}>
          <CodeOutlined style={{ color: '#0071e3' }} />{/* 【UI 重构】Apple Blue */}
          <Text strong style={{ fontSize: 13 }}>
            落盘产物预览
          </Text>
          {selectedId && (
            <Button size="small" type="text" icon={<ReloadOutlined />} onClick={() => void refreshPreview()} />
          )}
        </Space>
        {preview ? (
          <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
            <Text code style={{ fontSize: 11, display: 'block', marginBottom: 4 }}>
              agents/{form.name}.md
            </Text>
            <pre
              style={{
                background: '#1a1918',
                color: '#e0e0e0',
                padding: 12,
                borderRadius: 8,
                fontSize: 11.5,
                fontFamily: "'JetBrains Mono', monospace",
                lineHeight: 1.6,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
                margin: 0,
              }}
            >
              {preview}
            </pre>
          </div>
        ) : (
          <Alert
            type="info"
            showIcon
            title={creating ? '创建后可预览' : '选择一个 Agent'}
            description={
              <span style={{ fontSize: 12 }}>
                预览由后端渲染，与实际写入容器的文件<b>完全一致</b>。
              </span>
            }
          />
        )}
      </div>

      {/* 版本 Modal */}
      <Modal
        title="版本历史"
        open={versionOpen}
        onCancel={() => setVersionOpen(false)}
        footer={null}
        width={600}
        destroyOnHidden
      >
        {versions.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="还没有版本快照，点「存为版本」创建第一个"
          />
        ) : (
          <Table
            size="small"
            rowKey="id"
            pagination={false}
            dataSource={versions}
            columns={[
              { title: '版本', dataIndex: 'version', width: 70, render: (v) => `v${v}` },
              { title: '说明', dataIndex: 'change_note', render: (v) => v || '—' },
              {
                title: '时间',
                dataIndex: 'created_at',
                width: 150,
                render: (v) => (v ? new Date(v).toLocaleString() : '—'),
              },
              {
                title: '',
                key: 'act',
                width: 90,
                render: (_, r: AgentVersion) => (
                  <Popconfirm
                    title={`回滚到 v${r.version}？`}
                    description="当前未保存的修改会丢失"
                    onConfirm={() => void rollback(r.version)}
                  >
                    <Button size="small" icon={<RollbackOutlined />}>
                      回滚
                    </Button>
                  </Popconfirm>
                ),
              },
            ]}
          />
        )}
      </Modal>

      {/* 导入 Modal */}
      <Modal
        title="从 .md 导入 Agent"
        open={importOpen}
        onOk={() => void doImport()}
        onCancel={() => setImportOpen(false)}
        okText="导入"
        width={640}
        destroyOnHidden
      >
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          title="把手写的 agent 收进平台管理"
          description={
            <span style={{ fontSize: 12 }}>
              OpenCode 的 agent 名来自<b>文件名</b>，所以请显式填写名称。
              可从容器内 <Text code>~/.config/opencode/agents/*.md</Text> 复制内容。
            </span>
          }
        />
        <div style={{ marginBottom: 10 }}>
          <Text strong style={{ fontSize: 13 }}>
            Agent 名
          </Text>
          <Text type="secondary" style={{ fontSize: 11.5, marginLeft: 8, fontFamily: 'monospace' }}>
            例：my-reviewer
          </Text>
          <Input
            size="small"
            style={{ marginTop: 4, fontFamily: 'monospace' }}
            placeholder="my-reviewer"
            value={importName}
            onChange={(e) => setImportName(e.target.value)}
          />
        </div>
        <Text strong style={{ fontSize: 13 }}>
          .md 内容
        </Text>
        <Input.TextArea
          rows={12}
          style={{ marginTop: 4, fontFamily: 'monospace', fontSize: 12 }}
          placeholder={'---\ndescription: ...\nmode: subagent\npermission:\n  edit: deny\n---\n\n你是...'}
          value={importText}
          onChange={(e) => setImportText(e.target.value)}
        />
      </Modal>
    </div>
  );
}
