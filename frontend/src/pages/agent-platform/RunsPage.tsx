import { useCallback, useEffect, useMemo, useReducer, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Drawer,
  Flex,
  Progress,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  EyeOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { agentPlatformService } from '../../services/agentPlatform.service';
import { useAgentStream } from '../../hooks/useAgentStream';
import type { AgentPlatformEvent, AgentRun, RunStatus } from './types';
import { initialTimelineState, reduceTimeline } from './timelineReducer';
import { PlatformPageHeader, RunTimelinePanel } from './components';

const { Text } = Typography;

const statusMeta: Record<RunStatus, { label: string; color: string }> = {
  queued: { label: '排队中', color: 'default' },
  running: { label: '运行中', color: 'processing' },
  awaiting_approval: { label: '等待审批', color: 'gold' },
  paused: { label: '已暂停', color: 'warning' },
  needs_review: { label: '需要复核', color: 'orange' },
  completed: { label: '已完成', color: 'success' },
  failed: { label: '失败', color: 'error' },
  cancelled: { label: '已取消', color: 'default' },
};

export default function RunsPage() {
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<RunStatus | 'all'>('all');
  const [kind, setKind] = useState<AgentRun['kind'] | 'all'>('all');
  const [selected, setSelected] = useState<AgentRun | null>(null);
  const [timeline, dispatch] = useReducer(
    (state: ReturnType<typeof initialTimelineState>, event: AgentPlatformEvent | null) =>
      event ? reduceTimeline(state, event) : initialTimelineState(),
    undefined,
    initialTimelineState,
  );
  const stream = useAgentStream(selected?.id ?? null, dispatch);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRuns(await agentPlatformService.listRuns({
        status: status === 'all' ? undefined : status,
        kind: kind === 'all' ? undefined : kind,
      }));
    } catch (error) {
      message.error(error instanceof Error ? error.message : '加载运行记录失败');
    } finally {
      setLoading(false);
    }
  }, [kind, status]);

  useEffect(() => { void load(); }, [load]);

  const control = async (run: AgentRun, action: 'cancel' | 'pause' | 'resume' | 'retry') => {
    try {
      const updated = await agentPlatformService.controlRun(run.id, action);
      setRuns((current) => current.map((item) => item.id === updated.id ? updated : item));
      setSelected((current) => current?.id === updated.id ? updated : current);
      message.success(`Run ${action} 操作已提交`);
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Run 操作失败');
    }
  };

  const stats = useMemo(() => ({
    total: runs.length,
    active: runs.filter((run) => ['queued', 'running', 'paused', 'awaiting_approval'].includes(run.status)).length,
    failed: runs.filter((run) => run.status === 'failed' || run.status === 'needs_review').length,
  }), [runs]);

  const columns: ColumnsType<AgentRun> = [
    { title: 'Run', dataIndex: 'id', render: (value) => <Text code>{value}</Text> },
    { title: '类型', dataIndex: 'kind', render: (value) => <Tag>{value}</Tag> },
    { title: '目标', dataIndex: 'goal', ellipsis: true, render: (value) => value || '-' },
    {
      title: '状态',
      dataIndex: 'status',
      render: (value: RunStatus) => <Tag color={statusMeta[value]?.color}>{statusMeta[value]?.label ?? value}</Tag>,
    },
    {
      title: '进度',
      render: (_, run) => (
        <div style={{ minWidth: 140 }}>
          <Progress percent={run.progress ?? 0} size="small" status={run.status === 'failed' ? 'exception' : run.status === 'completed' ? 'success' : 'active'} />
          <Text type="secondary">{run.current_step ?? 0} / {run.total_steps ?? 0} 步</Text>
        </div>
      ),
    },
    { title: '开始时间', dataIndex: 'started_at', render: (value) => value ? new Date(value).toLocaleString() : '-' },
    {
      title: '操作',
      width: 280,
      render: (_, run) => (
        <Space size={4}>
          <Button size="small" icon={<EyeOutlined />} onClick={() => { dispatch(null); setSelected(run); }}>详情</Button>
          {run.kind === 'job' && run.status === 'running' ? <Button size="small" icon={<PauseCircleOutlined />} onClick={() => void control(run, 'pause')}>暂停</Button> : null}
          {run.status === 'paused' ? <Button size="small" type="primary" icon={<PlayCircleOutlined />} onClick={() => void control(run, 'resume')}>恢复</Button> : null}
          {['queued', 'running', 'awaiting_approval', 'paused'].includes(run.status) ? <Button size="small" danger icon={<StopOutlined />} onClick={() => void control(run, 'cancel')}>取消</Button> : null}
          {['failed', 'needs_review'].includes(run.status) ? <Button size="small" onClick={() => void control(run, 'retry')}>重试</Button> : null}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <PlatformPageHeader
        title="运行中心"
        subtitle="统一查看 chat、job、eval、discovery 与 deployment Run"
        extra={<Button icon={<ReloadOutlined />} loading={loading} onClick={() => void load()}>刷新</Button>}
      />
      <Flex gap={12} style={{ marginBottom: 12 }}>
        <Card size="small"><Text type="secondary">当前结果</Text><div style={{ fontSize: 24 }}>{stats.total}</div></Card>
        <Card size="small"><Text type="secondary">活跃</Text><div style={{ fontSize: 24 }}>{stats.active}</div></Card>
        <Card size="small"><Text type="secondary">异常/复核</Text><div style={{ fontSize: 24 }}>{stats.failed}</div></Card>
        <Card size="small" style={{ flex: 1 }}>
          <Space wrap>
            <Text>类型</Text>
            <Select value={kind} style={{ width: 150 }} onChange={setKind} options={['all', 'chat', 'job', 'eval', 'discovery', 'deployment'].map((value) => ({ value, label: value === 'all' ? '全部' : value }))} />
            <Text>状态</Text>
            <Select value={status} style={{ width: 150 }} onChange={setStatus} options={['all', ...Object.keys(statusMeta)].map((value) => ({ value, label: value === 'all' ? '全部' : statusMeta[value as RunStatus].label }))} />
          </Space>
        </Card>
      </Flex>
      <Table rowKey="id" loading={loading} columns={columns} dataSource={runs} scroll={{ x: 1100 }} />
      <Drawer width={720} open={Boolean(selected)} title={selected ? `Run ${selected.id}` : ''} onClose={() => setSelected(null)}>
        {selected?.error_message ? <Alert type="error" showIcon message={selected.error_message} style={{ marginBottom: 12 }} /> : null}
        <RunTimelinePanel entries={timeline.entries} connectionState={stream.state} error={stream.error} />
      </Drawer>
    </div>
  );
}
