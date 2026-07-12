/**
 * AgentJobPage (Wave 10 T55) — ETL-style long-running Agent Job dashboard.
 *
 * Layout: header + stat cards + filter bar + status/progress table + action
 * bar. Backend routes: `/api/v1/agent-looper/jobs*` (see agent_looper/test.py).
 *
 * State machine (mirrors AgentJobService):
 *
 *     pending → running → paused → running → completed
 *                       ↘         ↙
 *                        failed / cancelled
 *
 * The table renders a progress bar and per-row lifecycle buttons that call
 * `/jobs/{id}/transition` with the appropriate `action`. Terminal states hide
 * lifecycle buttons and reveal the delete affordance.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Col,
  Descriptions,
  Drawer,
  Form,
  Input,
  InputNumber,
  Modal,
  Progress,
  Row,
  Select,
  Space,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StepForwardOutlined,
  CheckCircleOutlined,
  StopOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
  DeleteOutlined,
  PlusOutlined,
  EyeOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  PauseOutlined,
  MinusCircleOutlined,
} from '@ant-design/icons';
import {
  PageHeader,
  GlassPanel,
  DataTable,
  StatCard,
  TagPill,
  DangerConfirm,
} from '../../components/common';
import api from '../../services/api';
import { resourcesAPI } from '../../services/resourcesAPI';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

type JobStatus =
  | 'pending'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled';

interface JobStep {
  name: string;
  status?: string;
  output?: unknown;
}

interface AgentJob {
  id: number;
  agent_id: number;
  name: string;
  status: JobStatus;
  steps: JobStep[];
  current_step: number;
  total_steps: number;
  progress: number;
  input_data: unknown;
  output_data: unknown;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_by_user_id: number;
  created_at: string | null;
  updated_at: string | null;
}

interface AgentOption {
  id: number;
  name: string;
}

const STATUS_META: Record<
  JobStatus,
  { color: string; label: string }
> = {
  pending: { color: 'default', label: '待运行' },
  running: { color: 'processing', label: '运行中' },
  paused: { color: 'warning', label: '已暂停' },
  completed: { color: 'success', label: '已完成' },
  failed: { color: 'error', label: '失败' },
  cancelled: { color: 'default', label: '已取消' },
};

const TERMINAL_STATUSES: ReadonlySet<JobStatus> = new Set([
  'completed',
  'failed',
  'cancelled',
]);

interface ApiEnvelope<T> {
  code?: string;
  message?: string;
  data: T;
}

async function listJobs(params: {
  agentId?: number;
  status?: JobStatus | 'all';
  mine?: boolean;
}): Promise<AgentJob[]> {
  const query: Record<string, unknown> = {};
  if (params.agentId != null) query.agent_id = params.agentId;
  if (params.status && params.status !== 'all') query.status = params.status;
  if (params.mine != null) query.mine = params.mine;
  const res = await api.get<ApiEnvelope<AgentJob[]>>(
    '/agent-looper/jobs',
    { params: query },
  );
  return res.data?.data ?? [];
}

async function createJob(payload: {
  agent_id: number;
  name: string;
  total_steps?: number;
  steps?: JobStep[];
  input_data?: unknown;
}): Promise<AgentJob> {
  const res = await api.post<ApiEnvelope<AgentJob>>(
    '/agent-looper/jobs',
    payload,
  );
  return res.data.data;
}

async function transitionJob(
  jobId: number,
  action: string,
  extra: Record<string, unknown> = {},
): Promise<AgentJob> {
  const res = await api.post<ApiEnvelope<AgentJob>>(
    `/agent-looper/jobs/${jobId}/transition`,
    { action, ...extra },
  );
  return res.data.data;
}

async function deleteJob(jobId: number): Promise<void> {
  await api.delete(`/agent-looper/jobs/${jobId}`);
}

export default function AgentJobPage() {
  const [jobs, setJobs] = useState<AgentJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<JobStatus | 'all'>('all');
  const [agentFilter, setAgentFilter] = useState<number | undefined>(undefined);
  const [mineOnly, setMineOnly] = useState(true);

  const [agents, setAgents] = useState<AgentOption[]>([]);
  const [detail, setDetail] = useState<AgentJob | null>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [createForm] = Form.useForm<{
    agent_id: number;
    name: string;
    total_steps: number;
    steps_text: string;
    input_text: string;
  }>();
  const [creating, setCreating] = useState(false);

  const loadJobs = useCallback(async () => {
    setLoading(true);
    try {
      const rows = await listJobs({
        agentId: agentFilter,
        status: statusFilter,
        mine: mineOnly,
      });
      setJobs(rows);
    } catch (err) {
      message.error(err instanceof Error ? err.message : '加载 Job 列表失败');
    } finally {
      setLoading(false);
    }
  }, [agentFilter, statusFilter, mineOnly]);

  const loadAgents = useCallback(async () => {
    try {
      const res = await resourcesAPI.listAgents({ skip: 0, limit: 500 });
      const list: AgentOption[] = res.data?.data ?? [];
      setAgents(list);
    } catch (err) {
      message.error(err instanceof Error ? err.message : '加载 Agent 列表失败');
    }
  }, []);

  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  useEffect(() => {
    void loadAgents();
  }, [loadAgents]);

  const stats = useMemo(() => {
    const acc: Record<JobStatus, number> = {
      pending: 0,
      running: 0,
      paused: 0,
      completed: 0,
      failed: 0,
      cancelled: 0,
    };
    for (const j of jobs) acc[j.status] = (acc[j.status] || 0) + 1;
    return acc;
  }, [jobs]);

  const handleTransition = useCallback(
    async (job: AgentJob, action: string, extra?: Record<string, unknown>) => {
      try {
        const updated = await transitionJob(job.id, action, extra);
        setJobs((prev) => prev.map((j) => (j.id === updated.id ? updated : j)));
        message.success(`Job #${job.id} · ${action} 已执行`);
      } catch (err) {
        message.error(err instanceof Error ? err.message : `${action} 失败`);
      }
    },
    [],
  );

  const handleDelete = useCallback((job: AgentJob) => {
    DangerConfirm({
      title: `删除 Job #${job.id}?`,
      content: `名称：${job.name}。删除后不可恢复。`,
      okText: '删除',
      onOk: async () => {
        try {
          await deleteJob(job.id);
          setJobs((prev) => prev.filter((j) => j.id !== job.id));
          message.success('已删除');
        } catch (err) {
          message.error(err instanceof Error ? err.message : '删除失败');
        }
      },
    });
  }, []);

  const handleCreate = useCallback(async () => {
    let values: {
      agent_id: number;
      name: string;
      total_steps: number;
      steps_text: string;
      input_text: string;
    };
    try {
      values = await createForm.validateFields();
    } catch {
      return;
    }
    const steps: JobStep[] = values.steps_text
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter(Boolean)
      .map((name) => ({ name, status: 'pending' }));
    let input_data: unknown = null;
    if (values.input_text && values.input_text.trim()) {
      try {
        input_data = JSON.parse(values.input_text);
      } catch {
        message.error('input_data 不是有效 JSON');
        return;
      }
    }
    setCreating(true);
    try {
      const created = await createJob({
        agent_id: values.agent_id,
        name: values.name,
        total_steps:
          values.total_steps ?? (steps.length > 0 ? steps.length : 1),
        steps: steps.length > 0 ? steps : undefined,
        input_data,
      });
      setJobs((prev) => [created, ...prev]);
      setCreateOpen(false);
      createForm.resetFields();
      message.success('Job 已创建');
    } catch (err) {
      message.error(err instanceof Error ? err.message : '创建 Job 失败');
    } finally {
      setCreating(false);
    }
  }, [createForm]);

  const columns: ColumnsType<AgentJob> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 70,
      render: (v: number) => (
        <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>#{v}</span>
      ),
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (v: string) => (
        <span style={{ color: '#e8eef5', fontWeight: 500 }}>{v}</span>
      ),
    },
    {
      title: 'Agent',
      dataIndex: 'agent_id',
      key: 'agent_id',
      width: 160,
      render: (aid: number) => {
        const a = agents.find((x) => x.id === aid);
        return (
          <TagPill color="blue">{a ? a.name : `agent #${aid}`}</TagPill>
        );
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: JobStatus) => (
        <Tag color={STATUS_META[s]?.color ?? 'default'}>
          {STATUS_META[s]?.label ?? s}
        </Tag>
      ),
    },
    {
      title: '进度',
      key: 'progress',
      width: 260,
      render: (_, row) => {
        const status: 'active' | 'success' | 'exception' | 'normal' =
          row.status === 'running'
            ? 'active'
            : row.status === 'completed'
            ? 'success'
            : row.status === 'failed'
            ? 'exception'
            : 'normal';
        return (
          <div>
            <Progress
              percent={row.progress}
              size="small"
              status={status}
              format={(p) => `${p ?? 0}%`}
            />
            <Text style={{ color: '#8895b4', fontSize: 12 }}>
              {row.current_step} / {row.total_steps} 步
            </Text>
          </div>
        );
      },
    },
    {
      title: '开始',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 170,
      render: (v: string | null) => (v ? new Date(v).toLocaleString() : '-'),
    },
    {
      title: '结束',
      dataIndex: 'finished_at',
      key: 'finished_at',
      width: 170,
      render: (v: string | null) => (v ? new Date(v).toLocaleString() : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 340,
      fixed: 'right',
      render: (_, row) => {
        const isTerminal = TERMINAL_STATUSES.has(row.status);
        return (
          <Space size={4} wrap>
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => setDetail(row)}
            >
              详情
            </Button>
            {row.status === 'pending' && (
              <Tooltip title="启动">
                <Button
                  size="small"
                  type="primary"
                  icon={<PlayCircleOutlined />}
                  onClick={() => handleTransition(row, 'start')}
                >
                  启动
                </Button>
              </Tooltip>
            )}
            {row.status === 'running' && (
              <>
                <Button
                  size="small"
                  icon={<StepForwardOutlined />}
                  onClick={() => handleTransition(row, 'advance_step')}
                  disabled={row.current_step >= row.total_steps}
                >
                  下一步
                </Button>
                <Button
                  size="small"
                  icon={<PauseCircleOutlined />}
                  onClick={() => handleTransition(row, 'pause')}
                >
                  暂停
                </Button>
                <Button
                  size="small"
                  icon={<CheckCircleOutlined />}
                  onClick={() => handleTransition(row, 'complete')}
                >
                  完成
                </Button>
                <Button
                  size="small"
                  danger
                  icon={<CloseCircleOutlined />}
                  onClick={() =>
                    handleTransition(row, 'fail', {
                      error_message: '手动标记为失败',
                    })
                  }
                >
                  失败
                </Button>
              </>
            )}
            {row.status === 'paused' && (
              <>
                <Button
                  size="small"
                  type="primary"
                  icon={<PlayCircleOutlined />}
                  onClick={() => handleTransition(row, 'resume')}
                >
                  恢复
                </Button>
                <Button
                  size="small"
                  icon={<StopOutlined />}
                  onClick={() => handleTransition(row, 'cancel')}
                >
                  取消
                </Button>
              </>
            )}
            {(row.status === 'pending' || row.status === 'running') && (
              <Button
                size="small"
                icon={<StopOutlined />}
                onClick={() => handleTransition(row, 'cancel')}
                disabled={row.status === 'running'}
              >
                取消
              </Button>
            )}
            {isTerminal && (
              <Button
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={() => handleDelete(row)}
              >
                删除
              </Button>
            )}
          </Space>
        );
      },
    },
  ];

  return (
    <div>
      <PageHeader
        title="Agent 长任务"
        subtitle="ETL 风格 Job 生命周期管理 · 支持 pending / running / paused / completed / failed / cancelled"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => void loadJobs()}>
              刷新
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreateOpen(true)}
            >
              新建 Job
            </Button>
          </Space>
        }
      />

      <Row gutter={12} style={{ marginBottom: 12 }}>
        <Col xs={12} md={4}>
          <StatCard
            icon={<ClockCircleOutlined />}
            label="待运行"
            value={stats.pending}
            accent="cyan"
          />
        </Col>
        <Col xs={12} md={4}>
          <StatCard
            icon={<SyncOutlined spin />}
            label="运行中"
            value={stats.running}
            accent="blue"
          />
        </Col>
        <Col xs={12} md={4}>
          <StatCard
            icon={<PauseOutlined />}
            label="已暂停"
            value={stats.paused}
            accent="amber"
          />
        </Col>
        <Col xs={12} md={4}>
          <StatCard
            icon={<CheckCircleOutlined />}
            label="已完成"
            value={stats.completed}
            accent="emerald"
          />
        </Col>
        <Col xs={12} md={4}>
          <StatCard
            icon={<CloseCircleOutlined />}
            label="失败"
            value={stats.failed}
            accent="rose"
          />
        </Col>
        <Col xs={12} md={4}>
          <StatCard
            icon={<MinusCircleOutlined />}
            label="已取消"
            value={stats.cancelled}
            accent="purple"
          />
        </Col>
      </Row>

      <GlassPanel style={{ marginBottom: 12 }}>
        <Space wrap>
          <Text style={{ color: '#8895b4' }}>状态</Text>
          <Select
            value={statusFilter}
            style={{ width: 140 }}
            onChange={(v: JobStatus | 'all') => setStatusFilter(v)}
            options={[
              { value: 'all', label: '全部' },
              { value: 'pending', label: '待运行' },
              { value: 'running', label: '运行中' },
              { value: 'paused', label: '已暂停' },
              { value: 'completed', label: '已完成' },
              { value: 'failed', label: '失败' },
              { value: 'cancelled', label: '已取消' },
            ]}
          />
          <Text style={{ color: '#8895b4' }}>Agent</Text>
          <Select
            value={agentFilter}
            allowClear
            placeholder="全部 Agent"
            style={{ width: 220 }}
            onChange={(v: number | undefined) => setAgentFilter(v)}
            options={agents.map((a) => ({ value: a.id, label: a.name }))}
          />
          <Text style={{ color: '#8895b4' }}>范围</Text>
          <Select
            value={mineOnly ? 'mine' : 'all'}
            style={{ width: 160 }}
            onChange={(v: string) => setMineOnly(v === 'mine')}
            options={[
              { value: 'mine', label: '仅我的' },
              { value: 'all', label: '全部用户' },
            ]}
          />
        </Space>
      </GlassPanel>

      <DataTable<AgentJob>
        rowKey="id"
        columns={columns}
        dataSource={jobs}
        loading={loading}
        emptyTitle="暂无 Job"
        emptyDescription="点击「新建 Job」创建一个长任务"
      />

      {/* Create Drawer */}
      <Drawer
        title="新建 Agent Job"
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        width={520}
        extra={
          <Space>
            <Button onClick={() => setCreateOpen(false)}>取消</Button>
            <Button type="primary" loading={creating} onClick={handleCreate}>
              创建
            </Button>
          </Space>
        }
      >
        <Form form={createForm} layout="vertical">
          <Form.Item
            name="agent_id"
            label="Agent"
            rules={[{ required: true, message: '请选择 Agent' }]}
          >
            <Select
              placeholder="选择要执行的 Agent"
              options={agents.map((a) => ({ value: a.id, label: a.name }))}
            />
          </Form.Item>
          <Form.Item
            name="name"
            label="Job 名称"
            rules={[{ required: true, message: '请输入名称' }]}
          >
            <Input placeholder="e.g. daily-etl-2026-07-12" maxLength={256} />
          </Form.Item>
          <Form.Item
            name="steps_text"
            label="步骤（每行一个，可空）"
            tooltip="每行一个 step 名称，例如：extract / transform / load"
            initialValue=""
          >
            <TextArea
              autoSize={{ minRows: 4, maxRows: 10 }}
              placeholder={'extract\ntransform\nload'}
            />
          </Form.Item>
          <Form.Item
            name="total_steps"
            label="总步骤数（可选）"
            tooltip="留空则按步骤行数推断；无步骤时默认 1。"
          >
            <InputNumber min={1} max={9999} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="input_text" label="input_data (JSON, 可选)">
            <TextArea
              autoSize={{ minRows: 3, maxRows: 8 }}
              placeholder='{"source": "mysql://..."}'
            />
          </Form.Item>
        </Form>
      </Drawer>

      {/* Detail Modal */}
      <Modal
        open={!!detail}
        onCancel={() => setDetail(null)}
        footer={null}
        width={720}
        title={detail ? `Job #${detail.id} · ${detail.name}` : ''}
      >
        {detail && (
          <>
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="状态">
                <Tag color={STATUS_META[detail.status]?.color}>
                  {STATUS_META[detail.status]?.label ?? detail.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="进度">
                {detail.progress}% · {detail.current_step}/{detail.total_steps}
              </Descriptions.Item>
              <Descriptions.Item label="开始">
                {detail.started_at
                  ? new Date(detail.started_at).toLocaleString()
                  : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="结束">
                {detail.finished_at
                  ? new Date(detail.finished_at).toLocaleString()
                  : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Agent" span={2}>
                agent #{detail.agent_id}
              </Descriptions.Item>
            </Descriptions>
            {detail.error_message && (
              <Alert
                type="error"
                message="错误信息"
                description={detail.error_message}
                style={{ marginTop: 12 }}
              />
            )}
            <Paragraph style={{ marginTop: 16, marginBottom: 4 }}>
              <Text style={{ color: '#8895b4' }}>步骤</Text>
            </Paragraph>
            {detail.steps.length === 0 ? (
              <Text style={{ color: '#8895b4' }}>(无)</Text>
            ) : (
              <ol style={{ paddingLeft: 20, color: '#c5cee0' }}>
                {detail.steps.map((s, i) => (
                  <li key={i}>
                    <span style={{ fontWeight: 500 }}>{s.name}</span>{' '}
                    <Tag>{s.status ?? 'pending'}</Tag>
                  </li>
                ))}
              </ol>
            )}
            <Paragraph style={{ marginTop: 12, marginBottom: 4 }}>
              <Text style={{ color: '#8895b4' }}>input_data</Text>
            </Paragraph>
            <pre
              style={{
                margin: 0,
                padding: 10,
                background: 'rgba(0,0,0,0.3)',
                borderRadius: 8,
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 12,
                color: '#c5cee0',
                maxHeight: 200,
                overflow: 'auto',
              }}
            >
              {JSON.stringify(detail.input_data, null, 2)}
            </pre>
            {detail.output_data != null && (
              <>
                <Paragraph style={{ marginTop: 12, marginBottom: 4 }}>
                  <Text style={{ color: '#8895b4' }}>output_data</Text>
                </Paragraph>
                <pre
                  style={{
                    margin: 0,
                    padding: 10,
                    background: 'rgba(0,0,0,0.3)',
                    borderRadius: 8,
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 12,
                    color: '#c5cee0',
                    maxHeight: 200,
                    overflow: 'auto',
                  }}
                >
                  {JSON.stringify(detail.output_data, null, 2)}
                </pre>
              </>
            )}
          </>
        )}
      </Modal>
    </div>
  );
}
