/**
 * ExpertTeamPage — 专家团管理页面（OALP v1.0 / Editorial Light 主题）
 *
 * 三 Tab：
 *  1. 专家 — 卡片网格 + 创建/编辑 Drawer（含 AI 一键生成、容器部署）
 *  2. Skills — 从本机 opencode/claude/.agents 发现 + 上传文件夹 + LLM 解读
 *  3. MCPs   — 从 opencode.json 发现 + LLM 解读
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  App, Button, Drawer, Empty, Form, Input, InputNumber, Modal,
  Popconfirm, Select, Space, Spin, Table, Tabs, Tag, Tooltip, Typography,
  Upload, message as antdMessage,
} from 'antd';
import type { UploadProps } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  PlusOutlined, ReloadOutlined, PoweroffOutlined,
  PlayCircleOutlined, EditOutlined, DeleteOutlined,
  ThunderboltOutlined, CloudUploadOutlined, RobotOutlined,
  InboxOutlined, FileSearchOutlined, ApiOutlined,
} from '@ant-design/icons';
import {
  expertService, type Expert, type ExpertAutoDraftResp,
  type DiscoveredSkill, type DiscoveredMCP, type AgentRelation,
} from '../../services/expert.service';
import { resourcesAPI, type MCPConfig } from '../../services/resourcesAPI';
import { fetchNodes, fetchTemplates } from '../../services/compute.service';
import type { ComputeNode, ContainerTemplate } from '../../pages/compute/types';

const { Text, Paragraph } = Typography;
const { Dragger } = Upload;

const STATUS_META: Record<Expert['status'], { color: string; label: string; dot: string }> = {
  online:  { color: '#476a4b', label: '在线',   dot: '#22c55e' },
  offline: { color: '#8f8b84', label: '离线',   dot: '#bfbcb5' },
  error:   { color: '#a5361e', label: '错误',   dot: '#ef4444' },
};

interface FormValues {
  id?: number;
  name: string;
  slug: string;
  avatar?: string;
  description?: string;
  role?: string;
  sop?: string;
  provider?: string;
  model?: string;
  temperature?: number;
  top_p?: number;
  mode?: 'primary' | 'subagent' | 'all';
  subagent_depth?: number;
  max_steps?: number;
  system_prompt?: string;
  skills?: string[];
  mcps?: string[];
  host?: string;
  port?: number;
  bind_skills_to_container?: boolean;
  container_template_id?: number;
  allowRead?: boolean;
  allowWrite?: boolean;
  allowBash?: boolean;
  allowTodo?: boolean;
}

export default function ExpertTeamPage() {
  const { message } = App.useApp();
  const [activeTab, setActiveTab] = useState<'experts' | 'skills' | 'mcps'>('experts');

  // ---- expert state ----
  const [experts, setExperts] = useState<Expert[]>([]);
  const [loading, setLoading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [editing, setEditing] = useState<Expert | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [form] = Form.useForm<FormValues>();

  // AI 一键生成
  const [autoDraftOpen, setAutoDraftOpen] = useState(false);
  const [autoDraftText, setAutoDraftText] = useState('');
  const [autoDraftLoading, setAutoDraftLoading] = useState(false);

  // 容器部署
  const [deployOpen, setDeployOpen] = useState(false);
  const [deployExpert, setDeployExpert] = useState<Expert | null>(null);
  const [deployNodeId, setDeployNodeId] = useState<number | undefined>();
  const [deployTemplateId, setDeployTemplateId] = useState<number | undefined>();
  const [deployPort, setDeployPort] = useState<number | undefined>();
  const [deployLoading, setDeployLoading] = useState(false);
  const [nodes, setNodes] = useState<ComputeNode[]>([]);
  const [templates, setTemplates] = useState<ContainerTemplate[]>([]);

  // ---- skill/mcp state ----
  const [discoveredSkills, setDiscoveredSkills] = useState<DiscoveredSkill[]>([]);
  const [discoveredMCPs, setDiscoveredMCPs] = useState<DiscoveredMCP[]>([]);
  const [dbSkills, setDbSkills] = useState<any[]>([]);
  const [dbMCPs, setDbMCPs] = useState<MCPConfig[]>([]);
  const [discoverLoading, setDiscoverLoading] = useState(false);
  const [summarizing, setSummarizing] = useState<number | null>(null);
  const [relations, setRelations] = useState<AgentRelation[]>([]);

  // ---- 关系编辑（专家抽屉里做"添加子 agent"）----
  const [relDrawerOpen, setRelDrawerOpen] = useState(false);
  const [relParent, setRelParent] = useState<Expert | null>(null);
  const [relForm] = Form.useForm<{
    child_expert_id: number;
    relation: 'delegate' | 'fan_out' | 'review';
    condition?: string;
    sort_order?: number;
  }>();

  // ---- loaders ----
  const loadExperts = useCallback(async () => {
    setLoading(true);
    try {
      setExperts(await expertService.list());
    } catch (err) {
      message.error(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [message]);

  const loadRelations = useCallback(async () => {
    try {
      setRelations(await expertService.listRelations());
    } catch {
      // 静默失败，不影响主流程
    }
  }, []);

  const loadSkillMcp = useCallback(async () => {
    setDiscoverLoading(true);
    try {
      const [skills, mcps, dbSk, dbMc, rels] = await Promise.allSettled([
        expertService.discoverSkills(),
        expertService.discoverMCPs(),
        resourcesAPI.listSkills({ limit: 200 }),
        resourcesAPI.listMCPs({ limit: 200 }),
        expertService.listRelations(),
      ]);
      if (skills.status === 'fulfilled') setDiscoveredSkills(skills.value);
      if (mcps.status === 'fulfilled') setDiscoveredMCPs(mcps.value);
      if (dbSk.status === 'fulfilled') setDbSkills((dbSk.value as any).data?.data ?? (dbSk.value as any).data ?? []);
      if (dbMc.status === 'fulfilled') setDbMCPs((dbMc.value as any).data?.data ?? (dbMc.value as any).data ?? []);
      if (rels.status === 'fulfilled') setRelations(rels.value);
    } catch (err) {
      message.error(err instanceof Error ? err.message : '加载失败');
    } finally {
      setDiscoverLoading(false);
    }
  }, [message]);

  useEffect(() => {
    void loadExperts();
    const t = window.setInterval(() => void loadExperts(), 10000);
    return () => window.clearInterval(t);
  }, [loadExperts]);

  const stats = useMemo(() => ({
    online: experts.filter((e) => e.status === 'online').length,
    total: experts.length,
    offline: experts.filter((e) => e.status !== 'online').length,
  }), [experts]);

  // ---- expert form ----
  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({
      host: '127.0.0.1', port: 4096,
      provider: 'agent-plan', model: 'ark-code-latest',
      mode: 'subagent', subagent_depth: 1, max_steps: undefined,
      skills: [], mcps: [],
      bind_skills_to_container: true,
      allowRead: true, allowWrite: true, allowBash: true, allowTodo: true,
    });
    setDrawerOpen(true);
  };

  const openEdit = (e: Expert) => {
    setEditing(e);
    form.resetFields();
    form.setFieldsValue({
      id: e.id, name: e.name, slug: e.slug,
      avatar: e.avatar ?? '',
      description: e.description ?? '',
      role: e.role ?? '',
      sop: e.sop ?? '',
      provider: e.provider ?? undefined,
      model: e.model ?? undefined,
      temperature: e.temperature ? Number(e.temperature) : undefined,
      top_p: e.top_p ? Number(e.top_p) : undefined,
      mode: e.mode,
      subagent_depth: e.subagent_depth,
      max_steps: e.max_steps ?? undefined,
      skills: e.skills ?? [],
      mcps: e.mcps ?? [],
      host: e.host, port: e.port,
      bind_skills_to_container: e.bind_skills_to_container,
      container_template_id: e.container_template_id ?? undefined,
      allowRead: e.tools?.read ?? true,
      allowWrite: e.tools?.write ?? true,
      allowBash: e.tools?.bash ?? true,
      allowTodo: e.tools?.todo ?? true,
    });
    setDrawerOpen(true);
  };

  const seed = async () => {
    setSeeding(true);
    try {
      const { added } = await expertService.seed();
      message.success(`已注入 ${added} 个内置专家`);
      await Promise.all([loadExperts(), loadRelations()]);
    } catch (err) {
      message.error(err instanceof Error ? err.message : '初始化失败');
    } finally {
      setSeeding(false);
    }
  };

  const doStart = async (e: Expert) => {
    setBusyId(e.id);
    try {
      await expertService.start(e.id);
      message.success(`${e.name} 已启动`);
      await loadExperts();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '启动失败');
    } finally { setBusyId(null); }
  };

  const doStop = async (e: Expert) => {
    setBusyId(e.id);
    try {
      await expertService.stop(e.id);
      message.success(`${e.name} 已关闭`);
      await loadExperts();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '关闭失败');
    } finally { setBusyId(null); }
  };

  const doDelete = async () => {
    if (!editing) return;
    try {
      await expertService.remove(editing.id);
      message.success(`${editing.name} 已删除`);
      setDrawerOpen(false); setEditing(null);
      await loadExperts();
      await loadRelations();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '删除失败');
    }
  };

  const submitForm = async () => {
    const v = await form.validateFields();
    const tools: Record<string, boolean> = {};
    if (v.allowRead) tools.read = true;
    if (v.allowWrite) tools.write = true;
    if (v.allowBash) tools.bash = true;
    if (v.allowTodo) tools.todo = true;

    const permission: Record<string, any> = {
      edit: v.allowWrite ? 'allow' : 'ask',
      bash: v.allowBash ? 'allow' : 'ask',
    };

    const payload = {
      name: v.name,
      avatar: v.avatar || null,
      description: v.description || null,
      role: v.role || null,
      sop: v.sop || null,
      provider: v.provider || null,
      model: v.model || null,
      temperature: v.temperature != null ? String(v.temperature) : null,
      top_p: v.top_p != null ? String(v.top_p) : null,
      mode: v.mode,
      subagent_depth: v.subagent_depth,
      max_steps: v.max_steps || null,
      system_prompt: v.role || null,
      permission,
      skills: v.skills ?? [],
      mcps: v.mcps ?? [],
      tools,
      host: v.host,
      port: v.port,
      bind_skills_to_container: v.bind_skills_to_container,
      container_template_id: v.container_template_id,
    };
    try {
      if (editing) {
        await expertService.update(editing.id, payload as any);
        message.success('已更新');
      } else {
        await expertService.create({ ...payload, slug: v.slug } as any);
        message.success('已创建');
      }
      setDrawerOpen(false); setEditing(null);
      await loadExperts();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '保存失败');
    }
  };

  // ---- AI 一键生成 ----
  const doAutoDraft = async () => {
    if (!autoDraftText.trim()) {
      message.warning('请输入一段描述');
      return;
    }
    setAutoDraftLoading(true);
    try {
      const draft: ExpertAutoDraftResp = await expertService.autoDraft(autoDraftText.trim());
      setAutoDraftOpen(false);
      setAutoDraftText('');
      // 跳到创建表单，预填
      setEditing(null);
      form.resetFields();
      form.setFieldsValue({
        name: draft.name,
        slug: draft.slug,
        avatar: draft.avatar,
        description: draft.description,
        role: draft.role,
        sop: draft.sop,
        provider: draft.provider,
        model: draft.model,
        temperature: Number(draft.temperature) || 0.3,
        skills: draft.skills || [],
        mcps: draft.mcps || [],
        host: '127.0.0.1', port: 4096,
        mode: 'subagent', subagent_depth: 1,
        bind_skills_to_container: true,
        allowRead: true, allowWrite: true, allowBash: true, allowTodo: true,
      });
      setDrawerOpen(true);
      message.success('草稿已生成，请微调后保存');
    } catch (err) {
      message.error(err instanceof Error ? err.message : '生成失败');
    } finally {
      setAutoDraftLoading(false);
    }
  };

  // ---- 容器部署 ----
  const openDeploy = async (e: Expert) => {
    setDeployExpert(e);
    setDeployNodeId(undefined);
    setDeployTemplateId(undefined);
    setDeployPort(undefined);
    setDeployOpen(true);
    // 加载节点 + 模板
    try {
      const [nodesData, tplData] = await Promise.all([
        fetchNodes(),
        fetchTemplates(),
      ]);
      setNodes(nodesData);
      setTemplates(tplData);
      // 优先选本地节点
      const local = nodesData.find((n: ComputeNode) => n.connType === 'local');
      if (local) setDeployNodeId(local.id);
      const opencodeAgent = tplData.find((t: ContainerTemplate) => t.name === 'opencode-agent');
      if (opencodeAgent) setDeployTemplateId(opencodeAgent.id);
    } catch (err) {
      // 静默
    }
  };

  const doDeploy = async () => {
    if (!deployExpert || !deployNodeId) {
      message.warning('请选择节点');
      return;
    }
    setDeployLoading(true);
    try {
      const res = await expertService.deployContainer(deployExpert.id, {
        node_id: deployNodeId,
        container_template_id: deployTemplateId,
        host_port: deployPort,
        auto_start: true,
      });
      message.success(`容器已部署：${res.container.url}${res.container.healthy ? ' (健康)' : ' (待健康检查)'}`);
      setDeployOpen(false);
      await loadExperts();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '部署失败');
    } finally {
      setDeployLoading(false);
    }
  };

  // ---- 关系管理 ----
  const openRelDrawer = (e: Expert) => {
    setRelParent(e);
    relForm.resetFields();
    relForm.setFieldsValue({ relation: 'delegate', sort_order: 0 });
    setRelDrawerOpen(true);
  };

  const submitRel = async () => {
    if (!relParent) return;
    const v = await relForm.validateFields();
    try {
      await expertService.createRelation({
        parent_expert_id: relParent.id,
        child_expert_id: v.child_expert_id,
        relation: v.relation,
        condition: v.condition,
        sort_order: v.sort_order || 0,
      });
      message.success('关系已建立（同步到 opencode.json）');
      setRelDrawerOpen(false);
      await loadRelations();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '创建关系失败');
    }
  };

  const deleteRel = async (id: number) => {
    try {
      await expertService.deleteRelation(id);
      message.success('已删除');
      await loadRelations();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '删除失败');
    }
  };

  // ---- skill / mcp ----
  const loadAll = useCallback(async () => {
    await Promise.all([loadSkillMcp()]);
  }, [loadSkillMcp]);

  useEffect(() => {
    if (activeTab !== 'experts') void loadAll();
  }, [activeTab, loadAll]);

  const doLoadSkills = async () => {
    try {
      const r = await expertService.loadSkills();
      message.success(`已加载：新增 ${r.added}，更新 ${r.updated}`);
      await loadAll();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '加载失败');
    }
  };

  const doLoadMCPs = async () => {
    try {
      const r = await expertService.loadMCPs();
      message.success(`已加载：新增 ${r.added}，更新 ${r.updated}`);
      await loadAll();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '加载失败');
    }
  };

  const uploadProps: UploadProps = {
    name: 'file',
    accept: '.zip',
    showUploadList: false,
    beforeUpload: async (file) => {
      try {
        const r = await expertService.uploadSkillFolder(file as any, false);
        const msg = `上传完成：新增 ${r.added} / 更新 ${r.updated} / 跳过 ${r.skipped}`;
        if (r.errors?.length) {
          antdMessage.warning(`${msg}，前 ${r.errors.length} 个错误已打印到控制台`);
          // eslint-disable-next-line no-console
          console.warn('[skill-upload] errors:', r.errors);
        } else {
          antdMessage.success(msg);
        }
        await loadAll();
      } catch (err) {
        antdMessage.error(err instanceof Error ? err.message : '上传失败');
      }
      return false; // 阻止默认上传
    },
  };

  const doSummarizeSkill = async (id: number) => {
    setSummarizing(id);
    try {
      await expertService.summarizeSkill(id);
      message.success('已生成解读');
      await loadAll();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '解读失败');
    } finally { setSummarizing(null); }
  };

  const doSummarizeMCP = async (id: number) => {
    setSummarizing(id);
    try {
      await expertService.summarizeMCP(id);
      message.success('已生成解读');
      await loadAll();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '解读失败');
    } finally { setSummarizing(null); }
  };

  // ---- 渲染 ----
  return (
    <div style={{ maxWidth: 1400, margin: '0 auto', padding: '8px 16px 24px' }}>
      <div style={{
        display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between',
        gap: 24, padding: '24px 4px 20px',
        borderBottom: '1px solid var(--border-hairline)', marginBottom: 24,
      }}>
        <div>
          <h1 style={{
            fontFamily: 'var(--font-serif)', fontSize: 34, fontWeight: 500,
            letterSpacing: '-0.02em', margin: 0, color: 'var(--ink-100)', fontStyle: 'italic',
          }}>专家团</h1>
          <Text style={{ color: 'var(--ink-60)', fontSize: 13, marginTop: 6, display: 'block' }}>
            OALP v1.0 — 每位专家 = opencode agent + 模型 + Skill/MCP 组合 + 可选容器
          </Text>
          <Space size={16} style={{ marginTop: 10 }}>
            <span style={{ fontSize: 12, color: 'var(--ink-40)' }}>
              总数 <b style={{ color: 'var(--ink-100)' }}>{stats.total}</b>
            </span>
            <span style={{ fontSize: 12, color: 'var(--ink-40)' }}>
              在线 <b style={{ color: '#22c55e' }}>{stats.online}</b>
            </span>
            <span style={{ fontSize: 12, color: 'var(--ink-40)' }}>
              离线 <b style={{ color: 'var(--ink-60)' }}>{stats.offline}</b>
            </span>
          </Space>
        </div>
        <Space>
          <Tooltip title="刷新">
            <Button icon={<ReloadOutlined />} onClick={() => {
              if (activeTab === 'experts') void loadExperts();
              else void loadAll();
            }} />
          </Tooltip>
          {activeTab === 'experts' && (
            <>
              <Button icon={<ThunderboltOutlined />} onClick={() => setAutoDraftOpen(true)}>
                AI 一键生成
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
                添加专家
              </Button>
            </>
          )}
        </Space>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={(k) => setActiveTab(k as any)}
        items={[
          {
            key: 'experts',
            label: <span><RobotOutlined /> 专家 ({stats.total})</span>,
            children: renderExpertsTab(),
          },
          {
            key: 'skills',
            label: <span><FileSearchOutlined /> Skills ({dbSkills.length})</span>,
            children: renderSkillsTab(),
          },
          {
            key: 'mcps',
            label: <span><ApiOutlined /> MCPs ({dbMCPs.length})</span>,
            children: renderMcpTab(),
          },
        ]}
      />

      {renderExpertDrawer()}
      {renderAutoDraftModal()}
      {renderDeployDrawer()}
      {renderRelDrawer()}
    </div>
  );

  // ---- 子函数：每个 tab 渲染 ----
  function renderExpertsTab() {
    if (loading && experts.length === 0) {
      return <div style={{ padding: 80, textAlign: 'center' }}><Spin /></div>;
    }
    if (experts.length === 0) {
      return (
        <div style={{
          padding: '80px 24px', textAlign: 'center',
          border: '1px dashed var(--border-subtle)', borderRadius: 14,
        }}>
          <Empty description={<span style={{ color: 'var(--ink-60)' }}>专家团为空</span>} />
          <Space style={{ marginTop: 16 }}>
            <Button type="primary" loading={seeding} onClick={seed}>
              注入 4 个内置专家
            </Button>
            <Button icon={<ThunderboltOutlined />} onClick={() => setAutoDraftOpen(true)}>
              AI 一键生成
            </Button>
          </Space>
        </div>
      );
    }
    return (
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
        gap: 16,
      }}>
        {experts.map((e) => {
          const meta = STATUS_META[e.status];
          const childCount = relations.filter((r) => r.parent_expert_id === e.id).length;
          return (
            <div
              key={e.id}
              onClick={() => openEdit(e)}
              style={{
                background: 'var(--paper-00)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 14, padding: 20, cursor: 'pointer',
                transition: 'border-color .12s, box-shadow .12s',
                position: 'relative', display: 'flex', flexDirection: 'column',
                gap: 12, minHeight: 200,
              }}
              onMouseEnter={(ev) => {
                ev.currentTarget.style.borderColor = 'var(--border-default)';
                ev.currentTarget.style.boxShadow = 'var(--shadow-sm)';
              }}
              onMouseLeave={(ev) => {
                ev.currentTarget.style.borderColor = 'var(--border-subtle)';
                ev.currentTarget.style.boxShadow = 'none';
              }}
            >
              <span style={{
                position: 'absolute', top: 16, right: 16,
                display: 'inline-flex', alignItems: 'center', gap: 6,
                fontSize: 11, color: meta.color, fontWeight: 500,
              }}>
                <span style={{
                  width: 6, height: 6, borderRadius: '50%',
                  background: meta.dot,
                  boxShadow: e.status === 'online' ? `0 0 0 3px ${meta.dot}22` : 'none',
                }} />
                {meta.label}
              </span>

              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                <div style={{
                  width: 44, height: 44, borderRadius: 12,
                  background: 'var(--paper-02)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 24, lineHeight: 1, flexShrink: 0,
                }}>{e.avatar || '🧑‍💼'}</div>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{
                    fontFamily: 'var(--font-serif)', fontSize: 17, fontWeight: 500,
                    color: 'var(--ink-100)', letterSpacing: '-0.01em',
                  }}>{e.name}</div>
                  {e.description && (
                    <Text style={{
                      fontSize: 12.5, color: 'var(--ink-60)', display: 'block', marginTop: 2,
                      overflow: 'hidden', textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap', maxWidth: 220,
                    }} title={e.description}>{e.description}</Text>
                  )}
                </div>
              </div>

              {e.role && (
                <Paragraph ellipsis={{ rows: 2 }} style={{
                  margin: 0, fontSize: 12.5, color: 'var(--ink-60)', lineHeight: 1.6,
                }}>{e.role.replace(/^#[^\n]*\n\n?/, '')}</Paragraph>
              )}

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {e.model && (
                  <Tag style={{
                    fontFamily: 'var(--font-mono)', fontSize: 10,
                    color: 'var(--ink-80)', background: 'var(--paper-02)',
                    border: '1px solid var(--border-hairline)',
                  }}>{e.model}</Tag>
                )}
                <Tag style={{ fontSize: 10, color: 'var(--ink-60)' }}>
                  {e.mode}{e.subagent_depth ? ` · d${e.subagent_depth}` : ''}
                </Tag>
                {e.container_id && (
                  <Tag color="geekblue" style={{ fontSize: 10 }}>容器化</Tag>
                )}
                {(e.skills || []).slice(0, 3).map((s) => (
                  <Tag key={s} style={{
                    fontSize: 10, color: 'var(--accent, #3b52af)',
                    background: 'rgba(59, 82, 175, 0.08)',
                    border: '1px solid rgba(59, 82, 175, 0.20)',
                  }}>{s}</Tag>
                ))}
                {e.skills && e.skills.length > 3 && (
                  <Tag style={{ fontSize: 10 }}>+{e.skills.length - 3}</Tag>
                )}
              </div>

              {childCount > 0 && (
                <div style={{ fontSize: 11, color: 'var(--ink-40)' }}>
                  可调用子专家：<b style={{ color: 'var(--accent)' }}>{childCount}</b> 个
                </div>
              )}

              <div style={{
                marginTop: 'auto', display: 'flex', gap: 8, flexWrap: 'wrap',
                paddingTop: 12, borderTop: '1px solid var(--border-hairline)',
              }} onClick={(ev) => ev.stopPropagation()}>
                {e.status === 'online' ? (
                  <Button danger size="small" icon={<PoweroffOutlined />}
                    loading={busyId === e.id} onClick={() => void doStop(e)}>关闭</Button>
                ) : (
                  <Button type="primary" size="small" icon={<PlayCircleOutlined />}
                    loading={busyId === e.id} onClick={() => void doStart(e)}>启动</Button>
                )}
                <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(e)}>编辑</Button>
                <Button size="small" icon={<CloudUploadOutlined />}
                  onClick={() => void openDeploy(e)}>部署容器</Button>
                <Button size="small" onClick={() => openRelDrawer(e)}>关系</Button>
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  function renderSkillsTab() {
    const skillCols: ColumnsType<any> = [
      { title: '名称', dataIndex: 'name', width: 180,
        render: (v: string) => <code style={{ fontSize: 12 }}>{v}</code> },
      { title: '类型', dataIndex: 'type', width: 100 },
      { title: '源路径', dataIndex: 'source_path', ellipsis: true,
        render: (v: string) => v ? <Text style={{ fontSize: 11, color: 'var(--ink-60)' }}>{v}</Text> : '-' },
      { title: '状态', dataIndex: 'is_loaded', width: 90,
        render: (v: boolean) => v
          ? <Tag color="green" style={{ fontSize: 10 }}>已加载</Tag>
          : <Tag style={{ fontSize: 10 }}>未加载</Tag> },
      { title: 'LLM 解读', dataIndex: 'auto_description', ellipsis: true,
        render: (v: string) => v
          ? <Tooltip title={<pre style={{ whiteSpace: 'pre-wrap', maxWidth: 480 }}>{v}</pre>}>
              <span style={{ fontSize: 12, color: 'var(--ink-80)' }}>{v.replace(/\n/g, ' ').slice(0, 80)}…</span>
            </Tooltip>
          : <Text style={{ fontSize: 11, color: 'var(--ink-40)' }}>—</Text> },
      { title: '操作', width: 160, fixed: 'right',
        render: (_: any, row: any) => (
          <Space size={4}>
            <Button size="small" icon={<RobotOutlined />} loading={summarizing === row.id}
              onClick={() => void doSummarizeSkill(row.id)}>LLM 解读</Button>
          </Space>
        ) },
    ];

    return (
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <Button icon={<ReloadOutlined />} onClick={loadAll} loading={discoverLoading}>重新发现</Button>
          <Button type="primary" icon={<CloudUploadOutlined />} onClick={doLoadSkills}>
            全部加载到 DB（{discoveredSkills.length}）
          </Button>
          <Dragger {...uploadProps} style={{ width: 280, padding: '4px 8px' }}>
            <p className="ant-upload-drag-icon" style={{ marginBottom: 2 }}>
              <InboxOutlined style={{ fontSize: 18 }} />
            </p>
            <p style={{ fontSize: 12, margin: 0 }}>拖入 zip 或点击上传</p>
          </Dragger>
          <Text style={{ fontSize: 12, color: 'var(--ink-60)' }}>
            已发现 <b>{discoveredSkills.length}</b> 个 SKILL.md（opencode + claude + .agents）
          </Text>
        </div>
        <Table rowKey="id" loading={discoverLoading} dataSource={dbSkills} columns={skillCols}
          size="small" pagination={{ pageSize: 20 }} scroll={{ x: 900 }} />
      </Space>
    );
  }

  function renderMcpTab() {
    const mcpCols: ColumnsType<MCPConfig> = [
      { title: '名称', dataIndex: 'name', width: 220,
        render: (v: string) => <code style={{ fontSize: 12 }}>{v}</code> },
      { title: '类型', dataIndex: 'transport_type', width: 90 },
      { title: '命令/URL', dataIndex: 'url', ellipsis: true,
        render: (_: any, row: MCPConfig) => {
          if (row.url) return <Text style={{ fontSize: 11, fontFamily: 'var(--font-mono)' }}>{row.url}</Text>;
          const cmd = row.command as any;
          if (Array.isArray(cmd)) return <Text style={{ fontSize: 11, fontFamily: 'var(--font-mono)' }}>{cmd.join(' ')}</Text>;
          if (typeof cmd === 'string') return <Text style={{ fontSize: 11 }}>{cmd}</Text>;
          return '-';
        } },
      { title: '启用', dataIndex: 'is_active', width: 80,
        render: (v: boolean) => v ? <Tag color="green" style={{ fontSize: 10 }}>ON</Tag> : <Tag style={{ fontSize: 10 }}>OFF</Tag> },
      { title: 'LLM 解读', dataIndex: 'auto_description', ellipsis: true,
        render: (v: string) => v
          ? <Tooltip title={<pre style={{ whiteSpace: 'pre-wrap', maxWidth: 480 }}>{v}</pre>}>
              <span style={{ fontSize: 12, color: 'var(--ink-80)' }}>{v.replace(/\n/g, ' ').slice(0, 80)}…</span>
            </Tooltip>
          : <Text style={{ fontSize: 11, color: 'var(--ink-40)' }}>—</Text> },
      { title: '操作', width: 160, fixed: 'right',
        render: (_: any, row: MCPConfig) => (
          <Space size={4}>
            <Button size="small" icon={<RobotOutlined />} loading={summarizing === row.id}
              onClick={() => void doSummarizeMCP(row.id)}>LLM 解读</Button>
          </Space>
        ) },
    ];

    return (
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <Button icon={<ReloadOutlined />} onClick={loadAll} loading={discoverLoading}>重新发现</Button>
          <Button type="primary" icon={<CloudUploadOutlined />} onClick={doLoadMCPs}>
            全部加载到 DB（{discoveredMCPs.length}）
          </Button>
          <Text style={{ fontSize: 12, color: 'var(--ink-60)' }}>
            已发现 <b>{discoveredMCPs.length}</b> 个 MCP（来自 opencode.json）
          </Text>
        </div>
        <Table rowKey="id" loading={discoverLoading} dataSource={dbMCPs} columns={mcpCols}
          size="small" pagination={{ pageSize: 20 }} scroll={{ x: 900 }} />
      </Space>
    );
  }

  function renderExpertDrawer() {
    return (
      <Drawer
        title={<span style={{ fontFamily: 'var(--font-serif)', fontSize: 18, fontWeight: 500 }}>
          {editing ? `编辑：${editing.name}` : '添加专家'}
        </span>}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={680}
        footer={
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <div>
              {editing && (
                <Popconfirm title={`确认删除「${editing.name}」？`} onConfirm={() => void doDelete()}>
                  <Button danger icon={<DeleteOutlined />}>删除</Button>
                </Popconfirm>
              )}
            </div>
            <Space>
              <Button onClick={() => setDrawerOpen(false)}>取消</Button>
              <Button type="primary" onClick={() => void submitForm()}>保存</Button>
            </Space>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <div style={sectionLabelStyle}>基本信息</div>
          <Space size={12} style={{ display: 'flex', width: '100%' }}>
            <Form.Item name="avatar" label="头像" style={{ width: 80, marginBottom: 12 }}>
              <Input placeholder="📊" maxLength={4} style={{ textAlign: 'center', fontSize: 18 }} />
            </Form.Item>
            <Form.Item name="name" label="名称" rules={[{ required: true }]} style={{ flex: 1, marginBottom: 12 }}>
              <Input placeholder="数据分析专家" />
            </Form.Item>
          </Space>
          <Form.Item name="slug" label="标识符 (slug — opencode agent 名)"
            tooltip="生成 ~/.config/opencode/agent/{slug}.md"
            rules={[
              { required: true },
              { pattern: /^[a-z0-9-]+$/, message: '仅允许小写字母、数字、连字符' },
            ]}
          >
            <Input placeholder="data-analyst" disabled={!!editing} />
          </Form.Item>
          <Form.Item name="description" label="一句话描述">
            <Input placeholder="擅长 SQL、数据建模、指标定义与数据可视化" maxLength={200} />
          </Form.Item>

          <div style={sectionLabelStyle}>角色 & 工作流</div>
          <Form.Item name="role" label="角色定位 (写入 agent md 顶部)">
            <Input.TextArea rows={5}
              placeholder={`# 角色定位\n\n你是一位资深数据分析师...`}
              style={{ fontFamily: 'var(--font-sans)', fontSize: 13 }}
            />
          </Form.Item>
          <Form.Item name="sop" label="SOP / 工作流程 (写入 agent md 底部)">
            <Input.TextArea rows={3}
              placeholder="1. 理解需求 → 2. 探查数据 → 3. 编写 SQL → 4. 验证 → 5. 出图"
              style={{ fontFamily: 'var(--font-sans)', fontSize: 13 }}
            />
          </Form.Item>

          <div style={sectionLabelStyle}>OALP 模式 / 循环约束</div>
          <Space size={12} style={{ display: 'flex', width: '100%' }}>
            <Form.Item name="mode" label="Mode" style={{ flex: 1, marginBottom: 12 }}>
              <Select options={[
                { value: 'subagent', label: 'subagent (默认，可被 @ 引用)' },
                { value: 'primary', label: 'primary (主对话)' },
                { value: 'all', label: 'all (两种都行)' },
              ]} />
            </Form.Item>
            <Form.Item name="subagent_depth" label="最大嵌套深度" style={{ width: 140, marginBottom: 12 }}>
              <InputNumber min={0} max={5} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="max_steps" label="最大循环步数" style={{ width: 140, marginBottom: 12 }}>
              <InputNumber min={1} max={10000} style={{ width: '100%' }} placeholder="不限" />
            </Form.Item>
          </Space>

          <div style={sectionLabelStyle}>模型配置</div>
          <Space size={12} style={{ display: 'flex', width: '100%' }}>
            <Form.Item name="provider" label="Provider" style={{ flex: 1, marginBottom: 12 }}>
              <Input placeholder="agent-plan" />
            </Form.Item>
            <Form.Item name="model" label="Model" style={{ flex: 2, marginBottom: 12 }}>
              <Input placeholder="ark-code-latest" />
            </Form.Item>
          </Space>
          <Space size={12} style={{ display: 'flex', width: '100%' }}>
            <Form.Item name="temperature" label="Temperature" style={{ width: 140, marginBottom: 12 }}>
              <InputNumber min={0} max={2} step={0.1} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="top_p" label="Top P" style={{ width: 140, marginBottom: 12 }}>
              <InputNumber min={0} max={1} step={0.05} style={{ width: '100%' }} />
            </Form.Item>
          </Space>

          <div style={sectionLabelStyle}>能力（Skills / MCPs / Tools）</div>
          <Form.Item name="skills" label="Skills" tooltip="从「Skills」Tab 加载后这里能多选">
            <Select mode="tags" placeholder="选或输入"
              options={dbSkills.map((s) => ({ value: s.name, label: s.name }))}
              tokenSeparators={[',', ' ']} />
          </Form.Item>
          <Form.Item name="mcps" label="MCPs" tooltip="从「MCPs」Tab 加载后这里能多选">
            <Select mode="tags" placeholder="选或输入"
              options={dbMCPs.map((m) => ({ value: m.name, label: m.name }))}
              tokenSeparators={[',', ' ']} />
          </Form.Item>
          <Form.Item label="工具权限">
            <Space size={16} wrap>
              <Form.Item name="allowRead" valuePropName="checked" noStyle>
                <label><input type="checkbox" style={{ marginRight: 4 }} />read</label>
              </Form.Item>
              <Form.Item name="allowWrite" valuePropName="checked" noStyle>
                <label><input type="checkbox" style={{ marginRight: 4 }} />write</label>
              </Form.Item>
              <Form.Item name="allowBash" valuePropName="checked" noStyle>
                <label><input type="checkbox" style={{ marginRight: 4 }} />bash</label>
              </Form.Item>
              <Form.Item name="allowTodo" valuePropName="checked" noStyle>
                <label><input type="checkbox" style={{ marginRight: 4 }} />todo</label>
              </Form.Item>
            </Space>
          </Form.Item>

          <div style={sectionLabelStyle}>opencode 服务端点（容器部署时改）</div>
          <Space size={12} style={{ display: 'flex', width: '100%' }}>
            <Form.Item name="host" label="Host" style={{ flex: 2, marginBottom: 0 }}>
              <Input placeholder="127.0.0.1" />
            </Form.Item>
            <Form.Item name="port" label="Port" style={{ width: 120, marginBottom: 0 }}>
              <InputNumber style={{ width: '100%' }} min={1} max={65535} />
            </Form.Item>
          </Space>
          <Form.Item name="bind_skills_to_container" valuePropName="checked"
            style={{ marginTop: 12 }}
            tooltip="容器化时自动把 expert md + skills + opencode.json mount 进去">
            <label><input type="checkbox" style={{ marginRight: 4 }} />容器拉起时注入 skills / opencode.json</label>
          </Form.Item>
        </Form>
      </Drawer>
    );
  }

  function renderAutoDraftModal() {
    return (
      <Modal
        open={autoDraftOpen}
        title={<span><ThunderboltOutlined /> AI 一键生成专家</span>}
        onCancel={() => setAutoDraftOpen(false)}
        onOk={() => void doAutoDraft()}
        okText="生成草稿"
        confirmLoading={autoDraftLoading}
      >
        <p style={{ color: 'var(--ink-60)', fontSize: 13 }}>
          用一段自然语言描述这个专家的工作内容，后端会调 LLM 帮你填好 name / slug / role / sop / skills / mcps 等字段。
          生成后你可以再微调保存。
        </p>
        <Input.TextArea
          rows={5}
          value={autoDraftText}
          onChange={(e) => setAutoDraftText(e.target.value)}
          placeholder="例：帮我写一个会做 Python 单元测试的专家，熟悉 pytest + mock 库，能给现有代码补测试。"
          maxLength={500}
          showCount
        />
      </Modal>
    );
  }

  function renderDeployDrawer() {
    return (
      <Drawer
        open={deployOpen}
        title={<span><CloudUploadOutlined /> 容器化部署：{deployExpert?.name}</span>}
        onClose={() => setDeployOpen(false)}
        width={520}
        footer={
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={() => setDeployOpen(false)}>取消</Button>
            <Button type="primary" loading={deployLoading} onClick={() => void doDeploy()}>
              拉起容器
            </Button>
          </Space>
        }
      >
        <p style={{ color: 'var(--ink-60)', fontSize: 13 }}>
          部署后会：写最新 agent md → 拉起 opencode 容器 → mount 专家 md + skills + opencode.json
          → 健康检查 → 写回 expert 行的 container_id / host_port。
        </p>
        <Form layout="vertical">
          <Form.Item label="Docker 节点">
            <Select
              value={deployNodeId}
              onChange={(v) => setDeployNodeId(v)}
              placeholder="选一个 Docker 节点"
              options={nodes.map((n) => ({
                value: n.id, label: `${n.name} (${n.connType})`,
              }))}
            />
          </Form.Item>
          <Form.Item label="容器模板">
            <Select
              value={deployTemplateId}
              onChange={(v) => setDeployTemplateId(v)}
              placeholder="默认 opencode-agent"
              allowClear
              options={templates.map((t) => ({ value: t.id, label: `${t.name} · ${t.image}` }))}
            />
          </Form.Item>
          <Form.Item label="宿主机端口（留空自动选 14100-15100）">
            <InputNumber
              value={deployPort}
              onChange={(v) => setDeployPort(v ?? undefined)}
              min={1} max={65535}
              style={{ width: '100%' }}
              placeholder="自动"
            />
          </Form.Item>
        </Form>
      </Drawer>
    );
  }

  function renderRelDrawer() {
    const candidates = experts.filter((e) => relParent && e.id !== relParent.id);
    return (
      <Drawer
        open={relDrawerOpen}
        title={<span>添加子专家：{relParent?.name} → ?</span>}
        onClose={() => setRelDrawerOpen(false)}
        width={520}
        footer={
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={() => setRelDrawerOpen(false)}>取消</Button>
            <Button type="primary" onClick={() => void submitRel()}>建立关系</Button>
          </Space>
        }
      >
        <p style={{ color: 'var(--ink-60)', fontSize: 13 }}>
          建立后会自动把 {`<parent-slug>`} 写入 opencode.json 的 agent.{`<parent>`}.permission.task 规则。
        </p>
        <Form form={relForm} layout="vertical">
          <Form.Item name="child_expert_id" label="子专家 (被调用方)" rules={[{ required: true }]}>
            <Select
              showSearch optionFilterProp="label"
              options={candidates.map((c) => ({
                value: c.id, label: `${c.avatar || ''} ${c.name} (${c.slug})`,
              }))}
              placeholder="选一个"
            />
          </Form.Item>
          <Form.Item name="relation" label="调用方式">
            <Select options={[
              { value: 'delegate', label: 'delegate — 委派任务给子 agent' },
              { value: 'fan_out', label: 'fan_out — 并行调用多个子 agent' },
              { value: 'review', label: 'review — 让子 agent 评审产物' },
            ]} />
          </Form.Item>
          <Form.Item name="condition" label="触发条件（自然语言）">
            <Input placeholder="例：需要数据支撑的决策时让数据分析师提供指标" />
          </Form.Item>
          <Form.Item name="sort_order" label="排序">
            <InputNumber min={0} max={999} style={{ width: '100%' }} />
          </Form.Item>
        </Form>

        {relParent && (
          <div style={{ marginTop: 16 }}>
            <div style={sectionLabelStyle}>已建立的关系</div>
            {relations.filter((r) => r.parent_expert_id === relParent.id).map((r) => (
              <div key={r.id} style={{
                padding: 8, border: '1px solid var(--border-hairline)', borderRadius: 8,
                marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8,
              }}>
                <Tag color="blue" style={{ fontSize: 10 }}>{r.relation}</Tag>
                <span style={{ flex: 1, fontSize: 12 }}>
                  → <b>{r.child_name}</b> <Text type="secondary">({r.child_slug})</Text>
                  {r.condition && <div style={{ color: 'var(--ink-60)', fontSize: 11, marginTop: 2 }}>{r.condition}</div>}
                </span>
                <Popconfirm title="确认删除？" onConfirm={() => void deleteRel(r.id)}>
                  <Button danger size="small" type="text" icon={<DeleteOutlined />} />
                </Popconfirm>
              </div>
            ))}
          </div>
        )}
      </Drawer>
    );
  }
}

const sectionLabelStyle: React.CSSProperties = {
  fontFamily: 'var(--font-serif)', fontSize: 13, fontWeight: 500,
  color: 'var(--ink-40)', textTransform: 'uppercase',
  letterSpacing: '0.06em', margin: '20px 0 12px',
};
