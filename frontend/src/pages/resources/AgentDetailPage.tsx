/**
 * Agent detail page (Wave 10 W2 T51) — upgraded from AgentLooperDetailPage.
 *
 * Six tabs:
 *   [配置]         — read-only Descriptions of the currently active config
 *                    + 「编辑」 opens a Drawer with the raw JSON in a TextArea.
 *   [版本历史]     — DataTable of AgentVersionRead rows, 查看 / 回滚。
 *   [测试]         — text prompt + 发送 → agentLooperService.test().
 *   [关联的 Skill] — Skill 列表 + 「已关联/未关联」标记（基于 spawnable_agents）。
 *   [关联的 MCP]   — MCP 列表 + 「已关联/未关联」标记（基于 resource_bindings）。
 *   [Job 历史]     — 该 Agent 的 AgentRun 历史（按 agent_id 过滤）。
 *
 * 保留 3 个原有 tab 的所有行为（Drawer 编辑、版本回滚、Test SSE 占位），
 * 新增 3 个 tab 目前使用 resourcesAPI 的 listSkills / listMCPs / listRuns 提供
 * 只读视图。真正的 bind/unbind 会在后续 T51 backend 端点完成后接入。
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Breadcrumb,
  Button,
  Descriptions,
  Drawer,
  Empty,
  Input,
  Modal,
  Space,
  Spin,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  EditOutlined,
  CloudUploadOutlined,
  SendOutlined,
  RollbackOutlined,
  ArrowLeftOutlined,
  ThunderboltOutlined,
  ApiOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  PageHeader,
  GlassPanel,
  DataTable,
  TagPill,
  DangerConfirm,
} from '../../components/common';
import { agentLooperService } from '../../services/agentLooper.service';
import { resourcesAPI } from '../../services/resourcesAPI';
import type {
  AgentConfig,
  AgentConfigRead,
  AgentTestRunResult,
  AgentType,
  AgentVersionRead,
} from '../../types/agent';
import type { AgentRun, MCPConfig, Skill } from '../../types';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

const TYPE_LABELS: Record<AgentType, string> = {
  custom_looper: '自定义 Loop',
  opencode_native: 'OpenCode 原生',
  mcp_agent: 'MCP Agent',
  imported: '导入',
};

const TYPE_COLORS: Record<
  AgentType,
  'blue' | 'purple' | 'cyan' | 'emerald' | 'amber' | 'rose'
> = {
  custom_looper: 'blue',
  opencode_native: 'purple',
  mcp_agent: 'cyan',
  imported: 'amber',
};

const STRATEGY_LABELS: Record<string, string> = {
  single_shot: '单次调用',
  react: 'ReAct',
  plan_execute: 'Plan-Execute',
  reflect: 'Reflect',
};

const RUN_STATUS_COLOR: Record<AgentRun['status'], string> = {
  initializing: 'processing',
  running: 'success',
  error: 'error',
  stopped: 'default',
};

type TabKey = 'config' | 'versions' | 'test' | 'skills' | 'mcps' | 'jobs';

export default function AgentDetailPage() {
  const { id: idParam } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const id = Number(idParam);
  const editModeInitial = searchParams.get('edit') === 'true';

  const [detail, setDetail] = useState<AgentConfigRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabKey>('config');
  const [publishing, setPublishing] = useState(false);

  // Edit drawer
  const [editOpen, setEditOpen] = useState(editModeInitial);
  const [editJson, setEditJson] = useState<string>('');
  const [editNote, setEditNote] = useState<string>('');
  const [savingEdit, setSavingEdit] = useState(false);

  // Versions tab
  const [versions, setVersions] = useState<AgentVersionRead[]>([]);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [viewingVersion, setViewingVersion] =
    useState<AgentVersionRead | null>(null);

  // Test tab
  const [testPrompt, setTestPrompt] = useState('');
  const [testResult, setTestResult] = useState<AgentTestRunResult | null>(null);
  const [testing, setTesting] = useState(false);

  // Skill / MCP / Job tabs
  const [skills, setSkills] = useState<Skill[]>([]);
  const [skillsLoading, setSkillsLoading] = useState(false);
  const [mcps, setMcps] = useState<MCPConfig[]>([]);
  const [mcpsLoading, setMcpsLoading] = useState(false);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [runsLoading, setRunsLoading] = useState(false);

  const isNew = idParam === 'new';

  const loadDetail = useCallback(async () => {
    if (isNew || !Number.isFinite(id)) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const d = await agentLooperService.getById(id);
      setDetail(d);
      setEditJson(
        d.active_config_json
          ? JSON.stringify(d.active_config_json, null, 2)
          : '{}',
      );
    } catch (err) {
      message.error(err instanceof Error ? err.message : '加载详情失败');
    } finally {
      setLoading(false);
    }
  }, [id, isNew]);

  const loadVersions = useCallback(async () => {
    if (isNew || !Number.isFinite(id)) return;
    setVersionsLoading(true);
    try {
      const list = await agentLooperService.getVersions(id);
      setVersions(list);
    } catch (err) {
      message.error(err instanceof Error ? err.message : '加载版本历史失败');
    } finally {
      setVersionsLoading(false);
    }
  }, [id, isNew]);

  const loadSkills = useCallback(async () => {
    setSkillsLoading(true);
    try {
      const res = await resourcesAPI.listSkills({ skip: 0, limit: 200 });
      const list: Skill[] = res.data?.data ?? [];
      setSkills(list);
    } catch (err) {
      message.error(err instanceof Error ? err.message : '加载 Skill 列表失败');
    } finally {
      setSkillsLoading(false);
    }
  }, []);

  const loadMcps = useCallback(async () => {
    setMcpsLoading(true);
    try {
      const res = await resourcesAPI.listMCPs({ skip: 0, limit: 200 });
      const list: MCPConfig[] = res.data?.data ?? [];
      setMcps(list);
    } catch (err) {
      message.error(err instanceof Error ? err.message : '加载 MCP 列表失败');
    } finally {
      setMcpsLoading(false);
    }
  }, []);

  const loadRuns = useCallback(async () => {
    if (isNew || !Number.isFinite(id)) return;
    setRunsLoading(true);
    try {
      const res = await resourcesAPI.listRuns({ skip: 0, limit: 200 });
      const list: AgentRun[] = res.data?.data ?? [];
      setRuns(list.filter((r) => r.agent_id === id));
    } catch (err) {
      message.error(err instanceof Error ? err.message : '加载 Job 历史失败');
    } finally {
      setRunsLoading(false);
    }
  }, [id, isNew]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  useEffect(() => {
    if (activeTab === 'versions') void loadVersions();
    else if (activeTab === 'skills') void loadSkills();
    else if (activeTab === 'mcps') void loadMcps();
    else if (activeTab === 'jobs') void loadRuns();
  }, [activeTab, loadVersions, loadSkills, loadMcps, loadRuns]);

  const cfg: AgentConfig | null = detail?.active_config_json ?? null;

  // Which Skills / MCPs are considered "linked" to this agent right now.
  // Backend bind/unbind endpoints will land in a follow-up; until then we
  // reflect the association state as encoded in the agent config.
  const linkedSkillNames = useMemo<Set<string>>(() => {
    const names = cfg?.spawnable_agents ?? [];
    return new Set(names.map((s) => s.trim()).filter(Boolean));
  }, [cfg]);

  const linkedMcpNames = useMemo<Set<string>>(() => {
    // Custom-tools slot is the canonical place MCP handles are referenced.
    const fromTools =
      cfg?.custom_tools?.map((t) => t.name).filter(Boolean) ?? [];
    return new Set(fromTools);
  }, [cfg]);

  const handleSaveEdit = async () => {
    let parsed: AgentConfig;
    try {
      parsed = JSON.parse(editJson) as AgentConfig;
    } catch {
      message.error('配置 JSON 解析失败，请检查语法');
      return;
    }
    setSavingEdit(true);
    try {
      if (isNew) {
        const created = await agentLooperService.create({
          name: parsed.name || '未命名 Agent',
          description: parsed.description || null,
          active_config_json: parsed,
        });
        message.success('创建成功');
        navigate(`/resources/agent/${created.id}`, { replace: true });
      } else {
        const updated = await agentLooperService.update(id, {
          active_config_json: parsed,
          note: editNote || null,
        });
        setDetail(updated);
        message.success('保存成功');
      }
      setEditOpen(false);
      setEditNote('');
    } catch (err) {
      message.error(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSavingEdit(false);
    }
  };

  const handlePublish = async () => {
    if (!Number.isFinite(id)) return;
    setPublishing(true);
    try {
      const res = await agentLooperService.publish(id);
      message.success(`已发布到本地：${res.path}`);
      await loadDetail();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '发布失败');
    } finally {
      setPublishing(false);
    }
  };

  const handleRollback = (v: AgentVersionRead) => {
    DangerConfirm({
      title: `确认回滚到 v${v.version_number}？`,
      content: '当前配置将被替换为该版本。历史版本仍会保留。',
      okText: '回滚',
      onOk: async () => {
        try {
          const updated = await agentLooperService.rollback(id, v.version_number);
          setDetail(updated);
          message.success(`已回滚到 v${v.version_number}`);
          await loadVersions();
        } catch (err) {
          message.error(err instanceof Error ? err.message : '回滚失败');
        }
      },
    });
  };

  const handleTest = async () => {
    if (!testPrompt.trim()) {
      message.warning('请输入测试 Prompt');
      return;
    }
    setTesting(true);
    setTestResult(null);
    try {
      const res = await agentLooperService.test(id, testPrompt.trim());
      setTestResult(res);
    } catch (err) {
      message.error(err instanceof Error ? err.message : '测试失败');
    } finally {
      setTesting(false);
    }
  };

  // ---- version columns ----
  const versionColumns: ColumnsType<AgentVersionRead> = [
    {
      title: '版本号',
      dataIndex: 'version_number',
      key: 'version_number',
      width: 90,
      render: (v: number) => (
        <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>v{v}</span>
      ),
    },
    {
      title: '模型快照',
      dataIndex: 'model_snapshot',
      key: 'model_snapshot',
      width: 200,
      render: (v: string | null) =>
        v ? (
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}>
            {v}
          </span>
        ) : (
          '-'
        ),
    },
    {
      title: '备注',
      dataIndex: 'note',
      key: 'note',
      render: (v: string | null) => v || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (v: string | null) => (v ? new Date(v).toLocaleString() : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: unknown, row) => (
        <Space size={0}>
          <Button
            type="link"
            size="small"
            onClick={() => setViewingVersion(row)}
          >
            查看
          </Button>
          <Button
            type="link"
            size="small"
            icon={<RollbackOutlined />}
            onClick={() => handleRollback(row)}
            disabled={row.id === detail?.current_version_id}
          >
            回滚到此版本
          </Button>
        </Space>
      ),
    },
  ];

  // ---- skills tab columns ----
  const skillColumns: ColumnsType<Skill> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (v: string) => (
        <span style={{ color: '#e8eef5', fontWeight: 500 }}>{v}</span>
      ),
    },
    {
      title: '类型',
      dataIndex: 'skill_type',
      key: 'skill_type',
      width: 100,
      render: (t: Skill['skill_type']) => <TagPill color="purple">{t}</TagPill>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (v: string | undefined) => v || '-',
    },
    {
      title: '关联状态',
      key: 'linked',
      width: 120,
      render: (_: unknown, row) =>
        linkedSkillNames.has(row.name) ? (
          <Tag color="success">已关联</Tag>
        ) : (
          <Tag>未关联</Tag>
        ),
    },
    {
      title: '已安装',
      dataIndex: 'is_installed',
      key: 'is_installed',
      width: 90,
      render: (v: boolean) =>
        v ? <Tag color="processing">是</Tag> : <Tag>否</Tag>,
    },
  ];

  // ---- MCP tab columns ----
  const mcpColumns: ColumnsType<MCPConfig> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (v: string) => (
        <span style={{ color: '#e8eef5', fontWeight: 500 }}>{v}</span>
      ),
    },
    {
      title: '类型',
      dataIndex: 'mcp_type',
      key: 'mcp_type',
      width: 100,
      render: (t: MCPConfig['mcp_type']) => (
        <TagPill color="cyan">{t}</TagPill>
      ),
    },
    {
      title: '端点',
      key: 'endpoint',
      ellipsis: true,
      render: (_: unknown, row) => row.url || row.command || '-',
    },
    {
      title: '关联状态',
      key: 'linked',
      width: 120,
      render: (_: unknown, row) =>
        linkedMcpNames.has(row.name) ? (
          <Tag color="success">已关联</Tag>
        ) : (
          <Tag>未关联</Tag>
        ),
    },
    {
      title: '启用',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (v: boolean) =>
        v ? <Tag color="success">启用</Tag> : <Tag>禁用</Tag>,
    },
  ];

  // ---- Job history columns ----
  const runColumns: ColumnsType<AgentRun> = [
    {
      title: 'Run ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
      render: (v: number) => (
        <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>#{v}</span>
      ),
    },
    {
      title: '名称',
      dataIndex: 'run_name',
      key: 'run_name',
      render: (v: string) => (
        <span style={{ color: '#e8eef5' }}>{v || '-'}</span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (s: AgentRun['status']) => (
        <Tag color={RUN_STATUS_COLOR[s] ?? 'default'}>{s}</Tag>
      ),
    },
    {
      title: '开始时间',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 170,
      render: (v: string | undefined) => (v ? new Date(v).toLocaleString() : '-'),
    },
    {
      title: '结束时间',
      dataIndex: 'stopped_at',
      key: 'stopped_at',
      width: 170,
      render: (v: string | undefined) => (v ? new Date(v).toLocaleString() : '-'),
    },
    {
      title: 'Exit',
      dataIndex: 'exit_code',
      key: 'exit_code',
      width: 70,
      render: (v: number | undefined) =>
        v == null ? (
          '-'
        ) : (
          <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>{v}</span>
        ),
    },
  ];

  const configTab = useMemo(() => {
    if (!detail || !cfg) {
      return (
        <GlassPanel>
          <Paragraph style={{ color: '#8895b4' }}>暂无配置</Paragraph>
        </GlassPanel>
      );
    }
    return (
      <GlassPanel>
        <Descriptions
          bordered
          size="small"
          column={2}
          styles={{ label: { width: 140 } }}
        >
          <Descriptions.Item label="名称">{detail.name}</Descriptions.Item>
          <Descriptions.Item label="类型">
            <TagPill color={TYPE_COLORS[detail.type] ?? 'blue'}>
              {TYPE_LABELS[detail.type] ?? detail.type}
            </TagPill>
          </Descriptions.Item>
          <Descriptions.Item label="模型">
            <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>
              {cfg.model || '-'}
            </span>
          </Descriptions.Item>
          <Descriptions.Item label="Provider">
            {cfg.provider || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="Temperature">
            {typeof cfg.temperature === 'number' ? cfg.temperature : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="循环策略">
            {STRATEGY_LABELS[cfg.loop_strategy] ?? cfg.loop_strategy}
          </Descriptions.Item>
          <Descriptions.Item label="模式">{cfg.mode}</Descriptions.Item>
          <Descriptions.Item label="Memory Window">
            {cfg.memory_window ?? '-'}
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            {detail.is_active ? (
              <Tag color="success">启用</Tag>
            ) : (
              <Tag>未启用</Tag>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="已发布">
            {detail.is_published ? (
              <Tag color="processing">已发布</Tag>
            ) : (
              <Tag>草稿</Tag>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="描述" span={2}>
            {detail.description || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="工具权限" span={2}>
            <Space size={4} wrap>
              {Object.entries(cfg.tool_permissions ?? {}).map(([k, v]) => (
                <TagPill
                  key={k}
                  color={v ? 'emerald' : 'rose'}
                >{`${k}: ${v ? 'on' : 'off'}`}</TagPill>
              ))}
              {Object.keys(cfg.tool_permissions ?? {}).length === 0 && '-'}
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="上下文文件" span={2}>
            {cfg.context_files && cfg.context_files.length > 0 ? (
              <Space size={4} wrap>
                {cfg.context_files.map((f) => (
                  <TagPill key={f} color="cyan">
                    {f}
                  </TagPill>
                ))}
              </Space>
            ) : (
              '-'
            )}
          </Descriptions.Item>
          <Descriptions.Item label="可派生 Agent" span={2}>
            {cfg.spawnable_agents && cfg.spawnable_agents.length > 0
              ? cfg.spawnable_agents.join(', ')
              : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="System Prompt" span={2}>
            <pre
              style={{
                margin: 0,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 12,
                color: '#c5cee0',
                maxHeight: 240,
                overflow: 'auto',
              }}
            >
              {cfg.system_prompt || '(未设置)'}
            </pre>
          </Descriptions.Item>
        </Descriptions>
      </GlassPanel>
    );
  }, [detail, cfg]);

  const versionsTab = (
    <DataTable<AgentVersionRead>
      rowKey="id"
      columns={versionColumns}
      dataSource={versions}
      loading={versionsLoading}
      emptyTitle="暂无版本历史"
      emptyDescription="编辑并保存配置后会生成新的版本记录"
    />
  );

  const testTab = (
    <GlassPanel>
      <div style={{ marginBottom: 12 }}>
        <Text style={{ color: '#8895b4' }}>测试 Prompt</Text>
      </div>
      <TextArea
        value={testPrompt}
        onChange={(e) => setTestPrompt(e.target.value)}
        placeholder="输入用于测试当前 Agent 的 Prompt..."
        autoSize={{ minRows: 3, maxRows: 8 }}
      />
      <div style={{ marginTop: 12, display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          type="primary"
          icon={<SendOutlined />}
          loading={testing}
          onClick={handleTest}
        >
          发送
        </Button>
      </div>
      {testResult && (
        <div
          style={{
            marginTop: 16,
            padding: 12,
            borderRadius: 10,
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.06)',
            maxHeight: 360,
            overflow: 'auto',
          }}
        >
          <Space size={8} style={{ marginBottom: 8 }}>
            <Tag
              color={
                testResult.status === 'success'
                  ? 'success'
                  : testResult.status === 'error'
                  ? 'error'
                  : 'processing'
              }
            >
              {testResult.status}
            </Tag>
            {testResult.duration_ms != null && (
              <Text style={{ color: '#8895b4', fontSize: 12 }}>
                耗时 {testResult.duration_ms} ms
              </Text>
            )}
          </Space>
          <pre
            style={{
              margin: 0,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 12,
              color: testResult.error ? '#fb7185' : '#c5cee0',
            }}
          >
            {testResult.error || testResult.output || '(无输出)'}
          </pre>
        </div>
      )}
    </GlassPanel>
  );

  const skillsTab = (
    <>
      <GlassPanel style={{ marginBottom: 12 }}>
        <Space size={8} align="center">
          <ThunderboltOutlined style={{ color: '#a78bfa' }} />
          <Text style={{ color: '#8895b4' }}>
            已关联 {linkedSkillNames.size} 个 Skill · 共 {skills.length} 个可选。
            关联关系目前由 <code>active_config_json.spawnable_agents</code> 维护，
            后续接入 bind/unbind API。
          </Text>
        </Space>
      </GlassPanel>
      <DataTable<Skill>
        rowKey="id"
        columns={skillColumns}
        dataSource={skills}
        loading={skillsLoading}
        emptyTitle="暂无 Skill"
        emptyDescription="请先在资源页新增或发现本地 Skill"
      />
    </>
  );

  const mcpsTab = (
    <>
      <GlassPanel style={{ marginBottom: 12 }}>
        <Space size={8} align="center">
          <ApiOutlined style={{ color: '#22d3ee' }} />
          <Text style={{ color: '#8895b4' }}>
            已关联 {linkedMcpNames.size} 个 MCP · 共 {mcps.length} 个可选。
            关联关系目前由 <code>active_config_json.custom_tools</code> 维护，
            后续接入 bind/unbind API。
          </Text>
        </Space>
      </GlassPanel>
      <DataTable<MCPConfig>
        rowKey="id"
        columns={mcpColumns}
        dataSource={mcps}
        loading={mcpsLoading}
        emptyTitle="暂无 MCP"
        emptyDescription="请先在资源页新增或自动发现 MCP"
      />
    </>
  );

  const jobsTab = (
    <>
      <GlassPanel style={{ marginBottom: 12 }}>
        <Space size={8} align="center">
          <HistoryOutlined style={{ color: '#60a5fa' }} />
          <Text style={{ color: '#8895b4' }}>
            该 Agent 关联的 Run 记录（按 agent_id 过滤）。共 {runs.length} 条。
          </Text>
        </Space>
      </GlassPanel>
      {runs.length === 0 && !runsLoading ? (
        <GlassPanel>
          <Empty description="暂无 Job 历史" />
        </GlassPanel>
      ) : (
        <DataTable<AgentRun>
          rowKey="id"
          columns={runColumns}
          dataSource={runs}
          loading={runsLoading}
          emptyTitle="暂无 Job 历史"
          emptyDescription="发起 Run 后会显示在此"
        />
      )}
    </>
  );

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <Spin />
      </div>
    );
  }

  const headerTitle = isNew
    ? '新建 Agent'
    : detail?.name ?? `Agent #${id}`;

  return (
    <div>
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { title: <Link to="/resources">资源管理</Link> },
          { title: '智能体' },
          { title: headerTitle },
        ]}
      />
      <PageHeader
        title={headerTitle}
        subtitle={detail?.description ?? undefined}
        extra={
          <Space>
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/resources')}
            >
              返回列表
            </Button>
            {!isNew && (
              <>
                <Button
                  icon={<EditOutlined />}
                  onClick={() => setEditOpen(true)}
                >
                  编辑
                </Button>
                <Button
                  type="primary"
                  icon={<CloudUploadOutlined />}
                  loading={publishing}
                  onClick={handlePublish}
                >
                  发布
                </Button>
              </>
            )}
            {isNew && (
              <Button
                type="primary"
                icon={<EditOutlined />}
                onClick={() => setEditOpen(true)}
              >
                编辑配置
              </Button>
            )}
          </Space>
        }
      />

      {isNew ? (
        <GlassPanel>
          <Paragraph style={{ color: '#8895b4' }}>
            点击「编辑配置」在 JSON 编辑器中输入完整的 Agent 配置以创建新
            Agent。
          </Paragraph>
        </GlassPanel>
      ) : (
        <Tabs
          activeKey={activeTab}
          onChange={(k) => setActiveTab(k as TabKey)}
          items={[
            { key: 'config', label: '配置', children: configTab },
            { key: 'versions', label: '版本历史', children: versionsTab },
            { key: 'test', label: '测试', children: testTab },
            { key: 'skills', label: '关联的 Skill', children: skillsTab },
            { key: 'mcps', label: '关联的 MCP', children: mcpsTab },
            { key: 'jobs', label: 'Job 历史', children: jobsTab },
          ]}
        />
      )}

      {/* Edit Drawer */}
      <Drawer
        title={
          <Space>
            <EditOutlined style={{ color: '#60a5fa' }} />
            {isNew ? '新建 Agent 配置' : '编辑配置'}
          </Space>
        }
        open={editOpen}
        onClose={() => setEditOpen(false)}
        width={720}
        extra={
          <Space>
            <Button onClick={() => setEditOpen(false)}>取消</Button>
            <Button type="primary" loading={savingEdit} onClick={handleSaveEdit}>
              保存
            </Button>
          </Space>
        }
      >
        <Paragraph style={{ color: '#8895b4', fontSize: 12 }}>
          直接编辑 <code>active_config_json</code> 内容。保存后会生成新的版本。
        </Paragraph>
        <TextArea
          value={editJson}
          onChange={(e) => setEditJson(e.target.value)}
          autoSize={{ minRows: 18, maxRows: 36 }}
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 12,
            background: 'rgba(0,0,0,0.25)',
          }}
        />
        {!isNew && (
          <div style={{ marginTop: 12 }}>
            <Text style={{ color: '#8895b4', fontSize: 12 }}>版本备注</Text>
            <Input
              value={editNote}
              onChange={(e) => setEditNote(e.target.value)}
              placeholder="可选：本次改动说明"
              style={{ marginTop: 4 }}
            />
          </div>
        )}
      </Drawer>

      {/* Version JSON viewer */}
      <Modal
        open={!!viewingVersion}
        onCancel={() => setViewingVersion(null)}
        footer={null}
        title={viewingVersion ? `v${viewingVersion.version_number} 配置` : ''}
        width={720}
      >
        {viewingVersion && (
          <pre
            style={{
              margin: 0,
              maxHeight: 480,
              overflow: 'auto',
              padding: 12,
              background: 'rgba(0,0,0,0.3)',
              borderRadius: 8,
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 12,
              color: '#c5cee0',
            }}
          >
            {JSON.stringify(viewingVersion.config_json, null, 2)}
          </pre>
        )}
      </Modal>
    </div>
  );
}
