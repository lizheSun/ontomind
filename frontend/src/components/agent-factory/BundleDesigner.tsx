/**
 * 编排方案设计器 — Loop 模式的可视化组装.
 *
 * Agent Loop 的本质是「一组 agent + 一套全局旋钮」，四个旋钮决定形态：
 * - permission.task    谁能调谁（glob，deny 会把 subagent 从 Task 描述里整条移除）
 * - subagent_depth     能嵌几层（0=禁止派生）
 * - default_agent      默认入口（必须是 primary）
 * - steps              单 agent 迭代上限（在 Agent 设计器里配）
 *
 * 所以这里以 Bundle 为单位管理，并用 SVG 拓扑把关系画出来 ——
 * 否则这些关系散落在多个 agent 的 permission 字段里，看不到全貌。
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  App,
  Alert,
  Button,
  Divider,
  Empty,
  Input,
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
  ApartmentOutlined,
  BranchesOutlined,
  DeleteOutlined,
  PlusOutlined,
  ReloadOutlined,
  RocketOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { extractErrMsg } from '../../stores/computeStore';
import * as svc from '../../services/agentFactory.service';
import type {
  AgentBundle,
  AgentTemplate,
  BundleMemberItem,
  BundlePattern,
  PermissionAction,
  PermissionConfig,
  PresetsResponse,
  PreviewResponse,
  SkillTemplate,
  ValidationResult,
} from '../../types/agentFactory';
import { bundlePatternLabel } from '../../types/agentFactory';
import LoopTopology from './LoopTopology';
import { ArtifactPreview, ArtifactTree, ValidationPanel } from './shared';

const { Text } = Typography;

const PATTERNS: BundlePattern[] = [
  'single',
  'plan-build',
  'orchestrator-workers',
  'research-loop',
  'review-loop',
  'pipeline',
  'custom',
];

/** 每个模式的一句话说明 —— 帮用户选对 */
const PATTERN_HINT: Record<BundlePattern, string> = {
  single: '一个 primary 全权限直接干活。最简单，适合个人快速上手。',
  'plan-build': '先用只读的 plan 出方案，确认后切 build 落地。防止未经确认就改代码。',
  'orchestrator-workers': '编排者拆解任务分派给专家，最后汇总。适合复杂多角色任务。',
  'research-loop': 'Plan→Search→Reflect→Synthesize 迭代，steps 放宽支撑多轮补全。',
  'review-loop': '实现后自动交给只读评审，形成「写-审」闭环。适合质量要求高的改动。',
  pipeline: '按固定顺序串行：探索→实现→测试→评审。适合流程标准化的任务。',
  custom: '完全自定义拓扑与旋钮。',
};

interface Props {
  presets: PresetsResponse | null;
  /** 切到发布中心并带上 bundle */
  onDeploy: (bundleId: number) => void;
}

export default function BundleDesigner({ presets, onDeploy }: Props) {
  const { notification } = App.useApp();

  const [list, setList] = useState<AgentBundle[]>([]);
  const [agents, setAgents] = useState<AgentTemplate[]>([]);
  const [skills, setSkills] = useState<SkillTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  /** 成员/授权有未保存改动 */
  const [dirty, setDirty] = useState(false);

  // 表单
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [pattern, setPattern] = useState<BundlePattern>('custom');
  const [defaultAgent, setDefaultAgent] = useState<string>('');
  const [depth, setDepth] = useState<number | undefined>(1);
  const [members, setMembers] = useState<BundleMemberItem[]>([]);

  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [previewPath, setPreviewPath] = useState('');

  const selected = useMemo(
    () => list.find((x) => x.id === selectedId) ?? null,
    [list, selectedId],
  );

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [b, a, s] = await Promise.all([
        svc.listBundles(),
        svc.listAgents(),
        svc.listSkills(),
      ]);
      setList(b);
      setAgents(a);
      setSkills(s);
    } catch (err) {
      notification.error({ title: '加载失败', description: extractErrMsg(err) });
    } finally {
      setLoading(false);
    }
  }, [notification]);

  useEffect(() => {
    void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 选中 → 回填
  useEffect(() => {
    if (!selected) return;
    setName(selected.name);
    setDescription(selected.description ?? '');
    setPattern(selected.pattern);
    setDefaultAgent(selected.default_agent ?? '');
    setDepth(selected.subagent_depth ?? undefined);
    setMembers(
      selected.members.map((m) => ({
        member_type: m.member_type,
        agent_template_id: m.agent_template_id,
        skill_template_id: m.skill_template_id,
        role: m.role,
        skill_permission: m.skill_permission,
        task_permission: m.task_permission,
        sort_order: m.sort_order,
      })),
    );
    setCreating(false);
    setDirty(false);
  }, [selected]);

  const refreshValidationAndPreview = useCallback(async () => {
    if (!selectedId) {
      setValidation(null);
      setPreview(null);
      return;
    }
    try {
      const [v, p] = await Promise.all([
        svc.validateBundle(selectedId),
        svc.previewBundle(selectedId),
      ]);
      setValidation(v);
      setPreview(p);
      setPreviewPath((cur) => cur || p.artifacts[0]?.path || '');
    } catch {
      /* 静默 */
    }
  }, [selectedId]);

  useEffect(() => {
    void refreshValidationAndPreview();
  }, [refreshValidationAndPreview]);

  /** 从预设生成骨架 —— 用户不必从零摸索 */
  const applyPreset = (presetName: string) => {
    const p = presets?.bundles.find((x) => x.name === presetName);
    if (!p) return;
    setCreating(true);
    setSelectedId(null);
    setName(`${p.name}（副本）`);
    setDescription(p.description ?? '');
    setPattern(p.pattern);
    setDefaultAgent(p.default_agent ?? '');
    setDepth(p.subagent_depth ?? 1);
    const ms: BundleMemberItem[] = [];
    let order = 0;
    p.agents.forEach((an) => {
      const a = agents.find((x) => x.name === an);
      if (a) {
        ms.push({
          member_type: 'agent',
          agent_template_id: a.id,
          role: a.mode === 'primary' ? 'primary' : 'subagent',
          sort_order: order++,
        });
      }
    });
    p.skills.forEach((sn) => {
      const s = skills.find((x) => x.name === sn);
      if (s) {
        ms.push({
          member_type: 'skill',
          skill_template_id: s.id,
          role: 'skill',
          skill_permission: 'allow',
          sort_order: order++,
        });
      }
    });
    setMembers(ms);
    setValidation(null);
    setPreview(null);
  };

  const startCreate = () => {
    setSelectedId(null);
    setCreating(true);
    setName('');
    setDescription('');
    setPattern('custom');
    setDefaultAgent('');
    setDepth(1);
    setMembers([]);
    setValidation(null);
    setPreview(null);
  };

  const save = async () => {
    if (!name.trim()) {
      notification.warning({ title: '请填写方案名' });
      return;
    }
    setSaving(true);
    try {
      const payload = {
        name: name.trim(),
        description: description.trim() || undefined,
        pattern,
        default_agent: defaultAgent.trim() || undefined,
        subagent_depth: depth,
        members: members.map((m, i) => ({ ...m, sort_order: i })),
      };
      if (creating) {
        const created = await svc.createBundle(payload as never);
        notification.success({ title: `方案「${created.name}」已创建` });
        setDirty(false);
        await loadAll();
        setSelectedId(created.id);
        setCreating(false);
      } else if (selectedId) {
        await svc.updateBundle(selectedId, payload as never);
        notification.success({ title: '已保存' });
        setDirty(false);
        await loadAll();
        await refreshValidationAndPreview();
      }
    } catch (err) {
      notification.error({ title: '保存失败', description: extractErrMsg(err), duration: 12 });
    } finally {
      setSaving(false);
    }
  };

  const remove = async (b: AgentBundle) => {
    try {
      await svc.deleteBundle(b.id);
      notification.success({ title: `已删除 ${b.name}` });
      if (selectedId === b.id) setSelectedId(null);
      await loadAll();
    } catch (err) {
      notification.error({ title: '删除失败', description: extractErrMsg(err), duration: 10 });
    }
  };

  // 成员操作
  const addAgent = (id: number) => {
    if (members.some((m) => m.agent_template_id === id)) return;
    const a = agents.find((x) => x.id === id);
    setMembers([
      ...members,
      {
        member_type: 'agent',
        agent_template_id: id,
        role: a?.mode === 'primary' ? 'primary' : 'subagent',
        sort_order: members.length,
      },
    ]);
  };

  const addSkill = (id: number) => {
    if (members.some((m) => m.skill_template_id === id)) return;
    setMembers([
      ...members,
      {
        member_type: 'skill',
        skill_template_id: id,
        role: 'skill',
        skill_permission: 'allow',
        sort_order: members.length,
      },
    ]);
  };

  const patchMember = (idx: number, p: Partial<BundleMemberItem>) => {
    setMembers(members.map((m, i) => (i === idx ? { ...m, ...p } : m)));
    setDirty(true);
  };

  const removeMember = (idx: number) => {
    setMembers(members.filter((_, i) => i !== idx));
    setDirty(true);
  };

  const nameOfMember = (m: BundleMemberItem): string => {
    if (m.member_type === 'agent') {
      return agents.find((a) => a.id === m.agent_template_id)?.name ?? '?';
    }
    return skills.find((s) => s.id === m.skill_template_id)?.name ?? '?';
  };

  /** 拓扑图需要的 name→permission 映射 */
  const permissionByName = useMemo(() => {
    const out: Record<string, PermissionConfig | null | undefined> = {};
    members
      .filter((m) => m.member_type === 'agent')
      .forEach((m) => {
        const a = agents.find((x) => x.id === m.agent_template_id);
        if (a) out[a.name] = a.permission_json;
      });
    return out;
  }, [members, agents]);

  /** 主对话 / 子代理成员（委派授权矩阵用） */
  const primaryMembers = useMemo(
    () => members.filter((m) => m.member_type === 'agent' && m.role === 'primary'),
    [members],
  );
  /** 带原始索引，便于按 index 精确改某一行的 task_permission */
  const subagentMembers = useMemo(
    () =>
      members
        .map((m, idx) => ({ m, idx }))
        .filter(({ m }) => m.member_type === 'agent' && m.role === 'subagent'),
    [members],
  );

  /**
   * 授权/收回某个 subagent 的委派权限。
   *
   * 关键：写的是 **bundle 成员**的 task_permission，**不改 agent 模板**。
   * 早期实现直接改模板，导致 A 方案的授权污染共享该模板的 B 方案
   * （在一个方案里授权 docs-writer，另一个没有该成员的方案就报「规则不会生效」）。
   * 发布时由渲染器按本方案成员重新合成 permission.task。
   */
  const setTaskPermission = (memberIdx: number, action: PermissionAction) => {
    setMembers((prev) =>
      prev.map((m, i) => (i === memberIdx ? { ...m, task_permission: action } : m)),
    );
    setDirty(true);
  };

  /** 清除方案内覆盖，回到「跟随 agent 模板」 */
  const clearTaskPermission = (memberIdx: number) => {
    setMembers((prev) =>
      prev.map((m, i) => (i === memberIdx ? { ...m, task_permission: null } : m)),
    );
    setDirty(true);
  };

  /** 拓扑图需要 BundleMember 形态（带 member_name） */
  const topoMembers = useMemo(
    () =>
      members.map((m, i) => ({
        ...m,
        id: i,
        member_name: nameOfMember(m),
        member_mode:
          m.member_type === 'agent'
            ? agents.find((a) => a.id === m.agent_template_id)?.mode
            : undefined,
      })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [members, agents, skills],
  );

  const primaryOptions = useMemo(() => {
    const inBundle = members
      .filter((m) => m.member_type === 'agent' && m.role === 'primary')
      .map((m) => nameOfMember(m));
    // OpenCode 内置 primary 也可以做 default_agent
    return ['build', 'plan', ...inBundle].filter((v, i, arr) => arr.indexOf(v) === i);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [members, agents]);

  const columns: ColumnsType<AgentBundle> = [
    {
      title: '方案',
      key: 'name',
      render: (_, r) => (
        <Space orientation="vertical" size={0}>
          <Space size={5}>
            <Text strong style={{ fontSize: 12.5 }}>
              {r.name}
            </Text>
            {r.is_builtin_preset && (
              <Tag color="blue" style={{ fontSize: 10, margin: 0 }}>
                预设
              </Tag>
            )}
          </Space>
          <Text type="secondary" style={{ fontSize: 10.5 }}>
            {bundlePatternLabel[r.pattern]} · {r.members.length} 成员 · depth={r.subagent_depth ?? '默认'}
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
    <div style={{ display: 'flex', gap: 12, height: '100%', alignItems: 'flex-start', padding: '14px 16px' }}>{/* 【UI 重构】参照左侧栏 14px 垂直内边距 */}
      {/* 左：列表 */}
      <div style={{ width: 230, flexShrink: 0, background: '#FFFFFF', borderRadius: 12, border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 1px 4px rgba(0,0,0,0.04)', padding: 12, display: 'flex', flexDirection: 'column', maxHeight: '100%' }}>
        <Space style={{ marginBottom: 8 }} size={4}>
          <Button size="small" type="primary" icon={<PlusOutlined />} onClick={startCreate}>
            新建
          </Button>
          <Button
            size="small"
            icon={<ReloadOutlined />}
            loading={loading}
            onClick={() => void loadAll()}
          />
        </Space>
        {presets && presets.bundles.length > 0 && (
          <div style={{ marginBottom: 8 }}>
            <Text type="secondary" style={{ fontSize: 11 }}>
              从预设模式开始：
            </Text>
            <Select
              size="small"
              style={{ width: '100%', marginTop: 3 }}
              placeholder="选一个 Loop 模式"
              options={presets.bundles.map((b) => ({
                value: b.name,
                label: b.name,
                title: b.description,
              }))}
              onChange={applyPreset}
              value={undefined}
            />
          </div>
        )}
        <Table<AgentBundle>
          size="small"
          rowKey="id"
          columns={columns}
          dataSource={list}
          loading={loading}
          pagination={false}
          showHeader={false}
          scroll={{ y: 'calc(100vh - 340px)' }}
          onRow={(r) => ({
            onClick: () => setSelectedId(r.id),
            style: {
              cursor: 'pointer',
              background: selectedId === r.id ? 'rgba(0,113,227,0.06)' : undefined,
            },
          })}
        />
      </div>

      {/* 中：编辑 */}
      <div style={{ flex: 1, minWidth: 0, maxHeight: '100%', overflowY: 'auto', padding: 16, background: '#FFFFFF', borderRadius: 12, border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
        {!editing ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <span>
                左侧选择一个编排方案
                <br />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  或从「预设模式」一键生成骨架（含拓扑与旋钮）
                </Text>
              </span>
            }
          />
        ) : (
          <>
            <Space size={12} style={{ marginBottom: 12, flexWrap: 'wrap' }} align="start">
              <div>
                <Text strong style={{ fontSize: 13 }}>
                  方案名 <Text type="danger">*</Text>
                </Text>
                <Input
                  size="small"
                  style={{ marginTop: 4, width: 220 }}
                  placeholder="实现与评审环"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <div>
                <Text strong style={{ fontSize: 13 }}>
                  Loop 模式
                </Text>
                <Select
                  size="small"
                  style={{ marginTop: 4, width: 210 }}
                  value={pattern}
                  onChange={(v) => setPattern(v)}
                  options={PATTERNS.map((p) => ({
                    value: p,
                    label: bundlePatternLabel[p],
                    title: PATTERN_HINT[p],
                  }))}
                />
              </div>
            </Space>

            <Alert
              type="info"
              showIcon
              style={{ marginBottom: 12 }}
              title={bundlePatternLabel[pattern]}
              description={<span style={{ fontSize: 12 }}>{PATTERN_HINT[pattern]}</span>}
            />

            <div style={{ marginBottom: 12 }}>
              <Text strong style={{ fontSize: 13 }}>
                方案说明
              </Text>
              <Input.TextArea
                rows={2}
                style={{ marginTop: 4 }}
                placeholder="build 实现后自动交给只读的 code-reviewer 评审，形成「写-审」闭环。"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            {/* 全局旋钮 */}
            <Space size={16} style={{ marginBottom: 14, flexWrap: 'wrap' }} align="start">
              <div>
                <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
                  <Tooltip title="OpenCode 要求必须是 primary，否则会忽略并 fallback 到 build">
                    默认入口 agent
                  </Tooltip>
                </Text>
                <Select
                  size="small"
                  style={{ width: 180 }}
                  allowClear
                  placeholder="留空=用 OpenCode 默认"
                  value={defaultAgent || undefined}
                  onChange={(v) => setDefaultAgent(v ?? '')}
                  options={primaryOptions.map((n) => ({ value: n, label: n }))}
                />
              </div>
              <div>
                <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
                  <Tooltip title="0=禁止派生 subagent / 1=默认（primary 可派生但 subagent 不能再派生）/ 2=允许再嵌一层">
                    subagent 嵌套深度
                  </Tooltip>
                </Text>
                <Segmented
                  size="small"
                  value={String(depth ?? 1)}
                  onChange={(v) => setDepth(Number(v))}
                  options={[
                    { label: '0 禁止', value: '0' },
                    { label: '1 默认', value: '1' },
                    { label: '2 深层', value: '2' },
                  ]}
                />
              </div>
            </Space>

            <Divider style={{ margin: '12px 0' }} />

            {/* 成员 */}
            <Space size={8} style={{ marginBottom: 8, flexWrap: 'wrap' }}>
              <Text strong style={{ fontSize: 13 }}>
                成员
              </Text>
              <Select
                size="small"
                style={{ width: 190 }}
                placeholder="+ 添加 Agent"
                value={undefined}
                onChange={(v) => addAgent(Number(v))}
                options={agents
                  .filter((a) => !members.some((m) => m.agent_template_id === a.id))
                  .map((a) => ({ value: a.id, label: `${a.name} (${a.mode})` }))}
              />
              <Select
                size="small"
                style={{ width: 190 }}
                placeholder="+ 添加 Skill"
                value={undefined}
                onChange={(v) => addSkill(Number(v))}
                options={skills
                  .filter((s) => !members.some((m) => m.skill_template_id === s.id))
                  .map((s) => ({ value: s.id, label: s.name }))}
              />
            </Space>

            {members.length === 0 ? (
              <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 10 }}>
                还没有成员。至少需要一个 primary agent 才能对话（或依赖 OpenCode 内置的 build/plan）。
              </Text>
            ) : (
              <div style={{ marginBottom: 10 }}>
                {members.map((m, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '5px 8px',
                      marginBottom: 4,
                      border: '1px solid rgba(0,0,0,0.06)',
                      borderRadius: 6,
                    }}
                  >
                    <Tag
                      color={m.member_type === 'agent' ? 'blue' : 'default'}
                      style={{ fontSize: 10, margin: 0, width: 44, textAlign: 'center' }}
                    >
                      {m.member_type === 'agent' ? 'Agent' : 'Skill'}
                    </Tag>
                    <Text style={{ fontSize: 12.5, fontFamily: 'monospace', flex: 1 }}>
                      {nameOfMember(m)}
                    </Text>
                    {m.member_type === 'agent' ? (
                      <Segmented
                        size="small"
                        value={m.role}
                        onChange={(v) => patchMember(i, { role: v as 'primary' | 'subagent' })}
                        options={[
                          { label: '主对话', value: 'primary' },
                          { label: '子代理', value: 'subagent' },
                        ]}
                      />
                    ) : (
                      <Segmented
                        size="small"
                        value={m.skill_permission ?? 'allow'}
                        onChange={(v) =>
                          patchMember(i, { skill_permission: v as PermissionAction })
                        }
                        options={[
                          { label: '允许', value: 'allow' },
                          { label: '询问', value: 'ask' },
                          { label: '禁止', value: 'deny' },
                        ]}
                      />
                    )}
                    <Button
                      size="small"
                      type="text"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={() => removeMember(i)}
                    />
                  </div>
                ))}
              </div>
            )}

            {/* ---- 委派授权（Loop 的核心旋钮）---- */}
            {primaryMembers.length > 0 && subagentMembers.length > 0 && (
              <>
                <Divider style={{ margin: '12px 0' }} />
                <Space size={6} style={{ marginBottom: 6 }} wrap>
                  <BranchesOutlined style={{ color: '#0071e3' }} />{/* 【UI 重构】Apple Blue */}
                  <Text strong style={{ fontSize: 13 }}>
                    委派授权
                  </Text>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    本方案里主对话能调用哪些 subagent —— 拓扑图连线的来源
                  </Text>
                  {dirty && (
                    <Tag color="warning" style={{ fontSize: 10, margin: 0 }}>
                      有未保存改动
                    </Tag>
                  )}
                </Space>

                <Alert
                  type="info"
                  showIcon
                  style={{ marginBottom: 10 }}
                  title="授权只作用于本方案，不会改动 agent 模板"
                  description={
                    <span style={{ fontSize: 12 }}>
                      OpenCode 把委派规则（<Text code>permission.task</Text>）放在 agent 定义里，
                      但它的语义是<b>方案级</b>的。所以平台把授权存在<b>方案成员</b>上，
                      发布时按本方案成员重新合成规则 —— 既不污染其它方案，
                      也会自动剔除指向方案外 agent 的无效规则。
                    </span>
                  }
                />

                {subagentMembers.map(({ m, idx }) => {
                  const sName = nameOfMember(m);
                  const srvMember = selected?.members.find(
                    (x) => x.agent_template_id === m.agent_template_id,
                  );
                  // 未保存时以本地 task_permission 为准；否则用后端算好的 effective
                  const overridden = m.task_permission ?? null;
                  const eff =
                    overridden ??
                    (srvMember?.effective_task as PermissionAction | undefined) ??
                    'allow';
                  const source = overridden
                    ? 'bundle'
                    : (srvMember?.task_source ?? 'default');
                  const detail = overridden
                    ? `本方案显式设为 ${overridden}`
                    : srvMember?.task_source_detail;

                  const SOURCE_LABEL: Record<string, string> = {
                    bundle: '本方案',
                    template: 'agent 模板',
                    default: '默认',
                  };

                  return (
                    <div
                      key={`${m.agent_template_id}-${idx}`}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        padding: '6px 10px',
                        marginBottom: 4,
                        border: '1px solid rgba(0,0,0,0.06)',
                        borderRadius: 6,
                        flexWrap: 'wrap',
                      }}
                    >
                      <span
                        style={{
                          width: 6,
                          height: 6,
                          borderRadius: '50%',
                          background:
                            eff === 'allow' ? '#22c55e' : eff === 'ask' ? '#faad14' : '#bfbcb5',
                          flexShrink: 0,
                        }}
                      />
                      <Text
                        style={{
                          fontSize: 12.5,
                          fontFamily: 'monospace',
                          width: 148,
                          color: eff === 'deny' ? 'var(--ink-40, #8f8b84)' : undefined,
                        }}
                      >
                        {sName}
                      </Text>
                      <Segmented
                        size="small"
                        value={eff}
                        onChange={(v) => setTaskPermission(idx, v as PermissionAction)}
                        options={[
                          { label: '允许', value: 'allow' },
                          { label: '需确认', value: 'ask' },
                          { label: '禁止', value: 'deny' },
                        ]}
                      />
                      {/* 权限溯源 —— 消除"隐性规则" */}
                      <Tooltip title={detail || '未配置，OpenCode 默认允许'}>
                        <Tag
                          color={source === 'bundle' ? 'blue' : 'default'}
                          style={{ fontSize: 10, margin: 0, cursor: 'help' }}
                        >
                          来源：{SOURCE_LABEL[source] ?? source}
                        </Tag>
                      </Tooltip>
                      {overridden && (
                        <Button
                          type="link"
                          size="small"
                          style={{ fontSize: 11, padding: 0, height: 'auto' }}
                          onClick={() => clearTaskPermission(idx)}
                        >
                          跟随模板
                        </Button>
                      )}
                      {eff === 'deny' && (
                        <Text type="secondary" style={{ fontSize: 10.5 }}>
                          模型看不到它，不会指派
                        </Text>
                      )}
                    </div>
                  );
                })}

                {dirty && (
                  <Text type="warning" style={{ fontSize: 11.5, display: 'block', marginTop: 2 }}>
                    改动需点下方「保存」才会生效，随后发布到容器。
                  </Text>
                )}
              </>
            )}

            {/* 拓扑图 */}
            <Divider style={{ margin: '12px 0' }} />
            <Space size={6} style={{ marginBottom: 6 }}>
              <ApartmentOutlined style={{ color: '#0071e3' }} />{/* 【UI 重构】Apple Blue */}
              <Text strong style={{ fontSize: 13 }}>
                Loop 拓扑
              </Text>
              <Text type="secondary" style={{ fontSize: 11 }}>
                箭头方向 = 委派关系，由各 primary 的 permission.task 决定
              </Text>
            </Space>
            <div
              style={{
                border: '1px solid rgba(0,0,0,0.06)',
                borderRadius: 8,
                padding: 10,
                background: 'var(--paper-01, #fafaf7)',
                marginBottom: 12,
                overflowX: 'auto',
              }}
            >
              <LoopTopology
                members={topoMembers as never}
                pattern={pattern}
                permissionByName={permissionByName}
                subagentDepth={depth}
                defaultAgent={defaultAgent || undefined}
                width={520}
              />
            </div>

            <div style={{ marginBottom: 12 }}>
              <ValidationPanel result={validation} />
            </div>

            <Space size={8}>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                loading={saving}
                onClick={() => void save()}
              >
                {creating ? '创建' : '保存'}
              </Button>
              {!creating && selectedId && (
                <Button icon={<RocketOutlined />} onClick={() => onDeploy(selectedId)}>
                  去发布
                </Button>
              )}
              {creating && <Button onClick={() => setCreating(false)}>取消</Button>}
            </Space>
          </>
        )}
      </div>

      {/* 右：产物预览 */}
      <div style={{ width: 340, flexShrink: 0, background: '#FFFFFF', borderRadius: 12, border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 1px 4px rgba(0,0,0,0.04)', padding: 12, maxHeight: '100%', display: 'flex', flexDirection: 'column' }}>
        <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 6 }}>
          全量落盘产物
        </Text>
        {preview ? (
          <>
            <ArtifactTree
              artifacts={preview.artifacts}
              selected={previewPath}
              onSelect={setPreviewPath}
            />
            <Divider style={{ margin: '8px 0' }} />
            <ArtifactPreview
              artifact={
                preview.artifacts.find((a) => a.path === previewPath) ?? preview.artifacts[0]
              }
              maxHeight={260}
            />
          </>
        ) : (
          <Alert
            type="info"
            showIcon
            title={creating ? '保存后可预览' : '选择一个方案'}
            description={
              <span style={{ fontSize: 12 }}>
                这里列出发布时会写入容器的<b>全部文件</b>，与实际落盘一致。
              </span>
            }
          />
        )}
      </div>
    </div>
  );
}
