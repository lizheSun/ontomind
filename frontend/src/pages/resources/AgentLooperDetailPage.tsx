/**
 * Agent Looper — detail page (Wave 9 W2 T38).
 *
 * Three tabs:
 *   [配置]     — read-only Descriptions of the currently active config
 *                + 「编辑」 opens a Drawer with the raw JSON in a TextArea.
 *   [版本历史] — DataTable of AgentLooperVersionRead rows,
 *                supports 查看 (JSON modal) + 回滚到此版本.
 *   [测试]     — text prompt + 发送 → agentLooperService.test().
 *                For now the result is rendered as a single block; SSE stream
 *                integration is a follow-up when the backend endpoint lands.
 *
 * A top-right 「发布」 button calls publish() and surfaces the returned file path.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Breadcrumb,
  Button,
  Descriptions,
  Drawer,
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
import type {
  AgentLooperConfig,
  AgentLooperConfigRead,
  AgentLooperTestRunResult,
  AgentLooperType,
  AgentLooperVersionRead,
} from '../../types/agentLooper';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

const TYPE_LABELS: Record<AgentLooperType, string> = {
  custom_looper: '自定义 Loop',
  opencode_native: 'OpenCode 原生',
  mcp_agent: 'MCP Agent',
  imported: '导入',
};

const TYPE_COLORS: Record<
  AgentLooperType,
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

type TabKey = 'config' | 'versions' | 'test';

export default function AgentLooperDetailPage() {
  const { id: idParam } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const id = Number(idParam);
  const editModeInitial = searchParams.get('edit') === 'true';

  const [detail, setDetail] = useState<AgentLooperConfigRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabKey>('config');
  const [publishing, setPublishing] = useState(false);

  // Edit drawer
  const [editOpen, setEditOpen] = useState(editModeInitial);
  const [editJson, setEditJson] = useState<string>('');
  const [editNote, setEditNote] = useState<string>('');
  const [savingEdit, setSavingEdit] = useState(false);

  // Versions tab
  const [versions, setVersions] = useState<AgentLooperVersionRead[]>([]);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [viewingVersion, setViewingVersion] =
    useState<AgentLooperVersionRead | null>(null);

  // Test tab
  const [testPrompt, setTestPrompt] = useState('');
  const [testResult, setTestResult] = useState<AgentLooperTestRunResult | null>(
    null,
  );
  const [testing, setTesting] = useState(false);

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

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  useEffect(() => {
    if (activeTab === 'versions') void loadVersions();
  }, [activeTab, loadVersions]);

  const cfg: AgentLooperConfig | null = detail?.active_config_json ?? null;

  const handleSaveEdit = async () => {
    let parsed: AgentLooperConfig;
    try {
      parsed = JSON.parse(editJson) as AgentLooperConfig;
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
        navigate(`/resources/agent-looper/${created.id}`, { replace: true });
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

  const handleRollback = (v: AgentLooperVersionRead) => {
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
  const versionColumns: ColumnsType<AgentLooperVersionRead> = [
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
    <DataTable<AgentLooperVersionRead>
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

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <Spin />
      </div>
    );
  }

  const headerTitle = isNew
    ? '新建 Agent Looper'
    : detail?.name ?? `Agent #${id}`;

  return (
    <div>
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { title: <Link to="/resources">资源管理</Link> },
          { title: 'Agent Looper' },
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
            点击「编辑配置」在 JSON 编辑器中输入完整的 Agent Looper 配置以创建新
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
